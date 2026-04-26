import sqlite3

def migrate():
    conn = sqlite3.connect("bot.db")
    try:
        conn.execute("DROP TABLE IF EXISTS session_results;")
        conn.execute("DROP TABLE IF EXISTS exports;")
        conn.execute("DROP TABLE IF EXISTS sessions;")
        conn.commit()
        print("Dropped old tables successfully.")
    except Exception as e:
        print(f"Error dropping tables: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
