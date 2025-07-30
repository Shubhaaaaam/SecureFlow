import firebase_admin
from firebase_admin import credentials, db
import sys
import json
import os

# Load data from command line argument
data_as_json = sys.argv[1]
data = json.loads(data_as_json)

# Use environment variables for confidential data
credential_path = os.environ.get('USERDB_CERT_PATH')
database_url = os.environ.get('USERDB_DB_URL')
app_name = 'usersdata'

cred = credentials.Certificate(credential_path)
firebase_app = firebase_admin.initialize_app(cred, {'databaseURL': database_url}, name=app_name)
ref = db.reference('/', app=firebase_app)
ref.push(data)
print("DONE")