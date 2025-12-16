from flask import Flask, request, jsonify, send_from_directory
import sqlite3, hashlib, secrets, datetime
from server_settings import MAX_SIZE,UPLOAD_FOLDER, token_valid
from product_routes import product_bp
from order_routes import order_bp
#import order_routes

# create app
app = Flask(__name__)

# register blueprints
app.register_blueprint(product_bp)
app.register_blueprint(order_bp)

# config
app.config['MAX_CONTENT_LENGTH'] = MAX_SIZE



@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()

        # Simple validation
        if 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Missing username or password'})

        username, password = data['username'], data['password']

        conn = sqlite3.connect("emap.db")
        cursor = conn.cursor()

        # Safe from SQL injection because of ?
        cursor.execute("SELECT user_id, password_hash, password_salt, username FROM users WHERE username = ? OR email = ?",
                       (username, username))  # Try both username and email

        user = cursor.fetchone()

        if not user:  # User doesn't exist
            return jsonify({'error': 'Login failed'})

        # Unpack
        user_id, stored_hash, salt, db_username = user

        # Check password
        test_hash = hashlib.sha256((password + salt).encode()).hexdigest()

        if test_hash == stored_hash:
            #PASSWORD IS CORRECT

            # Generate random token
            token = secrets.token_hex(32)  # 64 character token

            # Set expiration (7 days from now)
            expires_at = (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat()

            # Insert into tokens table
            cursor.execute("""
                           INSERT INTO tokens (user_id, token, type, expires_at)
                           VALUES (?, ?, 'auth', ?)
                           """, (user_id, token, expires_at))

            # Update last login time
            cursor.execute("""
                           UPDATE users
                           SET last_login = ?
                           WHERE user_id = ?
                           """, (datetime.datetime.now().isoformat(), user_id))

            conn.commit()
            conn.close()

            return jsonify({
                'success': True,
                'user_id': user_id,
                'username': db_username,
                'token': token,
                'expires_at': expires_at
            })

        else:
            return jsonify({'error': 'Login failed'})

    except Exception as e:
        return jsonify({'error': f'Server error: {e}'})

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        conn = sqlite3.connect("emap.db")
        cursor = conn.cursor()
        username, email, password = data['username'], data['email'], data['password']
        # FIX: Check if user exists first!
        cursor.execute("SELECT user_id FROM users WHERE username = ? OR email = ?",
                       (username, email))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Username or email already exists'})

        salt = secrets.token_hex(8)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, email, password_hash, password_salt) VALUES (?, ?, ?, ?)",
                      (data['username'], data['email'], password_hash, salt))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return jsonify({'success': True, 'user_id': user_id})
    except Exception as e:
        return jsonify({'error': f'error: {e}'})


@app.route('/check_token', methods=['POST'])
def check_token():
    try:
        data = request.get_json()
        token = data['token']

        conn = sqlite3.connect("emap.db")
        cursor = conn.cursor()

        # Get current time in same format as stored
        current_time = datetime.datetime.now().isoformat()

        # Use SQLite's datetime() function for proper date comparison
        cursor.execute("""
                       SELECT 1
                       FROM tokens
                       WHERE token = ?
                         AND datetime(expires_at) > datetime(?)
                       """, (token, current_time))

        result = cursor.fetchone()
        conn.close()

        return jsonify({'valid': bool(result), 'success': True}) if bool(result) else jsonify({'valid': False, "error": "token expired"})

    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})
@app.route('/information', methods=['POST'])
def info():
    try:
        data = request.get_json()
        token = data['token']

        conn = sqlite3.connect("emap.db")
        valid  = token_valid(conn, token)
        text = " okay this is a test text will see how it looks on the app hehe \n test test test \n more testing \n ."

        return jsonify({'text': text, 'success': True}) if valid else jsonify({"error": "token not valid"})

    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5013, debug=True)
