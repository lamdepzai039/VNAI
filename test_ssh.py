import subprocess
import time

print("Testing Localhost.run...")
cmd = "ssh -o StrictHostKeyChecking=no -R 80:localhost:5000 nokey@localhost.run"
proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

start_time = time.time()
while time.time() - start_time < 30:
    line = proc.stdout.readline()
    if line:
        print(f"OUT: {line.strip()}")
    if "lhr.life" in line:
        print("Link found!")
        break
    time.sleep(0.1)

proc.terminate()
print("Done test.")
