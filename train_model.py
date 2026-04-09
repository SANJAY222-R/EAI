import pandas as pd
import numpy as np
import pickle
import json
import os

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score

print("🔄 Loading dataset...")

# =========================
# Load dataset
# =========================
df = pd.read_csv("data/Diseases_Symptoms.csv")

# Clean column names
df.columns = df.columns.str.strip()

# Rename target column if needed
if "diseases" in df.columns:
    df.rename(columns={"diseases": "Disease"}, inplace=True)

# =========================
# Separate features & target
# =========================
y = df["Disease"]
X = df.drop(columns=["Disease"])

print("Dataset shape:", df.shape)

# =========================
# Encode labels
# =========================
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)

# =========================
# 🔥 Remove rare classes (IMPORTANT)
# =========================
counts = pd.Series(y_encoded).value_counts()
valid_classes = counts[counts >= 2].index

mask = pd.Series(y_encoded).isin(valid_classes)

X = X[mask]
y_encoded = y_encoded[mask]

print("After removing rare classes:", X.shape)

# =========================
# Train/Test split
# =========================
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded,
    test_size=0.2,
    random_state=42
)

# =========================
# Train model
# =========================
print("🤖 Training RandomForest model...")

model = RandomForestClassifier(
    n_estimators=200,
    max_depth=20,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# =========================
# Evaluate
# =========================
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"✅ Model Accuracy: {accuracy:.2%}")

# =========================
# Save everything
# =========================
os.makedirs("model", exist_ok=True)

# Model
with open("model/model.pkl", "wb") as f:
    pickle.dump(model, f)

# Label encoder
with open("model/encoder.pkl", "wb") as f:
    pickle.dump(encoder, f)

# Feature columns (VERY IMPORTANT)
with open("model/columns.pkl", "wb") as f:
    pickle.dump(X.columns.tolist(), f)

# Metrics
with open("model/metrics.json", "w") as f:
    json.dump({"accuracy": float(accuracy)}, f)

print("🎉 Model saved successfully!")