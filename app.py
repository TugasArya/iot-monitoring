
from flask import Flask, render_template, jsonify
import socket
import json
import threading
import time
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

latest_weather_data = {
    "temperature": 0.0,
    "humidity": 0.0,
    "timestamp": "Waiting for live data...",
    "history_labels": [],
    "history_temps": [],
    "history_humidities": []
}

packet_logs = []

def add_log(message):
    global packet_logs
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    packet_logs.insert(0, log_entry)
    if len(packet_logs) > 20:
        packet_logs.pop()

def fetch_weather_and_history_loop():
    global latest_weather_data
    
    LAT = -6.9277
    LON = 106.9300
    
    # Calculate date range for the past 7 days
    today = datetime.now()
    seven_days_ago = today - timedelta(days=7)
    start_date = seven_days_ago.strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    # API URL for past 7 days historical daily data
    history_url = f"https://archive-api.open-meteo.com/v1/archive?latitude={LAT}&longitude={LON}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_mean,relative_humidity_2m_mean"
    current_url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,relative_humidity_2m"

    while True:
        try:
            add_log("Fetching 7-day historical weather & live telemetry...")
            
            # 1. Fetch 7-day history
            hist_res = requests.get(history_url, timeout=10)
            hist_labels, hist_temps, hist_hums = [], [], []
            if hist_res.status_code == 200:
                hist_data = hist_res.json()
                daily = hist_data.get("daily", {})
                hist_labels = daily.get("time", [])
                hist_temps = daily.get("temperature_2m_mean", [])
                hist_hums = daily.get("relative_humidity_2m_mean", [])

            # 2. Fetch current live weather
            curr_res = requests.get(current_url, timeout=10)
            temp, humidity = 0.0, 0.0
            if curr_res.status_code == 200:
                curr_data = curr_res.json()
                current = curr_data.get("current", {})
                temp = current.get("temperature_2m", 0.0)
                humidity = current.get("relative_humidity_2m", 0.0)

            timestamp_str = time.strftime("%H:%M:%S")

            # 3. Transmit payload over TCP socket
            add_log(f"Establishing TCP socket connection to 127.0.0.1:65433...")
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', 65433))
            
            payload = json.dumps({
                "temperature": temp,
                "humidity": humidity,
                "history_days": len(hist_labels)
            })
            client.sendall(payload.encode('utf-8'))
            add_log(f"SENT TCP Payload (Live + 7-Day Context)")
            
            ack = client.recv(1024).decode('utf-8')
            add_log(f"RECEIVED Server ACK: {ack}")
            client.close()

            # Update cache
            latest_weather_data = {
                "temperature": temp,
                "humidity": humidity,
                "timestamp": timestamp_str,
                "history_labels": hist_labels,
                "history_temps": hist_temps,
                "history_humidities": hist_hums
            }
        except Exception as e:
            add_log(f"ERROR: {str(e)}")
            
        # Refresh every 60 seconds
        time.sleep(60)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    return jsonify(latest_weather_data)

@app.route('/api/logs')
def get_logs():
    return jsonify({"logs": packet_logs})

if __name__ == '__main__':
    weather_thread = threading.Thread(target=fetch_weather_and_history_loop, daemon=True)
    weather_thread.start()
    
    app.run(debug=True, port=5000)