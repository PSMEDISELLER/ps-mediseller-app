from datetime import datetime, timedelta
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
    payment_collected TEXT DEFAULT '0',
    completed_time TEXT
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
CREATE TABLE IF NOT EXISTS delivery_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    party_name TEXT NOT NULL,
    task_type TEXT NOT NULL, -- 'ডেলিভারি' বা 'ডিউ কালেকশন'
    due_amount TEXT DEFAULT '0',
    status TEXT DEFAULT 'Pending',
    assigned_date TEXT NOT NULL,
    completed_time TEXT
)
""")

# ডাটাবেসের পুরোনো ডেটা ক্লিনআপ (২৪ ঘণ্টা পার হওয়া কমপ্লিট অর্ডার ও প্ল্যান অটো ডিলিট)
current_time_str = datetime.now()
c.execute("SELECT id, completed_time FROM orders WHERE status='Completed'")
for o_id, c_time in c.fetchall():
  if c_time:
    try:
      if (current_time_str - datetime.strptime(c_time, "%Y-%m-%d %H:%M:%S")) > timedelta(hours=24):
        c.execute("DELETE FROM orders WHERE id=?", (o_id,))
    except:
      pass

c.execute("SELECT id, completed_time FROM delivery_plans WHERE status='Completed'")
for p_id, c_time in c.fetchall():
  if c_time:
    try:
      if (current_time_str - datetime.strptime(c_time, "%Y-%m-%d %H:%M:%S")) > timedelta(hours=24):
        c.execute("DELETE FROM delivery_plans WHERE id=?", (p_id,))
    except:
      pass
conn.commit()

# কলাম চেক ও আপডেট
c.execute("PRAGMA table_info(locations)")
existing_cols_loc = [row[1] for row in c.fetchall()]
if "party_phone" not in existing_cols_loc:
  c.execute("ALTER TABLE locations ADD COLUMN party_phone TEXT")

c.execute("PRAGMA table_info(orders)")
existing_cols_ord = [row[1] for row in c.fetchall()]
if "completed_time" not in existing_cols_ord:
  c.execute("ALTER TABLE orders ADD COLUMN completed_time TEXT")

conn.commit()

# ডিফল্ট ইউজার তৈরি
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
  c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin123", "admin"))
  c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("delivery", "user123", "staff"))
  conn.commit()

# সমস্ত ইউজারের জন্য লাইভ লোকেশন রো নিশ্চিত করা
c.execute("SELECT username FROM users")
all_app_users = c.fetchall()
for u in all_app_users:
  c.execute("INSERT OR IGNORE INTO agent_live_locations (username, completed_deliveries, completed_dues) VALUES (?, 0, 0)", (u[0],))
conn.commit()

# =========================================================
# LOCALSTORAGE LOGIN PERSISTENCE
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
# HEADER & LOGOUT
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
# GPS TRACKING (Background - Hidden to agents)
# =========================================================
loc = get_geolocation(component_key="safe_gps_tracker")
gps_lat, gps_lon = None, None

if loc and "coords" in loc:
  gps_lat = loc["coords"]["latitude"]
  gps_lon = loc["coords"]["longitude"]
  c.execute(
      "UPDATE agent_live_locations SET lat=?, lon=?, last_updated=? WHERE username=?",
      (gps_lat, gps_lon, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state["username"]),
  )
  conn.commit()

# =========================================================
# NAVIGATION MENU
# =========================================================
menu_options = [
    "📍 নতুন লোকেশন এড",
    "🔍 সার্চ",
    "📦 পেন্ডিং অর্ডার",
    "📋 ডিউ ক্লিয়ার ও ডেলিভারি প্ল্যান",
]
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
# 3. PENDING ORDERS (Auto-delete after 24 hours)
# =========================================================
elif selected_menu == "📦 পেন্ডিং অর্ডার":
  st.write("### 📦 পেন্ডিং অর্ডার তালিকা")
  
  orders_df = pd.read_sql_query("SELECT * FROM orders ORDER BY order_date DESC", conn)
  if not orders_df.empty:
    for index, row in orders_df.iterrows():
      cols = st.columns([2, 4, 2, 2])
      cols[0].write(f"**{row['party_name']}**\n\n_{row['order_date']}_")
      cols[1].write(row['order_details'])
      
      status_text = "✅ সম্পন্ন" if row['status'] == "Completed" else "⏳ পেন্ডিং"
      cols[2].write(status_text)

      if row['status'] == "Pending":
        if cols[3].button("✔️ টিক দিন", key=f"ord_btn_{row['id']}"):
          complete_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          c.execute("UPDATE orders SET status='Completed', completed_time=? WHERE id=?", (complete_time_str, row['id']))
          c.execute("UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?", (st.session_state["username"],))
          conn.commit()
          st.success("অর্ডার কমপ্লিট হিসেবে মার্ক করা হয়েছে! এটি ২৪ ঘণ্টা পর অটো মুছে যাবে।")
          st.rerun()
      else:
        cols[3].write("সম্পন্ন")
      st.write("---")
  else:
    st.info("কোনো পেন্ডিং অর্ডার নেই।")

# =========================================================
# 4. DUE CLEAR & DELIVERY PLAN (With Agent Allocation & Search)
# =========================================================
elif selected_menu == "📋 ডিউ ক্লিয়ার ও ডেলিভারি প্ল্যান":
  st.write("### 📋 ডিউ ক্লিয়ার ও ডেলিভারি প্ল্যান ম্যানেজমেন্ট")

  if st.session_state["user_role"] == "admin":
    st.write("#### ➕ এজেন্টকে নতুন কাজ এসাইন করুন")
    c.execute("SELECT username FROM users WHERE role='staff'")
    staff_list = [r[0] for r in c.fetchall()]
    c.execute("SELECT party_name FROM locations")
    loc_list = [r[0] for r in c.fetchall()]

    if staff_list and loc_list:
      with st.form("assign_plan_form"):
        sel_agent = st.selectbox("এজেন্ট সিলেক্ট করুন", staff_list)
        sel_party = st.selectbox("পার্টি সিলেক্ট করুন", loc_list)
        task_type = st.selectbox("কাজের ধরন", ["ডেলিভারি", "ডিউ কালেকশন"])
        due_amt = st.text_input("ডিউ টাকার পরিমাণ (যদি থাকে)", "0")
        
        assign_btn = st.form_submit_button("প্ল্যান এসাইন করুন")
        if assign_btn:
          c.execute(
              "INSERT INTO delivery_plans (agent_name, party_name, task_type, due_amount, status, assigned_date) VALUES (?, ?, ?, ?, ?, ?)",
              (sel_agent, sel_party, task_type, due_amt, "Pending", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
          )
          conn.commit()
          st.success("✅ সফলভাবে প্ল্যান এসাইন করা হয়েছে!")
          st.rerun()
    else:
      st.info("প্রথমে ইউজার ম্যানেজমেন্ট থেকে স্টাফ এবং লোকেশন যোগ করুন।")
    st.write("---")

  # Search & View Tasks
  st.write("#### 🔍 ডিউ ও ডেলিভারি সার্চ ও লিস্ট")
  search_plan = st.text_input("পার্টির নাম দিয়ে সার্চ করুন প্ল্যান লিস্টে")

  query_str = "SELECT * FROM delivery_plans"
  if st.session_state["user_role"] != "admin":
    query_str += f" WHERE agent_name='{st.session_state['username']}'"
  
  plans_df = pd.read_sql_query(query_str, conn)
  if search_plan:
    plans_df = plans_df[plans_df["party_name"].str.contains(search_plan, case=False, na=False)]

  if not plans_df.empty:
    # Home-to-Home Route Map Button Generation
    if st.button("🗺️ হোম-টু-হোম সহজ রুট ও ম্যাপ দেখুন"):
      st.info("সৈনিক/এজেন্টদের জন্য অপ্টিমাইজড রুট ম্যাপ:")
      c.execute("SELECT lat, lon, party_name FROM locations")
      route_locs = c.fetchall()
      if route_locs:
        route_map = folium.Map(location=[route_locs[0][0], route_locs[0][1]], zoom_start=14)
        points = []
        for r_lat, r_lon, r_name in route_locs:
          if r_lat and r_lon:
            points.append([r_lat, r_lon])
            folium.Marker([r_lat, r_lon], popup=r_name, icon=folium.Icon(color="blue", icon="info-sign")).add_to(route_map)
        if len(points) > 1:
          folium.PolyLine(points, color="red", weight=3, opacity=0.8).add_to(route_map)
        st_folium(route_map, width=900, height=400, key="route_map_view")

    st.write("---")
    for index, row in plans_df.iterrows():
      cols = st.columns([2, 2, 2, 2, 2])
      cols[0].write(f"**এজেন্ট:** {row['agent_name']}")
      cols[1].write(f"**পার্টি:** {row['party_name']}")
      cols[2].write(f"**কাজ:** {row['task_type']}")
      cols[3].write(f"**ডিউ:** ₹{row['due_amount']}" if row['task_type'] == "ডিউ কালেকশন" else "ডেলিভারি অর্ডার")
      
      if row['status'] == "Pending":
        if cols[4].button("✔️ সম্পন্ন করুন", key=f"plan_done_{row['id']}"):
          comp_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          c.execute("UPDATE delivery_plans SET status='Completed', completed_time=? WHERE id=?", (comp_time, row['id']))
          if row['task_type'] == "ডেলিভারি":
            c.execute("UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?", (row['agent_name'],))
          else:
            c.execute("UPDATE agent_live_locations SET completed_dues = completed_dues + 1 WHERE username=?", (row['agent_name'],))
          conn.commit()
          st.success("কাজ সম্পন্ন হয়েছে! এটি ২৪ ঘণ্টা পর স্বয়ংক্রিয়ভাবে মুছে যাবে।")
          st.rerun()
      else:
        cols[4].write("✅ সম্পন্ন")
      st.write("---")
  else:
    st.info("কোনো ডিউ বা ডেলিভারি প্ল্যান নেই।")

# =========================================================
# 5. ADMIN LIVE TRACKING (Hidden tracking from agents)
# =========================================================
elif selected_menu == "📊 লাইভ ট্র্যাকিং":
  if st.session_state["user_role"] != "admin":
    st.error("এই পেজটি শুধুমাত্র অ্যাডমিনের জন্য।")
  else:
    st.write("### 📊 ডেলিভারি পার্টনার লাইভ ট্র্যাকিং ও স্ট্যাটাস (গোপন ট্র্যাকিং)")
    
    agent_df = pd.read_sql_query("SELECT * FROM agent_live_locations", conn)
    if not agent_df.empty:
      for index, row in agent_df.iterrows():
        last_up = row['last_updated'] if row['last_updated'] else "এখনও সিঙ্ক হয়নি"
        lat_val = row['lat'] if row['lat'] else "লোকেশন নেই"
        lon_val = row['lon'] if row['lon'] else ""
        
        with st.expander(f"👤 এজেন্ট: {row['username']} (শেষ আপডেট: {last_up})"):
          st.write(f"📍 বর্তমান স্থানাঙ্ক (Lat, Lon): `{lat_val}, {lon_val}`")
          st.write(f"✅ সম্পন্ন ডেলিভারি সংখ্যা: **{row['completed_deliveries']} টি**")
          st.write(f"💰 ডিউ ক্লিয়ারেন্স সংখ্যা: **{row['completed_dues']} টি**")
          
          if row['lat'] and row['lon']:
            agent_map_url = f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}"
            st.markdown(f'<a href="{agent_map_url}" target="_blank" style="text-decoration:none;"><button style="background-color:#1a73e8; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;">🧭 ম্যাপে এজেন্ট কোথায় আছেন দেখুন</button></a>', unsafe_allow_html=True)
          else:
            st.warning("এই এজেন্ট এখনও জিপিএস লোকেশন শেয়ার করেনি।")
    else:
      st.info("কোনো এজেন্টের ডেটা পাওয়া যায়নি।")

# =========================================================
# 6. SETTINGS & AGENT MANAGEMENT
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
              c.execute("UPDATE agent_live_locations SET username=? WHERE username=?", (new_name, u_name))
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
            c.execute("INSERT OR IGNORE INTO agent_live_locations (username, completed_deliveries, completed_dues) VALUES (?, 0, 0)", (n_user,))
            conn.commit()
            st.success("নতুন এজেন্ট সফলভাবে যোগ করা হয়েছে!")
            st.rerun()
          except:
            st.error("এই ইউজারনেমটি আগেই রয়েছে।")
        else:
          st.error("সব ঘর পূরণ করুন।")
