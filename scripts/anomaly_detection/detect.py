#!/usr/bin/env python
"""
detect.py

Polls the PLC’s holding registers in real time, applies the trained IsolationForest,
and logs anomalies (with SHAP values) to logs/alerts/anomaly.log without warnings.
"""

import time
import joblib
import shap
import pandas as pd
from pymodbus.client import ModbusTcpClient

# PLC connection settings
PLC_HOST      = "192.168.64.1"
PLC_PORT      = 502
PLC_SLAVE     = 1
POLL_INTERVAL = 0.1  # seconds
ANOMALY_THRESH = 0   # decision_function < 0 => anomaly

# Load model and explainer
clf = joblib.load("models/isoforest.pkl")
explainer = shap.TreeExplainer(clf)

# Get the exact feature names the model was trained on
feature_cols = list(clf.feature_names_in_)

# Connect to PLC
client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)
if not client.connect():
    raise RuntimeError(f"Unable to connect to PLC at {PLC_HOST}:{PLC_PORT}")

print("Connected to PLC; starting real-time detection...")

try:
    while True:
        rr = client.read_holding_registers(address=0, count=len(feature_cols), slave=PLC_SLAVE)
        if rr.isError() or len(rr.registers) != len(feature_cols):
            # Skip iteration on error or unexpected register count
            time.sleep(POLL_INTERVAL)
            continue

        # Build a DataFrame so feature names match exactly
        df = pd.DataFrame([rr.registers], columns=feature_cols)
        score = clf.decision_function(df)[0]

        if score < ANOMALY_THRESH:
            shap_vals = explainer.shap_values(df)
            ts = time.time()
            with open("logs/alerts/anomaly.log", "a") as f:
                f.write(f"{ts},{rr.registers},{score},{shap_vals}\n")
            print(f"[ANOMALY] {ts}: regs={rr.registers}, score={score:.4f}")

        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    print("Detection stopped by user.")

finally:
    client.close()
    print("PLC connection closed.")
