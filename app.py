from flask import Flask, request, jsonify, render_template
from google import genai
from database import Database

app = Flask(__name__)

client = genai.Client(api_key="AIzaSyC7O9RS1ABidRSjUbdux9LRs1OGm9KVK1s")

database = Database()
conversation_state = {}

BOT_GREETING = "hello, how can i help you today?"


def detect_intent(message):

    message_lower = message.lower()

    if "complaint" in message_lower or "problem" in message_lower or "issue" in message_lower or "not working" in message_lower or "connection" in message_lower:
        return "complaint"

    prompt = f"""
Classify the user intent into one word only from:
appointment, service, complaint, survey, campaign, escalation, unknown.

Message: {message}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        return response.text.strip().lower()

    except:
        return "unknown"



def process_message(user_id, text):

    text_lower = text.lower().strip()

   
    if BOT_GREETING in text_lower:
        return ""   

    intent = detect_intent(text)

    if user_id not in conversation_state:
        conversation_state[user_id] = {
            "flow": None,
            "step": 0,
            "data": {},
            "greeted": False
        }

    state = conversation_state[user_id]
    flow = state["flow"]
    step = state["step"]

    database.save_conversation(text, intent, flow)

    if not state["greeted"]:
        state["greeted"] = True
        return "Hello, how can I help you today?"

    
    if intent == "appointment" or flow == "appointment":

        if flow != "appointment":
            state["flow"] = "appointment"
            state["step"] = 1
            return "Sure. What service do you need?"

        if step == 1:
            state["data"]["service"] = text
            state["step"] = 2
            return "Please provide preferred date."

        if step == 2:
            state["data"]["date"] = text
            state["step"] = 3
            return "Please provide preferred time."

        if step == 3:
            conversation_state[user_id] = {
                "flow": None,
                "step": 0,
                "data": {},
                "greeted": True
            }
            return "Your appointment has been booked successfully."

   
    if intent == "complaint" or flow == "complaint":

        if flow != "complaint":
            state["flow"] = "complaint"
            state["step"] = 1
            return "Please describe your issue."

        if step == 1:
            state["data"]["issue"] = text
            state["step"] = 2
            return "Please provide your address."

        if step == 2:
            issue = state["data"]["issue"]
            ticket = database.create_ticket(issue)

            conversation_state[user_id] = {
                "flow": None,
                "step": 0,
                "data": {},
                "greeted": True
            }

            return f"Your complaint has been registered. Ticket ID {ticket}."

    
    return """I am Nexora AI assistant designed for:
Public service requests
Customer support
Surveys
Grievance systems
Outreach campaigns"""


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():

    data = request.json
    user_id = data.get("user_id")
    message = data.get("message")

    reply = process_message(user_id, message)

    return jsonify({"response": reply})


@app.route("/dashboard")
def dashboard():

    data = database.get_dashboard_data()

    return render_template("dashboard.html", data=data)


if __name__ == "__main__":
    app.run(debug=True)
