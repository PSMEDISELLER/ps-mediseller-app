from datetime import datetime, timedelta
import urllib.parse
import folium
from folium.plugins import MousePosition
import pandas as pd
import sqlite3
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation, streamlit_js_eval

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

# ইউজার টেবিল চেক ও আপডেট
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
""")
# নতুন কলাম যোগ করা (যদি না থাকে)
c.execute("PRAGMA table_info(users)")
existing_user_cols = [row[1] for row in c.fetchall()]
if "fullname" not in existing_user_cols:
    c.execute("ALTER TABLE users ADD COLUMN fullname TEXT")
if "created_at" not in existing_user_cols:
    c.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
conn.commit()

# অন্যান্য টেবিল
c.execute("CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY AUTOINCREMENT, party_name TEXT NOT NULL UNIQUE, address TEXT, party_phone TEXT UNIQUE, lat REAL, lon REAL, route_order INTEGER DEFAULT 0)")
c.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, party_name TEXT NOT NULL, order_details TEXT, order_date TEXT NOT NULL, status TEXT DEFAULT 'Pending', payment_collected TEXT DEFAULT '0')")
c.execute("CREATE TABLE IF NOT EXISTS agent_live_locations (username TEXT PRIMARY KEY, lat REAL, lon REAL, last_updated TEXT, completed_deliveries INTEGER DEFAULT 0, completed_dues INTEGER DEFAULT 0)")
c.execute("CREATE TABLE IF NOT EXISTS task_assignments (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_name TEXT NOT NULL, party_name TEXT NOT NULL, task_type TEXT NOT NULL, due_amount TEXT DEFAULT '0', status TEXT DEFAULT 'Pending', created_at TEXT NOT NULL)")

conn.commit()

# ডিফল্ট ইউজার তৈরি
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
  c.execute("INSERT INTO users (username, password, role, fullname, created_at) VALUES (?, ?, ?, ?, ?)", ("admin", "admin123", "admin", "Admin", datetime.now()))
  c.execute("INSERT INTO users (username, password, role, fullname, created_at) VALUES (?, ?, ?, ?, ?)", ("delivery", "user123", "staff", "Delivery Agent", datetime.now()))
  conn.commit()

# =========================================================
# (বাকি কোড আগের মতোই, শুধুমাত্র সেটিংস ও নতুন এজেন্ট সেকশনে পরিবর্তন করা হয়েছে)
# =========================================================

# ... (GPS ও অন্যান্য ফাংশন আগের মতোই থাকবে, এখানে শুধু মূল অংশগুলো দেখাচ্ছি) ...

# =========================================================
# 7. সেটিংস ও এজেন্ট ম্যানেজমেন্ট (আপডেটেড)
# =========================================================
# (কোডের মাঝের অংশগুলো আগের মতোই থাকবে, নিচে শুধু এই অংশটি রিপ্লেস করুন)
# =========================================================

# (আপনার আগের কোডের শেষে থাকা 'elif selected_menu == "⚙️ সেটিংস ও এজেন্ট ম্যানেজমেন্ট":' অংশটি নিচের কোড দিয়ে পরিবর্তন করুন)

if selected_menu == "⚙️ সেটিংস ও এজেন্ট ম্যানেজমেন্ট":
  if st.session_state["user_role"] != "admin":
    st.error("এই পেজটি শুধুমাত্র অ্যাডমিনের জন্য।")
  else:
    st.write("### 👥 ডেলিভারি এজেন্ট তালিকা ও ম্যানেজমেন্ট")
    
    # ডেটা আনা
    c.execute("SELECT username, role, fullname, created_at FROM users")
    agents = c.fetchall()
    st.write(f"মোট রেজিস্টার্ড ইউজার/এজেন্ট সংখ্যা: **{len(agents)}**")

    for ag in agents:
      u_name, u_role, f_name, c_date = ag
      # নাম না থাকলে ডিফল্ট দেখাবে
      display_name = f_name if f_name else "নাম নেই"
      join_date = c_date if c_date else "অজানা"
      
      with st.expander(f"👤 {display_name} (ইউজারনেম: {u_name})"):
        st.write(f"📅 যোগদানের তারিখ: `{join_date}`")
        
        with st.form(f"edit_form_{u_name}"):
          new_name = st.text_input("প্রকৃত নাম এডিট করুন", value=display_name, key=f"fname_{u_name}")
          
          if u_role == "admin":
            new_pass = st.text_input("নতুন পাসওয়ার্ড দিন", type="password", key=f"pass_{u_name}")
          
          update_btn = st.form_submit_button("পরিবর্তন সেভ করুন")
          
          if update_btn:
            if u_role == "admin":
              if new_pass.strip():
                c.execute("UPDATE users SET fullname=?, password=? WHERE username=?", (new_name, new_pass, u_name))
                conn.commit()
                st.success("সফলভাবে আপডেট হয়েছে!")
                st.rerun()
              else:
                st.warning("পাসওয়ার্ড খালি রাখা যাবে না।")
            else:
              c.execute("UPDATE users SET fullname=? WHERE username=?", (new_name, u_name))
              conn.commit()
              st.success("সফলভাবে আপডেট হয়েছে!")
              st.rerun()

    st.write("---")
    st.write("### ➕ নতুন এজেন্ট যোগ করুন")
    with st.form("new_agent_form"):
      n_fullname = st.text_input("এজেন্টের প্রকৃত নাম (পুরো নাম)")
      n_user = st.text_input("ইউজারনেম (লগইন আইডি)")
      n_pass = st.text_input("পাসওয়ার্ড", type="password")
      n_role = st.selectbox("রোল", ["staff", "admin"])
      add_agent_btn = st.form_submit_button("এজেন্ট যুক্ত করুন")

      if add_agent_btn:
        if n_fullname and n_user and n_pass:
          try:
            c.execute("INSERT INTO users (username, password, role, fullname, created_at) VALUES (?, ?, ?, ?, ?)", 
                      (n_user, n_pass, n_role, n_fullname, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            st.success(f"নতুন এজেন্ট '{n_fullname}' সফলভাবে যোগ করা হয়েছে!")
            st.rerun()
          except Exception as e:
            st.error("এই ইউজারনেমটি আগেই রয়েছে।")
        else:
          st.error("সব ঘর পূরণ করুন।")
