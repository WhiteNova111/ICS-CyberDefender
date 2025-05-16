# scripts/anomaly_detection/evaluate_attacks.py

import pandas as pd
import joblib

# 1. Load the trained model
clf = joblib.load("models/isoforest.pkl")

# 2. Get the feature names the model expects
#    (requires scikit-learn ≥1.0)
try:
    feature_cols = list(clf.feature_names_in_)
except AttributeError:
    # fallback: infer numeric columns from a sample CSV
    sample = pd.read_csv("data/raw/baseline.csv")
    feature_cols = sample.select_dtypes(include=['number']).columns.tolist()

print(f"Model expects features: {feature_cols}")

# 3. Define your attack CSVs
attack_files = {
    "false_data":     "data/raw/false_data.csv",
    "logic_injection":"data/raw/logic_injection.csv",
    "dos_flood":      "data/raw/dos_flood.csv",
    "fuzz_modbus":    "data/raw/fuzz_modbus.csv",
    "replay_attack":  "data/raw/replay_attack.csv",
    "multi_register": "data/raw/write_multiple_registers.csv",
}

# 4. Evaluate each attack trace
for name, path in attack_files.items():
    df = pd.read_csv(path)
    # Select the same columns the model was trained on
    df_feat = df[feature_cols]
    # Compute anomaly scores and count how many are below threshold
    scores = clf.decision_function(df_feat)
    total     = len(df_feat)
    anomalies = (scores < 0).sum()   # scores<0 indicates anomalies *after* offset
    print(f"{name}: {anomalies}/{total} frames flagged as anomalies")
