import time
import os

ANOMALY_LOG_PATH = '/home/airobot/projects/ICS-CyberDefender/logs/alerts/anomaly.log'
SLEEP_INTERVAL = 2

def tail_f(filename):
    with open(filename, 'r') as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(SLEEP_INTERVAL)
                continue
            yield line

def main():
    print("[INFO] VLAN Manager started. Monitoring anomaly log...")
    isolated = False

    while not os.path.exists(ANOMALY_LOG_PATH):
        print(f"[WARN] Waiting for anomaly log at {ANOMALY_LOG_PATH}")
        time.sleep(SLEEP_INTERVAL)

    for line in tail_f(ANOMALY_LOG_PATH):
        line = line.strip()
        if line:
            print(f"[ALERT] Anomaly detected: {line}")
            if not isolated:
                print("[INFO] (Simulated) Isolating PLC interface - no physical interface present")
                isolated = True
            else:
                print("[INFO] Interface already (simulated) isolated")

if __name__ == '__main__':
    main()
