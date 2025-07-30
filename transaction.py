import firebase_admin
from firebase_admin import credentials, db
import sys
import json
import mysql.connector
from pymongo import MongoClient
import os

success=0
data_as_json = sys.argv[1]
data = json.loads(data_as_json)
user_id=data["user_id"]
upi=data["upi"]
amount=data["amount"]
bank=data["bank"]
mydb = mysql.connector.connect(
    host=os.environ.get('DB_HOST', '127.0.0.1'),
    user=os.environ.get('DB_USER'),
    passwd=os.environ.get('DB_PASS'),
    database=os.environ.get('DB_NAME', 'banking_system')
)
mycursor=mydb.cursor()
try:
    print("Trying First Server")
    credential_path = os.environ.get('TRANSACTION1_CERT_PATH')
    cred = credentials.Certificate(credential_path)
    database_url = os.environ.get('TRANSACTION1_DB_URL')
    app_name = 'Transaction1'
    firebase_app = firebase_admin.initialize_app(cred,{'databaseURL': database_url},name=app_name)
    ref = db.reference('/', app=firebase_app)
    ref.push(data)
    success=1
    print("Data inserted into Firebase 1 successfully.")
    try:
        l = "SELECT balance FROM registry WHERE user_id = '{}';".format(user_id)
        mycursor.execute(l)
        for i in mycursor:
            a=i[0]
            balance=int(a)-int(amount)
            mycursor.execute("UPDATE registry SET balance = %s WHERE user_id = %s", (balance, user_id))
            mydb.commit()
            print("Balance Updated")
    except Exception as e:
        print(e)
        print("SQL Error")
except:
    try:
        print("Trying Second Server")
        credential_path = os.environ.get('TRANSACTION2_CERT_PATH')
        cred = credentials.Certificate(credential_path)
        database_url = os.environ.get('TRANSACTION2_DB_URL')
        app_name = 'Transaction2'
        firebase_app = firebase_admin.initialize_app(cred,{'databaseURL': database_url},name=app_name)
        ref = db.reference('/', app=firebase_app)
        ref.push(data)
        success=1
        print("Data inserted into Firebase 2 successfully.")
    except:
        client = MongoClient("mongodb://localhost:27017/")
        db = client["transactionDB"]
        collection = db["transactions"]
        transaction_data = {
            "user_id": user_id,
            "upi_id": upi,
            "amount": amount,
            "bank":bank
            }
        result = collection.insert_one(transaction_data)
        print(f"Failed Transaction saved with ID: {result.inserted_id}")
        l="Select balance from users where userid= 'admin'"
        mycursor.execute(l)
        for i in mycursor:
            a=i[0]
            balance=int(a)-int(amount)
            l = "UPDATE users SET balance ="+str(balance)+" WHERE userid = 'admin'"
            mycursor.execute(l)
            mydb.commit()
        print("Data inserted into Mongo DB successfully.")