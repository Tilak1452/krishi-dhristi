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
)

# --- 2. SESSION STATE INITIALIZATION ---
if 'view_state' not in st.session_state:
    st.session_state.view_state = 'initial'
if 'drawn_aoi' not in st.session_state:
    st.session_state.drawn_aoi = None
if 'mock_data' not in st.session_state:
    st.session_state.mock_data = None

# --- 3. BACKEND SIMULATION & DATA GENERATION ---
def generate_mock_data(aoi):
    severe_pct = np.random.randint(5, 25)
    stressed_pct = np.random.randint(10, 30)
    healthy_pct = 100 - severe_pct - stressed_pct
    return {
        "stress_map_array": np.random.choice([0, 1, 2], size=(100, 100), p=[healthy_pct/100, stressed_pct/100, severe_pct/100]),
        "health_distribution": {'Healthy': healthy_pct, 'Stressed': stressed_pct, 'Severe': severe_pct},
        "ndvi_hist": sorted(np.random.uniform(0.55, 0.75, 12).tolist()),
        "ndvi_pred": sorted(np.random.uniform(0.45, 0.7, 14).tolist(), reverse=random.choice([True, False])),
        "soil_moisture_hist": np.random.uniform(20, 45, 30).tolist(),
        "dates": [datetime.now().date() - timedelta(days=i) for i in range(30)],
        "aoi_bounds": get_aoi_bounds(aoi['coordinates'][0])
    }

def get_aoi_bounds(coords):
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]

# --- 4. DASHBOARD COMPONENTS ---
def display_spectral_health_map(stress_array, bounds, aoi_coords):
    map_center = [np.mean([p[1] for p in aoi_coords]), np.mean([p[0] for p in aoi_coords])]
    health_map = folium.Map(location=map_center, zoom_start=16, tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", attr="Google")
    colormap = np.array([[0, 128, 0, 128], [255, 255, 0, 128], [255, 0, 0, 128]], dtype=np.uint8)
    colored_array = colormap[stress_array]
    img = Image.fromarray(colored_array, 'RGBA')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    image_url = f'data:image/png;base64,{image_base64}'
    folium.raster_layers.ImageOverlay(image=image_url, bounds=bounds, opacity=0.6, name='Spectral Health Map').add_to(health_map)
    folium.Polygon(locations=[(lat, lon) for lon, lat in aoi_coords], color='white', weight=2, fill=False, tooltip="Your Farm Boundary").add_to(health_map)
    st_folium(health_map, width="100%", height=500, returned_objects=[])

def create_temporal_trend_chart(hist_data, pred_data):
    fig = go.Figure()
    hist_len = len(hist_data)
    fig.add_trace(go.Scatter(x=list(range(hist_len)), y=hist_data, mode='lines+markers', name='Historical NDVI', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=list(range(hist_len - 1, hist_len + len(pred_data))), y=[hist_data[-1]] + pred_data, mode='lines', name='14-Day Forecast', line=dict(color='red', dash='dash')))
    fig.update_layout(title_text='<b>Crop Health Forecast (NDVI)</b>', xaxis_title='Time', yaxis_title='NDVI Value', legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.5)'))
    return fig

def display_anomaly_alert_system(forecast, health_dist):
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
    fig.add_trace(go.Scatter(x=dates, y=moisture_data, mode='lines', fill='tozeroy', name='Soil Moisture', line=dict(color='#633A0B')))
    fig.update_layout(title_text='<b>Historical Soil Moisture</b>', xaxis_title='Date', yaxis_title='Soil Moisture Level')
    return fig

# --- 5. STREAMLIT APP LAYOUT ---
with st.sidebar:
    st.title("🌾 Krishi-Drishti")
    st.info("A seamless and professional user experience.")
    st.header("How to Use")
    st.markdown("1. **Find your farm** using the search bar.\n2. **Draw the boundary** using the polygon tool.\n3. **Select a date range** for analysis.\n4. Click **Analyze Farm**.")
    st.divider()
    
    st.header("Define Your Query")
    date_range = st.date_input("Select a date range", (datetime.now().date() - timedelta(days=30), datetime.now().date()))
    
    if st.button("Analyze Farm", type="primary", use_container_width=True):
        if st.session_state.drawn_aoi:
            with st.spinner("Running analysis... Please wait."):
                st.session_state.mock_data = generate_mock_data(st.session_state.drawn_aoi)
                time.sleep(3)
            st.session_state.view_state = 'dashboard'
            st.rerun()
        else:
            st.error("Please draw a polygon on the map first.")
            
    if st.session_state.view_state == 'dashboard':
        if st.button("Start New Analysis", use_container_width=True):
            st.session_state.view_state = 'initial'
            st.session_state.drawn_aofoi = None
            st.session_state.mock_data = None
            st.rerun()

st.header("Krishi-Drishti: AI-Powered Farm Analysis")

if st.session_state.view_state == 'initial':
    st.write("Draw your farm boundary using the polygon tool 툴 on the map to get started.")
    
    initial_map = folium.Map(location=[22.3, 73.1], zoom_start=12)
    
    # Add Google Map Layers
    folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite').add_to(initial_map)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Google Hybrid').add_to(initial_map)
    
    # Add Plugins to the initial map
    folium.plugins.Geocoder(collapsed=False, position='topleft', add_marker=False).add_to(initial_map)
    folium.plugins.Draw(export=False, draw_options={'polyline': False, 'marker': False, 'circlemarker': False, 'circle': False}).add_to(initial_map)
    folium.LayerControl().add_to(initial_map)
    
    map_output = st_folium(initial_map, width="100%", height=600)
    
    if map_output and map_output.get("all_drawings"):
        st.session_state.drawn_aoi = map_output["all_drawings"][0]['geometry']
        st.success("✅ Farm boundary captured! Click 'Analyze Farm' in the sidebar to proceed.")

elif st.session_state.view_state == 'dashboard':
    data = st.session_state.mock_data
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("Spectral Health Map")
        display_spectral_health_map(data['stress_map_array'], data['aoi_bounds'], st.session_state.drawn_aoi['coordinates'][0])
    
    with col2:
        st.subheader("Key Insights")
        display_anomaly_alert_system(data['ndvi_pred'], data['health_distribution'])
        
        # Display key metric
        yield_val = float(np.mean(data['ndvi_hist']) * 6.5) # Example calculation
        st.metric(label="Estimated Yield", value=f"{yield_val:.2f} Tonnes/Hectare", delta=f"{(yield_val - 4.5):.2f} vs. avg")
        
        # Display health distribution chart
        pie_fig = go.Figure(data=[go.Pie(labels=list(data['health_distribution'].keys()), values=list(data['health_distribution'].values()), hole=.4, marker_colors=['#2ca02c', '#ff7f0e', '#d62728'])])
        pie_fig.update_layout(title_text='<b>Farm Health Distribution</b>', showlegend=True, height=250, margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(pie_fig, use_container_width=True)

    st.divider()
    
    st.subheader("Temporal Analytics")
    st.plotly_chart(create_temporal_trend_chart(data['ndvi_hist'], data['ndvi_pred']), use_container_width=True)
    
    with st.expander("View Environmental Data"):
        st.plotly_chart(create_soil_condition_chart(data['dates'], data['soil_moisture_hist']), use_container_width=True)