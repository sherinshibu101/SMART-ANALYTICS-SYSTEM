from influxdb_client import InfluxDBClient
from config import INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET

query = f'''
from(bucket:"{INFLUXDB_BUCKET}")
  |> range(start: 0)
  |> filter(fn: (r) => r["_measurement"] == "energy_usage")
  |> limit(n: 10)
'''

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
result = client.query_api().query(org=INFLUXDB_ORG, query=query)

records = []
for table in result:
    for r in table.records:
        records.append((str(r.get_time()), r.get_field(), r.get_value(), r.values.get("household_id")))

print(f"records_total={len(records)}")
for row in records[:5]:
    print(row)
