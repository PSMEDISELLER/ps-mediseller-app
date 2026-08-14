import streamlit as st
import sqlite3
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import json
import math

# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(page_title="P.S Mediseller", page_icon="🚚", layout="wide")

# =========================================================
# DATABASE SETUP
# =========================================================
DB_FILE = "mediseller_delivery.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# টেবিল তৈরি
c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL, role TEXT NOT NULL)")
c.execute("CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY AUTOINCREMENT, party_name TEXT NOT NULL UNIQUE, address TEXT, party_phone TEXT UNIQUE, lat REAL, lon REAL)")
c.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, party_name TEXT NOT NULL, order_details TEXT, order_date TEXT NOT NULL, status TEXT DEFAULT 'Pending')")
c.execute("CREATE TABLE IF NOT EXISTS task_assignments (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_name TEXT NOT NULL, party_name TEXT NOT NULL, task_type TEXT NOT NULL, due_amount TEXT DEFAULT '0', status TEXT DEFAULT 'Pending', created_at TEXT NOT NULL)")
c.execute("CREATE TABLE IF NOT EXISTS agent_live_locations (username TEXT PRIMARY KEY, lat REAL, lon REAL, last_updated TEXT, completed_deliveries INTEGER DEFAULT 0, completed_dues INTEGER DEFAULT 0)")

# ডিফল্ট ইউজার তৈরি (যদি না থাকে)
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
    c.execute("INSERT INTO users VALUES (?, ?, ?)", ("admin", "admin123", "admin"))
    c.execute("INSERT INTO users VALUES (?, ?, ?)", ("staff1", "123", "staff"))
    conn.commit()

# =========================================================
# LOGIN SYSTEM
# =========================================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("🔑 পি এস মেডিসেলার লগইন")
    
    c.execute("SELECT username, role FROM users")
    all_users = c.fetchall()
    user_map = {u[0]: u[1] for u in all_users}
    
    selected_user = st.selectbox("আপনার আইডি সিলেক্ট করুন", list(user_map.keys()))
    role = user_map[selected_user]

    if role == "admin":
        password = st.text_input("পাসওয়ার্ড দিন", type="password")
        if st.button("🔒 অ্যাডমিন লগইন"):
            c.execute("SELECT password FROM users WHERE username=?", (selected_user,))
            if c.fetchone()[0] == password:
                st.session_state["logged_in"] = True
                st.session_state["username"] = selected_user
                st.session_state["role"] = "admin"
                st.rerun()
            else:
                st.error("ভুল পাসওয়ার্ড!")
    else:
        if st.button("🚀 প্রবেশ করুন (পাসওয়ার্ড লাগবে না)"):
            st.session_state["logged_in"] = True
            st.session_state["username"] = selected_user
            st.session_state["role"] = "staff"
            st.rerun()
    st.stop()

# =========================================================
# MAIN APP
# =========================================================
st.sidebar.title(f"👤 {st.session_state['username']}")
if st.sidebar.button("🚪 লগআউট"):
    st.session_state["logged_in"] = False
    st.rerun()

menu = ["📍 নতুন এন্ট্রি", "🔍 সার্চ ও ম্যানেজমেন্ট", "📦 পেন্ডিং অর্ডার", "📋 ডেলিভারি প্ল্যান", "📊 লাইভ ট্র্যাকিং", "⚙️ সেটিংস"]
choice = st.sidebar.radio("মেনু", menu)

# --- নতুন এন্ট্রি ---
if choice == "📍 নতুন এন্ট্রি":
    st.header("📍 নতুন লোকেশন ও অর্ডার এন্ট্রি")
    with st.form("new_entry"):
        p_name = st.text_input("পার্টির নাম")
        p_phone = st.text_input("ফোন নম্বর")
        p_addr = st.text_input("ঠিকানা")
        if st.form_submit_button("সেভ করুন"):
            try:
                c.execute("INSERT INTO locations (party_name, address, party_phone) VALUES (?, ?, ?)", (p_name, p_addr, p_phone))
                conn.commit()
                st.success("সেভ হয়েছে!")
            except:
                st.error("এই নামে বা নম্বরে আগেই এন্ট্রি আছে।")

# --- সার্চ ও ম্যানেজমেন্ট ---
elif choice == "🔍 সার্চ ও ম্যানেজমেন্ট":
    st.header("🔍 সার্চ করুন")
    search = st.text_input("নাম, ফোন বা ঠিকানা দিয়ে সার্চ করুন")
    if search:
        df = pd.read_sql_query(f"SELECT * FROM locations WHERE party_name LIKE '%{search}%' OR party_phone LIKE '%{search}%'", conn)
        st.dataframe(df)
        if st.session_state["role"] == "admin":
            if st.button("সব ডিলিট করুন (সতর্কতা)"):
                c.execute("DELETE FROM locations WHERE party_name LIKE '%{search}%'")
                conn.commit()

# --- পেন্ডিং অর্ডার ---
elif choice == "📦 পেন্ডিং অর্ডার":
    st.header("📦 পেন্ডিং অর্ডার")
    orders = pd.read_sql_query("SELECT * FROM orders WHERE status='Pending'", conn)
    st.table(orders)

# --- ডেলিভারি প্ল্যান ---
elif choice == "📋 ডেলিভারি প্ল্যান":
    st.header("📋 কাজ অ্যাসাইন করুন")
    agents = [u[0] for u in c.execute("SELECT username FROM users WHERE role='staff'").fetchall()]
    sel_agent = st.selectbox("এজেন্ট", agents)
    parties = [p[0] for p in c.execute("SELECT party_name FROM locations").fetchall()]
    sel_party = st.selectbox("পার্টি", parties)
    
    if st.button("কাজ দিন"):
        c.execute("INSERT INTO task_assignments (agent_name, party_name, task_type, created_at) VALUES (?, ?, ?, ?)", 
                  (sel_agent, sel_party, "ডেলিভারি", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        st.success("অ্যাসাইন করা হয়েছে!")

# --- লাইভ ট্র্যাকিং (শুধু অ্যাডমিন) ---
elif choice == "📊 লাইভ ট্র্যাকিং":
    if st.session_state["role"] == "admin":
        st.header("📊 এজেন্ট ট্র্যাকিং")
        agents_data = pd.read_sql_query("SELECT * FROM agent_live_locations", conn)
        st.dataframe(agents_data)
    else:
        st.warning("আপনি এই পেজটি দেখার অনুমতি পাননি।")

# --- সেটিংস ---
elif choice == "⚙️ সেটিংস":
    if st.session_state["role"] == "admin":
        st.header("⚙️ ইউজার ম্যানেজমেন্ট")
        new_u = st.text_input("নতুন ইউজার")
        new_p = st.text_input("পাসওয়ার্ড", type="password")
        if st.button("যোগ করুন"):
            c.execute("INSERT INTO users VALUES (?, ?, ?)", (new_u, new_p, "staff"))
            conn.commit()
            st.rerun()
    else:
        st.info("আপনার এখানে কোনো সেটিংস নেই।")
