import os
import json
import pickle
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
app = Flask(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

print("🔄 Loading ML model...")
model = pickle.load(open("model/model.pkl", "rb"))
encoder = pickle.load(open("model/encoder.pkl", "rb"))
columns = pickle.load(open("model/columns.pkl", "rb"))
metrics = json.load(open("model/metrics.json"))
print("✅ Model loaded successfully")


# =========================
# 🔥 RULE ENGINE CONFIG
# =========================
SERIOUS_KEYWORDS = [
    "cancer", "tumor", "stroke",
    "heart attack", "failure"
]

def is_serious(disease):
    disease = disease.lower()
    return any(word in disease for word in SERIOUS_KEYWORDS)


# =========================
# 🔥 SMART SYMPTOM MATCHING + COUNT
# =========================
def get_symptom_vector(symptom_text):
    symptom_text = symptom_text.lower()

    vector = [0] * len(columns)
    match_count = 0

    for i, col in enumerate(columns):
        col_clean = col.replace("_", " ")

        if any(word in symptom_text for word in col_clean.split()):
            vector[i] = 1
            match_count += 1

    return np.array(vector), match_count


# =========================
# 🤖 GROQ RESPONSE
# =========================
def get_groq_response(symptoms, predictions, serious_flag):
    preds_text = "\n".join(
        [f"{p['disease']} ({p['confidence']:.1f}%)" for p in predictions]
    )

    prompt = f"""
User symptoms: {symptoms}

Possible conditions:
{preds_text}

Instructions:
- Be calm and practical
- Do NOT exaggerate rare serious diseases
- If symptoms are mild → reassure user
- If serious_flag → suggest doctor
- Keep under 80 words
"""

    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )
        return res.choices[0].message.content.strip()

    except Exception:
        return "Monitor symptoms. Visit a doctor if needed."


# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.json
        symptoms = data.get("symptoms", "").strip()

        if not symptoms:
            return jsonify({"success": False})

        # =========================
        # 1️⃣ ML LAYER
        # =========================
        features, match_count = get_symptom_vector(symptoms)
        df_input = pd.DataFrame([features], columns=columns)

        probs = model.predict_proba(df_input)[0]
        top_indices = np.argsort(probs)[-3:][::-1]

        raw_predictions = []
        for idx in top_indices:
            raw_predictions.append({
                "disease": encoder.inverse_transform([idx])[0],
                "confidence": float(probs[idx] * 100)
            })

        # =========================
        # 2️⃣ RULE ENGINE
        # =========================

        # Remove unrealistic serious diseases
        filtered = []
        for p in raw_predictions:
            if is_serious(p["disease"]) and p["confidence"] < 35:
                continue
            filtered.append(p)

        if not filtered:
            filtered = raw_predictions[:1]

        serious_flag = any(is_serious(p["disease"]) for p in filtered)

        # Relative confidence
        best = probs[top_indices[0]]
        second = probs[top_indices[1]]
        relative_conf = (best - second) * 100

        print("DEBUG match_count:", match_count)
        print("DEBUG relative_conf:", relative_conf)

        # =========================
        # 🔥 FINAL DECISION ENGINE
        # =========================

        if match_count <= 1:
            status = "mild"

        elif serious_flag:
            status = "critical"

        elif match_count <= 2 and relative_conf < 10:
            status = "moderate"

        elif relative_conf < 5:
            status = "critical"

        elif relative_conf < 15:
            status = "moderate"

        else:
            status = "mild"

        # =========================
        # 3️⃣ UI SAFETY LAYER
        # =========================
        display_predictions = []

        for p in filtered:
            name = p["disease"]

            if is_serious(name):
                name = "Possible serious condition"

            display_predictions.append({
                "disease": name,
                "confidence": p["confidence"]
            })

        explanation = get_groq_response(symptoms, display_predictions, serious_flag)

        return jsonify({
            "success": True,
            "status": status,
            "top_predictions": display_predictions,
            "response": explanation
        })

    except Exception as e:
        print("❌ ERROR:", e)
        return jsonify({"success": False})


# =========================
# RUN
# =========================
if __name__ == "__main__":
    print("🚀 Running at http://127.0.0.1:5000")
    app.run(debug=True)