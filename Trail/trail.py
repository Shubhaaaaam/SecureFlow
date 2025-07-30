import time
import subprocess
import concurrent.futures
import time

n=50
def my_code():
    subprocess.Popen(['python', 'runner.py'], start_new_session=False)

start = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=n*2) as executor:
    futures = [executor.submit(my_code) for _ in range(n)]
    concurrent.futures.wait(futures)

end = time.time()
print(f"Executed in: {end - start:.4f} seconds")
