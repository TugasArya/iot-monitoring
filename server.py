import socket
import json
from datetime import datetime

# Global variable to hold the latest sensor reading
latest_sensor_data = {
    "temperature": 0.0,
    "humidity": 0.0,
    "timestamp": "No data yet"
}

def start_sensor_server():
    global latest_sensor_data
    HOST = '127.0.0.1'
    PORT = 65433

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    
    print(f"[*] IoT TCP Server listening on {HOST}:{PORT}")

    while True:
        conn, addr = server_socket.accept()
        data = conn.recv(1024)
        if not data:
            break
        
        try:
            # Expecting JSON data from client/sensor simulator: e.g. {"temperature": 31.5, "humidity": 58}
            decoded_data = data.decode('utf-8')
            sensor_payload = json.loads(decoded_data)
            
            latest_sensor_data = {
                "temperature": sensor_payload.get("temperature", 0.0),
                "humidity": sensor_payload.get("humidity", 0.0),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            print(f"[+] Received IoT Data: {latest_sensor_data}")
            
            conn.sendall(b"ACK: Data received successfully")
        except Exception as e:
            print(f"[-] Error parsing telemetry: {e}")
            conn.sendall(b"ERROR: Invalid payload format")
            
        conn.close()

if __name__ == "__main__":
    start_sensor_server()