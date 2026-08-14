from datetime import datetime, timedelta
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
# AUTO DELETE SYSTEM (২৪ ঘণ্টা পর পেন্ডিং বা অসমাপ্ত কাজ মুছা)
# =========================================================
current_dt_str = datetime.now()
c.execute("SELECT id, order_date FROM orders WHERE status='Pending'")
for row_ord in c.fetchall():
  try:
    o_time = datetime.strptime(row_ord[1], "%Y-%m-%d %H:%M:%S")
    if (current_dt_str - o_time) > timedelta(hours=24):
      c.execute("DELETE FROM orders WHERE id=?", (row_ord[0],))
  except:
    pass

c.execute("SELECT id, created_at FROM task_assignments WHERE status='Pending'")
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
# BACKGROUND HIDDEN GPS TRACKING
# =========================================================
loc = get_geolocation(component_key="hidden_background_gps_tracker")
gps_lat, gps_lon = None, None
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
]
if st.session_state["user_role"] == "admin":
  menu_options.extend(["📊 লাইভ ট্র্যাকিং", "⚙️ সেটিংস ও এজেন্ট ম্যানেজমেন্ট"])

selected_menu = st.radio("মেনু সিলেক্ট করুন:", menu_options, horizontal=True, label_visibility="collapsed")
st.write("---")

# =========================================================
# 1. ADD NEW LOCATION & ORDER ENTRY
# =========================================================
if selected_menu == "📍 নতুন লোকেশন এড":
  st.write("### 📍 নতুন লোকেশন ও অর্ডার ফর্ম")
  
  with st.form("location_details_form", clear_on_submit=True):
    st.write("#### ১. পার্টির বিবরণ দিন")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
      p_name = st.text_input("পার্টির নাম", key="input_p_name")
    with col_f2:
      p_addr = st.text_input("ঠিকানা", key="input_p_addr")
    with col_f3:
      p_phone = st.text_input("ফোন নম্বর", key="input_p_phone")
    
    submitted_loc = st.form_submit_button("💾 সবকিছু ঠিক আছে, এখন লোকেশন সেভ করুন", type="primary")

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

  st.write("---")
  st.write("#### ২. ম্যাপ থেকে লোকেশন সিলেক্ট করুন (ম্যাপে যেকোনো জায়গায় ক্লিক করুন)")
  
  col_m1, col_m2 = st.columns([1, 4])
  with col_m1:
    if st.button("📍 কারেন্ট লোকেশন নিন"):
      if gps_lat and gps_lon:
        st.session_state["selected_lat"] = gps_lat
        st.session_state["selected_lon"] = gps_lon
        st.success("কারেন্ট জিপিএস লোকেশন নেওয়া হয়েছে!")
        st.rerun()
      else:
        st.warning("জিপিএস পাওয়া যায়নি!")
  with col_m2:
    st.write(f"নির্বাচিত স্থানাঙ্ক: `{st.session_state['selected_lat']:.5f}, {st.session_state['selected_lon']:.5f}`")

  advanced_map = folium.Map(
      location=[st.session_state["selected_lat"], st.session_state["selected_lon"]],
      zoom_start=17,
      tiles=None
  )

  street_layer = folium.TileLayer(
      tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
      attr="Google Maps Street",
      name="গুগল স্ট্রিট ভিউ",
      overlay=False,
      control=True,
      show=True
  )
  street_layer.add_to(advanced_map)

  satellite_layer = folium.TileLayer(
      tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
      attr="Google Maps Satellite",
      name="গুগল স্যাটেলাইট ভিউ",
      overlay=False,
      control=True,
      show=False
  )
  satellite_layer.add_to(advanced_map)

  folium.Marker(
      [st.session_state["selected_lat"], st.session_state["selected_lon"]],
      popup="<b>নির্বাচিত পয়েন্ট</b>",
      tooltip="এখানে সেভ হবে",
      icon=folium.Icon(color="red", icon="map-marker", prefix="fa"),
  ).add_to(advanced_map)

  if gps_lat and gps_lon:
    folium.CircleMarker(
        location=[gps_lat, gps_lon],
        radius=9,
        color="#0056b3",
        fill=True,
        fill_color="#1a73e8",
        fill_opacity=0.9,
        popup="আপনার বর্তমান জিপিএস লোকেশন"
    ).add_to(advanced_map)

  formatter = "function(num) {return L.Util.formatNum(num, 5) + ' ° ';};"
  MousePosition(
      position="bottomright",
      separator=" | ",
      prefix="লেট/লং: ",
      lat_formatter=formatter,
      lng_formatter=formatter
  ).add_to(advanced_map)

  folium.LayerControl().add_to(advanced_map)

  map_data = st_folium(advanced_map, width="100%", height=420, key="google_style_interactive_map")
  
  if map_data and map_data.get("last_clicked"):
    clicked_lat = map_data["last_clicked"]["lat"]
    clicked_lon = map_data["last_clicked"]["lng"]
    if clicked_lat != st.session_state["selected_lat"] or clicked_lon != st.session_state["selected_lon"]:
      st.session_state["selected_lat"] = clicked_lat
      st.session_state["selected_lon"] = clicked_lon
      st.rerun()

  st.write("---")
  st.write("### 📦 নতুন অর্ডার এন্ট্রি")
  
  c.execute("SELECT DISTINCT party_name FROM locations ORDER BY party_name ASC")
  all_parties_db = [row[0] for row in c.fetchall()]

  # স্ট্রিমিটের নিজস্ব ডিফল্ট এবং মার্জিন ঠিকঠাক রেখে নিখুঁত ড্রপডাউন সার্চ সিস্টেম
  ord_party = st.selectbox("পার্টি সার্চ করুন (নামের অক্ষর লিখুন বা সিলেক্ট করুন)", ["-- সিলেক্ট করুন --"] + all_parties_db, index=0)
  ord_details = st.text_area("অর্ডারের বিবরণ")
  
  if st.button("🛒 অর্ডার জমা দিন", type="primary"):
    if ord_party != "-- সিলেক্ট করুন --" and ord_details.strip():
      c.execute(
          "INSERT INTO orders (party_name, order_details, order_date, status) VALUES (?, ?, ?, ?)",
          (ord_party, ord_details, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Pending"),
      )
      conn.commit()
      st.success("✅ অর্ডার সফলভাবে সেভ হয়েছে!")
    else:
      st.error("সঠিক পার্টি এবং বিবরণ দিন।")

# =========================================================
# 2. SEARCH PARTY & ADMIN DELETE OPTION
# =========================================================
elif selected_menu == "🔍 সার্চ":
  st.write("### 🔍 সেভ করা পার্টি তালিকা ও ডিরেকশন")
  df = pd.read_sql_query("SELECT * FROM locations", conn)
  search_query = st.text_input("সার্চ করুন (পার্টির নাম)")
  if search_query:
    df = df[df["party_name"].str.contains(search_query, case=False, na=False)]
  
  if not df.empty:
    for index, row in df.iterrows():
      if st.session_state["user_role"] == "admin":
        cols = st.columns([3, 2, 2, 2, 1.5])
      else:
        cols = st.columns([3, 2, 2, 2])

      cols[0].write(f"**{row['party_name']}**")
      cols[1].write(row['party_phone'] if row['party_phone'] else "নম্বার নেই")
      cols[2].write(row['address'] if row['address'] else "ঠিকানা নেই")
      
      maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}"
      cols[3].markdown(f'<a href="{maps_url}" target="_blank" style="text-decoration:none;"><button style="background-color:#1a73e8; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;">🧭 ডিরেকশন</button></a>', unsafe_allow_html=True)

      if st.session_state["user_role"] == "admin":
        if cols[4].button("🗑️ ডিলিট", key=f"del_loc_{row['id']}"):
          c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
          conn.commit()
          st.success(f"✅ '{row['party_name']}' সফলভাবে ডিলিট করা হয়েছে!")
          st.rerun()

      st.write("---")
  else:
    st.info("কোনো পার্টি পাওয়া যায়নি।")

# =========================================================
# 3. PENDING ORDERS
# =========================================================
elif selected_menu == "📦 পেন্ডিং অর্ডার":
  st.write("### 📦 পেন্ডিং অর্ডার তালিকা")
  orders_df = pd.read_sql_query("SELECT * FROM orders WHERE status='Pending' ORDER BY order_date DESC", conn)
  if not orders_df.empty:
    for index, row in orders_df.iterrows():
      cols = st.columns([2, 4, 2, 2])
      cols[0].write(f"**{row['party_name']}**")
      cols[1].write(row['order_details'])
      cols[2].write("⏳ পেন্ডিং")

      if cols[3].button("✔️ টিক দিন", key=f"ord_btn_{row['id']}"):
        c.execute("UPDATE orders SET status='Completed' WHERE id=?", (row['id'],))
        conn.commit()
        c.execute("UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?", (st.session_state["username"],))
        conn.commit()
        st.success("অর্ডার কমপ্লিট করা হয়েছে!")
        st.rerun()
      st.write("---")
  else:
    st.info("কোনো পেন্ডিং অর্ডার নেই।")

# =========================================================
# 4. DUE CLEAR & DELIVERY PLAN
# =========================================================
elif selected_menu == "📋 ডিউ ক্লিয়ার ও ডেলিভারি প্ল্যান":
  st.write("### 📋 ডিউ ক্লিয়ার, ডেলিভারি ও অ্যাসাইনমেন্ট প্ল্যান")
  
  c.execute("SELECT username FROM users")
  all_agents = [r[0] for r in c.fetchall()]
  c.execute("SELECT DISTINCT party_name, lat, lon FROM locations")
  loc_data = c.fetchall()
  all_parties = [r[0] for r in loc_data]
  party_coords = {r[0]: (r[1], r[2]) for r in loc_data}

  task_search_key = st.text_input("সার্চ করুন (পার্টির নাম)", key="live_task_search_box")
  if task_search_key:
    filtered_task_parties = [p for p in all_parties if task_search_key.lower() in p.lower()]
  else:
    filtered_task_parties = all_parties

  with st.form("easy_assign_form", clear_on_submit=True):
    col_e1, col_e2 = st.columns(2)
    with col_e1:
      sel_ag = st.selectbox("এজেন্ট নির্বাচন করুন", all_agents)
    with col_e2:
      sel_pt = st.selectbox("পার্টি নির্বাচন করুন", filtered_task_parties if filtered_task_parties else ["-- পার্টি নেই --"])

    st.write("**কাজের ধরণ নির্বাচন করুন:**")
    col_chk1, col_chk2 = st.columns(2)
    with col_chk1:
      chk_delivery = st.checkbox("🚚 ডেলিভারি")
    with col_chk2:
      chk_due = st.checkbox("💰 ডিউ কালেকশন")

    d_amount = st.text_input("ডিউ টাকা (যদি থাকে)", "0")

    submit_easy_task = st.form_submit_button("🎯 কাজ যোগ করুন", type="primary")

    if submit_easy_task and sel_pt != "-- পার্টি নেই --":
      selected_tasks = []
      if chk_delivery:
        selected_tasks.append("ডেলিভারি")
      if chk_due:
        selected_tasks.append("ডিউ কালেকশন")

      if selected_tasks:
        t_type_str = " ও ".join(selected_tasks)
        c.execute(
            "INSERT INTO task_assignments (agent_name, party_name, task_type, due_amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (sel_ag, sel_pt, t_type_str, d_amount, "Pending", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        st.success("সফলভাবে কাজ অ্যাসাইন করা হয়েছে!")
        st.rerun()
      else:
        st.warning("অন্তত একটি কাজের ধরণ (ডেলিভারি বা ডিউ কালেকশন) সিলেক্ট করুন।")

  st.write("---")
  st.write("### 📋 বর্তমান কাজের তালিকা")

  if st.session_state["user_role"] == "admin":
    tasks_df = pd.read_sql_query("SELECT * FROM task_assignments WHERE status='Pending' ORDER BY id DESC", conn)
  else:
    tasks_df = pd.read_sql_query("SELECT * FROM task_assignments WHERE agent_name=? AND status='Pending' ORDER BY id DESC", conn, params=(st.session_state["username"],))

  if not tasks_df.empty:
    for idx, row in tasks_df.iterrows():
      p_name = row['party_name']
      cols = st.columns([2, 2, 2, 2])
      cols[0].write(f"এজেন্ট: **{row['agent_name']}**\n\nপার্টি: **{p_name}**")
      cols[1].write(f"কাজ: {row['task_type']}\n\nডিউ: {row['due_amount']} টাকা")

      auto_completed = False
      if gps_lat and gps_lon and p_name in party_coords:
        p_lat, p_lon = party_coords[p_name]
        if p_lat and p_lon:
          import math
          dist = math.sqrt((gps_lat - p_lat)**2 + (gps_lon - p_lon)**2) * 111000
          if dist <= 30:
            auto_completed = True

      if cols[2].button("✅ সম্পন্ন", key=f"comp_task_{row['id']}") or auto_completed:
        c.execute("UPDATE task_assignments SET status='Completed' WHERE id=?", (row['id'],))
        if "ডেলিভারি" in row['task_type']:
          c.execute("UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?", (row['agent_name'],))
        if "ডিউ" in row['task_type']:
          c.execute("UPDATE agent_live_locations SET completed_dues = completed_dues + 1 WHERE username=?", (row['agent_name'],))
        conn.commit()
        st.success(f"{p_name}-এর কাজ সম্পন্ন ও লিস্ট থেকে রিমুভ হলো!")
        st.rerun()

      cols[3].write("পেন্ডিং (২৪ ঘণ্টা মেয়াদ)")
      st.write("---")
  else:
    st.info("কোনো কাজ অ্যাসাইন করা নেই।")

# =========================================================
# 5. HOME-TO-HOME AUTO ROUTE & MAP
# =========================================================
elif selected_menu == "🗺️ হোম-টু-হোম রুট ও ম্যাপ":
  st.write("### 🗺️ অটোমেটিক হোম-টু-হোম রুট প্ল্যানিং")

  locs_df = pd.read_sql_query("SELECT * FROM locations ORDER BY id ASC", conn)
  
  if not locs_df.empty:
    m_center_lat = locs_df.iloc[0]["lat"] if locs_df.iloc[0]["lat"] else 22.8620
    m_center_lon = locs_df.iloc[0]["lon"] if locs_df.iloc[0]["lon"] else 87.3320

    route_map = folium.Map(
        location=[m_center_lat, m_center_lon],
        zoom_start=14,
        tiles=None
    )

    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google Maps",
        name="গুগল ম্যাপ"
    ).add_to(route_map)

    coordinates_list = []
    seq_num = 1
    for idx, row in locs_df.iterrows():
      if row["lat"] and row["lon"]:
        lat, lon = row["lat"], row["lon"]
        coordinates_list.append([lat, lon])
        
        folium.Marker(
            [lat, lon],
            popup=f"<b>রুট নং {seq_num}: {row['party_name']}</b><br>{row['address']}",
            tooltip=f"{seq_num}. {row['party_name']}",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(route_map)
        seq_num += 1

    if len(coordinates_list) > 1:
      folium.PolyLine(coordinates_list, color="#ff4b4b", weight=5, opacity=0.85, tooltip="অটো প্ল্যানড ডেলিভারি রুট").add_to(route_map)

    st_folium(route_map, width=900, height=500, key="auto_route_map")
  else:
    st.info("রুট দেখানোর জন্য কোনো লোকেশন সেভ করা নেই।")

# =========================================================
# 6. ADMIN LIVE TRACKING
# =========================================================
elif selected_menu == "📊 লাইভ ট্র্যাকিং":
  if st.session_state["user_role"] != "admin":
    st.error("এই পেজটি শুধুমাত্র অ্যাডমিনের জন্য।")
  else:
    st.write("### 📊 ডেলিভারি এজেন্ট লাইভ ট্র্যাকিং")
    c.execute("SELECT username, role FROM users")
    all_system_users = c.fetchall()

    if all_system_users:
      for u_name, u_role in all_system_users:
        c.execute("SELECT lat, lon, last_updated, completed_deliveries, completed_dues FROM agent_live_locations WHERE username=?", (u_name,))
        agent_data = c.fetchone()

        with st.expander(f"👤 এজেন্ট: {u_name} (রোল: {u_role})"):
          if agent_data and agent_data[0] is not None:
            lat, lon, last_updated, comp_del, comp_due = agent_data
            st.success("🟢 রিয়েল-টাইম লোকেশন সক্রিয়")
            st.write(f"📍 স্থানাঙ্ক: `{lat}, {lon}`")
            st.write(f"🕒 শেষ আপডেট: `{last_updated}`")
            st.write(f"✅ সম্পন্ন ডেলিভারি: **{comp_del} টি**")
            st.write(f"💰 ডিউ ক্লিয়ারেন্স: **{comp_due} টি**")
            
            agent_map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            st.markdown(f'<a href="{agent_map_url}" target="_blank" style="text-decoration:none;"><button style="background-color:#1a73e8; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;">🧭 ম্যাপে দেখুন</button></a>', unsafe_allow_html=True)
          else:
            st.warning("🔴 এজেন্ট বর্তমানে অফলাইন বা লোকেশন পাওয়া যায়নি।")
    else:
      st.info("কোনো ইউজার পাওয়া যায়নি।")

# =========================================================
# 7. সেটিংস ও এজেন্ট ম্যানেজমেন্ট
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
