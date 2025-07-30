import firebase_admin
from firebase_admin import credentials, db
import random
import time
import os

start = time.time()

credential_path = os.environ.get('SBI_CERT_PATH')
database_url = os.environ.get('SBI_DB_URL')
app_name = 'SBI_Server'

try:
    firebase_app = firebase_admin.initialize_app(
        credentials.Certificate(credential_path),
        {'databaseURL': database_url},
        name=app_name)
except ValueError:
    firebase_app = firebase_admin.get_app(app_name)

def generate_transaction():
    banks = ['SBI', 'HDFC', 'ICICI', 'Axis', 'Kotak', 'PNB']
    user_id = f"user_{random.randint(1000, 9999)}"
    upi = f"{user_id}@{random.choice(['ybl', 'oksbi', 'okhdfcbank'])}"
    amount = round(random.uniform(50, 5000), 2)
    bank = random.choice(banks)
    return {
        "transaction_id": f"txn_{random.randint(00000000000000,999999999999999)}",
        "user_id": user_id,
        "upi": upi,
        "amount": amount,
        "bank": bank,
        "timestamp": time.time()}

def push_transaction():
    ref = db.reference('/', app=firebase_app)
    for i in range(10):
        data = generate_transaction()
        ref.push(data)

end = time.time()
print(f"Transaction Done before : {end - start:.4f} seconds")
push_transaction()