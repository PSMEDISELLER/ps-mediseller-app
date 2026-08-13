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
if "selected_lat" not in st.session_state:
  st.session_state["selected_lat"] = 22.8620
if "selected_lon" not in st.session_state:
  st.session_state["selected_lon"] = 87.3320

query_params = st.query_params
active_user = query_params.get("auth_user", None)

if active_user:
  c.execute("SELECT role FROM users WHERE username=?", (active_user,))
  r_data = c.fetchone()
  if r_data:
    st.session_state["logged_in"] = True
    st.session_state["username"] = active_user
    st.session_state["user_role"] = r_data[0]
  else:
    st.session_state["logged_in"] = False
else:
  if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# =========================================================
# LOGIN SCREEN
# =========================================================
if not st.session_state.get("logged_in", False):
  st.title("🔑 পি এস মেডিসেলার - লগইন")
  
  c.execute("SELECT username FROM users")
  all_users = [row[0] for row in c.fetchall()]
  
  sel_user = st.selectbox("ইউজারনেম নির্বাচন করুন", all_users, key="login_user_box")
  input_pass = st.text_input("পাসওয়ার্ড দিন", type="password", key="login_pass_box")
  
  if st.button("সরাসরি লগইন করুন", type="primary", key="direct_login_btn"):
    c.execute("SELECT password, role FROM users WHERE username=?", (sel_user,))
    user_row = c.fetchone()
    if user_row and user_row[0] == input_pass:
      st.session_state["logged_in"] = True
      st.session_state["username"] = sel_user
      st.session_state["user_role"] = user_row[1]
      st.query_params["auth_user"] = sel_user
      st.success("লগইন সফল হয়েছে!")
      st.rerun()
    else:
      st.error("❌ ভুল পাসওয়ার্ড!")
  st.stop()

# =========================================================
# MAIN APP HEADER & LOGOUT
# =========================================================
st.title("🚚 পি এস মেডিসেলার")

col_u1, col_u3 = st.columns([3, 1])
with col_u1:
  st.write(f"👤 ইউজার: **{st.session_state['username']}** (`{st.session_state['user_role']}`)")
with col_u3:
  if st.button("🚪 লগআউট", key="logout_btn"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = None
    st.session_state["user_role"] = None
    st.query_params.clear()
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
  menu_options.append("📊 লাইভ ট্র্যাকিং")

selected_menu = st.radio("মেনু সিলেক্ট করুন:", menu_options, horizontal=True, label_visibility="collapsed", key="main_navigation_radio")
st.write("---")

# =========================================================
# 1. ADD NEW LOCATION & ORDER ENTRY (HTML LOCALSTORAGE PASSTHROUGH)
# =========================================================
if selected_menu == "📍 নতুন লোকেশন এড":
  col1, col2 = st.columns(2)

  with col1:
    st.write("### 📍 লোকেশন পিন করুন")
    if st.button("🔄 কারেন্ট লোকেশনে পিন সেট করুন", key="set_gps_btn"):
      if gps_lat and gps_lon:
        st.session_state["selected_lat"] = gps_lat
        st.session_state["selected_lon"] = gps_lon
        st.success("✅ লোকেশন আপডেট হয়েছে!")
        st.rerun()
      else:
        st.warning("GPS সিগন্যাল পাওয়া যায়নি।")

    # ব্রাউজারের নিজস্ব মেমোরি (LocalStorage) ব্যবহার করে ইনপুট ধরে রাখার ব্যবস্থা
    html_form_code = """
    <div style="background-color:transparent; padding:0px; font-family:sans-serif;">
      <form id="locForm" onsubmit="saveData(event)">
        <label style="font-size:14px; font-weight:600; color:#31333F;">পার্টির নাম:</label><br>
        <input type="text" id="p_name" name="p_name" style="width:100%; padding:8px; margin-top:4px; margin-bottom:12px; border:1px solid #cccccc; border-radius:4px;" oninput="localStorage.setItem('p_name', this.value)"><br>
        
        <label style="font-size:14px; font-weight:600; color:#31333F;">ঠিকানা:</label><br>
        <input type="text" id="p_addr" name="p_addr" style="width:100%; padding:8px; margin-top:4px; margin-bottom:12px; border:1px solid #cccccc; border-radius:4px;" oninput="localStorage.setItem('p_addr', this.value)"><br>
        
        <label style="font-size:14px; font-weight:600; color:#31333F;">ফোন নম্বর:</label><br>
        <input type="text" id="p_phone" name="p_phone" style="width:100%; padding:8px; margin-top:4px; margin-bottom:12px; border:1px solid #cccccc; border-radius:4px;" oninput="localStorage.setItem('p_phone', this.value)"><br>
        
        <button type="submit" style="background-color:#FF4B4B; color:white; border:none; padding:10px 20px; border-radius:4px; font-weight:bold; cursor:pointer; width:100%;">💾 লোকেশন সেভ করুন</button>
      </form>
    </div>

    <script>
      document.getElementById('p_name').value = localStorage.getItem('p_name') || '';
      document.getElementById('p_addr').value = localStorage.getItem('p_addr') || '';
      document.getElementById('p_phone').value = localStorage.getItem('p_phone') || '';

      function saveData(e) {
        e.preventDefault();
        const pName = document.getElementById('p_name').value;
        const pAddr = document.getElementById('p_addr').value;
        const pPhone = document.getElementById('p_phone').value;
        
        if(!pName || !pPhone) {
          alert("পার্টির নাম এবং ফোন নম্বর আবশ্যক।");
          return;
        }
        
        // Streamlit-এর সাথে ডেটা সিঙ্ক করার জন্য প্যারামিটার পাঠানো
        const url = new URL(window.location.href);
        url.searchParams.set('action', 'save_loc');
        url.searchParams.set('p_name', encodeURIComponent(pName));
        url.searchParams.set('p_addr', encodeURIComponent(pAddr));
        url.searchParams.set('p_phone', encodeURIComponent(pPhone));
        window.location.href = url.toString();
      }
    </script>
    """
    st.components.v1.html(html_form_code, height=320)

    # পাইথন ব্যাকএন্ডে ডেটা রিসিভ ও সেভ করার লজিক
    params = st.query_params
    if params.get("action") == "save_loc":
      r_name = urllib.parse.unquote(params.get("p_name", ""))
      r_addr = urllib.parse.unquote(params.get("p_addr", ""))
      r_phone = urllib.parse.unquote(params.get("p_phone", ""))
      
      if r_name and r_phone:
        c.execute(
            "INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, ?, ?)",
            (r_name, r_addr, r_phone, st.session_state["selected_lat"], st.session_state["selected_lon"]),
        )
        conn.commit()
        st.success("✅ লোকেশন সফলভাবে সেভ হয়েছে!")
        st.query_params.clear()
        st.query_params["auth_user"] = st.session_state["username"]
        st.rerun()

  with col2:
    st.write("### 📦 নতুন অর্ডার এন্ট্রি")
    c.execute("SELECT DISTINCT party_name FROM locations ORDER BY party_name ASC")
    all_parties_db = [row[0] for row in c.fetchall()]

    ord_party = st.selectbox("পার্টি নির্বাচন করুন", ["-- সিলেক্ট করুন --"] + all_parties_db, key="input_order_party")
    ord_details = st.text_area("অর্ডারের বিবরণ", key="input_order_details")

    if st.button("🛒 অর্ডার জমা দিন", type="primary", key="save_order_direct_btn"):
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
  
  map_data = st_folium(m_click, width=900, height=450, key="interactive_map_safe")
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
  search_query = st.text_input("সার্চ করুন (পার্টির নাম)", key="search_party_input")
  if search_query:
    df = df[df["party_name"].str.contains(search_query, case=False, na=False)]
  st.dataframe(df, use_container_width=True, hide_index=True)

# =========================================================
# 3. ROUTE PLANNING
# =========================================================
elif selected_menu == "🗺️ রুট প্ল্যান":
  locations_df = pd.read_sql_query("SELECT * FROM locations", conn)
  if not locations_df.empty:
    selected_parties = st.multiselect("পার্টি সিলেক্ট করুন:", locations_df["party_name"].tolist(), key="route_multi_select")
    if st.button("🚀 রুট তৈরি করুন", key="route_btn"):
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
