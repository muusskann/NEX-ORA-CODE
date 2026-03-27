import sqlite3


class Database:

    def __init__(self):
        self.init_db()

    def init_db(self):

        conn = sqlite3.connect("nexora.db")
        cur = conn.cursor()

        # ✅ UPDATED conversations table (user_id added)
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS conversations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        user_text TEXT,
        intent TEXT,
        flow TEXT
        )
        """
        )

        # ✅ UPDATED tickets table (call_type added)
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS tickets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue TEXT,
        call_status TEXT,
        call_type TEXT
        )
        """
        )

        conn.commit()
        conn.close()

    # ✅ UPDATED (user_id added)
    def save_conversation(self, user_id, text, intent, flow):

        conn = sqlite3.connect("nexora.db")
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO conversations(user_id,user_text,intent,flow) VALUES(?,?,?,?)",
            (user_id, text, intent, flow),
        )

        conn.commit()
        conn.close()

    # ✅ UPDATED (call_type added)
    def create_ticket(self, issue, call_type):

        conn = sqlite3.connect("nexora.db")
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO tickets(issue, call_status, call_type) VALUES(?,?,?)",
            (issue, "pending", call_type),
        )

        ticket_id = cur.lastrowid

        conn.commit()
        conn.close()

        return ticket_id

    def mark_called(self):

        conn = sqlite3.connect("nexora.db")
        cur = conn.cursor()

        cur.execute(
            "UPDATE tickets SET call_status='called' WHERE call_status='pending'",
        )

        conn.commit()
        conn.close()

    def get_dashboard_data(self):

        conn = sqlite3.connect("nexora.db")
        cur = conn.cursor()

        # total conversations (unique users)
        cur.execute("SELECT COUNT(DISTINCT user_id) FROM conversations")
        conversations = cur.fetchone()[0]

        # total tickets
        cur.execute("SELECT COUNT(*) FROM tickets")
        tickets = cur.fetchone()[0]

        # total complaints (unique users)
        cur.execute(
            "SELECT COUNT(DISTINCT user_id) FROM conversations WHERE intent='complaint'"
        )
        complaints = cur.fetchone()[0]

        # escalation count
        cur.execute(
            """
        SELECT COUNT(*) FROM conversations
        WHERE user_text LIKE '%payment%'
        OR user_text LIKE '%money%'
        OR user_text LIKE '%upi%'
        OR user_text LIKE '%transaction%'
        """
        )
        escalations = cur.fetchone()[0]

        # graph data
        cur.execute(
            """
        SELECT intent, COUNT(*) 
        FROM conversations 
        WHERE intent NOT IN ('bot','unknown')
        GROUP BY intent
        """
        )
        graph_data = cur.fetchall()

        # latest message per user
        cur.execute(
            """
        SELECT user_id, user_text, flow
        FROM conversations
        ORDER BY user_id,id ASC
        """
        )
        rows = cur.fetchall()

        # ✅ UPDATED CALL LOGIC (from tickets instead of conversations)
        cur.execute(
            """
        SELECT call_type FROM tickets
        WHERE call_status='pending'
        ORDER BY id DESC LIMIT 1
        """
        )

        call_row = cur.fetchone()
        call_type = call_row[0] if call_row else None

        conn.commit()
        conn.close()

        return {
            "conversations": conversations,
            "tickets": tickets,
            "complaints": complaints,
            "escalations": escalations,
            "rows": rows,
            "graph_data": graph_data,
            "call_type": call_type,
        }
