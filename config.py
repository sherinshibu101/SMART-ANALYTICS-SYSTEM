import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# InfluxDB Configuration
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "")
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "https://us-east-1-1.aws.cloud2.influxdata.com")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "smart_energy")

# Backend Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))

# Simulator Configuration
SIMULATION_INTERVAL_SECONDS = int(os.getenv("SIMULATION_INTERVAL_SECONDS", 300))
HOUSEHOLDS_COUNT = int(os.getenv("HOUSEHOLDS_COUNT", 5))

# Dashboard Configuration
DASHBOARD_REFRESH_INTERVAL = int(os.getenv("DASHBOARD_REFRESH_INTERVAL", 10))

# Constants
APPLIANCE_TYPES = ["AC", "Refrigerator", "Washing Machine", "Lights", "Water Heater"]
REGIONS = ["North", "South", "East", "West", "Central"]

# Anomaly Detection Thresholds
ANOMALY_THRESHOLD_SPIKE = 1.8  # 1.8x average usage
ANOMALY_THRESHOLD_DAILY = 1.3  # 1.3x 7-day average
