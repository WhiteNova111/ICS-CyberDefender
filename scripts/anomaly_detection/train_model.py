import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

# 1. Load the CSV
df_full = pd.read_csv("data/raw/baseline.csv")

# 2. Select only numeric columns (here 'func_code')
numeric_cols = df_full.select_dtypes(include=['number']).columns.tolist()
df = df_full[numeric_cols]

print(f"Training on numeric columns: {numeric_cols} ({len(df)} samples)")

# 3. Fit the IsolationForest
model = IsolationForest(contamination=0.01, random_state=42)
model.fit(df)

# 4. Save the model
joblib.dump(model, "models/isoforest.pkl")
print("Model saved to models/isoforest.pkl")
