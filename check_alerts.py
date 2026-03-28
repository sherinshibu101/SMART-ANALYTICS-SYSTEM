from influxdb_client import InfluxDBClient
from config import INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET

query = f'''
from(bucket:"{INFLUXDB_BUCKET}")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "alerts")
  |> limit(n: 20)
'''

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
result = client.query_api().query(org=INFLUXDB_ORG, query=query)

alerts = []
for table in result:
    for record in table.records:
        alerts.append({
            'time': str(record.get_time()),
            'household_id': record.values.get('household_id'),
            'alert_type': record.values.get('alert_type'),
            'severity': record.get_value() if record.get_field() != 'reason' else None,
            'field': record.get_field(),
            'value': record.get_value()
        })

print(f"Total alert records: {len(alerts)}")
print("\nRecent alerts:")
for alert in alerts[:10]:
    print(f"  {alert['household_id']} | {alert['alert_type']} | {alert['field']}: {alert['value']}")
