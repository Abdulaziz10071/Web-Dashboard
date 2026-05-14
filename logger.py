import paho.mqtt.client as mqtt
from datetime import datetime
import socket


class MQTTReceiver:
    def __init__(self, broker_ip="localhost", port=1883, topic="aziz/#"):
        self.broker_ip = broker_ip
        self.port = port
        self.topic = topic
        self.sensor_data_log = []
        self.is_recording = False
        self.start_time = None
        self.connection_failed = False

        # Initialize the client IMMEDIATELY upon creation
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        # Safely attempt connection without crashing the Flask server
        try:
            self.client.connect(self.broker_ip, self.port, 60)
            self.client.loop_start()
            print("MQTT Client initialized and listening in the background.")
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            print(f"CRITICAL ERROR: Could not connect to Mosquitto Broker. Reason: {e}")
            self.connection_failed = True

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"Connected to Broker at {self.broker_ip}.")
            self.client.subscribe(self.topic)
        else:
            print(f"Connection failed: {reason_code}")

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        print(f"WARNING: Disconnected from Broker! Reason Code: {reason_code}")

    def on_message(self, client, userdata, msg):
        # The client ALWAYS receives messages, but ONLY logs them if is_recording is True
        if self.is_recording:
            payload = msg.payload.decode('utf-8')
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            data_entry = {"timestamp": timestamp, "raw_payload": payload}
            self.sensor_data_log.append(data_entry)

    def start_recording(self):
        if not self.is_recording:
            self.sensor_data_log = []  # Clear any old data from the buffer
            self.is_recording = True  # Open the data valve
            self.start_time = datetime.now()
            print("Recording STARTED. Saving incoming data to memory...")
            return True
        return False

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False  # Close the data valve

            # 1. Get total raw seconds
            raw_seconds = (datetime.now() - self.start_time).total_seconds()

            # 2. Convert to Hours, Minutes, and Seconds
            hours, remainder = divmod(int(raw_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)

            # 3. Format as 00:00:00
            formatted_duration = f"{hours:02}:{minutes:02}:{seconds:02}"

            print(f"Recording STOPPED. Captured {len(self.sensor_data_log)} points in {formatted_duration}.")

            # Make a copy of the captured data to return
            captured_data = list(self.sensor_data_log)

            # Clear the active list to immediately free up RAM
            self.sensor_data_log = []

            return captured_data, formatted_duration

        return [], "00:00:00"
