"""
Collect baseline data from live PLC simulator
Run plc_simulator.py first in another terminal
"""
import pandas as pd
import time
from pymodbus.client import ModbusTcpClient
from dotenv import load_dotenv
import os

load_dotenv()

HOST = os.getenv("PLC_HOST", "127.0.0.1")
PORT = int(os.getenv("PLC_PORT", 5020))
SLAVE = int(os.getenv("PLC_SLAVE", 1))

def collect(duration_seconds=300, interval=0.5, label=0, output_file="data/raw/baseline.csv"):
    client = ModbusTcpClient(HOST, port=PORT)
    client.connect()
    print(f"Connected to PLC at {HOST}:{PORT}")
    print(f"Collecting {duration_seconds}s of data → {output_file}")

    records = []
    start = time.time()
    prev_vals = None
    prev_time = None

    while time.time() - start < duration_seconds:
        ts = time.time()
        rr = client.read_holding_registers(address=0, count=5, slave=SLAVE)

        if not rr.isError():
            vals = rr.registers
            inter_arrival = (ts - prev_time) if prev_time else 0.0
            delta = [abs(vals[i] - prev_vals[i]) for i in range(5)] if prev_vals else [0]*5

            record = {
                "timestamp":        ts,
                "inter_arrival_ms": inter_arrival * 1000,
                "reg_temp":         vals[0],
                "reg_pressure":     vals[1],
                "reg_flow":         vals[2],
                "reg_level":        vals[3],
                "reg_status":       vals[4],
                "delta_temp":       delta[0],
                "delta_pressure":   delta[1],
                "delta_flow":       delta[2],
                "delta_level":      delta[3],
                "label":            label   # 0=normal, 1=attack
            }
            records.append(record)
            prev_vals = vals
            prev_time = ts

            elapsed = time.time() - start
            if len(records) % 50 == 0:
                print(f"  [{elapsed:.0f}s] {len(records)} samples | temp={vals[0]} pressure={vals[1]} flow={vals[2]}")

        time.sleep(interval)

    client.close()
    df = pd.DataFrame(records)
    df.to_csv(output_file, index=False)
    print(f"\nSaved {len(df)} samples → {output_file}")
    print(df.describe())
    return df

if __name__ == "__main__":
    collect(duration_seconds=300, interval=0.5, label=0, output_file="data/raw/baseline.csv")