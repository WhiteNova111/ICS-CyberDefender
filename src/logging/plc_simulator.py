from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock
import random, time, threading

def dynamic_updater(context):
    while True:
        slave = context[0x01]
        current = slave.getValues(3, 0, count=5)
        new_vals = [
            max(0, min(1000, current[0] + random.randint(-3, 3))),
            max(0, min(500,  current[1] + random.randint(-2, 2))),
            max(0, min(200,  current[2] + random.randint(-1, 1))),
            max(0, min(100,  current[3] + random.randint(-1, 1))),
            max(0, min(50,   current[4] + random.randint(0, 1))),
        ]
        slave.setValues(3, 0, new_vals)
        time.sleep(0.1)

def run_simulator():
    block = ModbusSequentialDataBlock(0, [100, 250, 80, 60, 1] + [0]*95)
    store = ModbusSlaveContext(hr=block)
    context = ModbusServerContext(slaves={0x01: store}, single=False)
    t = threading.Thread(target=dynamic_updater, args=(context,), daemon=True)
    t.start()
    print("PLC Simulator running on 127.0.0.1:5020")
    StartTcpServer(context=context, address=("127.0.0.1", 5020))

if __name__ == "__main__":
    run_simulator()