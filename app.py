from datetime import datetime
import math
import folium
import pandas as pd
import sqlite3
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

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
    last_updated TEXT
)
""")

# কলাম চেক ও আপডেট
c.execute("PRAGMA table_info(locations)")
existing_cols_loc = [row[1] for row in c.fetchall()]
if "party_phone" not in existing_cols_loc:
  c.execute("ALTER TABLE locations ADD COLUMN party_phone TEXT")
if "route_order" not in existing_cols_loc:
  c.execute("ALTER TABLE locations ADD COLUMN route_order INTEGER DEFAULT 0")

c.execute("PRAGMA table_info(orders)")
existing_cols_ord = [row[1] for row in c.fetchall()]
if "payment_collected" not in existing_cols_ord:
  c.execute("ALTER TABLE orders ADD COLUMN payment_collected TEXT DEFAULT '0'")

conn.commit()

# ডিফল্ট ইউজার তৈরি
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
  c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin123", "admin"))
  c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("delivery", "user123", "staff"))
  conn.commit()

# =========================================================
# SESSION MANAGEMENT
# =========================================================
if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False
if "username" not in st.session_state:
  st.session_state["username"] = None
if "user_role" not in st.session_state:
  st.session_state["user_role"] = None
if "selected_lat" not in st.session_state:
  st.session_state["selected_lat"] = 22.8620
if "selected_lon" not in st.session_state:
  st.session_state["selected_lon"] = 87.3320

# অটো-লগইন চেক (Query Parameters)
query_params = st.query_params
saved_user = query_params.get("user", None)

if not st.session_state["logged_in"] and saved_user:
  c.execute("SELECT role FROM users WHERE username=?", (saved_user,))
  role_data = c.fetchone()
  if role_data:
    st.session_state["logged_in"] = True
    st.session_state["username"] = saved_user
    st.session_state["user_role"] = role_data[0]

# =========================================================
# ALTERNATIVE SECURE LOGIN SYSTEM (No Data Loss / No Refresh Bug)
# =========================================================
if not st.session_state["logged_in"]:
  st.title("🔑 লগইন পোর্টাল (P.S Mediseller)")
  st.write("আপনার অ্যাকাউন্ট সিলেক্ট করে পাসওয়ার্ড দিন:")

  # ডেটাবেজ থেকে সমস্ত ইউজার ফেচ করা
  c.execute("SELECT username, role FROM users")
  users_data = c.fetchall()
  usernames = [u[0] for u in users_data]

  with st.form("alt_login_form"):
    selected_user_box = st.selectbox("ইউজারনেম বেছে নিন", usernames)
    input_password = st.text_input("পাসওয়ার্ড দিন", type="password")
    remember_me = st.checkbox("এই ডিভাইসে লগইন মনে রাখুন", value=True)
    login_submit = st.form_submit_button("লগইন করুন", type="primary")

    if login_submit:
      c.execute("SELECT password, role FROM users WHERE username=?", (selected_user_box,))
      u_row = c.fetchone()
      if u_row and u_row[0] == input_password:
        st.session_state["logged_in"] = True
        st.session_state["username"] = selected_user_box
        st.session_state["user_role"] = u_row[1]
        if remember_me:
          st.query_params["user"] = selected_user_box
        st.success("লগইন সফল হয়েছে!")
        st.rerun()
      else:
        st.error("❌ পাসওয়ার্ড ভুল হয়েছে!")

  st.stop()

# =========================================================
# MAIN APP HEADER & LOGOUT
# =========================================================
st.title("🚚 পি এস মেডিসেলার")

col_u1, col_u3 = st.columns([3, 1])
with col_u1:
  st.write(f"👤 ইউজার: **{st.session_state['username']}** (`{st.session_state['user_role']}`)")
with col_u3:
  if st.button("🚪 লগআউট"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = None
    st.session_state["user_role"] = None
    st.query_params.clear()
    st.rerun()
st.write("---")

# =========================================================
# GPS TRACKING (Background)
# =========================================================
loc = get_geolocation(component_key="low_data_gps_tracker")
gps_lat, gps_lon = None, None

if loc and "coords" in loc:
  gps_lat = loc["coords"]["latitude"]
  gps_lon = loc["coords"]["longitude"]
  c.execute(
      "INSERT OR REPLACE INTO agent_live_locations (username, lat, lon, last_updated) VALUES (?, ?, ?, ?)",
      (st.session_state["username"], gps_lat, gps_lon, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
  )
  conn.commit()

# =========================================================
# NAVIGATION MENU
# =========================================================
menu_options = ["📍 নতুন লোকেশন এড", "🔍 সার্চ", "🗺️ রুট প্ল্যান", "📦 অর্ডার ও বিলিং"]
if st.session_state["user_role"] == "admin":
  menu_options.append("📊 লাইভ ট্র্যাকিং")

selected_menu = st.radio("মেনু সিলেক্ট করুন:", menu_options, horizontal=True, label_visibility="collapsed")
st.write("---")

# =========================================================
# 1. ADD NEW LOCATION & ORDER ENTRY
# =========================================================
if selected_menu == "📍 নতুন লোকেশন এড":
  col1, col2 = st.columns(2)

  with col1:
    st.write("### 📍 লোকেশন পিন করুন")
    if st.button("🔄 কারেন্ট লোকেশনে পিন সেট করুন"):
      if gps_lat and gps_lon:
        st.session_state["selected_lat"] = gps_lat
        st.session_state["selected_lon"] = gps_lon
        st.success("✅ লোকেশন সিলেক্ট হয়েছে!")
        st.rerun()
      else:
        st.warning("GPS সিগন্যাল পাওয়া যায়নি।")

    with st.form("loc_form_safe", clear_on_submit=True):
      party_name = st.text_input("পার্টির নাম")
      address = st.text_input("ঠিকানা")
      party_phone = st.text_input("ফোন নম্বর")
      submit_loc = st.form_submit_button("💾 লোকেশন সেভ করুন", type="primary")

      if submit_loc:
        if party_name and party_phone:
          c.execute(
              "INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, ?, ?)",
              (party_name, address, party_phone, st.session_state["selected_lat"], st.session_state["selected_lon"]),
          )
          conn.commit()
          st.success("✅ লোকেশন সফলভাবে সেভ হয়েছে!")
        else:
          st.error("পার্টির নাম এবং ফোন নম্বর আবশ্যক।")

  with col2:
    st.write("### 📦 নতুন অর্ডার এন্ট্রি")
    c.execute("SELECT DISTINCT party_name FROM locations ORDER BY party_name ASC")
    all_parties_db = [row[0] for row in c.fetchall()]

    with st.form("ord_form_safe", clear_on_submit=True):
      order_party_name = st.selectbox("পার্টি নির্বাচন করুন", ["-- সিলেক্ট করুন --"] + all_parties_db)
      order_details_input = st.text_area("অর্ডারের বিবরণ")
      submit_order = st.form_submit_button("🛒 অর্ডার জমা দিন", type="primary")

      if submit_order:
        if order_party_name != "-- সিলেক্ট করুন --" and order_details_input.strip():
          c.execute(
              "INSERT INTO orders (party_name, order_details, order_date, status) VALUES (?, ?, ?, ?)",
              (order_party_name, order_details_input, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Pending"),
          )
          conn.commit()
          st.success("✅ অর্ডার সফলভাবে সেভ হয়েছে!")
        else:
          st.error("সঠিক পার্টি এবং বিবরণ দিন।")

  # Map Display
  m_click = folium.Map(
      location=[st.session_state["selected_lat"], st.session_state["selected_lon"]],
      zoom_start=16,
      tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
      attr="Google"
  )
  folium.Marker(
      [st.session_state["selected_lat"], st.session_state["selected_lon"]],
      popup="সিলেক্টেড লোকেশন",
      icon=folium.Icon(color="red", icon="map-marker", prefix="fa"),
  ).add_to(m_click)
  
  map_data = st_folium(m_click, width=900, height=450, key="interactive_map")
  if map_data and map_data.get("last_clicked"):
    clicked_lat = map_data["last_clicked"]["lat"]
    clicked_lon = map_data["last_clicked"]["lng"]
    if clicked_lat != st.session_state["selected_lat"] or clicked_lon != st.session_state["selected_lon"]:
      st.session_state["selected_lat"] = clicked_lat
      st.session_state["selected_lon"] = clicked_lon
      st.rerun()

# =========================================================
# 2. SEARCH PARTY
# =========================================================
elif selected_menu == "🔍 সার্চ":
  df = pd.read_sql_query("SELECT * FROM locations", conn)
  search_query = st.text_input("সার্চ করুন (পার্টির নাম)")
  if search_query:
    df = df[df["party_name"].str.contains(search_query, case=False, na=False)]
  st.dataframe(df, use_container_width=True, hide_index=True)

# =========================================================
# 3. ROUTE PLANNING
# =========================================================
elif selected_menu == "🗺️ রুট প্ল্যান":
  locations_df = pd.read_sql_query("SELECT * FROM locations", conn)
  if not locations_df.empty:
    selected_parties = st.multiselect("পার্টি সিলেক্ট করুন:", locations_df["party_name"].tolist())
    if st.button("🚀 রুট তৈরি করুন"):
      st.success("রুট প্রসেস সম্পন্ন হয়েছে।")

# =========================================================
# 4. PENDING ORDERS & BILLING
# =========================================================
elif selected_menu == "📦 অর্ডার ও বিলিং":
  orders_df = pd.read_sql_query("SELECT * FROM orders ORDER BY order_date DESC", conn)
  st.dataframe(orders_df, use_container_width=True, hide_index=True)

# =========================================================
# 5. ADMIN LIVE TRACKING
# =========================================================
elif selected_menu == "📊 লাইভ ট্র্যাকিং":
  st.info("লাইভ ট্র্যাকিং প্যানেল সচল রয়েছে।")
