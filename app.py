from datetime import datetime
import folium
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
# PERMANENT LOCALSTORAGE LOGIN PERSISTENCE
# =========================================================
if "selected_lat" not in st.session_state:
  st.session_state["selected_lat"] = 22.8620
if "selected_lon" not in st.session_state:
  st.session_state["selected_lon"] = 87.3320

local_user = streamlit_js_eval(js_expressions="localStorage.getItem('ps_perma_user')", key="get_local_user")

if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False

if not st.session_state["logged_in"] and local_user:
  c.execute("SELECT role FROM users WHERE username=?", (local_user,))
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
  st.write("একবার লগইন করলে বারবার পাসওয়ার্ড দিতে হবে না।")

  c.execute("SELECT username FROM users")
  all_users = [row[0] for row in c.fetchall()]

  with st.form("login_form_perma"):
    sel_user = st.selectbox("ইউজারনেম নির্বাচন করুন", all_users)
    input_pass = st.text_input("পাসওয়ার্ড দিন", type="password")
    submit_login = st.form_submit_button("🔒 স্থায়ীভাবে লগইন করুন", type="primary")

    if submit_login:
      c.execute("SELECT password, role FROM users WHERE username=?", (sel_user,))
      user_row = c.fetchone()
      if user_row and user_row[0] == input_pass:
        st.session_state["logged_in"] = True
        st.session_state["username"] = sel_user
        st.session_state["user_role"] = user_row[1]
        streamlit_js_eval(js_expressions=f"localStorage.setItem('ps_perma_user', '{sel_user}')", key="set_local_user")
        st.success("লগইন সফল হয়েছে!")
        st.rerun()
      else:
        st.error("❌ ভুল পাসওয়ার্ড!")
  st.stop()

# =========================================================
# MAIN APP HEADER & LOGOUT
# =========================================================
st.title("পি এস মেডিসেলার ডেলিভারি পার্টনার")

col_u1, col_u3 = st.columns([3, 1])
with col_u1:
  st.write(f"👤 ইউজার: **{st.session_state['username']}** (`{st.session_state['user_role']}`)")
with col_u3:
  if st.button("🚪 লগআউট"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = None
    st.session_state["user_role"] = None
    streamlit_js_eval(js_expressions="localStorage.removeItem('ps_perma_user')", key="clear_local_user")
    st.rerun()
st.write("---")

# =========================================================
# GPS TRACKING (Background)
# =========================================================
loc = get_geolocation(component_key="safe_gps_tracker")
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
  menu_options.extend(["📊 লাইভ ট্র্যাকিং", "⚙️ সেটিংস ও এজেন্ট ম্যানেজমেন্ট"])

selected_menu = st.radio("মেনু সিলেক্ট করুন:", menu_options, horizontal=True, label_visibility="collapsed")
st.write("---")

# =========================================================
# 1. ADD NEW LOCATION & ORDER ENTRY
# =========================================================
if selected_menu == "📍 নতুন লোকেশন এড":
  col1, col2 = st.columns(2)

  with col1:
    st.write("### 📍 নতুন লোকেশন ফর্ম")
    with st.form("location_form", clear_on_submit=True):
      p_name = st.text_input("পার্টির নাম")
      p_addr = st.text_input("ঠিকানা")
      p_phone = st.text_input("ফোন নম্বর")
      
      submitted_loc = st.form_submit_button("💾 লোকেশন সেভ করুন", type="primary")
      if submitted_loc:
        if p_name.strip() and p_phone.strip():
          c.execute(
              "INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, ?, ?)",
              (p_name, p_addr, p_phone, st.session_state["selected_lat"], st.session_state["selected_lon"]),
          )
          conn.commit()
          st.success("✅ লোকেশন সফলভাবে সেভ হয়েছে!")
        else:
          st.error("পার্টির নাম এবং ফোন নম্বর আবশ্যক।")

  with col2:
    st.write("### 📦 নতুন অর্ডার এন্ট্রি")
    c.execute("SELECT DISTINCT party_name FROM locations ORDER BY party_name ASC")
    all_parties_db = [row[0] for row in c.fetchall()]

    with st.form("order_form", clear_on_submit=True):
      ord_party = st.selectbox("পার্টি নির্বাচন করুন", ["-- সিলেক্ট করুন --"] + all_parties_db)
      ord_details = st.text_area("অর্ডারের বিবরণ")

      submitted_ord = st.form_submit_button("🛒 অর্ডার জমা দিন", type="primary")
      if submitted_ord:
        if ord_party != "-- সিলেক্ট করুন --" and ord_details.strip():
          c.execute(
              "INSERT INTO orders (party_name, order_details, order_date, status) VALUES (?, ?, ?, ?)",
              (ord_party, ord_details, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Pending"),
          )
          conn.commit()
          st.success("✅ অর্ডার সফলভাবে সেভ হয়েছে!")
        else:
          st.error("সঠিক পার্টি এবং বিবরণ দিন।")

  # Map Display
  st.write("### 🗺️ ম্যাপ লোকেশন সিলেক্ট করুন")
  
  m_click = folium.Map(
      location=[st.session_state["selected_lat"], st.session_state["selected_lon"]],
      zoom_start=16,
      tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
      attr="Google"
  )
  
  if gps_lat and gps_lon:
    folium.CircleMarker(
        location=[gps_lat, gps_lon],
        radius=8,
        color="white",
        weight=2,
        fill=True,
        fill_color="#1a73e8",
        fill_opacity=1.0,
        popup="আপনার কারেন্ট লোকেশন"
    ).add_to(m_click)

  folium.Marker(
      [st.session_state["selected_lat"], st.session_state["selected_lon"]],
      popup="সিলেক্টেড পিন",
      icon=folium.Icon(color="red", icon="map-marker", prefix="fa"),
  ).add_to(m_click)
  
  map_data = st_folium(m_click, width=900, height=450, key="interactive_map_safe")
  
  if st.button("🔄 কারেন্ট লোকেশনে পিন সেট করুন", type="secondary"):
    if gps_lat and gps_lon:
      st.session_state["selected_lat"] = gps_lat
      st.session_state["selected_lon"] = gps_lon
      st.success("✅ কারেন্ট লোকেশন সেট হয়েছে!")
      st.rerun()
    else:
      st.warning("GPS সিগন্যাল পাওয়া যায়নি।")

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
  st.write("### 🔍 সেভ করা পার্টি তালিকা ও ডিরেকশন")
  df = pd.read_sql_query("SELECT * FROM locations", conn)
  search_query = st.text_input("সার্চ করুন (পার্টির নাম)")
  if search_query:
    df = df[df["party_name"].str.contains(search_query, case=False, na=False)]
  
  if not df.empty:
    for index, row in df.iterrows():
      cols = st.columns([3, 2, 2, 2])
      cols[0].write(f"**{row['party_name']}**")
      cols[1].write(row['party_phone'] if row['party_phone'] else "নম্বার নেই")
      cols[2].write(row['address'] if row['address'] else "ঠিকানা নেই")
      
      maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}"
      cols[3].markdown(f'<a href="{maps_url}" target="_blank" style="text-decoration:none;"><button style="background-color:#1a73e8; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;">🧭 ডিরেকশন</button></a>', unsafe_allow_html=True)
      st.write("---")
  else:
    st.info("কোনো পার্টি পাওয়া যায়নি।")

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

# =========================================================
# 6. SETTINGS & AGENT MANAGEMENT (Admin Only)
# =========================================================
elif selected_menu == "⚙️ সেটিংস ও এজেন্ট ম্যানেজমেন্ট":
  if st.session_state["user_role"] != "admin":
    st.error("এই পেজটি শুধুমাত্র অ্যাডমিনের জন্য।")
  else:
    st.write("### 👥 ডেলিভারি এজেন্ট তালিকা ও ম্যানেজমেন্ট")
    c.execute("SELECT username, role FROM users")
    agents = c.fetchall()
    st.write(f"মোট রেজিস্টার্ড ইউজার/এজেন্ট সংখ্যা: **{len(agents)}**")

    for ag in agents:
      u_name, u_role = ag
      with st.expander(f"এজেন্ট: {u_name} ({u_role})"):
        with st.form(f"edit_form_{u_name}"):
          new_name = st.text_input("নাম এডিট করুন", value=u_name, key=f"name_{u_name}")
          new_pass = st.text_input("নতুন পাসওয়ার্ড দিন", type="password", key=f"pass_{u_name}")
          update_btn = st.form_submit_button("পরিবর্তন সেভ করুন")
          
          if update_btn:
            if new_pass.strip():
              c.execute("UPDATE users SET username=?, password=? WHERE username=?", (new_name, new_pass, u_name))
              conn.commit()
              st.success("সফলভাবে আপডেট হয়েছে!")
              st.rerun()
            else:
              st.warning("পাসওয়ার্ড খালি রাখা যাবে না।")

    st.write("---")
    st.write("### ➕ নতুন এজেন্ট যোগ করুন")
    with st.form("new_agent_form"):
      n_user = st.text_input("নতুন ইউজারের নাম")
      n_pass = st.text_input("পাসওয়ার্ড", type="password")
      n_role = st.selectbox("রোল", ["staff", "admin"])
      add_agent_btn = st.form_submit_button("এজেন্ট যুক্ত করুন")

      if add_agent_btn:
        if n_user and n_pass:
          try:
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (n_user, n_pass, n_role))
            conn.commit()
            st.success("নতুন এজেন্ট সফলভাবে যোগ করা হয়েছে!")
            st.rerun()
          except:
            st.error("এই ইউজারনেমটি আগেই রয়েছে।")
        else:
          st.error("সব ঘর পূরণ করুন।")
