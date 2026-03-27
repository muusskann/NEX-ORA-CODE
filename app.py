from flask import Flask, request, jsonify, render_template, session
import requests
import random
import re
from langdetect import detect
from deep_translator import GoogleTranslator
from database import Database

db = Database()

app = Flask(__name__)
app.secret_key = "nexora_secret"
conversation_state = {}

def safe_detect(text):
    try:
        return detect(text)
    except:
        return "en"


def translate_to_en(text):
    try:
        return GoogleTranslator(source="auto", target="en").translate(text)
    except:
        return text


def translate_back(text, lang):
    try:
        return GoogleTranslator(source="en", target=lang).translate(text)
    except:
        return text


def generate_ticket():
    return "NX" + str(random.randint(1000, 9999))


def detect_language(text):
    text_lower = text.lower()

    if re.search("[ऀ-ॿ]", text):
        return "hi"

    hindi_words = [
        "mera",
        "meri",
        "nahi",
        "hai",
        "kaam",
        "kya",
        "kyun",
        "subah",
        "haan",
        "theek",
    ]
    if any(word in text_lower for word in hindi_words):
        return "hinglish"

    return "en"

def detect_intent(msg):
    msg = msg.lower()

    if any(x in msg for x in ["appointment", "book", "doctor", "meeting"]):
        return "appointment"

    if any(
        x in msg
        for x in [
            "wifi",
            "internet",
            "not working",
            "issue",
            "problem",
            "order",
            "delivery",
        ]
    ):
        return "complaint"

    if any(x in msg for x in ["payment", "refund", "money", "upi"]):
        return "payment"

    if any(x in msg for x in ["feedback", "survey", "rating"]):
        return "survey"

    if any(x in msg for x in ["price", "plan", "buy", "interested"]):
        return "lead"

    return "unknown"


def ask_ai(text_en):
    try:
        prompt = f"Reply in simple English in one short line: {text_en}"
       
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "phi",
                "prompt": prompt,
                "stream": False,
            },
        )

        data = res.json()
        reply = data.get("response", "")

        if not reply:
            return "Sorry i didn't understand that."

        return reply.strip()

    except Exception as e:
        print("ERROR:", e)
        return "Server issue, try again."


def process_message(user_id, text):

    original_text_lower = text.lower()
    
    lang = detect_language(text)
    if lang=="hinglish":
        lang = "hi"
        
    elif lang not in ["en", "hi"]:
        lang = safe_detect(text)

    if lang=="en":
        text_en = text
    else:
        text_en = translate_to_en(text)
        
    text_lower = text_en.lower()

    if text_lower in ["hi", "hello", "hey", "namaste", "namaskar"]:
        response_en = "Hi, how can I help you today?"
        if lang =="hi":
            return translate_back(response_en, "hi")
        return response_en

    intent = detect_intent(text_en)

    if user_id not in conversation_state:
        flow_val = None
    else:
        flow_val = conversation_state[user_id]["flow"]

    # ✅ PAYMENT FIX
    if intent == "payment":
        db.create_ticket("payment issue", "payment")
        response_en = " I'm sorry to hear that you're facing a payment issue ,i'm connecting you to a human agent who can assist you further."
        if lang=="en":
            return response_en
        return translate_back(response_en, lang)

    if user_id not in conversation_state:
        conversation_state[user_id] = {"flow": None, "step": 0, "data": {}}

    state = conversation_state[user_id]

    if state["flow"] is None and intent != "unknown":
        state["flow"] = intent
        state["step"] = 0
        state["data"] = {}

    flow_val = state["flow"]
    db.save_conversation(user_id, "You: " + text, intent, flow_val)

    flow = state["flow"]
    step = state["step"]

    # 📡 COMPLAINT
    if flow == "complaint":

        if step == 0:
            state["data"]["issue"] = text
            state["step"] += 1

            response_en="Please share your registered mobile number."
            if lang=="en":
                return response_en
            return translate_back(response_en, lang)

        elif step == 1:
            state["step"] += 1

            response_en = "May I know your name?"
            if lang=="en":
                return response_en
            return translate_back(response_en, lang)

        elif step == 2:
            state["step"] += 1
            issue = state["data"]["issue"].lower()

            if "order" in issue or "delivery" in issue:

                response_en = "Please share your order ID."
                if lang=="en":
                    return response_en
                return translate_back(response_en, lang)

            response_en = "Which provider or plan are you using?"
            if lang=="en":
                return response_en
            return translate_back(response_en, lang)

        elif step == 3:
            state["step"] += 1
            issue = state["data"]["issue"].lower()

            if "wifi" in issue or "internet" in issue:
                response_en = "Please restart your router and check lights."
                if lang=="en":
                    return response_en
                return translate_back(response_en, lang)

            response_en = "We are checking your issue."
            if lang=="en":
                return response_en
            return translate_back(response_en, lang)
        
        elif step == 4:
            state["step"] += 1
            response_en = "Is your issue resolved?"
            if lang=="en":
                return response_en
            return translate_back(response_en, lang)

        elif step == 5:

            issue = state["data"]["issue"].lower()

            if any(
                x in text_lower for x in ["yes", "haan", "ho gaya", "resolved", "theek","done","fixed","okay"]
            ):
                conversation_state[user_id] = {"flow": None, "step": 0, "data": {}}
                
                response_en = "Glad your issue is resolved!"
                return translate_back(response_en, lang)

            elif any(x in text_lower for x in ["no", "nahi", "abhi bhi", "not yet"]):
                try:
                    ticket = db.create_ticket(state["data"]["issue"], "complaint")

                    conversation_state[user_id] = {"flow": None, "step": 0, "data": {}}

                    response_en =f"Our technician will visit within 24 hours. Ticket ID: {ticket}"
                    return{
                        "reply": translate_back(response_en, lang),
                        "call": True,
                        "call_type": "complaint",
                        "flow": "complaint"
                    }

                except Exception as e:
                    print("ERROR STEP 5:", e)
                    return "Server issue, try again."

    # 📅 APPOINTMENT
    elif flow == "appointment":

        if step == 0:
            state["step"] += 1
            
            response_en ="What service do you want?"
            if lang=="en":
                return response_en
            return translate_back(response_en, lang)
        
        elif step == 1:
            state["step"] += 1
            response_en = "Select date."
            if lang=="en":
                return response_en
            return translate_back(response_en, lang)

        elif step == 2:
            state["step"] += 1
            response_en = "Select time."
            if lang=="en":
                return response_en
            return translate_back(response_en, lang)

        elif step == 3:

            conversation_state[user_id] = {"flow": None, "step": 0, "data": {}}
        
            response_en = "Your appointment is confirmed."
            return{
                "reply": translate_back(response_en, lang),
                "call": True,
                "call_type": "appointment",
                "flow": "appointment"
            }

    # 📊 SURVEY (NO CALL)
    elif flow == "survey":
        if step == 0:
            state["step"] += 1
            response_en ="Rate our service from 1 to 5."
            if lang=="en":
                return response_en
            return translate_back(response_en, lang)
        
        elif step == 1:
            state["step"] += 1
            response_en = "Thank you for your feedback! Any suggestions?"
            if lang=="en":
                return response_en
            return translate_back(response_en, lang)
        
        elif step == 2:
            conversation_state[user_id] = {"flow": None, "step": 0, "data": {}}
            response_en = "Thank you for your feedback!"
            if lang=="en":
                return response_en
            return translate_back(response_en, lang)

    # 💼 LEAD
    elif flow == "lead":

        if step == 0:
            state["step"] += 1
            response_en = "May I know your name?"
            if lang=="en":
                return response_en
            return translate_back(response_en, lang)

        elif step == 1:
            state["step"] += 1
            response_en = "Please share your contact number."
            if lang=="en":
                return response_en
            return translate_back(response_en, lang)

        elif step == 2:
            state["step"] += 1
            response_en = "What are you looking for?"
            if lang=="en":
                return response_en
            return translate_back(response_en, lang)

        elif step == 3:
            db.create_ticket("lead generated", "lead")
            conversation_state[user_id] = {"flow": None, "step": 0, "data": {}}
            response_en = "Thank you for your interest! Our sales team will contact you soon."
            return{
                "reply": translate_back(response_en , lang),
                "call":True,
                "call_type": "lead",
                "flow": "lead",
            }

    response_en = ask_ai(text_en)
    if lang=="en":
        return response_en
    return translate_back(response_en, lang)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    data = db.get_dashboard_data()
    grouped = {}

    for row in data["rows"]:
        user = row[0]
        message = row[1]
        flow = row[2]

        if user not in grouped:
            grouped[user] = {}
        if "messages" not in grouped[user]: 
            grouped[user]["messages"] = []
        grouped [user]["user"] = user
        if flow:
            grouped[user]["flow"] = flow
            
        grouped[user]["messages"].append(message)

    data["grouped_conversations"] = list(grouped.values())
    return render_template("dashboard.html", data=data)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data["message"]

    # ✅ Fix indentation + logic
    if "user_id" not in session:
        session["user_id"] = "user_" + str(random.randint(1000, 9999))

    user_id = session["user_id"]

    reply = process_message(user_id, data["message"])

    if isinstance(reply, dict):
        reply_text_val = reply["reply"]
    else:
        reply_text_val = reply

    if isinstance(reply, dict) and "flow" in reply:
        flow_val = reply["flow"]
    else:
        flow_val = conversation_state.get(user_id, {}).get("flow")

    db.save_conversation(user_id, "Nexora: " + reply_text_val, "bot", flow_val)

    return jsonify(reply if isinstance(reply, dict) else {"reply": reply})


@app.route("/mark_called", methods=["POST"])
def mark_called():
    db.mark_called()
    return jsonify({"status": "updated"})


if __name__ == "__main__":
    app.run(debug=True)
