from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import mysql.connector
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://dispenser-995ac0zww-nics-projects-3fed757a.vercel.app"}})  # Allow specific frontend
socketio = SocketIO(app, cors_allowed_origins="*")  # Enable WebSocket support

# Database connection configuration
db_config = {
    'user': 'james',
    'password': 'J@mes123!',
    'host': '13.212.247.100',
    'database': 'Vendo'
}

# Create table if not exists
def create_table():
    try:
        with mysql.connector.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS WastePrize (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        Waste VARCHAR(255) NOT NULL,
                        Prize VARCHAR(255) NOT NULL,
                        Status VARCHAR(50) NOT NULL,
                        TimeDate DATETIME NOT NULL,
                        SensorResponse VARCHAR(255) DEFAULT NULL
                    );
                ''')
                conn.commit()
    except mysql.connector.Error as err:
        print(f"[ERROR] Database error: {err}")

# Initialize the database table
create_table()

# Add waste and prize
@app.route('/add_waste_prize', methods=['POST'])
def add_waste_prize():
    try:
        data = request.json
        waste, prize = data.get('Waste'), data.get('Prize')

        if not waste or not prize:
            return jsonify({'error': 'Waste and Prize fields are required'}), 400

        time_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with mysql.connector.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO WastePrize (Waste, Prize, Status, TimeDate) 
                    VALUES (%s, %s, %s, %s)
                ''', (waste, prize, 'Pending', time_date))
                conn.commit()
                record_id = cursor.lastrowid

        socketio.emit('new_waste_prize', {'id': record_id, 'Waste': waste, 'Prize': prize, 'Status': 'Pending'})

        return jsonify({'message': 'Record added successfully', 'id': record_id}), 201

    except mysql.connector.Error as err:
        return jsonify({'error': f'Database error: {err}'}), 500

# Update sensor response
@app.route('/update_sensor_response', methods=['PUT'])
def update_sensor_response():
    try:
        data = request.json
        sensor_response = data.get('SensorResponse')

        if not sensor_response:
            return jsonify({'error': 'SensorResponse field is required'}), 400

        with mysql.connector.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT MAX(id) FROM WastePrize')
                max_id = cursor.fetchone()[0]

                if not max_id:
                    return jsonify({'error': 'No records found'}), 404

                cursor.execute('UPDATE WastePrize SET SensorResponse = %s WHERE id = %s', (sensor_response, max_id))
                conn.commit()

        socketio.emit('sensor_response_update', {'record_id': max_id, 'SensorResponse': sensor_response})
        return jsonify({'message': 'SensorResponse updated successfully'}), 200

    except mysql.connector.Error as err:
        return jsonify({'error': f'Database error: {err}'}), 500

# Get current process
@app.route('/get_current_process', methods=['GET'])
def get_current_process():
    try:
        with mysql.connector.connect(**db_config) as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute('''
                    SELECT Waste, Prize 
                    FROM WastePrize 
                    WHERE Status = "Pending"
                    ORDER BY id DESC 
                    LIMIT 1
                ''')
                result = cursor.fetchone()

        return jsonify(result if result else {'error': 'No pending processes found'}), 200

    except mysql.connector.Error as err:
        return jsonify({'error': f'Database error: {err}'}), 500

# Update status
@app.route('/update_status/<int:record_id>', methods=['PUT'])
def update_status(record_id):
    try:
        data = request.json
        new_status = data.get('Status')

        with mysql.connector.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute('UPDATE WastePrize SET Status = %s WHERE id = %s', (new_status, record_id))
                conn.commit()

        socketio.emit('status_update', {'record_id': record_id, 'status': new_status})
        return jsonify({'message': 'Status updated successfully'}), 200

    except mysql.connector.Error as err:
        return jsonify({'error': f'Database error: {err}'}), 500

# Check sensor response
@app.route('/check_sensor_response/<int:record_id>', methods=['GET'])
def check_sensor_response(record_id):
    try:
        with mysql.connector.connect(**db_config) as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute('SELECT Waste, SensorResponse FROM WastePrize WHERE id = %s', (record_id,))
                result = cursor.fetchone()

        if not result:
            return jsonify({'error': 'Record not found'}), 404

        if result['Waste'] == 'Plastic Bottles' and result['SensorResponse'] == 'bottle_verified':
            return jsonify({'SensorResponse': 'verified'}), 200
        elif result['Waste'] == 'Paper' and result['SensorResponse'] == 'weight_verified':
            return jsonify({'SensorResponse': 'verified'}), 200

        return jsonify({'SensorResponse': result['SensorResponse']}), 200

    except mysql.connector.Error as err:
        return jsonify({'error': f'Database error: {err}'}), 500

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    print("[INFO] Client connected to WebSocket.")

@socketio.on('disconnect')
def handle_disconnect():
    print("[INFO] Client disconnected from WebSocket.")

# Run the Flask app with WebSocket support
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
