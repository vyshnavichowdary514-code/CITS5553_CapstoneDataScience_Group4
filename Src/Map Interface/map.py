import streamlit as st
from streamlit_folium import st_folium
import folium
import datetime

# -------------------------------
# Mock Data
# -------------------------------
samples = [
    {"SampleID": 1, "name": "Granite A", "desc": "Coarse-grained granite", "lat": -33.87, "lon": 151.21, "date": "2023-05-01"},
    {"SampleID": 2, "name": "Basalt B", "desc": "Dark volcanic rock", "lat": -37.81, "lon": 144.96, "date": "2023-05-02"},
    {"SampleID": 3, "name": "Limestone C", "desc": "Fossiliferous limestone", "lat": -31.95, "lon": 115.86, "date": "2023-05-03"},
    {"SampleID": 4, "name": "Shale D", "desc": "Fine-grained shale", "lat": -34.93, "lon": 138.60, "date": "2023-05-04"},
    {"SampleID": 5, "name": "Sandstone E", "desc": "Cross-bedded sandstone", "lat": -27.47, "lon": 153.03, "date": "2023-05-05"},
    {"SampleID": 6, "name": "Gabbro F", "desc": "Coarse dark gabbro", "lat": -12.46, "lon": 130.84, "date": "2023-05-06"},
    {"SampleID": 7, "name": "Marble G", "desc": "Metamorphic marble", "lat": -42.88, "lon": 147.32, "date": "2023-05-07"},
    {"SampleID": 8, "name": "Quartzite H", "desc": "Hard quartzite", "lat": -23.70, "lon": 133.87, "date": "2023-05-08"},
    {"SampleID": 9, "name": "Coal I", "desc": "Black coal seam", "lat": -32.93, "lon": 151.78, "date": "2023-05-09"},
    {"SampleID": 10, "name": "Chert J", "desc": "Siliceous chert", "lat": -35.28, "lon": 149.13, "date": "2023-05-10"},
]

sample_images = {
    1: [
        {"path": "https://i.postimg.cc/SQWvDQKL/TEST-FIB.png", "caption": "SEM Caption 1", "equipment": "Camera X", "etype": "FIB"},
        {"path": "https://i.postimg.cc/C5Hr172r/TEST-SEM.png", "caption": "Thin section under microscope", "equipment": "Microscope A", "etype": "SEM"},
        {"path": "https://i.postimg.cc/JnX2wM5L/TEST-EPMA.png", "caption": "Outcrop photo", "equipment": "Drone 1", "etype": "EPMA"},
    ],
    2: [{"path": "https://i.postimg.cc/JnX2wM5L/TEST-EPMA.png", "caption": "Thin section under microscope", "equipment": "Microscope A", "etype": "EPMA"}],
    3: [{"path": "https://i.postimg.cc/7hyQwdKT/TEST-TEM.png", "caption": "Outcrop photo", "equipment": "Drone 1", "etype": "TEM"}],
    4: [{"path": "https://i.postimg.cc/SQWvDQKL/TEST-FIB.png", "caption": "Field image", "equipment": "Camera Y", "etype": "FIB"}],
    5: [{"path": "https://i.postimg.cc/7hyQwdKT/TEST-TEM.png", "caption": "Sample closeup", "equipment": "Microscope B", "etype": "TEM"}],
    6: [{"path": "https://i.postimg.cc/SQWvDQKL/TEST-FIB.png", "caption": "Thin section image", "equipment": "Microscope A", "etype": "FIB"}],
    7: [{"path": "https://i.postimg.cc/C5Hr172r/TEST-SEM.png", "caption": "Outcrop overview", "equipment": "Drone 2", "etype": "SEM"}],
    8: [{"path": "https://i.postimg.cc/C5Hr172r/TEST-SEM.png", "caption": "Sample detail", "equipment": "Camera Z", "etype": "SEM"}],
    9: [{"path": "https://i.postimg.cc/SQWvDQKL/TEST-FIB.png", "caption": "Coal face", "equipment": "Camera X", "etype": "FIB"}],
    10: [{"path": "https://i.postimg.cc/C5Hr172r/TEST-SEM.png", "caption": "Sample fracture surface", "equipment": "Microscope C", "etype": "SEM"}],
}

references = {
    1: [{"name": "Granite study 2021", "link": "https://example.com/granite"}],
    2: [{"name": "Basalt volcanism 2020", "link": "https://example.com/basalt"}],
    3: [{"name": "Limestone fossils 2019", "link": "https://example.com/limestone"}],
}

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

all_dates = [datetime.datetime.strptime(s["date"], "%Y-%m-%d").date() for s in samples]
min_date, max_date = min(all_dates), max(all_dates)
all_types = sorted(set(img["etype"] for imgs in sample_images.values() for img in imgs))

if "date_range" not in st.session_state:
    st.session_state.date_range = [min_date, max_date]
if "eq_type_filter" not in st.session_state:
    st.session_state.eq_type_filter = all_types

# Reset button
if st.sidebar.button("Reset Filters"):
    st.session_state.date_range = [min_date, max_date]
    st.session_state.eq_type_filter = all_types


date_range = st.sidebar.date_input("Date range", st.session_state.date_range)
eq_type_filter = st.sidebar.multiselect("Equipment type", all_types, default = st.session_state.eq_type_filter)

st.session_state.date_range = date_range
st.session_state.eq_type_filter = eq_type_filter

# -------------------------------
# Apply Filters
# -------------------------------
filtered_samples = []
for s in samples:
    s_date = datetime.datetime.strptime(s["date"], "%Y-%m-%d").date()

    # Filter by date
    if len(date_range) == 2:
        if not (date_range[0] <= s_date <= date_range[1]):
            continue

    # Filter by equipment type
    if eq_type_filter:
        imgs = sample_images.get(s["SampleID"], [])
        if not any(img["etype"] in eq_type_filter for img in imgs):
            continue


    filtered_samples.append(s)

# -------------------------------
# Map
# -------------------------------
m = folium.Map(location=[-28, 135], zoom_start=4.4)


for s in filtered_samples:

    # Use tooltip as a clean identifier
    folium.Marker(
        [s['lat'], s['lon']],
        tooltip=f"""
        Name: {s['name']}; SampleID: {s['SampleID']}
        """
    ).add_to(m)

map_data = st_folium(m, width=1050, height=600)

st.divider()

# -------------------------------
# Details Panel
# -------------------------------
if map_data and map_data.get("last_object_clicked_tooltip"):
    tmp_tt = map_data["last_object_clicked_tooltip"].split(";")[1]
    sid = int(tmp_tt.removeprefix(" SampleID: "))
    st.session_state.selected_sample = sid

if st.session_state.selected_sample:
    sid = st.session_state.selected_sample
    sample = next((s for s in filtered_samples if s["SampleID"] == sid),None)

    if sample:
        st.header(f"{sample['name']} (SampleID : {sample["SampleID"]})")
        st.write(f"**Description:**")
        st.write(f"{sample['desc']}")
        st.write(f"**Collected on:**")
        st.write(f"{sample['date']}")

        with st.expander("**Images**"):
            images = sample_images.get(sid, [])
            eq_types = sorted(set(img["etype"] for img in images))
            eq_filter = st.selectbox("Filter by equipment type", ["All"] + eq_types)

            for img in images:
                if eq_filter == "All" or img["etype"] == eq_filter:
                    st.image(
                        img["path"],
                        caption=f"{img['caption']} (Equipment: {img['equipment']}, Type: {img['etype']})"
                    )

        with st.expander("**References**"):
            refs = references.get(sid, [])
            if refs:
                for ref in refs:
                    st.markdown(f"- [{ref['name']}]({ref['link']})")
            else:
                st.write("No references available.")

    else:
        st.session_state.selected_sample = None