# scripts/attack_injection/modbus_scan.py

from pymodbus.client import ModbusTcpClient

def main():
    client = ModbusTcpClient('192.168.64.1', port=502)
    if not client.connect():
        print("ERROR: Cannot connect to PLC")
        return

    rr = client.read_coils(1, 1, slave=1)
    if rr.isError():
        print("Read error:", rr)
    else:
        print(f"Coil 1 state: {rr.bits[0]}")

    client.close()

if __name__ == "__main__":
    main()
