import streamlit as st
from streamlit_folium import st_folium
import folium
from sqlalchemy import create_engine, text
import pandas as pd
from PIL import Image
from io import BytesIO
import tempfile
import os
import requests 
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# --- TIFF Conversion Function ---
# This function converts a TIFF file (from a local path) to a temporary JPEG file
@st.cache_data(show_spinner=False)
def convert_tiff_to_jpeg(tiff_url, image_id):
    """
    Downloads a TIFF image from a remote URL, converts it to JPEG in memory,
    and returns the path to the temporary JPEG file.
    """
    # 1. Download the TIFF image data
    try:
        response = requests.get(tiff_url, timeout=10) # Set a timeout for safety
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        image_data = response.content
    except requests.exceptions.RequestException as e:
        st.error(f"Error downloading TIFF from URL: {tiff_url}. Error: {e}")
        return None

    try:
        # 2. Open the image from the in-memory binary data
        img = Image.open(BytesIO(image_data))
        
        # 3. Create a temporary file path for the JPEG output
        temp_dir = tempfile.gettempdir()
        temp_jpeg_path = os.path.join(temp_dir, f"temp_img_{image_id}.jpeg")

        # 4. Convert and save as JPEG
        img.convert('RGB').save(temp_jpeg_path, 'jpeg', quality=85)
        
        return temp_jpeg_path
    
    except Exception as e:
        st.error(f"Error processing TIFF image data: {e}")
        return None


def load_data():
    with engine.connect() as conn:
        samples = pd.read_sql("""
            SELECT 
                id AS sample_id,
                sample_name AS name,
                description AS desc,
                sample_image_url,
                ST_Y(origin::geometry) AS lat,
                ST_X(origin::geometry) AS lon,
                date_collected::date AS date
            FROM Sample
        """, conn)
        samples['date'] = pd.to_datetime(samples['date']).dt.date

        sample_images = pd.read_sql("""
            SELECT 
                si.id AS image_id,
                si.sample_id,
                si.image_url AS path,
                si.caption,
                e.name AS equipment,
                e.type AS etype,
                si.date_obtained::date AS date
            FROM SampleImage si
            LEFT JOIN Equipment e ON si.equipment_id = e.id
        """, conn)
        sample_images['date'] = pd.to_datetime(sample_images['date']).dt.date

        references = pd.read_sql("""
            SELECT 
                r.sample_id,
                d.document_name AS name,
                d.document_url AS link
            FROM Reference r
            JOIN Document d ON r.document_id = d.document_id
        """, conn)

    return samples, sample_images, references


samples_df, sample_images_df, references_df = load_data()



# -------------------------------
# Streamlit Layout
# -------------------------------
st.set_page_config(layout="wide")
st.title("Geological Samples Map (with Filters)")

# Keep state of selected sample
if "selected_sample" not in st.session_state:
    st.session_state.selected_sample = None

# -------------------------------
# Sidebar Filters
# -------------------------------
st.sidebar.header("Filters")

# Correctly extract unique dates and equipment types from DataFrames
all_dates = samples_df['date'].unique()
min_date, max_date = samples_df['date'].min(), samples_df['date'].max()
all_types = sorted(sample_images_df['etype'].dropna().unique())

if "date_range" not in st.session_state:
    st.session_state.date_range = [min_date, max_date]
if "eq_type_filter" not in st.session_state:
    st.session_state.eq_type_filter = all_types

# Reset button
if st.sidebar.button("Reset Filters"):
    st.session_state.date_range = [min_date, max_date]
    st.session_state.eq_type_filter = all_types


date_range = st.sidebar.date_input("Date range", st.session_state.date_range)
# Ensure date_range is a list of date objects for correct filtering later
if isinstance(date_range, tuple):
    date_range = list(date_range)

eq_type_filter = st.sidebar.multiselect("Equipment type", all_types, default=st.session_state.eq_type_filter)

st.session_state.date_range = date_range
st.session_state.eq_type_filter = eq_type_filter

# -------------------------------
# Apply Filters (using Pandas for efficiency)
# -------------------------------

# 1. Filter by Date
if len(date_range) == 2:
    start_date = date_range[0]
    end_date = date_range[1]
    date_filtered_samples_df = samples_df[
        (samples_df['date'] >= start_date) & 
        (samples_df['date'] <= end_date)
    ]
else:
    date_filtered_samples_df = samples_df.copy()

# 2. Filter by Equipment Type
if eq_type_filter:
    # Get a list of sample_ids that have at least one image with the selected equipment type
    valid_sample_ids = sample_images_df[
        sample_images_df['etype'].isin(eq_type_filter)
    ]['sample_id'].unique()
    
    # Filter the date-filtered samples by these valid IDs
    filtered_samples_df = date_filtered_samples_df[
        date_filtered_samples_df['sample_id'].isin(valid_sample_ids)
    ]
else:
    # If no equipment type filter, use the date-filtered samples
    filtered_samples_df = date_filtered_samples_df

# Convert to list of dicts for simpler iteration in the map section
filtered_samples = filtered_samples_df.to_dict('records')


# -------------------------------
# Map
# -------------------------------
australia_bounds = [[-44.0, 112.0], [-10.0, 154.0]]

m = folium.Map(tiles="Cartodb Positron")
m.fit_bounds(australia_bounds)



for s in filtered_samples:
    # Use tooltip as a clean identifier
    folium.Marker(
        [s['lat'], s['lon']],
        tooltip=f"""
        Name: {s['name']}; SampleID: {s['sample_id']}
        """
    ).add_to(m)

map_data = st_folium(m, width=1050, height=600)

st.divider()

# -------------------------------
# Details Panel
# -------------------------------
sid = None # Initialize sid

if map_data and map_data.get("last_object_clicked_tooltip"):
    tmp_tt = map_data["last_object_clicked_tooltip"]
    # Extract the SampleID from the tooltip string
    try:
        # Find the part that contains "SampleID: X" and extract X
        sample_id_part = tmp_tt.split(';')[1].strip()
        sid = int(sample_id_part.removeprefix("SampleID: "))
    except (IndexError, ValueError):
        sid = None # Handle cases where extraction fails
        
    st.session_state.selected_sample = sid

if st.session_state.selected_sample is not None:
    sid = st.session_state.selected_sample
    
    # Retrieve the selected sample's details
    sample_row = samples_df[samples_df['sample_id'] == sid]

    if not sample_row.empty:
        # Convert row to dictionary for easy access, should only be one row
        sample = sample_row.iloc[0].to_dict() 
        

        st.header(f"{sample['name']} (SampleID : {sample['sample_id']})")
        if sample['sample_image_url']:
            if sample['sample_image_url'].lower().endswith(('.tif', '.tiff')):
                # Convert TIFF to JPEG and use the temporary path
                display_path = convert_tiff_to_jpeg(sample['sample_image_url'], f"sample_{sid}")
            if display_path:
                st.image(display_path, use_container_width ='auto')
        st.write(f"**Description:** {sample['desc']}")
        st.write(f"**Collected on:** {sample['date']}")

        # Get images for the selected sample
        images_df = sample_images_df[sample_images_df['sample_id'] == sid]

        with st.expander("**Images**"):
            if not images_df.empty:
                eq_types = sorted(images_df['etype'].dropna().unique())
                eq_filter = st.selectbox("Filter by equipment type", ["All"] + eq_types, key=f"image_filter_{sid}")

                # Filter images by selected equipment type
                if eq_filter != "All":
                    filtered_images_df = images_df[images_df['etype'] == eq_filter]
                else:
                    filtered_images_df = images_df
                
                # Iterate over the filtered images DataFrame
                for _, img in filtered_images_df.iterrows():

                    # --- TIFF HANDLING LOGIC ---
                    if img["path"].lower().endswith(('.tif', '.tiff')):
                        # Convert TIFF to JPEG and use the temporary path
                        display_path = convert_tiff_to_jpeg(img["path"], img["image_id"])
                        if display_path:
                            st.image(
                                display_path,
                                caption=f"{img['caption']} (Equipment: {img['equipment']}, Type: {img['etype']}, Date: {img['date']}) - Converted from TIFF"
                            )
                    else:
                        # Display non-TIFF images directly
                        st.image(
                            img["path"],
                            caption=f"{img['caption']} (Equipment: {img['equipment']}, Type: {img['etype']}, Date: {img['date']})"
                        )
                    # --- END TIFF HANDLING LOGIC ---
            else:
                st.write("No images available for this sample.")


        # Get references for the selected sample
        refs_df = references_df[references_df['sample_id'] == sid]

        with st.expander("**References**"):
            if not refs_df.empty:
                for _, ref in refs_df.iterrows():
                    st.markdown(f"- [{ref['name']}]({ref['link']})")
            else:
                st.write("No references available.")

    else:
        # This handles a case where a previously selected sample is filtered out
        st.session_state.selected_sample = None
        st.info("The selected sample is no longer visible due to the current filters.")
else:
    st.info("Click a marker on the map to see sample details.")