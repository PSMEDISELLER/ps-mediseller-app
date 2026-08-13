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
# অ্যাসাইনমেন্ট টেবিল (পয়েন্ট ৩ এর জন্য)
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

# কলাম চেক ও আপডেট
c.execute("PRAGMA table_info(locations)")
existing_cols_loc = [row[1] for row in c.fetchall()]
if "party_phone" not in existing_cols_loc:
  c.execute("ALTER TABLE locations ADD COLUMN party_phone TEXT")

c.execute("PRAGMA table_info(orders)")
existing_cols_ord = [row[1] for row in c.fetchall()]
if "payment_collected" not in existing_cols_ord:
  c.execute("ALTER TABLE orders ADD COLUMN payment_collected TEXT DEFAULT '0'")
if "status" not in existing_cols_ord:
  c.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'Pending'")

c.execute("PRAGMA table_info(agent_live_locations)")
existing_cols_agent = [row[1] for row in c.fetchall()]
if "completed_deliveries" not in existing_cols_agent:
  c.execute("ALTER TABLE agent_live_locations ADD COLUMN completed_deliveries INTEGER DEFAULT 0")
if "completed_dues" not in existing_cols_agent:
  c.execute("ALTER TABLE agent_live_locations ADD COLUMN completed_dues INTEGER DEFAULT 0")

conn.commit()

# ডিফল্ট ইউজার তৈরি
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
  c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin123", "admin"))
  c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("delivery", "user123", "staff"))
  conn.commit()

# =========================================================
# AUTO DELETE COMPLETED TASKS AFTER 24 HOURS (পয়েন্ট ৪ ও ৬)
# =========================================================
current_dt_str = datetime.now()
# ২৪ ঘণ্টার পুরোনো সম্পন্ন টাস্ক বা অর্ডার মুছে ফেলা হবে
c.execute("SELECT id, order_date FROM orders WHERE status='Completed'")
for row_ord in c.fetchall():
  try:
    o_time = datetime.strptime(row_ord[1], "%Y-%m-%d %H:%M:%S")
    if (current_dt_str - o_time) > timedelta(hours=24):
      c.execute("DELETE FROM orders WHERE id=?", (row_ord[0],))
  except:
    pass

c.execute("SELECT id, created_at FROM task_assignments WHERE status='Completed'")
for row_task in c.fetchall():
  try:
    t_time = datetime.strptime(row_task[1], "%Y-%m-%d %H:%M:%S")
    if (current_dt_str - t_time) > timedelta(hours=24):
      c.execute("DELETE FROM task_assignments WHERE id=?", (row_task[0],))
  except:
    pass
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
# BACKGROUND HIDDEN GPS TRACKING (পয়েন্ট ৫ ও ৬)
# =========================================================
# এজেন্ট বা ইউজার বুঝতে পারবে না, ব্যাকগ্রাউন্ডে জিপিএস আপডেট হতে থাকবে
loc = get_geolocation(component_key="hidden_background_gps_tracker")
if loc and "coords" in loc:
  gps_lat = loc["coords"]["latitude"]
  gps_lon = loc["coords"]["longitude"]
  c.execute(
      "UPDATE agent_live_locations SET lat=?, lon=?, last_updated=? WHERE username=?",
      (gps_lat, gps_lon, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state["username"]),
  )
  if c.rowcount == 0:
    c.execute(
        "INSERT INTO agent_live_locations (username, lat, lon, last_updated) VALUES (?, ?, ?, ?)",
        (st.session_state["username"], gps_lat, gps_lon, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
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
    "🗺️ হোম-টু-হোম রুট ও ম্যাপ",
    "📌 এজেন্ট অ্যাসাইনমেন্ট",
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

  # Map Display for Pin Selection
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
# 3. PENDING ORDERS
# =========================================================
elif selected_menu == "📦 পেন্ডিং অর্ডার":
  st.write("### 📦 পেন্ডিং অর্ডার তালিকা (তারিখ অনুযায়ী)")
  
  orders_df = pd.read_sql_query("SELECT * FROM orders WHERE status='Pending' ORDER BY order_date DESC", conn)
  if not orders_df.empty:
    orders_df["date_only"] = orders_df["order_date"].astype(str).str.split(" ").str[0]
    unique_dates = orders_df["date_only"].unique()

    for u_date in unique_dates:
      st.markdown(f"#### 📅 তারিখ: {u_date}")
      date_df = orders_df[orders_df["date_only"] == u_date]

      for index, row in date_df.iterrows():
        cols = st.columns([2, 4, 2, 2])
        cols[0].write(f"**{row['party_name']}**")
        cols[1].write(row['order_details'])
        cols[2].write("⏳ পেন্ডিং")

        if cols[3].button("✔️ টিক দিন", key=f"ord_btn_{row['id']}"):
          c.execute("UPDATE orders SET status='Completed', order_date=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row['id']))
          conn.commit()
          c.execute("UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?", (st.session_state["username"],))
          conn.commit()
          st.success("অর্ডার কমপ্লিট হিসেবে মার্ক করা হয়েছে!")
          st.rerun()
      st.write("---")
  else:
    st.info("কোনো পেন্ডিং অর্ডার নেই।")

# =========================================================
# 4. DUE CLEAR & DELIVERY PLAN (পয়েন্ট ১: সার্চ বার ও অপশন)
# =========================================================
elif selected_menu == "📋 ডিউ ক্লিয়ার ও ডেলিভারি প্ল্যান":
  st.write("### 📋 ডিউ ক্লিয়ার ও ডেলিভারি প্ল্যান (সার্চ ও অপশন)")
  
  locations_df = pd.read_sql_query("SELECT * FROM locations", conn)
  all_parties = locations_df["party_name"].tolist() if not locations_df.empty else []

  # সার্চ বার ও অপশন সিলেকশন
  search_party_plan = st.selectbox("পার্টি সার্চ বা সিলেক্ট করুন", ["-- সমস্ত পার্টি দেখান --"] + all_parties)
  
  if search_party_plan != "-- সমস্ত পার্টি দেখান --":
    filtered_locs = locations_df[locations_df["party_name"] == search_party_plan]
  else:
    filtered_locs = locations_df

  if not filtered_locs.empty:
    for index, row in filtered_locs.iterrows():
      st.markdown(f"#### 🏥 পার্টি: **{row['party_name']}**")
      st.write(f"ঠিকানা: {row['address'] if row['address'] else 'নেই'} | ফোন: {row['party_phone'] if row['party_phone'] else 'নেই'}")
      
      col_p1, col_p2, col_p3 = st.columns([2, 2, 2])
      
      # কাজের ধরণ সিলেক্ট করা (ডেলিভারি নাকি ডিউ কালেকশন)
      task_option = col_p1.selectbox("কাজের ধরণ নির্বাচন করুন", ["ডেলিভারি", "ডিউ কালেকশন", "উভয়ই"], key=f"task_opt_{row['id']}")
      
      due_amt = ""
      if "ডিউ" in task_option or task_option == "উভয়ই":
        due_amt = col_p2.text_input("ডিউ টাকার পরিমাণ লিখুন", key=f"due_amt_{row['id']}")
      else:
        col_p2.write("ডিউ নেই")

      if col_p3.button("✅ কাজ সম্পন্ন করুন", key=f"complete_plan_{row['id']}"):
        if "ডেলিভারি" in task_option or task_option == "উভয়ই":
          c.execute("UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?", (st.session_state["username"],))
        if ("ডিউ" in task_option or task_option == "উভয়ই") and due_amt.strip():
          c.execute("UPDATE agent_live_locations SET completed_dues = completed_dues + 1 WHERE username=?", (st.session_state["username"],))
        conn.commit()
        st.success(f"✅ {row['party_name']}-এর কাজ সফলভাবে আপডেট করা হয়েছে!")
        st.rerun()
      st.write("---")
  else:
    st.info("কোনো লোকেশন পাওয়া যায়নি।")

# =========================================================
# 5. HOME-TO-HOME ROUTE & MAP (পয়েন্ট ২: হোম-টু-হোম রুট ও অটোম্যাপ)
# =========================================================
elif selected_menu == "🗺️ হোম-টু-হোম রুট ও ম্যাপ":
  st.write("### 🗺️ হোম-টু-হোম রুট ও অটোমেটিক ম্যাপ প্ল্যানিং")
  st.write("এখানে আপনার সেভ করা সমস্ত পার্টির লোকেশন সিকোয়েন্স অনুযায়ী ম্যাপে রুট আকারে দেখা যাবে।")

  locs_df = pd.read_sql_query("SELECT * FROM locations", conn)
  
  if not locs_df.empty:
    # ডিফল্ট সেন্টার (প্রথম লোকেশন বা ইউজারের কারেন্ট লোকেশন)
    m_center_lat = locs_df.iloc[0]["lat"] if locs_df.iloc[0]["lat"] else 22.8620
    m_center_lon = locs_df.iloc[0]["lon"] if locs_df.iloc[0]["lon"] else 87.3320

    route_map = folium.Map(
        location=[m_center_lat, m_center_lon],
        zoom_start=14,
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google"
    )

    coordinates_list = []
    for idx, row in locs_df.iterrows():
      if row["lat"] and row["lon"]:
        lat, lon = row["lat"], row["lon"]
        coordinates_list.append([lat, lon])
        
        # মার্কার এড করা
        folium.Marker(
            [lat, lon],
            popup=f"<b>{row['party_name']}</b><br>{row['address']}",
            tooltip=row["party_name"],
            icon=folium.Icon(color="blue", icon="store", prefix="fa")
        ).add_to(route_map)

    # হোম-টু-হোম রুট লাইন আঁকা
    if len(coordinates_list) > 1:
      folium.PolyLine(coordinates_list, color="red", weight=4, opacity=0.8, tooltip="ডেলিভারি রুট").add_to(route_map)

    st_folium(route_map, width=900, height=500, key="route_map_view")
  else:
    st.info("রুট দেখানোর জন্য কোনো লোকেশন সেভ করা নেই। প্রথমে লোকেশন এড করুন।")

# =========================================================
# 6. AGENT ASSIGNMENT (পয়েন্ট ৩: এডমিন বা ডেলিভারি যে কেউ কাজ ভাগ করতে পারবে)
# =========================================================
elif selected_menu == "📌 এজেন্ট অ্যাসাইনমেন্ট":
  st.write("### 📌 নির্দিষ্ট এজেন্টের নামে ডিউ বা ডেলিভারি কাজ অ্যাসাইন করুন")
  
  # ইউজার বা এজেন্ট তালিকা আনা
  c.execute("SELECT username FROM users")
  all_agent_names = [r[0] for r in c.fetchall()]
  
  # পার্টি তালিকা আনা
  c.execute("SELECT DISTINCT party_name FROM locations")
  all_party_names = [r[0] for r in c.fetchall()]

  with st.form("assign_task_form"):
    col_a1, col_a2 = st.columns(2)
    with col_a1:
      sel_agent = st.selectbox("এজেন্ট নির্বাচন করুন", all_agent_names)
      sel_party = st.selectbox("পার্টি নির্বাচন করুন", all_party_names)
    with col_a2:
      task_type_sel = st.selectbox("কাজের ধরণ", ["ডেলিভারি", "ডিউ কালেকশন"])
      task_due_amt = st.text_input("ডিউ পরিমাণ (যদি থাকে)", "0")

    submit_assignment = st.form_submit_button("🎯 কাজ অ্যাসাইন করুন", type="primary")
    if submit_assignment:
      if sel_party:
        c.execute(
            "INSERT INTO task_assignments (agent_name, party_name, task_type, due_amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (sel_agent, sel_party, task_type_sel, task_due_amt, "Pending", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        st.success(f"✅ সফলভাবে **{sel_agent}**-এর নামে কাজ অ্যাসাইন করা হয়েছে!")
        st.rerun()
      else:
        st.error("পার্টি সিলেক্ট করুন।")

  st.write("---")
  st.write("### 📋 অ্যাসাইন করা কাজের তালিকা (আপনার বা সবার)")
  
  # যদি ইউজার স্টাফ হয় তবে শুধু তার নিজের অ্যাসাইনমেন্ট দেখাবে, আর অ্যাডমিন হলে সবার দেখতে পারবে
  if st.session_state["user_role"] == "admin":
    assigned_df = pd.read_sql_query("SELECT * FROM task_assignments ORDER BY id DESC", conn)
  else:
    assigned_df = pd.read_sql_query("SELECT * FROM task_assignments WHERE agent_name=? ORDER BY id DESC", conn, params=(st.session_state["username"],))

  if not assigned_df.empty:
    for idx, row in assigned_df.iterrows():
      cols = st.columns([2, 2, 2, 2, 2])
      cols[0].write(f"এজেন্ট: **{row['agent_name']}**")
      cols[1].write(f"পার্টি: **{row['party_name']}**")
      cols[2].write(f"কাজ: {row['task_type']} ({row['due_amount']})")
      cols[3].write(f"স্ট্যাটাস: {row['status']}")

      if row['status'] == "Pending":
        if cols[4].button("✔️ সম্পন্ন", key=f"complete_assign_{row['id']}"):
          c.execute("UPDATE task_assignments SET status='Completed', created_at=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row['id']))
          conn.commit()
          st.success("টাস্ক সম্পন্ন হয়েছে!")
          st.rerun()
      else:
        cols[4].write("সম্পন্ন")
      st.write("---")
  else:
    st.info("কোনো অ্যাসাইন করা কাজ নেই।")

# =========================================================
# 7. ADMIN LIVE TRACKING (পয়েন্ট ৫: হিডেন ট্র্যাকিং)
# =========================================================
elif selected_menu == "📊 লাইভ ট্র্যাকিং":
  if st.session_state["user_role"] != "admin":
    st.error("এই পেজটি শুধুমাত্র অ্যাডমিনের জন্য।")
  else:
    st.write("### 📊 ডেলিভারি এজেন্ট লাইভ ট্র্যাকিং (ব্যাকগ্রাউন্ড হিডেন)")
    
    c.execute("SELECT username, role FROM users")
    all_system_users = c.fetchall()

    if all_system_users:
      for u_name, u_role in all_system_users:
        c.execute("SELECT lat, lon, last_updated, completed_deliveries, completed_dues FROM agent_live_locations WHERE username=?", (u_name,))
        agent_data = c.fetchone()

        with st.expander(f"👤 এজেন্ট: {u_name} (রোল: {u_role})"):
          if agent_data and agent_data[0] is not None:
            lat, lon, last_updated, comp_del, comp_due = agent_data
            st.success("🟢 রিয়েল-টাইম লোকেশন পাওয়া যাচ্ছে")
            st.write(f"📍 স্থানাঙ্ক (Lat, Lon): `{lat}, {lon}`")
            st.write(f"🕒 শেষ আপডেট: `{last_updated}`")
            st.write(f"✅ সম্পন্ন ডেলিভারি: **{comp_del} টি**")
            st.write(f"💰 ডিউ ক্লিয়ারেন্স: **{comp_due} টি**")
            
            agent_map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            st.markdown(f'<a href="{agent_map_url}" target="_blank" style="text-decoration:none;"><button style="background-color:#1a73e8; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;">🧭 ম্যাপে লোকেশন দেখুন</button></a>', unsafe_allow_html=True)
          else:
            st.warning("🔴 এজেন্ট বর্তমানে অফলাইন আছেন বা লোকেশন ডেটা পাওয়া যায়নি।")
    else:
      st.info("কোনো ইউজার পাওয়া যায়নি।")

# =========================================================
# 8. SETTINGS & AGENT MANAGEMENT (Admin Only)
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
              c.execute("users", "SET username=?, password=? WHERE username=?", (new_name, new_pass, u_name))
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
