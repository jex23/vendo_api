from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import mysql.connector
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*")  # Enable WebSocket support

# Database connection configuration
db_config = {
    'user': 'james',
    'password': 'J@mes123!',
    'host': '13.212.247.100',
    'database': 'Vendo'
}

# Connect to the database and create the table if it doesn't exist
def create_table():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
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
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

# Initialize the table
create_table()


# API endpoint to insert waste and prize into the table
@app.route('/add_waste_prize', methods=['POST'])
def add_waste_prize():
    try:
        data = request.json
        waste = data.get('Waste')
        prize = data.get('Prize')
        status = 'Pending'
        time_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not waste or not prize:
            return jsonify({'error': 'Waste and Prize fields are required'}), 400

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO WastePrize (Waste, Prize, Status, TimeDate) 
            VALUES (%s, %s, %s, %s)
        ''', (waste, prize, status, time_date))
        conn.commit()
        record_id = cursor.lastrowid
        cursor.close()
        conn.close()

        # Emit real-time event via WebSocket
        socketio.emit('new_waste_prize', {'id': record_id, 'Waste': waste, 'Prize': prize, 'Status': status})

        return jsonify({'message': 'Record added successfully', 'id': record_id}), 201
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


#api endpoint for updating sensor response
@app.route('/update_sensor_response', methods=['PUT'])
def update_sensor_response():
    try:
        data = request.json
        new_sensor_response = data.get('SensorResponse')

        if not new_sensor_response:
            return jsonify({'error': 'SensorResponse field is required'}), 400

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Get the ID of the most recent record
        cursor.execute('SELECT MAX(id) FROM WastePrize')
        max_id = cursor.fetchone()[0]

        if max_id is None:
            return jsonify({'error': 'No records found in the database'}), 404

        # Update the most recent record using the max_id
        cursor.execute('UPDATE WastePrize SET SensorResponse = %s WHERE id = %s', (new_sensor_response, max_id))
        conn.commit()

        if cursor.rowcount > 0:
            # Emit real-time update via WebSocket
            socketio.emit('sensor_response_update', {'record_id': max_id, 'SensorResponse': new_sensor_response})
            response = jsonify({'message': 'SensorResponse updated successfully'})
            status_code = 200
        else:
            response = jsonify({'error': 'Record not found'})
            status_code = 404

        cursor.close()
        conn.close()
        return response, status_code

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


@app.route('/get_current_process', methods=['GET'])
def get_current_process():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT Waste, Prize 
            FROM WastePrize 
            WHERE Status = "Pending"
            ORDER BY id DESC 
            LIMIT 1
        ''')
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            return jsonify(result), 200
        else:
            return jsonify({'error': 'No pending processes found'}), 404
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500



# API endpoint to update status
@app.route('/update_status/<int:record_id>', methods=['PUT'])
def update_status(record_id):
    try:
        data = request.json
        new_status = data.get('Status')

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute('UPDATE WastePrize SET Status = %s WHERE id = %s', (new_status, record_id))
        conn.commit()
        cursor.close()
        conn.close()

        if cursor.rowcount > 0:
            # Emit real-time status update via WebSocket
            socketio.emit('status_update', {'record_id': record_id, 'status': new_status})
            return jsonify({'message': 'Status updated successfully'}), 200
        else:
            return jsonify({'error': 'Record not found'}), 404
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500

# API endpoint to check sensor response
@app.route('/check_sensor_response/<int:record_id>', methods=['GET'])
def check_sensor_response(record_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT Waste, SensorResponse, Prize FROM WastePrize WHERE id = %s', (record_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            if result['Waste'] == 'Plastic Bottles' and result['SensorResponse'] == 'bottle_verified':
                return jsonify({'SensorResponse': 'verified'}), 200
            elif result['Waste'] == 'Paper' and result['SensorResponse'] == 'weight_verified':
                return jsonify({'SensorResponse': 'verified'}), 200
            return jsonify({'SensorResponse': result['SensorResponse']}), 200
        else:
            return jsonify({'error': 'Record not found'}), 404
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    print("[INFO] Client connected to WebSocket.")

@socketio.on('disconnect')
def handle_disconnect():
    print("[INFO] Client disconnected from WebSocket.")

if __name__ == '__main__':
    # Use `socketio.run` instead of `app.run` for WebSocket support
    socketio.run(app, host='0.0.0.0', port=5000)
