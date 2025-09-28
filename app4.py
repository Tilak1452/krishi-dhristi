import streamlit as st
import folium
from folium import LayerControl
from streamlit_folium import st_folium
from folium.plugins import Draw, Geocoder
import numpy as np
import plotly.graph_objects as go
from PIL import Image
import io
import time
from datetime import datetime, timedelta
import random
import base64

# --- 1. APP CONFIGURATION ---
st.set_page_config(
    page_title="Krishi-Drishti",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CUSTOM STYLING (CSS Injection) ---
# This CSS enhances the visual appeal with a dark theme and card-like containers.
st.markdown("""
<style>
    /* Main app background */
    .stApp {
        background-color: #0f1116;
        color: white; /* Ensure text is visible on dark background */
    }
    
    /* Headers and subheaders for better contrast */
    h1, h2, h3, h4, h5, h6 {
        color: #e0e0e0;
    }

    /* Card-like containers */
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"],
    .st-emotion-cache-nahz7x { /* Targeting direct st.container(border=True) */
        border: 1px solid rgba(255, 255, 255, 0.2);
        background-color: #161a25;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
        margin-bottom: 15px; /* Add some space between cards */
    }
    
    /* Primary button hover effect */
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #00b359;
        color: white;
        border-color: #00b359;
    }

    /* Adjust sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #161a25;
        color: white;
    }
    [data-testid="stSidebar"] .stButton > button {
        background-color: #333945; /* Darker button for sidebar */
        color: white;
        border: 1px solid #4a515f;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #4a515f;
        border-color: #6a7385;
    }

    /* Info, Success, Warning, Error boxes */
    .stAlert {
        border-radius: 8px;
        font-weight: bold;
    }
    .stAlert.info { background-color: rgba(51, 187, 255, 0.1); color: #33bbff; border-color: #33bbff; }
    .stAlert.success { background-color: rgba(44, 160, 44, 0.1); color: #2ca02c; border-color: #2ca02c; }
    .stAlert.warning { background-color: rgba(255, 127, 14, 0.1); color: #ff7f0e; border-color: #ff7f0e; }
    .stAlert.error { background-color: rgba(214, 39, 40, 0.1); color: #d62728; border-color: #d62728; }

    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #212630;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 10px;
        color: #e0e0e0;
    }
    .streamlit-expanderContent {
        background-color: #161a25;
        border-radius: 0 0 8px 8px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-top: none;
        padding: 15px;
    }

</style>
""", unsafe_allow_html=True)


# --- 3. SESSION STATE INITIALIZATION ---
if 'view_state' not in st.session_state:
    st.session_state.view_state = 'initial'
if 'drawn_aoi' not in st.session_state:
    st.session_state.drawn_aoi = None
if 'mock_data' not in st.session_state:
    st.session_state.mock_data = None

# --- 4. BACKEND SIMULATION & DATA GENERATION ---

# Define anomaly types and their example detection descriptions/colors
ANOMALY_TYPES = {
    "Double Plant": {"color": "#FFD700", "description": "High density planting, potentially impacting yield and resource competition.", "pattern_shape": "rectangle"},
    "Drydown": {"color": "#8B4513", "description": "Area showing signs of severe water stress or maturation, check irrigation.", "pattern_shape": "polygon"},
    "Endrow": {"color": "#00CED1", "description": "Irregular planting or stress detected at the end of rows. Could be due to turns or machinery issues.", "pattern_shape": "polygon"},
    "Nutrient Deficiency": {"color": "#A0522D", "description": "Area indicating lack of essential nutrients. Consider soil testing.", "pattern_shape": "rectangle"},
    "Planter Skip": {"color": "#DC143C", "description": "Gaps in planting due to planter malfunction. May lead to yield loss.", "pattern_shape": "rectangle"},
    "Water Accumulation": {"color": "#4682B4", "description": "Ponding or waterlogged area. Can cause root damage and disease.", "pattern_shape": "polygon"}
}

def generate_mock_data(aoi):
    """Generates realistic mock data for the dashboard, now including anomalies."""
    severe_pct = np.random.randint(5, 25)
    stressed_pct = np.random.randint(10, 30)
    healthy_pct = 100 - severe_pct - stressed_pct
    
    # Simulate anomaly detection
    detected_anomaly = None
    if random.random() < 0.7: # 70% chance to detect an anomaly
        anomaly_name = random.choice(list(ANOMALY_TYPES.keys()))
        anomaly_info = ANOMALY_TYPES[anomaly_name]
        
        # Generate a random, simple polygon/rectangle within the AOI for the anomaly
        aoi_coords = aoi['coordinates'][0]
        lons = [c[0] for c in aoi_coords]
        lats = [c[1] for c in aoi_coords]
        
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)
        
        center_lon = (min_lon + max_lon) / 2
        center_lat = (min_lat + max_lat) / 2
        
        lon_span = (max_lon - min_lon) * 0.1
        lat_span = (max_lat - min_lat) * 0.1
        
        offset_lon = random.uniform(-lon_span, lon_span)
        offset_lat = random.uniform(-lat_span, lat_span)

        anomaly_lon = center_lon + offset_lon
        anomaly_lat = center_lat + offset_lat
        
        if anomaly_info["pattern_shape"] == "rectangle":
            anomaly_polygon = [
                (anomaly_lon - lon_span/2, anomaly_lat - lat_span/2),
                (anomaly_lon + lon_span/2, anomaly_lat - lat_span/2),
                (anomaly_lon + lon_span/2, anomaly_lat + lat_span/2),
                (anomaly_lon - lon_span/2, anomaly_lat + lat_span/2),
                (anomaly_lon - lon_span/2, anomaly_lat - lat_span/2)
            ]
        else: # Simple polygon
             anomaly_polygon = [
                (anomaly_lon, anomaly_lat + lat_span/2),
                (anomaly_lon + lon_span/2, anomaly_lat - lat_span/4),
                (anomaly_lon - lon_span/2, anomaly_lat - lat_span/4),
                (anomaly_lon, anomaly_lat + lat_span/2)
            ]

        detected_anomaly = {
            "type": anomaly_name,
            "description": anomaly_info["description"],
            "color": anomaly_info["color"],
            "coordinates": anomaly_polygon
        }

    return {
        "stress_map_array": np.random.choice([0, 1, 2], size=(100, 100), p=[healthy_pct/100, stressed_pct/100, severe_pct/100]),
        "health_distribution": {'Healthy': healthy_pct, 'Stressed': stressed_pct, 'Severe': severe_pct},
        "ndvi_hist": sorted(np.random.uniform(0.55, 0.75, 12).tolist()),
        "ndvi_pred": sorted(np.random.uniform(0.45, 0.7, 14).tolist(), reverse=random.choice([True, False])),
        "soil_moisture_hist": np.random.uniform(20, 45, 30).tolist(),
        "temperature_hist": np.random.uniform(25, 40, 30).tolist(), # <-- ADDED TEMPERATURE DATA
        "dates": [(datetime.now().date() - timedelta(days=i)) for i in range(30)][::-1],
        "aoi_bounds": get_aoi_bounds(aoi['coordinates'][0]),
        "detected_anomaly": detected_anomaly
    }

def get_aoi_bounds(coords):
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]

# --- 5. DASHBOARD COMPONENTS ---
def display_spectral_health_map(stress_array, bounds, aoi_coords, detected_anomaly=None):
    map_center = [np.mean([p[1] for p in aoi_coords]), np.mean([p[0] for p in aoi_coords])]
    health_map = folium.Map(location=map_center, zoom_start=16, tiles="CartoDB dark_matter", attr="CartoDB")
    
    colormap = np.array([[0, 128, 0, 180], [255, 255, 0, 180], [255, 0, 0, 180]], dtype=np.uint8)
    colored_array = colormap[stress_array]
    img = Image.fromarray(colored_array, 'RGBA')
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    image_url = f'data:image/png;base64,{image_base64}'
    
    folium.raster_layers.ImageOverlay(
        image=image_url, bounds=bounds, opacity=0.7, name='Spectral Health Map'
    ).add_to(health_map)
    
    folium.Polygon(
        locations=[(lat, lon) for lon, lat in aoi_coords], color='#33bbff', 
        weight=3, fill=False, tooltip="Your Farm Boundary"
    ).add_to(health_map)

    if detected_anomaly:
        anomaly_folium_coords = [(c[1], c[0]) for c in detected_anomaly['coordinates']]
        folium.Polygon(
            locations=anomaly_folium_coords, color=detected_anomaly['color'], weight=4,
            fill=True, fill_color=detected_anomaly['color'], fill_opacity=0.4,
            tooltip=f"Anomaly Detected: {detected_anomaly['type']}"
        ).add_to(health_map)
        folium.Marker(
            location=anomaly_folium_coords[0],
            icon=folium.Icon(color='red', icon='exclamation-triangle', prefix='fa'),
            tooltip=f"Anomaly: {detected_anomaly['type']}"
        ).add_to(health_map)

    st_folium(health_map, width="100%", height=500, returned_objects=[])

def create_temporal_trend_chart(hist_data, pred_data):
    fig = go.Figure()
    hist_len = len(hist_data)
    
    fig.add_trace(go.Scatter(x=list(range(hist_len)), y=hist_data, mode='lines+markers', name='Historical NDVI', line=dict(color='#33bbff', width=3)))
    fig.add_trace(go.Scatter(x=list(range(hist_len - 1, hist_len + len(pred_data))), y=[hist_data[-1]] + pred_data, mode='lines', name='14-Day Forecast', line=dict(color='#ff6a6a', dash='dash', width=3)))
    
    fig.update_layout(
        title_text='<b>Crop Health Forecast (NDVI)</b>',
        xaxis_title='Time', yaxis_title='NDVI Value',
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(0,0,0,0.5)', bordercolor='white', borderwidth=1),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white')
    )
    return fig

def display_anomaly_alert_system(forecast, health_dist, detected_anomaly=None):
    if detected_anomaly:
        st.error(f"🚨 **Pattern Detected: {detected_anomaly['type']}!**", icon="🔎")
        st.markdown(f"**Description:** {detected_anomaly['description']}")
        st.markdown(f"**Recommended Action:** Investigate the highlighted area on the map immediately.")
        st.markdown("---")

    is_declining = forecast[-1] < forecast[0]
    is_severe = health_dist.get('Severe', 0) > 20
    
    if is_severe:
        st.error(f"‼️ **Action Required:** {health_dist['Severe']}% of your farm shows significant stress. Investigate the highlighted red zones immediately.", icon="🚨")
    elif is_declining:
        st.warning("⚠️ **Early Warning:** Crop health is predicted to decline. Check irrigation and nutrient levels.", icon="📉")
    else:
        st.success("✅ **All Clear:** Your farm is healthy and the forecast is stable.", icon="👍")

def create_soil_condition_chart(dates, moisture_data):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=moisture_data, mode='lines', fill='tozeroy', name='Soil Moisture', line=dict(color='#966919', width=2)))
    fig.update_layout(
        title_text='<b>Historical Soil Moisture</b>',
        xaxis_title='Date', yaxis_title='Soil Moisture Level',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white')
    )
    return fig

# --- NEW FUNCTION FOR TEMPERATURE CHART ---
def create_temperature_chart(dates, temp_data):
    """Creates a themed Plotly line chart for temperature."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=temp_data, mode='lines', name='Temperature', line=dict(color='#FF5733', width=2)))
    fig.update_layout(
        title_text='<b>Historical Temperature</b>',
        xaxis_title='Date', yaxis_title='Temperature (°C)',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white')
    )
    return fig

# --- 6. STREAMLIT APP LAYOUT ---

# --- SIDEBAR ---
with st.sidebar:
    st.title("🌾 Krishi-Drishti")
    st.markdown("---")

    with st.container(border=True):
        st.header("How to Use")
        st.markdown("""
        1. **Find your farm** using the search bar.
        2. **Draw the boundary** using the polygon tool.
        3. **Select a date range** for analysis.
        4. Click **Analyze Farm**.
        """)
    
    st.header("Define Your Query")
    date_range = st.date_input(
        "Select a date range",
        (datetime.now().date() - timedelta(days=30), datetime.now().date())
    )
    
    if st.button("Analyze Farm", type="primary", use_container_width=True):
        if st.session_state.drawn_aoi:
            with st.spinner("🛰️ Fetching satellite data & running analysis..."):
                time.sleep(1.5)
                st.session_state.mock_data = generate_mock_data(st.session_state.drawn_aoi)
                time.sleep(1.5)
            st.session_state.view_state = 'dashboard'
            st.rerun()
        else:
            st.error("Please draw a farm boundary on the map first.")
            
    if st.session_state.view_state == 'dashboard':
        st.markdown("---")
        if st.button("Start New Analysis", use_container_width=True):
            st.session_state.view_state = 'initial'
            st.session_state.drawn_aoi = None
            st.session_state.mock_data = None
            st.rerun()

# --- MAIN PANEL ---
st.header("Krishi-Drishti: AI-Powered Farm Analysis")
st.markdown("---")

# --- INITIAL VIEW ---
if st.session_state.view_state == 'initial':
    st.info("🎯 **Get Started:** Draw your farm boundary using the polygon tool 툴 on the map.", icon="🗺️")
    
    initial_map = folium.Map(location=[22.3, 73.1], zoom_start=12, tiles="CartoDB dark_matter", attr="CartoDB")
    
    folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite').add_to(initial_map)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Google Hybrid').add_to(initial_map)
    
    Geocoder(collapsed=False, position='topleft', add_marker=False).add_to(initial_map)
    Draw(
        export=False,
        draw_options={'polyline': False, 'marker': False, 'circlemarker': False, 'circle': False, 'polygon': {'shapeOptions': {'color': '#33bbff'}}}
    ).add_to(initial_map)
    LayerControl().add_to(initial_map)
    
    map_output = st_folium(initial_map, width="100%", height=600)
    
    if map_output and map_output.get("all_drawings"):
        if map_output["all_drawings"]:
            st.session_state.drawn_aoi = map_output["all_drawings"][0]['geometry']
            st.success("✅ Farm boundary captured! Click 'Analyze Farm' in the sidebar to proceed.")

# --- DASHBOARD VIEW ---
elif st.session_state.view_state == 'dashboard':
    data = st.session_state.mock_data
    
    col1, col2 = st.columns([3, 2], gap="large")
    
    with col1:
        with st.container(border=True):
            st.subheader("📍 Spectral Health Map & Anomaly Finder")
            display_spectral_health_map(data['stress_map_array'], data['aoi_bounds'], st.session_state.drawn_aoi['coordinates'][0], data['detected_anomaly'])
    
    with col2:
        with st.container(border=True):
            st.subheader("💡 Key Insights & Alerts")
            display_anomaly_alert_system(data['ndvi_pred'], data['health_distribution'], data['detected_anomaly'])
            
            yield_val = float(np.mean(data['ndvi_hist']) * 6.5)
            st.metric(label="Estimated Yield", value=f"{yield_val:.2f} Tonnes/Hectare", delta=f"{(yield_val - 4.5):.2f} vs. avg")
            
            pie_fig = go.Figure(data=[go.Pie(
                labels=list(data['health_distribution'].keys()), 
                values=list(data['health_distribution'].values()), 
                hole=.4, marker_colors=['#2ca02c', '#ff7f0e', '#d62728'],
                pull=[0, 0, 0.1]
            )])
            pie_fig.update_layout(
                title_text='<b>Farm Health Distribution</b>', showlegend=True, height=280, 
                margin=dict(t=50, b=10, l=10, r=10),
                paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white')
            )
            st.plotly_chart(pie_fig, use_container_width=True)

    st.markdown("---")
    
    with st.container(border=True):
        st.subheader("📈 Temporal Analytics")
        st.plotly_chart(create_temporal_trend_chart(data['ndvi_hist'], data['ndvi_pred']), use_container_width=True)
    
        with st.expander("View Environmental Data"):
            # --- UPDATED TO DISPLAY CHARTS SIDE-BY-SIDE ---
            env_col1, env_col2 = st.columns(2)
            with env_col1:
                st.plotly_chart(create_soil_condition_chart(data['dates'], data['soil_moisture_hist']), use_container_width=True)
            with env_col2:
                st.plotly_chart(create_temperature_chart(data['dates'], data['temperature_hist']), use_container_width=True)