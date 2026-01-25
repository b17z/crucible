# BAD: SQL injection vulnerability
import sqlite3


def get_user(username: str) -> dict:
    """Fetch user by username - VULNERABLE to SQL injection."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # BAD: String formatting in SQL query
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()


def delete_user(user_id: str) -> None:
    """Delete user - VULNERABLE to SQL injection."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # BAD: Direct string concatenation
    cursor.execute("DELETE FROM users WHERE id = " + user_id)
    conn.commit()
