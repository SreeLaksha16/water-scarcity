"""
WaterScarcity Compass authentication module.
Uses a separate users.db and does not modify the existing water warehouse.
"""
import hashlib
import hmac
import os
import sqlite3
import streamlit as st

AUTH_DB = os.path.join(os.path.dirname(__file__), "users.db")
_ITERATIONS = 240_000


def _connect():
    conn = sqlite3.connect(AUTH_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def _hash_password(password, salt_hex):
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return digest.hex()


def _create_account(email, password):
    email = email.strip().lower()
    salt_hex = os.urandom(16).hex()
    password_hash = _hash_password(password, salt_hex)
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO users(email, password_hash, salt) VALUES (?, ?, ?)",
                (email, password_hash, salt_hex),
            )
        return True, "Account created. Please sign in."
    except sqlite3.IntegrityError:
        return False, "An account with that email already exists."


def _check_login(email, password):
    email = email.strip().lower()
    with _connect() as conn:
        row = conn.execute(
            "SELECT password_hash, salt FROM users WHERE email = ?", (email,)
        ).fetchone()
    if not row:
        return False
    stored_hash, salt_hex = row
    supplied_hash = _hash_password(password, salt_hex)
    return hmac.compare_digest(stored_hash, supplied_hash)


def require_auth():
    """Show login/register and stop the app until a user is authenticated."""
    if st.session_state.get("authenticated", False):
        with st.sidebar:
            st.caption("Signed in as")
            st.write(st.session_state.get("user_email", ""))
            if st.button("Log out", key="auth_logout"):
                st.session_state.authenticated = False
                st.session_state.user_email = ""
                st.rerun()
        return

    st.markdown("""
    <div style="text-align:center;padding:1.5rem 0 0.5rem">
      <h1>💧 WaterScarcity Compass</h1>
      <p>Regional Water Monitoring and Water-Stress Intelligence</p>
    </div>
    """, unsafe_allow_html=True)

    login_tab, register_tab = st.tabs(["Sign In", "Create Account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email address", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)
        if submitted:
            if _check_login(email, password):
                st.session_state.authenticated = True
                st.session_state.user_email = email.strip().lower()
                st.success("Login successful.")
                st.rerun()
            else:
                st.error("Email or password is incorrect.")

    with register_tab:
        with st.form("register_form"):
            new_email = st.text_input("Email address", key="register_email")
            new_password = st.text_input("Password", type="password", key="register_password")
            confirm_password = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create Account", use_container_width=True)
        if submitted:
            if not new_email.strip() or "@" not in new_email or "." not in new_email.split("@")[-1]:
                st.error("Please enter a valid email address.")
            elif len(new_password) < 8:
                st.error("Password must be at least 8 characters long.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                ok, message = _create_account(new_email, new_password)
                if ok:
                    st.success(message)
                else:
                    st.error(message)

    st.stop()
