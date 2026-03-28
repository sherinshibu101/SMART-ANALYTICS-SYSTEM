import random
import sys
from pathlib import Path
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Allow running as a script: `py simulator/generator.py`
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import (
    INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_URL, INFLUXDB_BUCKET,
    HOUSEHOLDS_COUNT, APPLIANCE_TYPES, REGIONS,
    ANOMALY_THRESHOLD_SPIKE, ANOMALY_THRESHOLD_DAILY
)

class EnergyDataSimulator:
    """Simulates realistic smart meter energy readings with anomaly detection"""
    
    def __init__(self):
        self.client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.households = [f"household_{i}" for i in range(1, HOUSEHOLDS_COUNT + 1)]
        self.daily_total = {hh: 0 for hh in self.households}
        self.recent_readings = {hh: [] for hh in self.households}  # Track recent readings
        self.daily_readings = {hh: [] for hh in self.households}   # Track daily totals
    
    def get_hour_usage_pattern(self, hour: int) -> float:
        """
        Daily usage pattern:
        - Morning (6-12): moderate usage
        - Afternoon (12-18): low usage
        - Evening (18-23): peak usage
        - Night (23-6): minimal usage
        """
        if 6 <= hour < 12:
            return random.uniform(0.3, 0.6)  # Morning: moderate
        elif 12 <= hour < 18:
            return random.uniform(0.1, 0.3)  # Afternoon: low
        elif 18 <= hour < 23:
            return random.uniform(0.7, 1.2)  # Evening: peak
        else:
            return random.uniform(0.05, 0.2)  # Night: minimal
    
    def get_appliance_baseline(self, appliance: str) -> float:
        """Get baseline consumption for each appliance"""
        baselines = {
            "AC": 2.5,
            "Refrigerator": 0.15,
            "Washing Machine": 0.5,
            "Lights": 0.3,
            "Water Heater": 1.8,
        }
        return baselines.get(appliance, 0.5)
    
    def get_recent_average(self, household_id: str) -> float:
        """Calculate average of recent readings for a household"""
        recent = self.recent_readings.get(household_id, [])
        if len(recent) == 0:
            return 0.5  # Default if no history
        return sum(recent) / len(recent)
    
    def get_daily_average(self, household_id: str) -> float:
        """Calculate average of last 7 days for a household"""
        daily = self.daily_readings.get(household_id, [])
        if len(daily) < 7:
            return sum(daily) / len(daily) if daily else 10.0
        return sum(daily[-7:]) / 7  # Last 7 days
    
    def detect_and_alert(self, household_id: str, energy_kwh: float, now: datetime):
        """Detect anomalies and write alerts to InfluxDB"""
        recent_avg = self.get_recent_average(household_id)
        daily_avg = self.get_daily_average(household_id)
        
        alerts = []
        
        # Rule 1: Spike detection (current > 1.8x average)
        if recent_avg > 0 and energy_kwh > recent_avg * ANOMALY_THRESHOLD_SPIKE:
            alert_point = Point("alerts") \
                .tag("household_id", household_id) \
                .tag("alert_type", "spike") \
                .field("severity", "high") \
                .field("reason", f"Usage spike detected: {energy_kwh:.2f} kWh (avg: {recent_avg:.2f})") \
                .field("current_value", energy_kwh) \
                .field("threshold_value", recent_avg * ANOMALY_THRESHOLD_SPIKE) \
                .time(now, write_precision="ns")
            alerts.append(alert_point)
        
        # Rule 2: Daily threshold (daily > 1.3x daily average)
        if daily_avg > 0 and (self.daily_total[household_id] > daily_avg * ANOMALY_THRESHOLD_DAILY):
            alert_point = Point("alerts") \
                .tag("household_id", household_id) \
                .tag("alert_type", "daily_threshold") \
                .field("severity", "medium") \
                .field("reason", f"High daily usage: {self.daily_total[household_id]:.2f} kWh (7-day avg: {daily_avg:.2f})") \
                .field("current_value", self.daily_total[household_id]) \
                .field("threshold_value", daily_avg * ANOMALY_THRESHOLD_DAILY) \
                .time(now, write_precision="ns")
            alerts.append(alert_point)
        
        # Write alerts if any detected
        if alerts:
            try:
                for alert in alerts:
                    self.write_api.write(bucket=INFLUXDB_BUCKET, record=alert)
            except Exception as e:
                print(f"⚠️ Error writing alerts: {e}")
    
    def generate_reading(self, household_id: str, hour: int):
        """Generate a single realistic reading"""
        appliance = random.choice(APPLIANCE_TYPES)
        region = random.choice(REGIONS)
        
        # Base consumption from appliance
        base_consumption = self.get_appliance_baseline(appliance)
        
        # Hour-based multiplier
        hour_multiplier = self.get_hour_usage_pattern(hour)
        
        # Random variation (±10%)
        variation = random.uniform(0.9, 1.1)
        
        # Occasional spikes (5% chance)
        spike = random.uniform(1.0, 2.5) if random.random() < 0.05 else 1.0
        
        energy_kwh = base_consumption * hour_multiplier * variation * spike
        
        # Realistic electrical parameters
        voltage = random.uniform(220, 240)
        current = random.uniform(5, 20)
        power_factor = random.uniform(0.85, 0.98)
        
        return {
            "household_id": household_id,
            "appliance_type": appliance,
            "region": region,
            "energy_kwh": round(energy_kwh, 3),
            "voltage": round(voltage, 2),
            "current": round(current, 2),
            "power_factor": round(power_factor, 2),
        }
    
    def ingest_batch(self, num_readings: int = 10):
        """Generate and ingest a batch of readings"""
        points = []
        now = datetime.utcnow()
        
        for household_id in self.households:
            # Reset daily total for new batch
            self.daily_total[household_id] = 0
            
            for i in range(num_readings):
                reading = self.generate_reading(household_id, now.hour)
                energy_kwh = reading["energy_kwh"]
                
                # Track for anomaly detection
                self.recent_readings[household_id].append(energy_kwh)
                if len(self.recent_readings[household_id]) > 20:  # Keep last 20 readings
                    self.recent_readings[household_id].pop(0)
                
                self.daily_total[household_id] += energy_kwh
                
                # Create InfluxDB point
                point = Point("energy_usage") \
                    .tag("household_id", reading["household_id"]) \
                    .tag("appliance_type", reading["appliance_type"]) \
                    .tag("region", reading["region"]) \
                    .field("energy_kwh", reading["energy_kwh"]) \
                    .field("voltage", reading["voltage"]) \
                    .field("current", reading["current"]) \
                    .field("power_factor", reading["power_factor"]) \
                    .time(now - timedelta(minutes=i*5), write_precision="ns")
                
                points.append(point)
                
                # Detect anomalies
                self.detect_and_alert(household_id, energy_kwh, now - timedelta(minutes=i*5))
            
            # Track daily total for 7-day average calculation
            self.daily_readings[household_id].append(self.daily_total[household_id])
            if len(self.daily_readings[household_id]) > 7:  # Keep last 7 days
                self.daily_readings[household_id].pop(0)
        
        try:
            self.write_api.write(bucket=INFLUXDB_BUCKET, record=points)
            print(f"✓ Successfully ingested {len(points)} readings")
            return True
        except Exception as e:
            print(f"✗ Error ingesting readings: {e}")
            return False
    
    def close(self):
        """Close InfluxDB connection"""
        self.client.close()

if __name__ == "__main__":
    simulator = EnergyDataSimulator()
    print("🔌 Starting energy data simulator...")
    simulator.ingest_batch(num_readings=10)
    simulator.close()
    print("✓ Simulation complete!")
