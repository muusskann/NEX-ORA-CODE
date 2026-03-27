from flask import Flask, request, jsonify, render_template, session
import requests
import random
import re

from database import Database

db = Database()

app = Flask(__name__)
app.secret_key = "nexora_secret"
conversation_state = {}


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


def reply_text(lang, en, hi, hinglish):
    if lang == "en":
        return en
    else:
        return hi


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


def ask_ai(text, lang):
    try:
        if lang == "en":
            prompt = f"Reply ONLY in English in 1 short line: {text}"
        else:
            prompt = f"Reply ONLY in Hindi in 1 short line: {text}"

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

    text_lower = text.lower()
    lang = detect_language(text)

    if text_lower in ["hi", "hello", "hey", "namaste", "namaskar"]:
        return reply_text(
            lang,
            "Hi, how can I help you today?",
            "नमस्ते, मैं आपकी कैसे मदद कर सकता हूँ?",
            "Namaste, main aapki kaise madad kar sakta hoon?",
        )

    intent = detect_intent(text)

    if user_id not in conversation_state:
        flow_val = None
    else:
        flow_val = conversation_state[user_id]["flow"]

    # ✅ PAYMENT FIX
    if intent == "payment":
        db.create_ticket("payment issue", "payment")
        return reply_text(
            lang,
            "I’m connecting you to a human agent.",
            "मैं आपको एक मानव एजेंट से जोड़ रहा हूँ।",
            "Main aapko human agent se connect kar raha hoon.",
        )

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
            return reply_text(
                lang,
                "Please share your registered mobile number.",
                "कृपया अपना मोबाइल नंबर बताएं।",
                "Please apna mobile number bataiye.",
            )

        elif step == 1:
            state["step"] += 1
            return reply_text(
                lang,
                "May I know your name?",
                "कृपया अपना नाम बताएं।",
                "Aapka naam kya hai?",
            )

        elif step == 2:
            state["step"] += 1
            issue = state["data"]["issue"].lower()

            if "order" in issue or "delivery" in issue:
                return reply_text(
                    lang,
                    "Please share your order ID.",
                    "कृपया अपना ऑर्डर आईडी बताएं।",
                    "Apna order ID bataiye.",
                )

            return reply_text(
                lang,
                "Which provider or plan are you using?",
                "आप कौन सा प्लान या प्रोवाइडर उपयोग कर रहे हैं?",
                "Kaunsa provider ya plan use kar rahe ho?",
            )

        elif step == 3:
            state["step"] += 1
            issue = state["data"]["issue"].lower()

            if "wifi" in issue or "internet" in issue:
                return reply_text(
                    lang,
                    "Please restart your router and check lights.",
                    "कृपया अपना राउटर रीस्टार्ट करें और लाइट्स चेक करें।",
                    "Router restart karke lights check karo.",
                )

            return reply_text(
                lang,
                "We are checking your issue.",
                "हम आपकी समस्या की जांच कर रहे हैं।",
                "Hum aapka issue check kar rahe hain.",
            )

        elif step == 4:
            state["step"] += 1
            return reply_text(
                lang,
                "Is your issue resolved?",
                "क्या आपकी समस्या हल हो गई?",
                "Kya aapka issue solve ho gaya?",
            )

        elif step == 5:

            issue = state["data"]["issue"].lower()

            if any(
                x in text_lower for x in ["yes", "haan", "ho gaya", "resolved", "theek"]
            ):
                conversation_state[user_id] = {"flow": None, "step": 0, "data": {}}
                return reply_text(
                    lang,
                    "Glad your issue is resolved!",
                    "अच्छा है कि आपकी समस्या हल हो गई!",
                    "Achha hai aapka issue solve ho gaya!",
                )

            elif any(x in text_lower for x in ["no", "nahi", "abhi bhi", "not yet"]):
                try:
                    ticket = db.create_ticket(state["data"]["issue"], "complaint")

                    conversation_state[user_id] = {"flow": None, "step": 0, "data": {}}

                    return {
                        "reply": reply_text(
                            lang,
                            f"Our technician will visit within 24 hours. Ticket ID: {ticket}",
                            f"हमारा तकनीशियन 24 घंटे में आएगा। टिकट आईडी: {ticket}",
                            f"Technician 24 hours me aayega. Ticket ID: {ticket}",
                        ),
                        "call": True,
                        "call_type": "complaint",
                        "flow": "complaint",
                    }

                except Exception as e:
                    print("ERROR STEP 5:", e)
                    return "Server issue, try again."

    # 📅 APPOINTMENT
    elif flow == "appointment":

        if step == 0:
            state["step"] += 1
            return reply_text(
                lang,
                "What service do you want?",
                "आप कौन सी सेवा चाहते हैं?",
                "Kaunsi service chahiye?",
            )

        elif step == 1:
            state["step"] += 1
            return reply_text(lang, "Select date.", "तारीख चुनें।", "Date select karo.")

        elif step == 2:
            state["step"] += 1
            return reply_text(lang, "Select time.", "समय चुनें।", "Time select karo.")

        elif step == 3:

            conversation_state[user_id] = {"flow": None, "step": 0, "data": {}}

            return {
                "reply": reply_text(
                    lang,
                    "Your appointment is confirmed.",
                    "आपकी अपॉइंटमेंट कन्फर्म हो गई है।",
                    "Appointment confirm ho gaya.",
                ),
                "call": True,
                "call_type": "appointment",
                "flow": "appointment",
            }

    # 📊 SURVEY (NO CALL)
    elif flow == "survey":
        if step == 0:
            state["step"] += 1
            return reply_text(
                lang,
                "Rate our service from 1 to 5.",
                "कृपया हमारी सेवा को 1 से 5 तक रेट करें।",
                "Service ko 1 se 5 tak rate karo.",
            )
        elif step == 1:
            state["step"] += 1
            return reply_text(
                lang, "Any suggestions?", "कोई सुझाव?", "Koi suggestion hai?"
            )
        elif step == 2:
            conversation_state[user_id] = {"flow": None, "step": 0, "data": {}}
            return reply_text(
                lang,
                "Thank you for your feedback!",
                "आपके फीडबैक के लिए धन्यवाद!",
                "Feedback ke liye thanks!",
            )

    # 💼 LEAD
    elif flow == "lead":

        if step == 0:
            state["step"] += 1
            return reply_text(
                lang,
                "May I know your name?",
                "कृपया अपना नाम बताएं।",
                "Aapka naam kya hai?",
            )

        elif step == 1:
            state["step"] += 1
            return reply_text(
                lang,
                "Please share your contact number.",
                "कृपया अपना संपर्क नंबर बताएं।",
                "Apna contact number bataiye.",
            )

        elif step == 2:
            state["step"] += 1
            return reply_text(
                lang,
                "What are you looking for?",
                "आप क्या ढूंढ रहे हैं?",
                "Kya chahiye aapko?",
            )

        elif step == 3:
            db.create_ticket("lead generated", "lead")

            conversation_state[user_id] = {"flow": None, "step": 0, "data": {}}

            return {
                "reply": reply_text(
                    lang,
                    "Our team will contact you soon.",
                    "हमारी टीम आपसे जल्द संपर्क करेगी।",
                    "Team jaldi contact karegi.",
                ),
                "call": True,
                "call_type": "lead",
                "flow": "lead",
            }

    return ask_ai(text, lang)


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
            grouped[user] = {"flow": flow, "messages": []}
        if flow is not None:
            grouped[user]["flow"] = flow

        grouped[user]["messages"].append(message)

    data["grouped_conversations"] = list(grouped.values())
    return render_template("dashboard.html", data=data)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data["message"].lower()

    # ✅ Fix indentation + logic
    if (
        "user_id" not in session
        or message in ["hi", "hello", "start"]
        or conversation_state.get(session.get("user_id"), {}).get("flow") is None
    ):
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
