from datetime import datetime, timedelta
import folium
from folium.plugins import MousePosition
import pandas as pd
import sqlite3
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation, streamlit_js_eval
import math


# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="P.S Mediseller",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# DATABASE SETUP
# =========================================================
DB_FILE = "mediseller_delivery.db"


def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


conn = get_db_connection()
c = conn.cursor()


# =========================================================
# CREATE TABLES
# =========================================================
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    party_name TEXT NOT NULL,
    address TEXT,
    party_phone TEXT,
    lat REAL,
    lon REAL,
    route_order INTEGER DEFAULT 0
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    party_name TEXT NOT NULL,
    order_details TEXT,
    order_date TEXT NOT NULL,
    status TEXT DEFAULT 'Pending',
    payment_collected TEXT DEFAULT '0'
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS agent_live_locations (
    username TEXT PRIMARY KEY,
    lat REAL,
    lon REAL,
    last_updated TEXT,
    completed_deliveries INTEGER DEFAULT 0,
    completed_dues INTEGER DEFAULT 0
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS task_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    party_name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    due_amount TEXT DEFAULT '0',
    status TEXT DEFAULT 'Pending',
    created_at TEXT NOT NULL
)
""")


# =========================================================
# DATABASE MIGRATION / COLUMN CHECK
# =========================================================

c.execute("PRAGMA table_info(locations)")
existing_cols_loc = [row[1] for row in c.fetchall()]

if "party_phone" not in existing_cols_loc:
    c.execute("ALTER TABLE locations ADD COLUMN party_phone TEXT")


c.execute("PRAGMA table_info(orders)")
existing_cols_ord = [row[1] for row in c.fetchall()]

if "payment_collected" not in existing_cols_ord:
    c.execute(
        "ALTER TABLE orders ADD COLUMN payment_collected TEXT DEFAULT '0'"
    )

if "status" not in existing_cols_ord:
    c.execute(
        "ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'Pending'"
    )


c.execute("PRAGMA table_info(agent_live_locations)")
existing_cols_agent = [row[1] for row in c.fetchall()]

if "completed_deliveries" not in existing_cols_agent:
    c.execute(
        "ALTER TABLE agent_live_locations "
        "ADD COLUMN completed_deliveries INTEGER DEFAULT 0"
    )

if "completed_dues" not in existing_cols_agent:
    c.execute(
        "ALTER TABLE agent_live_locations "
        "ADD COLUMN completed_dues INTEGER DEFAULT 0"
    )

conn.commit()


# =========================================================
# DEFAULT USERS
# =========================================================
c.execute("SELECT COUNT(*) FROM users")

if c.fetchone()[0] == 0:

    c.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin", "admin123", "admin")
    )

    c.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        ("delivery", "user123", "staff")
    )

    conn.commit()


# =========================================================
# AUTO DELETE SYSTEM
# Pending orders/tasks older than 24 hours will be deleted
# =========================================================

current_dt = datetime.now()


# Pending Orders
c.execute(
    "SELECT id, order_date FROM orders WHERE status='Pending'"
)

for row_ord in c.fetchall():

    try:
        order_time = datetime.strptime(
            row_ord[1],
            "%Y-%m-%d %H:%M:%S"
        )

        if (current_dt - order_time) > timedelta(hours=24):

            c.execute(
                "DELETE FROM orders WHERE id=?",
                (row_ord[0],)
            )

    except Exception:
        pass


# Pending Tasks
c.execute(
    "SELECT id, created_at FROM task_assignments WHERE status='Pending'"
)

for row_task in c.fetchall():

    try:
        task_time = datetime.strptime(
            row_task[1],
            "%Y-%m-%d %H:%M:%S"
        )

        if (current_dt - task_time) > timedelta(hours=24):

            c.execute(
                "DELETE FROM task_assignments WHERE id=?",
                (row_task[0],)
            )

    except Exception:
        pass


conn.commit()


# =========================================================
# SEARCHABLE SELECTBOX
# =========================================================
def searchable_selectbox(
    label,
    options,
    key,
    placeholder="-- সিলেক্ট করুন --"
):
    """
    Streamlit-এর নিজস্ব searchable selectbox ব্যবহার করা হয়েছে।

    ব্যবহারকারী box-এর ভিতরে:
        A
        R
        Ra
        Raj
    ইত্যাদি টাইপ করলে matching option dropdown-এ
    automatically filter হবে।
    """

    clean_options = []

    for item in options:
        if item is not None:
            item = str(item).strip()

            if item and item not in clean_options:
                clean_options.append(item)

    final_options = [placeholder] + clean_options

    return st.selectbox(
        label,
        final_options,
        index=0,
        key=key,
        help=(
            "এই বক্সে ক্লিক করে ১–২টি অক্ষর টাইপ করুন। "
            "মিল থাকা নামগুলো dropdown-এ দেখাবে।"
        )
    )


# =========================================================
# PERMANENT LOCAL STORAGE LOGIN
# =========================================================

if "selected_lat" not in st.session_state:
    st.session_state["selected_lat"] = 22.8620

if "selected_lon" not in st.session_state:
    st.session_state["selected_lon"] = 87.3320


local_user = streamlit_js_eval(
    js_expressions="localStorage.getItem('ps_perma_user')",
    key="get_local_user"
)


if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False


if not st.session_state["logged_in"] and local_user:

    c.execute(
        "SELECT role FROM users WHERE username=?",
        (local_user,)
    )

    r_data = c.fetchone()

    if r_data:

        st.session_state["logged_in"] = True
        st.session_state["username"] = local_user
        st.session_state["user_role"] = r_data[0]


# =========================================================
# LOGIN SCREEN
# =========================================================

if not st.session_state.get("logged_in", False):

    st.title("🔑 পি এস মেডিসেলার - লগইন পোর্টাল")

    st.write(
        "একবার লগইন করলে বারবার পাসওয়ার্ড দিতে হবে না।"
    )

    c.execute("SELECT username FROM users")

    all_users = [
        row[0]
        for row in c.fetchall()
    ]

    with st.form("login_form_perma"):

        sel_user = searchable_selectbox(
            "ইউজারনেম নির্বাচন করুন",
            all_users,
            key="login_username_select",
            placeholder="-- ইউজারনেম সিলেক্ট করুন --"
        )

        input_pass = st.text_input(
            "পাসওয়ার্ড দিন",
            type="password"
        )

        submit_login = st.form_submit_button(
            "🔒 স্থায়ীভাবে লগইন করুন",
            type="primary"
        )

        if submit_login:

            if sel_user == "-- ইউজারনেম সিলেক্ট করুন --":

                st.error("প্রথমে ইউজারনেম নির্বাচন করুন।")

            else:

                c.execute(
                    "SELECT password, role FROM users WHERE username=?",
                    (sel_user,)
                )

                user_row = c.fetchone()

                if user_row and user_row[0] == input_pass:

                    st.session_state["logged_in"] = True
                    st.session_state["username"] = sel_user
                    st.session_state["user_role"] = user_row[1]

                    safe_user = sel_user.replace("'", "\\'")

                    streamlit_js_eval(
                        js_expressions=(
                            "localStorage.setItem("
                            "'ps_perma_user', "
                            f"'{safe_user}'"
                            ")"
                        ),
                        key="set_local_user"
                    )

                    st.success(
                        "লগইন সফল হয়েছে!"
                    )

                    st.rerun()

                else:

                    st.error(
                        "❌ ভুল পাসওয়ার্ড!"
                    )

    st.stop()


# =========================================================
# MAIN APP HEADER
# =========================================================

st.title(
    "পি এস মেডিসেলার ডেলিভারি পার্টনার"
)


col_u1, col_u3 = st.columns([3, 1])


with col_u1:

    st.write(
        f"👤 ইউজার: "
        f"**{st.session_state['username']}** "
        f"(`{st.session_state['user_role']}`)"
    )


with col_u3:

    if st.button("🚪 লগআউট"):

        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.session_state["user_role"] = None

        streamlit_js_eval(
            js_expressions=(
                "localStorage.removeItem('ps_perma_user')"
            ),
            key="clear_local_user"
        )

        st.rerun()


st
