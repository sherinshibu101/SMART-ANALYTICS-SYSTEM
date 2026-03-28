from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List
from config import (
    INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_URL, INFLUXDB_BUCKET,
    API_HOST, API_PORT, ANOMALY_THRESHOLD_SPIKE, ANOMALY_THRESHOLD_DAILY
)

# Initialize FastAPI app
app = FastAPI(title="Smart Energy Analytics API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize InfluxDB client
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

# Data Models
class ReadingInput(BaseModel):
    household_id: str
    appliance_type: str
    region: str
    energy_kwh: float
    voltage: float
    current: float
    power_factor: float
    timestamp: str = None

class Alert(BaseModel):
    household_id: str
    severity: str
    reason: str
    timestamp: str
    current_value: float
    threshold_value: float

# Health Check
@app.get("/health")
def health_check():
    """API health check"""
    return {"status": "healthy", "service": "Smart Energy Analytics"}

# POST: Ingest readings
@app.post("/readings")
def ingest_reading(reading: ReadingInput):
    """Ingest a single energy reading into InfluxDB"""
    try:
        point = Point("energy_usage") \
            .tag("household_id", reading.household_id) \
            .tag("appliance_type", reading.appliance_type) \
            .tag("region", reading.region) \
            .field("energy_kwh", reading.energy_kwh) \
            .field("voltage", reading.voltage) \
            .field("current", reading.current) \
            .field("power_factor", reading.power_factor) \
            .time(datetime.utcnow(), write_precision="ns")
        
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
        return {"status": "success", "message": "Reading ingested"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# GET: Retrieve readings for a household
@app.get("/readings/{household_id}")
def get_readings(household_id: str, hours: int = 24):
    """Get readings for a specific household"""
    try:
        query = f'''
        from(bucket:"{INFLUXDB_BUCKET}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r["_measurement"] == "energy_usage")
            |> filter(fn: (r) => r["_field"] == "energy_kwh")
            |> filter(fn: (r) => r["household_id"] == "{household_id}")
            |> sort(columns: ["_time"], desc: true)
        '''
        result = query_api.query(org=INFLUXDB_ORG, query=query)
        
        readings = []
        for table in result:
            for record in table.records:
                readings.append({
                    "timestamp": record.get_time(),
                    "household_id": record.values.get("household_id"),
                    "appliance_type": record.values.get("appliance_type"),
                    "energy_kwh": record.get_value(),
                })
        return {"household_id": household_id, "readings": readings}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# GET: Daily consumption
@app.get("/analytics/daily/{household_id}")
def get_daily_consumption(household_id: str):
    """Get daily total consumption"""
    try:
        query = f'''
        from(bucket:"{INFLUXDB_BUCKET}")
            |> range(start: -30d)
            |> filter(fn: (r) => r["_measurement"] == "energy_usage")
            |> filter(fn: (r) => r["household_id"] == "{household_id}")
            |> filter(fn: (r) => r["_field"] == "energy_kwh")
            |> aggregateWindow(every: 1d, fn: sum)
        '''
        result = query_api.query(org=INFLUXDB_ORG, query=query)
        
        daily = []
        for table in result:
            for record in table.records:
                daily.append({
                    "date": record.get_time().date(),
                    "total_kwh": record.get_value(),
                })
        return {"household_id": household_id, "daily_consumption": daily}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# GET: Peak hours
@app.get("/analytics/peak-hours/{household_id}")
def get_peak_hours(household_id: str):
    """Get peak usage hours"""
    try:
        query = f'''
        from(bucket:"{INFLUXDB_BUCKET}")
            |> range(start: -7d)
            |> filter(fn: (r) => r["_measurement"] == "energy_usage")
            |> filter(fn: (r) => r["household_id"] == "{household_id}")
            |> filter(fn: (r) => r["_field"] == "energy_kwh")
            |> aggregateWindow(every: 1h, fn: mean)
        '''
        result = query_api.query(org=INFLUXDB_ORG, query=query)
        
        peak_hours = []
        for table in result:
            for record in table.records:
                peak_hours.append({
                    "hour": record.get_time(),
                    "avg_kwh": record.get_value(),
                })
        
        peak_hours.sort(key=lambda x: x["avg_kwh"], reverse=True)
        return {"household_id": household_id, "peak_hours": peak_hours[:5]}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# GET: Alerts
@app.get("/alerts/{household_id}")
def get_alerts(household_id: str, hours: int = 24):
    """Get anomaly alerts for a household"""
    try:
        query = f'''
        from(bucket:"{INFLUXDB_BUCKET}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r["_measurement"] == "alerts")
            |> filter(fn: (r) => r["household_id"] == "{household_id}")
            |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
            |> sort(columns:["_time"], desc:true)
        '''
        result = query_api.query(org=INFLUXDB_ORG, query=query)
        
        alerts = []
        for table in result:
            for record in table.records:
                alerts.append({
                    "timestamp": record.get_time(),
                    "severity": record.values.get("severity"),
                    "reason": record.values.get("reason"),
                    "current_value": record.values.get("current_value"),
                    "threshold_value": record.values.get("threshold_value"),
                    "alert_type": record.values.get("alert_type"),
                })
        return {"household_id": household_id, "alerts": alerts}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
