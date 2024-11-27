import firebase_admin
from firebase_admin import credentials, db
import sys
import json
data_as_json = sys.argv[1]
data = json.loads(data_as_json)
credential_path = r'C:\Users\shubh\Desktop\SecureFlow\keys\userdatabase.json'
cred = credentials.Certificate(credential_path)
database_url = 'https://bankingserver-400-default-rtdb.firebaseio.com/'
app_name = 'usersdata'
firebase_app = firebase_admin.initialize_app(cred,{'databaseURL': database_url},name=app_name)
ref = db.reference('/', app=firebase_app)
ref.push(data)
print("DONE")