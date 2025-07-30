import subprocess
import time
while True:
    process = subprocess.Popen(['python', 'main.py'], start_new_session=False)
    process = subprocess.Popen(['python', 'faliure_maintainence.py'], start_new_session=False)
    time.sleep(60)
    process.terminate()
    process.wait()

#python SecureFlow.py