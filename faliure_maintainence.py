from pymongo import MongoClient
import firebase_admin
from firebase_admin import credentials, db
import time
import mysql.connector
import os

mydb = mysql.connector.connect(
    host=os.environ.get('DB_HOST', '127.0.0.1'),
    user=os.environ.get('DB_USER'),
    passwd=os.environ.get('DB_PASS'),
    database=os.environ.get('DB_NAME', 'banking_system'))
mycursor=mydb.cursor()

status = [0, 0, 0]
server_app = []

def print_transaction_details():
    try:
        
        client = MongoClient("mongodb://localhost:27017/")
        db = client["transactionDB"]
        collection = db["transactions"]
        transaction_count = collection.count_documents({})

        if transaction_count == 0:
            print("No Pending Transactions Found.")
        else:
            print("Transaction Details:")
            print("---------------------")
            for transaction in collection.find():
                print(f"User ID: {transaction['user_id']}")
                print(f"UPI ID: {transaction['upi_id']}")
                print(f"Amount: {transaction['amount']}")
                print(f"Bank: {transaction['bank']}")
                print(f"Transaction ID: {transaction['_id']}")
                print("---------------------")
                data = {
                    "user_id": transaction['user_id'],
                    "upi_id": transaction['upi_id'],
                    "amount": transaction['amount'],
                    "bank": transaction['bank'],
                    "id": str(transaction['_id'])
                }
                if store_data(transaction['bank'], data,str(transaction['_id'])):
                    collection.delete_one({"_id": transaction["_id"]})
                    l="Select balance from users where userid= 'admin'"
                    mycursor.execute(l)
                    for i in mycursor:
                        a=i[0]
                    balance=int(a)+int(transaction['amount'])
                    l = "UPDATE users SET balance ="+str(balance)+" WHERE userid = 'admin'"
                    mycursor.execute(l)
                    mydb.commit()
                    print(f"Transaction with ID {transaction['_id']} deleted from MongoDB.")
                    return

    except Exception as e:
        print(f"An error occurred: {e}")
        print("PASS")

def store_data(name, data,id):
    try:
        if name == "SBI":
            ref = db.reference('/'+str(id), app=server_app[0])
        elif name == "AXIS":
            ref = db.reference('/', app=server_app[1])
        elif name == "HDFC":
            ref = db.reference('/', app=server_app[2])
        else:
            print(f"Bank '{name}' not recognized.")
            return False

        ref.push(data)
        print(f"Data pushed to {name} Firebase server.")
        return True

    except Exception as e:
        print(f"Failed to push data to {name}: {e}")
        return False

def initialize_firebase_app(cert_path, db_url, nm):
    try:
        if not firebase_admin._apps.get(nm):
            cred = credentials.Certificate(cert_path)
            app = firebase_admin.initialize_app(cred, {'databaseURL': db_url}, name=nm)
            server_app.append(app)
            print(f"Server {nm}: ACTIVATED")
        else:
            print(f"Server {nm} is already activated.")
    except Exception as e:
        print(f"Failed to initialize {nm} server: {e}")

def start():
    initialize_firebase_app(
        os.environ.get('SBI_CERT_PATH'),
        os.environ.get('SBI_DB_URL'),
        "SBI_Server"
    )
    initialize_firebase_app(
        os.environ.get('AXIS_CERT_PATH'),
        os.environ.get('AXIS_DB_URL'),
        "AXIS_Server"
    )
    initialize_firebase_app(
        os.environ.get('HDFC_CERT_PATH'),
        os.environ.get('HDFC_DB_URL'),
        "HDFC_Server"
    )
    while True:
        print_transaction_details()
        time.sleep(5)

start()
