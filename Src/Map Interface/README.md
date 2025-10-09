# Streamlit-folium Interactive Data Atlas

This Streamlit-folium application provides an interactive map interface for visualizing and exploring geological samples across Australia.
It connects to a PostgreSQL + PostGIS database, displays sample locations on a folium map, and allows users to explore details, images, and references for each sample. The intended database schema can be found under this repository.

The app supports filtering samples by date and equipment type, dynamically displaying markers and detailed information for selected samples, including automatic TIFF-to-JPEG image conversion for display compatibility.

# Requirements
Python 3.9 or newer is required, along with the following libraries.
- streamlit
- streamlit-folium
- folium
- sqlalchemy
- psycopg2-binary
- pillow

These can be installed using:

`pip install streamlit streamlit-folium folium sqlalchemy psycopg2-binary pandas pillow requests`

# Setup Instructions
The current setup is configured for default localhost PostgreSQL databases. The setup can be found at the start of the code in map.py, and should be modified to connect to your hosted database.

After setting up, the app can be run with the following:

`streamlit run app.py`

## Deployed Application
In the future, the database should be remotely hosted and the streamlit application can be deployed and hosted online.
