from flask import Flask, request, render_template, redirect, session
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import os
import random
import mysql.connector
import socket
import requests
import subprocess
import json
from datetime import datetime

# Replace sensitive values with environment variables or placeholders
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_bot_token_here")
chat_id = os.getenv("TELEGRAM_CHAT_ID", "your_chat_id_here")

# Database connection (use environment variables for credentials)
mydb = mysql.connector.connect(
    host=os.getenv("DB_HOST", "your_database_host_here"),
    user=os.getenv("DB_USER", "your_username_here"),
    passwd=os.getenv("DB_PASSWORD", "your_password_here"),
    database=os.getenv("DB_NAME", "your_database_name_here")
)
mycursor = mydb.cursor()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
bcrypt = Bcrypt(app)
CORS(app)

# Helper Functions
def get_IP():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
    except Exception as e:
        local_ip = None
        print("No Internet or error in fetching IP:", e)

    return local_ip

def active_users_data(user_id):
    query = """SELECT full_name, dob, gender, aadhar, pan, bank, ip_address, 
               user_id, pass, address, upi, age, balance 
               FROM registry WHERE user_id=%s"""
    mycursor.execute(query, (user_id,))
    result = mycursor.fetchall()
    return result[0] if result else ["Null"] * 13

def process_transaction(bank, upi, user_id, amount, count):
    transaction_data = {
        "user_id": user_id,
        "upi": str(upi),
        "amount": str(amount),
        "bank": str(bank)
    }
    data_as_json = json.dumps(transaction_data)
    subprocess.Popen(['python', 'transaction.py', data_as_json], start_new_session=False)

def generateotp(user_id):
    otp = str(random.randint(100000, 900000))
    try:
        message = str(otp)
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
        requests.get(url).json()
        query = "UPDATE registry SET otp = %s WHERE user_id = %s"
        mycursor.execute(query, (otp, user_id))
        mydb.commit()
        print("OTP sent")
    except Exception as e:
        print("Error sending OTP:", e)
        query = "UPDATE registry SET otp = %s WHERE user_id = %s"
        mycursor.execute(query, (otp, user_id))
        mydb.commit()
        print("Fallback OTP:", otp)

# Routes
@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('homepage.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    user_id = request.form.get('user_id')
    password = request.form.get('password')
    IP = get_IP()

    query = "SELECT * FROM users WHERE userid = %s"
    mycursor.execute(query, (user_id,))
    user = mycursor.fetchone()

    if user and bcrypt.check_password_hash(user[3], password):
        session_active = user[2]
        stored_IP = user[1]
        if session_active and stored_IP != IP:
            return render_template('multiplelogin.html', user_id=user_id)
        elif not session_active and stored_IP != IP:
            generateotp(user_id)
            return render_template('otp.html', user_id=user_id)

        # Update session and balance
        mycursor.execute("UPDATE users SET session=1 WHERE userid=%s", (user_id,))
        mydb.commit()
        mycursor.execute("SELECT balance FROM registry WHERE user_id=%s", (user_id,))
        balance = mycursor.fetchone()[0]
        return render_template('dashboard.html', user_id=user_id, totalbalance=balance)

    return render_template('homepage.html', error="Invalid login credentials")

@app.route('/register', methods=['GET', 'POST'])
def register():
    full_name = request.form.get('name')
    dob = request.form.get('dob')
    gender = request.form.get('gender')
    aadhar = request.form.get('aadhar')
    pan = request.form.get('pan')
    bank = request.form.get('bank')
    user_id = request.form.get('userid')
    password = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
    IP = get_IP()

    try:
        age = datetime.now().year - int(dob.split('-')[0])
        registry_query = """INSERT INTO registry 
                            (full_name, dob, gender, aadhar, pan, bank, user_id, pass, ip_address, age) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        registry_values = (full_name, dob, gender, aadhar, pan, bank, user_id, password, IP, age)
        mycursor.execute(registry_query, registry_values)

        user_query = "INSERT INTO users (userid, IP, session, pass) VALUES (%s, %s, %s, %s)"
        mycursor.execute(user_query, (user_id, IP, 0, password))
        mydb.commit()

        generateotp(user_id)
        return render_template('newregistry.html', user_id=user_id)

    except Exception as e:
        print("Error during registration:", e)
        return render_template('homepage.html', error="User already exists. Please login.")

@app.route('/verify', methods=['POST'])
def verify():
    user_id = request.form.get('user_id')
    entered_otp = request.form.get('otp')

    mycursor.execute("SELECT otp FROM registry WHERE user_id = %s", (user_id,))
    result = mycursor.fetchone()

    if result and entered_otp == str(result[0]):
        IP = get_IP()
        update_queries = [
            "UPDATE users SET session=1, IP=%s WHERE userid=%s",
            "UPDATE registry SET ip_address=%s WHERE user_id=%s"
        ]
        for query in update_queries:
            mycursor.execute(query, (IP, user_id))
        mydb.commit()
        return render_template('homepage.html', success="Verification successful")

    return render_template('otp.html', user_id=user_id, error="Incorrect OTP")

@app.route('/logout', methods=['POST'])
def logout():
    user_id = request.form.get('user_id')
    mycursor.execute("UPDATE users SET session=0 WHERE userid=%s", (user_id,))
    mydb.commit()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
