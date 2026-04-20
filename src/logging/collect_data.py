#!/usr/bin/env python
"""
collect_data.py

Continuously polls the PLC for its holding registers and writes them to a CSV.
"""

import csv
import time
import argparse
from pymodbus.client import ModbusTcpClient

def collect(host, port, unit, duration, interval, output):
    client = ModbusTcpClient(host, port=port)
    if not client.connect():
        print(f"ERROR: Cannot connect to {host}:{port}")
        return

    with open(output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["reg0", "reg1"])
        start = time.time()
        while time.time() - start < duration:
            # read holding registers instead of input registers
            rr = client.read_holding_registers(address=0, count=2, slave=unit)
            if not rr.isError():
                writer.writerow(rr.registers)
            else:
                # record NaNs on error
                writer.writerow([None, None])
            time.sleep(interval)

    client.close()
    print(f"Done: {output}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--host",     default="192.168.64.1")
    p.add_argument("--port",     type=int, default=502)
    p.add_argument("--unit",     type=int, default=1)
    p.add_argument("--duration", type=float, default=120.0,
                   help="Seconds to poll")
    p.add_argument("--interval", type=float, default=0.1,
                   help="Seconds between polls")
    p.add_argument("--output",   required=True,
                   help="CSV file to write")
    args = p.parse_args()
    collect(args.host, args.port, args.unit,
            args.duration, args.interval, args.output)
