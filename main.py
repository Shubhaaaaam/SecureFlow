from flask import Flask, request, render_template, redirect
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from cryptography.fernet import Fernet
from datetime import datetime
import os
import random
import mysql.connector
import socket
import requests
import subprocess
import json
import google.generativeai as genai

Api = os.environ.get('GENAI_API_KEY')
genai.configure(api_key=Api)
model = genai.GenerativeModel("gemini-2.0-flash")

TOKEN = os.environ.get('TELEGRAM_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')

key = os.environ.get('FERNET_KEY').encode()
cipher_suite = Fernet(key)

mydb = mysql.connector.connect(
    host="127.0.0.1",
    user=os.environ.get('DB_USER'),
    passwd=os.environ.get('DB_PASS'),
    database="banking_system"
)
mycursor=mydb.cursor()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
bcrypt = Bcrypt(app)
CORS(app)

def get_IP():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
    except:
            local_ip = None
            print("No Internet")

    IP=local_ip
    return IP

def active_users_data(user_id):
    query = "SELECT full_name, dob, gender, aadhar, pan, bank, ip_address, user_id, pass, mpin, upi, age, balance FROM registry WHERE user_id=%s"
    mycursor.execute(query, (user_id,))
    a = mycursor.fetchall()
    try:
        row = a[0]
        decrypted_data = (
        row[0],
        row[1],
        row[2],
        cipher_suite.decrypt(row[3].encode()).decode(),
        cipher_suite.decrypt(row[4].encode()).decode(),
        cipher_suite.decrypt(row[5].encode()).decode(),
        row[6],
        row[7],
        cipher_suite.decrypt(row[8].encode()).decode(),
        row[9],
        row[10],
        row[11],
        row[12]
        )
        return decrypted_data

    except:
        print("No Data Available")
        return ["Null","Null","Null","Null","Null","Null","Null","Null","Null","Null","Null"]
   
def process_transaction(bank,upi,user_id,amount,count):
    upi=upi
    bank=bank
    user_id=user_id
    amount=amount
    firebase_data = {
                "user_id":user_id,
                "upi": str(upi),
                "amount": str(amount),
                "bank": str(bank)
            }
    data_as_json = json.dumps(firebase_data)
    subprocess.Popen(['python', 'transaction.py', data_as_json], start_new_session=False)
    return
    
def generateotp(user_id):
    otp = random.randint(100000, 900000)
    otp = str(otp)
    try:
        message = str(otp)
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
        requests.get(url).json()
        l = "UPDATE registry SET otp = %s WHERE user_id = %s"
        mycursor.execute(l, (otp, user_id))
        mydb.commit()
        return print("OTP sent")
    except:
        l = "UPDATE registry SET otp = %s WHERE user_id = %s"
        mycursor.execute(l, (otp, user_id))
        mydb.commit()
        return print("OTP could not be sent.\nOTP: ",otp)

@app.route('/', methods=['GET', 'POST'])
def home():
    get_IP()
    return render_template('homepage.html')

@app.route('/chatting', methods=['GET', 'POST'])
def chat():
    chat = model.start_chat()
    query = request.form.get('chatInput')
    response = chat.send_message(str(query))
    truncated_text = response.text
    if len(truncated_text) > 200:
        truncated_text = truncated_text[:200] + "..."
    return render_template('chat.html', response=truncated_text)


@app.route('/login', methods=['GET', 'POST'])
def login():
    IP=get_IP()
    user_id = request.form.get('user_id')
    password = request.form.get('password')
    l="select * from users where userid ='"+user_id+"'"
    mycursor.execute(l)
    for i in mycursor:
        a=i[3]
        l=cipher_suite.decrypt(str(a)).decode()
        passw=l
        print(passw)
        if password==passw and str(i[2])==str(1):
            if str(IP)!=str(i[1]):
                print("Multiple Login"+20*"-")
                return render_template('multiplelogin.html',user_id=user_id)
            else:
                l="select balance from registry where user_id ='"+user_id+"'"
                mycursor.execute(l)
                for i in mycursor:
                    totalbalance=i[0]
                return render_template('dashboard.html',user_id=user_id,totalbalance=totalbalance)

        elif password==passw and str(i[2])==str(0):
            if str(IP)!=str(i[1]):
                generateotp(user_id)
                return render_template('otp.html',user_id=user_id)
            active_users_data(user_id)
            l="update users set session=1 where userid ="+"'"+user_id+"'"
            mycursor.execute(l)
            mydb.commit()
            l="select balance from registry where user_id ='"+user_id+"'"
            mycursor.execute(l)
            for i in mycursor:
                totalbalance=i[0]
            return render_template('dashboard.html',user_id=user_id,totalbalance=totalbalance)
    data="Incorrect User ID or Password"
    return render_template('homepage.html',data=data)

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    IP=get_IP()
    user_id = request.form.get('user_id')
    entered_otp = request.form.get('otp')
    l = "SELECT otp FROM registry WHERE user_id = %s"
    mycursor.execute(l, (user_id,))
    result = mycursor.fetchone()
    correct_otp = str(result[0])
    if str(entered_otp) == str(correct_otp):
        l = "UPDATE users SET session = 0 WHERE userid ="+"'"+str(user_id)+"'"
        mycursor.execute(l)
        l = "UPDATE users SET IP = "+"'"+str(IP)+"'"+" WHERE userid ="+"'"+user_id+"'"
        mycursor.execute(l)
        l = "UPDATE registry SET ip_address = "+"'"+str(IP)+"'"+" WHERE user_id ="+"'"+user_id+"'"
        mycursor.execute(l)
        mydb.commit()
        print("Verification Successful")
        return render_template('homepage.html')
    else:
        data="Incorrect OTP. Please Enter Correct OTP"
        print("Incorrect OTP")
        return render_template('otp.html', user_id=user_id,data=data)

@app.route('/utility', methods=['GET', 'POST'])
def utility():
    user_id = request.form.get('user_id')
    button=request.form.get('button')
    data=active_users_data(user_id)
    if button=='profile':
        return render_template('profile.html',data=data,user_id=user_id)
    elif button=='support':
        return render_template('support.html',data=data,user_id=user_id)
    elif button=='transactions':
        return render_template('transactions.html',data=data,user_id=user_id)
    elif button=='chat':
        response="Please Tell Us Your Problem"
        return render_template('chat.html',response=response)
    elif button=='dashboard':
        totalbalance=data[12]
        return render_template('dashboard.html',data=data,user_id=user_id,totalbalance=totalbalance)
    else:
        return render_template('dashboard.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    IP=get_IP()
    full_name = request.form.get('name', '')  
    dob = request.form.get('dob', '')  
    gender = request.form.get('gender', '')  
    mpin = request.form.get('mpin', '')  
    user_id = request.form.get('userid', '')  
    aadhar = cipher_suite.encrypt(request.form.get('aadhar', '').encode())
    pan = cipher_suite.encrypt(request.form.get('pan', '').encode())
    bank = cipher_suite.encrypt(request.form.get('bank', '').encode())
    password = cipher_suite.encrypt(request.form.get('password', '').encode())
    a=(full_name,dob,gender,aadhar,pan,bank,user_id,password)
    a=list(a)
    cal=dob.split(sep='-')
    cal=cal[0]
    now = datetime.now()
    cur = now.year
    age=(int(cur)-int(cal))
    try:
        query = """INSERT INTO registry (full_name, dob, gender, aadhar, pan, bank, user_id, pass, ip_address,age,mpin) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        values = (full_name, dob, gender, aadhar, pan, bank, user_id, password, IP, age, mpin)
        mycursor.execute(query, values)

        query = """INSERT INTO users (userid, IP, session, pass) VALUES (%s, %s, %s, %s)"""
        mycursor.execute(query, (user_id, IP, 0, password)) 

        mydb.commit()
        data="Registrations in MysQL is Successful"
        
    except Exception as e:
        print(e)
        data="Already Registered. Please Login"
        print("Resubmission Aborted")
        return render_template('homepage.html',data=data)

    generateotp(user_id)
    return render_template('newregistry.html',user_id=user_id,a=a)

@app.route('/confirmation', methods=['GET', 'POST'])
def confirmation():
    IP=get_IP()
    full_name = request.form.get('name')
    dob = request.form.get('dob')
    gender = request.form.get('gender')
    aadhar = request.form.get('aadhar')
    pan = request.form.get('pan')
    bank = request.form.get('bank')
    user_id = request.form.get('user_id')
    password = request.form.get('password')
    a=(full_name,dob,gender,aadhar,pan,bank,user_id,password)
    a=list(a)
    entered_otp = request.form.get('otp')
    l = "SELECT otp FROM registry WHERE user_id = %s"
    mycursor.execute(l, (user_id,))
    result = mycursor.fetchone()
    correct_otp = str(result[0])
    if str(entered_otp) == str(correct_otp):        
        try:
            firebase_data = {
                'userid': user_id,
                'IP': IP,
                'password': password,
                'full_name':full_name,
                'dob': dob,
                'gender': gender,
                'aadhar': aadhar,
                'pan': pan,
                'bank': bank
            }
            data_as_json = json.dumps(firebase_data)
            subprocess.Popen(['python', 'server_banking.py', data_as_json], start_new_session=False)
            print("Data inserted into Firebase successfully.")
        except Exception as e:
            print(e)
            print("Data not inserted into Firebase.")
            data="Could Not Process. Try Again."
            return render_template('homepage.html',data=data)
        
    else:
        data="Incorrect OTP. Please Enter Correct OTP"
        print("Incorrect OTP Entered")
        return render_template('newregistry.html',data=data,a=a)
    data="Registrations Successful"
    return render_template('homepage.html',data=data)

@app.route('/update' , methods=['GET', 'POST'])
def update():
    user_id = request.form.get('user_id')
    data=active_users_data(user_id)
    print(data[9])

    password1 = cipher_suite.encrypt(request.form.get('password', '').encode())
    if password1 =="":
        password = data[8]
    else:
        password = password1
    
    mpin = request.form.get('mpin')
    if mpin =="":
        mpin = data[9]
    else:
        mpin=mpin
    upi1 = request.form.get('upi')
    if upi1=="":
        upi=data[10]
    else:
        upi=upi1

    if mpin=="" and password1=="" and upi1=="":
        message="No Update in Profile"
    else:
        query = """UPDATE registry SET mpin=%s, Pass=%s, Upi=%s WHERE user_id=%s"""
        mycursor.execute(query, (mpin, password, upi, user_id)) 
        query = """UPDATE users SET Pass=%s WHERE userid=%s"""
        mycursor.execute(query, (password,user_id)) 
        mydb.commit()
        message = "Profile updated successfully"
        data=active_users_data(user_id)
    return render_template('profile.html',data=data ,message=message,user_id=user_id)

@app.route('/transactionverify' , methods=['GET', 'POST'])
def transactionverify():
    user_id = request.form.get('user_id')
    mpin = request.form.get('mpin')
    l="select mpin from registry where user_id ='"+user_id+"'"
    mycursor.execute(l)
    for i in mycursor:
        a=[i[0]]
    print(a[0])
    print(mpin)
    if mpin==a[0]:
        user_id = request.form.get('user_id')
        return render_template('transfer.html',user_id=user_id)
    else:
        data=active_users_data(user_id)
        return render_template('transactions.html',data=data,user_id=user_id)

@app.route('/transaction' , methods=['GET', 'POST'])
def transaction():
    user_id = request.form.get('user_id')
    return render_template('mpin.html',user_id=user_id)

@app.route('/process' , methods=['GET', 'POST'])
def process():
    upi = request.form.get('upi')
    amount = request.form.get('amount')
    user_id = request.form.get('user_id')
    bank = request.form.get('bank')
    data=active_users_data(user_id)
    balance=data[12]
    if int(amount)<=int(balance):
        process_transaction(bank,upi, user_id,amount,0)
        return render_template('processed.html')
    else:
        print("Low Balance")
        return render_template('lowbalance.html')

@app.route('/logout' , methods=['GET', 'POST'])
def logout():
    user_id = request.form.get('user_id')
    l="update users set session=0 where userid ="+"'"+str(user_id)+"'"
    mycursor.execute(l)
    mydb.commit()
    print("Logged out")
    return redirect('http://127.0.0.1:5000/')

if __name__ == '__main__':
    app.run(debug=True)