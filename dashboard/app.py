import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import requests
from datetime import datetime, timedelta

# Page Configuration
st.set_page_config(
    page_title="⚡ Smart Energy Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("⚡ Smart Energy Analytics Dashboard")
st.markdown("Real-time energy consumption monitoring and anomaly detection")

# Sidebar Configuration
st.sidebar.header("Configuration")
api_url = st.sidebar.text_input("API URL", value="http://localhost:8000")
household_id = st.sidebar.selectbox(
    "Select Household",
    [f"household_{i}" for i in range(1, 6)]
)
hours = st.sidebar.slider("Data Range (hours)", 1, 168, 24)

# API Functions
def fetch_health():
    try:
        response = requests.get(f"{api_url}/health")
        return response.status_code == 200
    except:
        return False

def fetch_readings(household_id, hours=24):
    try:
        response = requests.get(f"{api_url}/readings/{household_id}", params={"hours": hours})
        if response.status_code == 200:
            return response.json().get("readings", [])
        return []
    except:
        return []

def fetch_daily_consumption(household_id):
    try:
        response = requests.get(f"{api_url}/analytics/daily/{household_id}")
        if response.status_code == 200:
            return response.json().get("daily_consumption", [])
        return []
    except:
        return []

def fetch_peak_hours(household_id):
    try:
        response = requests.get(f"{api_url}/analytics/peak-hours/{household_id}")
        if response.status_code == 200:
            return response.json().get("peak_hours", [])
        return []
    except:
        return []

def fetch_alerts(household_id, hours=24):
    try:
        response = requests.get(f"{api_url}/alerts/{household_id}", params={"hours": hours})
        if response.status_code == 200:
            return response.json().get("alerts", [])
        return []
    except:
        return []

# Check API Health
if not fetch_health():
    st.error(f"⚠️ Cannot connect to API at {api_url}")
    st.info("Make sure the FastAPI backend is running: `python -m uvicorn backend.main:app --reload`")
else:
    st.success(f"✓ Connected to API")

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Household View", "🚨 Alerts"])

# TAB 1: Overview
with tab1:
    st.subheader("Dashboard Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Fetch data
    readings = fetch_readings(household_id, hours)
    daily_consumption = fetch_daily_consumption(household_id)
    alerts = fetch_alerts(household_id, hours)
    
    if readings:
        total_consumption = sum([r.get("energy_kwh", 0) for r in readings])
        avg_consumption = total_consumption / len(readings) if readings else 0
    else:
        total_consumption = 0
        avg_consumption = 0
    
    with col1:
        st.metric("Total Consumption (kWh)", f"{total_consumption:.2f}")
    
    with col2:
        st.metric("Average Usage (kWh)", f"{avg_consumption:.2f}")
    
    with col3:
        st.metric("Total Alerts", len(alerts))
    
    with col4:
        st.metric("Household ID", household_id)
    
    # Empty state
    if not readings:
        st.warning("No data available. Make sure the simulator is running.")

# TAB 2: Household View
with tab2:
    st.subheader(f"Detailed View - {household_id}")
    
    # Time Series Chart
    readings = fetch_readings(household_id, hours)
    
    if readings:
        df = pd.DataFrame(readings)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            
            fig = px.line(
                df,
                x="timestamp",
                y="energy_kwh",
                color="appliance_type",
                title="Energy Consumption Over Time",
                labels={"energy_kwh": "Energy (kWh)", "timestamp": "Time"}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Daily Consumption
    col1, col2 = st.columns(2)
    
    with col1:
        daily = fetch_daily_consumption(household_id)
        if daily:
            df_daily = pd.DataFrame(daily)
            fig = px.bar(
                df_daily,
                x="date",
                y="total_kwh",
                title="Daily Consumption",
                labels={"total_kwh": "Total (kWh)", "date": "Date"}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        peak = fetch_peak_hours(household_id)
        if peak:
            df_peak = pd.DataFrame(peak)
            fig = px.bar(
                df_peak,
                x="hour",
                y="avg_kwh",
                title="Peak Usage Hours",
                labels={"avg_kwh": "Average (kWh)", "hour": "Hour"}
            )
            st.plotly_chart(fig, use_container_width=True)

# TAB 3: Alerts
with tab3:
    st.subheader(f"Anomaly Alerts - {household_id}")
    
    alerts = fetch_alerts(household_id, hours)
    
    if alerts:
        df_alerts = pd.DataFrame(alerts)
        
        # Severity color coding
        severity_colors = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢"
        }
        
        for idx, alert in enumerate(df_alerts.itertuples(), 1):
            severity_icon = severity_colors.get(getattr(alert, "severity", "low"), "⚪")
            with st.expander(f"{severity_icon} {getattr(alert, 'reason', 'Unknown')} - {getattr(alert, 'timestamp', 'N/A')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Severity:** {getattr(alert, 'severity', 'N/A')}")
                with col2:
                    st.write(f"**Time:** {getattr(alert, 'timestamp', 'N/A')}")
    else:
        st.info("✓ No anomalies detected in the selected time range")

# Footer
st.markdown("---")
st.markdown("🔧 Smart Energy Analytics Platform | Backend: FastAPI | Database: InfluxDB | Dashboard: Streamlit")
