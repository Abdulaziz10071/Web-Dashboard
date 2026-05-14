import pandas as pd
import json

def process_sensor_data(raw_json_string):
    """
    Takes the raw JSON string from the database, flattens the MQTT batches,
    and returns web-ready summary statistics without the distracting device ID.
    """
    if not raw_json_string or raw_json_string == "No data captured.":
        return 0, []

    try:
        # 1. Load string into a basic DataFrame
        raw_list = json.loads(raw_json_string)
        df = pd.DataFrame(raw_list)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # 2. Unpack the nested batched payload
        all_records = []
        for index, row in df.iterrows():
            try:
                raw_data = json.loads(row['raw_payload'])
                # Device ID extraction removed here
                sensor_batches = raw_data.get('payload', [])

                for reading in sensor_batches:
                    record = {
                        'mqtt_timestamp': row['timestamp'],
                        'sensor_name': reading.get('name', 'Unknown_Sensor'),
                    }
                    # Flatten the x, y, z or single values
                    values = reading.get('values', {})
                    for axis, val in values.items():
                        record[axis] = val

                    all_records.append(record)
            except Exception:
                pass  # Skip malformed packets silently

        # 3. Create the clean dataframe
        clean_df = pd.DataFrame(all_records)
        total_points = len(clean_df)

        # 4. Group by ONLY the sensor name now
        grouped_data = clean_df.groupby('sensor_name')
        stats_list = []

        for sensor, group_df in grouped_data:
            stat = {
                'sensor': sensor.upper(),
                'count': len(group_df),
                'type': 'Single-Value Sensor'
            }

            # If it's an accelerometer/gyro, calculate the means
            if 'x' in group_df.columns and 'y' in group_df.columns and 'z' in group_df.columns:
                stat['type'] = '3-Axis Sensor'
                stat['mean_x'] = round(group_df['x'].mean(), 4)
                stat['mean_y'] = round(group_df['y'].mean(), 4)
                stat['mean_z'] = round(group_df['z'].mean(), 4)

            stats_list.append(stat)

        return total_points, stats_list

    except Exception as e:
        print(f"Data Processing Error: {e}")
        return 0, []
