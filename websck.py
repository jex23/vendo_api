from flask import Flask
from flask_socketio import SocketIO, emit
import mysql.connector

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Database connection configuration
db_config = {
    'user': 'james',
    'password': 'J@mes123!',
    'host': '13.212.247.100',
    'database': 'Vendo'
}

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    print("[INFO] Client connected to WebSocket.")

@socketio.on('disconnect')
def handle_disconnect():
    print("[INFO] Client disconnected from WebSocket.")

@socketio.on('status_update')
def handle_status_update(data):
    print(f"[INFO] Status update received: {data}")
    emit('server_response', {'message': 'Status update processed successfully!'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=6000)  # Use a separate port for WebSocket

