# BAD: Hardcoded secrets
# Note: semgrep p/bandit doesn't catch these, but native bandit does (B105, B106)
import mysql.connector

import requests


def call_api(endpoint: str) -> dict:
    """Call external API with hardcoded key."""
    # BAD: Hardcoded API key in header
    headers = {"Authorization": "Bearer sk-1234567890abcdef1234567890abcdef"}
    return requests.get(endpoint, headers=headers, timeout=10).json()


def connect_db() -> None:
    """Connect to database with hardcoded password - B106."""
    # BAD: password= kwarg with string literal
    conn = mysql.connector.connect(
        host="localhost",
        user="admin",
        password="super_secret_password_123",  # B106: hardcoded_password_funcarg
    )
    return conn


# BAD: Hardcoded password in dict - B105
DATABASE_CONFIG = {
    "host": "localhost",
    "user": "admin",
    "PASSWORD": "another_secret_123",  # B105: hardcoded_password_string
}


def get_secret() -> str:
    """Return hardcoded secret - B105."""
    password = "hardcoded_password"  # B105
    return password
