import sqlite3

class Database:

    def __init__(self):
        self.init_db()

    def init_db(self):

        conn=sqlite3.connect("nexora.db")
        cur=conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_text TEXT,
        intent TEXT,
        flow TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue TEXT
        )
        """)

        conn.commit()
        conn.close()

    def save_conversation(self,text,intent,flow):

        conn=sqlite3.connect("nexora.db")
        cur=conn.cursor()

        cur.execute(
        "INSERT INTO conversations(user_text,intent,flow) VALUES(?,?,?)",
        (text,intent,flow)
        )

        conn.commit()
        conn.close()

    def create_ticket(self,issue):

        conn=sqlite3.connect("nexora.db")
        cur=conn.cursor()

        cur.execute("INSERT INTO tickets(issue) VALUES(?)",(issue,))
        ticket_id=cur.lastrowid

        conn.commit()
        conn.close()

        return ticket_id

    def get_dashboard_data(self):

        conn=sqlite3.connect("nexora.db")
        cur=conn.cursor()

        cur.execute("SELECT COUNT(*) FROM conversations")
        conversations=cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM tickets")
        tickets=cur.fetchone()[0]

        conn.close()

        return {"conversations":conversations,"tickets":tickets}