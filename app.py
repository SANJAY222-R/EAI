import os
import json
import pickle
import re
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from groq import Groq
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
from bson.objectid import ObjectId

load_dotenv()
app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "super-secret-key")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client.get_database("medai_db")
    users_collection = db.users
    chat_sessions_collection = db.chat_sessions
    print("MongoDB connection successful")
except Exception as e:
    print("Warning: MongoDB connection failed:", e)

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
    
    stop_words = {
        "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", 
        "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", 
        "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", 
        "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", 
        "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", 
        "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", 
        "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", 
        "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", 
        "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", 
        "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", 
        "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", 
        "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now",
        "hello", "hi", "hey", "good", "morning", "afternoon", "evening", "night", "bro", "whats", "what's"
    }

    vector = [0] * len(columns)
    match_count = 0

    for i, col in enumerate(columns):
        col_clean = col.replace("_", " ")
        words = [w for w in col_clean.split() if w not in stop_words]
        
        if any(re.search(rf"\b{re.escape(word)}\b", symptom_text) for word in words):
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
# ROUTES & MIDDLEWARE
# =========================

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
            
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = users_collection.find_one({'email': data['email']})
            if not current_user:
                return jsonify({'message': 'Invalid token!'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"message": "Missing email or password"}), 400
        
    if users_collection.find_one({"email": email}):
        return jsonify({"message": "User already exists"}), 400
        
    hashed_password = generate_password_hash(password)
    users_collection.insert_one({"email": email, "password": hashed_password})
    return jsonify({"message": "User created successfully"}), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    
    user = users_collection.find_one({"email": email})
    
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"message": "Login failed"}), 401
        
    token = jwt.encode({
        'email': user['email'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    
    return jsonify({"token": token}), 200

@app.route("/api/chats", methods=["GET"])
@token_required
def get_chats(current_user):
    chats = list(chat_sessions_collection.find(
        {"user_id": str(current_user["_id"])},
        {"messages": 0}
    ).sort("created_at", -1))
    
    for chat in chats:
        chat["_id"] = str(chat["_id"])
        
    return jsonify(chats), 200

@app.route("/api/chats/new", methods=["POST"])
@token_required
def new_chat(current_user):
    chat = {
        "user_id": str(current_user["_id"]),
        "session_name": "New Chat",
        "messages": [],
        "created_at": datetime.datetime.utcnow()
    }
    result = chat_sessions_collection.insert_one(chat)
    return jsonify({"_id": str(result.inserted_id), "session_name": "New Chat"}), 201

@app.route("/api/chats/<session_id>", methods=["GET"])
@token_required
def get_chat(current_user, session_id):
    try:
        chat = chat_sessions_collection.find_one({"_id": ObjectId(session_id), "user_id": str(current_user["_id"])})
        if not chat:
            return jsonify({"message": "Chat not found"}), 404
        chat["_id"] = str(chat["_id"])
        return jsonify(chat), 200
    except:
        return jsonify({"message": "Invalid ID"}), 400

@app.route("/api/chats/<session_id>", methods=["DELETE"])
@token_required
def delete_chat(current_user, session_id):
    try:
        result = chat_sessions_collection.delete_one({"_id": ObjectId(session_id), "user_id": str(current_user["_id"])})
        if result.deleted_count:
            return jsonify({"success": True}), 200
        return jsonify({"message": "Chat not found"}), 404
    except:
        return jsonify({"message": "Invalid ID"}), 400

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
@token_required
def predict(current_user):
    try:
        data = request.json
        symptoms = data.get("symptoms", "").strip()
        session_id = data.get("session_id")

        if not symptoms:
            return jsonify({"success": False})

        # =========================
        # 1️⃣ ML LAYER
        # =========================
        features, match_count = get_symptom_vector(symptoms)

        if match_count == 0:
            prompt = f"The user said: '{symptoms}'. You are MedAI, a strict and professional medical AI assistant. Reply pleasantly but firmly that you are only here to analyze medical symptoms and answer health-related queries. Ask them to describe their symptoms. Do NOT diagnose. Keep it under 40 words."
            try:
                res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.6
                )
                explanation = res.choices[0].message.content.strip()
            except Exception:
                explanation = "Hello! Please describe your symptoms."
                
            try:
                if not session_id:
                    title_words = symptoms.split()[:5]
                    title = " ".join(title_words)
                    if len(symptoms.split()) > 5:
                        title += "..."
                    chat = {
                        "user_id": str(current_user["_id"]),
                        "session_name": title,
                        "messages": [],
                        "created_at": datetime.datetime.utcnow()
                    }
                    result = chat_sessions_collection.insert_one(chat)
                    session_id = str(result.inserted_id)

                new_messages = [
                    {"role": "user", "content": symptoms},
                    {
                        "role": "model", 
                        "content": explanation,
                        "type": "conversational"
                    }
                ]
                chat_sessions_collection.update_one(
                    {"_id": ObjectId(session_id)},
                    {"$push": {"messages": {"$each": new_messages}}}
                )
            except Exception as e:
                print("Error saving to db:", e)

            return jsonify({
                "success": True,
                "type": "conversational",
                "response": explanation,
                "session_id": str(session_id) if session_id else None
            })

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

        symptom_text_lower = symptoms.lower()
        matched_keywords = []
        stop_words = {
            "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", 
            "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", 
            "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", 
            "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", 
            "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", 
            "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", 
            "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", 
            "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", 
            "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", 
            "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", 
            "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", 
            "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now",
            "hello", "hi", "hey", "good", "morning", "afternoon", "evening", "night", "bro", "whats", "what's"
        }
        for col in columns:
            col_clean = col.replace("_", " ")
            words = [w for w in col_clean.split() if w not in stop_words]
            if any(re.search(rf"\b{re.escape(word)}\b", symptom_text_lower) for word in words):
                matched_keywords.append(col_clean)

        try:
            if not session_id:
                title_words = symptoms.split()[:5]
                title = " ".join(title_words)
                if len(symptoms.split()) > 5:
                    title += "..."
                chat = {
                    "user_id": str(current_user["_id"]),
                    "session_name": title,
                    "messages": [],
                    "created_at": datetime.datetime.utcnow()
                }
                result = chat_sessions_collection.insert_one(chat)
                session_id = str(result.inserted_id)

            new_messages = [
                {"role": "user", "content": symptoms},
                {
                    "role": "model", 
                    "content": explanation,
                    "status": status,
                    "predictions": display_predictions,
                    "matched_keywords": matched_keywords,
                    "type": "medical"
                }
            ]
            chat_sessions_collection.update_one(
                {"_id": ObjectId(session_id)},
                {"$push": {"messages": {"$each": new_messages}}}
            )
        except Exception as e:
            print("Error saving to db:", e)

        return jsonify({
            "success": True,
            "type": "medical",
            "status": status,
            "top_predictions": display_predictions,
            "response": explanation,
            "matched_keywords": matched_keywords,
            "session_id": str(session_id) if session_id else None
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