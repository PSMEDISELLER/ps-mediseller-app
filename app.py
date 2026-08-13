from datetime import datetime, timedelta
import math
import folium
from geopy.geocoders import Nominatim
import pandas as pd
import sqlite3
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation


# =========================================================
# PAGE CONFIGURATION & PWA SETTINGS
# =========================================================

st.set_page_config(
    page_title="P.S Mediseller",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <head>
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="application-name" content="P.S Mediseller">
        <meta name="apple-mobile-web-app-title" content="P.S Mediseller">
        <meta name="theme-color" content="#FF4B4B">
    </head>
    <script>
        // সাইডবারের যেকোনো বাটনে বা রেডিও অপশনে ক্লিক করলেই মোবাইল ভিউতে সাইডবার ক্লোজ করার স্ক্রিপ্ট
        document.addEventListener('click', function(e) {
            const target = e.target;
            const sidebar = document.querySelector('[data-testid="stSidebar"]');
            
            if (sidebar && sidebar.contains(target)) {
                if (target.closest('button') || target.closest('label') || target.closest('[data-baseweb="radio"]')) {
                    if (!target.closest('[data-testid="stExpander"]')) {
                        setTimeout(() => {
                            const closeButton = document.querySelector('button[kind="header"]');
                            const computedStyle = window.getComputedStyle(sidebar);
                            if (closeButton && computedStyle.display !== 'none' && window.innerWidth <= 992) {
                                closeButton.click();
                            }
                        }, 150);
                    }
                }
            }
        });
    </script>
""",
    unsafe_allow_html=True,
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


# =========================================================
# DEFAULT USERS
# =========================================================

c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
  c.execute(
      "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
      ("admin", "admin123", "admin"),
  )
  c.execute(
      "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
      ("delivery", "user123", "staff"),
  )
  conn.commit()


# =========================================================
# SESSION MANAGEMENT (PERMANENT LOGIN FIX)
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
# LOGIN PAGE
# =========================================================

if not st.session_state["logged_in"]:
  st.title("🔑 লগইন পোর্টাল")
  st.subheader("P.S Mediseller Location App")

  tab1, tab2 = st.tabs(["লগইন", "পাসওয়ার্ড ভুলে গেছেন?"])

  with tab1:
    with st.form("login_form"):
      username = st.text_input("ইউজারনেম", key="login_user")
      password = st.text_input("পাসওয়ার্ড", type="password", key="login_pass")
      remember_me = st.checkbox("আমাকে মনে রাখুন (Permanent Login)", value=True)

      submit_login = st.form_submit_button("লগইন করুন", type="primary")

      if submit_login:
        c.execute("SELECT password, role FROM users WHERE username=?", (username,))
        user_data = c.fetchone()
        if user_data and user_data[0] == password:
          st.session_state["logged_in"] = True
          st.session_state["username"] = username
          st.session_state["user_role"] = user_data[1]
          
          if remember_me:
            st.query_params["user"] = username
            
          st.success("লগইন সফল হয়েছে!")
          st.rerun()
        else:
          st.error("❌ ভুল ইউজারনেম অথবা পাসওয়ার্ড!")

  with tab2:
    with st.form("forgot_pass_form"):
      f_user = st.text_input("ইউজারনেম", key="forgot_user")
      new_pass = st.text_input("নতুন পাসওয়ার্ড", type="password", key="new_pass_admin")
      admin_pass = st.text_input("বর্তমান অ্যাডমিন পাসওয়ার্ড", type="password", key="admin_auth")

      submit_reset = st.form_submit_button("পাসওয়ার্ড রিসেট করুন")

      if submit_reset:
        c.execute("SELECT password FROM users WHERE username='admin'")
        admin_data = c.fetchone()
        if admin_data and admin_pass == admin_data[0]:
          c.execute("SELECT username FROM users WHERE username=?", (f_user,))
          if c.fetchone():
            c.execute("UPDATE users SET password=? WHERE username=?", (new_pass, f_user))
            conn.commit()
            st.success("✅ পাসওয়ার্ড সফলভাবে পরিবর্তন হয়েছে।")
          else:
            st.error("এই ইউজারনেম পাওয়া যায়নি।")
        else:
          st.error("❌ অ্যাডমিন পাসওয়ার্ড ভুল!")
  st.stop()


# =========================================================
# SIDEBAR & PROFILE / ADMIN SETTINGS
# =========================================================

with st.sidebar:
  st.header("👤 ইউজার তথ্য")
  st.write(f"ইউজার: **{st.session_state['username']}**")
  if st.session_state["user_role"] == "admin":
    st.success("রোল: ADMIN")
  else:
    st.info("রোল: DELIVERY USER (staff)")

  if st.session_state["user_role"] != "admin":
    with st.expander("⚙️ আমার অ্যাকাউন্ট সেটিংস (নাম ও রোল)"):
      with st.form("staff_self_update_form"):
        st.write("আপনার নাম বা রোল পরিবর্তন করুন:")
        s_new_name = st.text_input("নতুন ইউজারনেম", value=st.session_state["username"])
        s_current_role_idx = 0 if st.session_state["user_role"] == "admin" else 1
        s_new_role = st.selectbox("রোল সিলেক্ট করুন", ["admin", "staff"], index=s_current_role_idx)

        if st.form_submit_button("💾 আপডেট করুন", type="primary"):
          if not s_new_name.strip():
            st.error("ইউজারনেম খালি রাখা যাবে না!")
          else:
            try:
              old_uname = st.session_state["username"]
              c.execute("SELECT password FROM users WHERE username=?", (old_uname,))
              current_pass = c.fetchone()[0]

              if old_uname != s_new_name:
                c.execute("SELECT COUNT(*) FROM users WHERE username=?", (s_new_name,))
                if c.fetchone()[0] > 0:
                  st.error("❌ এই ইউজারনেমটি ইতিমধ্যে ব্যবহৃত হচ্ছে!")
                  st.stop()
                c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (s_new_name, current_pass, s_new_role))
                c.execute("DELETE FROM users WHERE username=?", (old_uname,))
              else:
                c.execute("UPDATE users SET role=? WHERE username=?", (s_new_role, old_uname))

              conn.commit()
              st.session_state["username"] = s_new_name
              st.session_state["user_role"] = s_new_role
              st.query_params["user"] = s_new_name
              st.success("✅ সফলভাবে আপডেট হয়েছে!")
              st.rerun()
            except Exception as e:
              st.error(f"ত্রুটি: {e}")

  if st.session_state["user_role"] == "admin":
    with st.expander("⚙️ অ্যাডমিন কন্ট্রোল (ইউজার ও পাসওয়ার্ড ম্যানেজমেন্ট)"):
      c.execute("SELECT username, role FROM users")
      all_users = c.fetchall()
      st.info(f"👥 মোট ইউজার সংখ্যা: **{len(all_users)} জন**")

      user_list = [u[0] for u in all_users]
      target_user = st.selectbox("ইউজার সিলেক্ট করুন", user_list)

      c.execute("SELECT role, password FROM users WHERE username=?", (target_user,))
      t_data = c.fetchone()
      t_current_role = t_data[0] if t_data else "staff"
      t_current_pass = t_data[1] if t_data else ""

      with st.form("admin_edit_user_form"):
        st.write(f"এডিট করছেন: `{target_user}`")
        new_u_name = st.text_input("নতুন ইউজারনেম", value=target_user)
        new_u_pass = st.text_input("নতুন পাসওয়ার্ড", value=t_current_pass, type="password")
        
        role_idx = 0 if t_current_role == "admin" else 1
        new_u_role = st.selectbox("রোল নির্ধারণ করুন", ["admin", "staff"], index=role_idx)

        if st.form_submit_button("💾 পরিবর্তন সেভ করুন", type="primary"):
          if not new_u_name.strip():
            st.error("ইউজারনেম খালি রাখা যাবে না!")
          else:
            try:
              if target_user != new_u_name:
                c.execute("SELECT COUNT(*) FROM users WHERE username=?", (new_u_name,))
                if c.fetchone()[0] > 0:
                  st.error("❌ এই ইউজারনেমটি ইতিমধ্যে ব্যবহৃত হচ্ছে!")
                  st.stop()
                c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (new_u_name, new_u_pass, new_u_role))
                c.execute("DELETE FROM users WHERE username=?", (target_user,))
              else:
                c.execute("UPDATE users SET password=?, role=? WHERE username=?", (new_u_pass, new_u_role, target_user))
              
              conn.commit()
              st.success(f"✅ '{target_user}'-এর তথ্য সফলভাবে আপডেট করা হয়েছে!")
              st.rerun()
            except Exception as e:
              st.error(f"ত্রুটি: {e}")

      st.write("---")
      del_target_user = st.selectbox("ডিলিট ইউজার", user_list, key="del_u_box")
      if st.button("🗑️ ইউজার রিমুভ করুন", type="primary"):
        if del_target_user == st.session_state["username"]:
          st.error("❌ নিজের অ্যাকাউন্ট ডিলিট করা নিষেধ!")
        else:
          c.execute("DELETE FROM users WHERE username=?", (del_target_user,))
          conn.commit()
          st.success(f"✅ '{del_target_user}' রিমুভ করা হয়েছে।")
          st.rerun()

  st.write("---")
  if st.button("🚪 লগআউট"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = None
    st.session_state["user_role"] = None
    st.query_params.clear()
    st.rerun()


# =========================================================
# LOW-DATA GPS TRACKER FOR DELIVERY AGENT
# =========================================================

st.title("🚚 পি এস মেডিসেলার")

loc = get_geolocation(component_key="low_data_gps_tracker")

gps_lat, gps_lon = None, None
if loc and "coords" in loc:
  gps_lat = loc["coords"]["latitude"]
  gps_lon = loc["coords"]["longitude"]

  current_user_name = st.session_state["username"]
  c.execute(
      "INSERT OR REPLACE INTO agent_live_locations (username, lat, lon, last_updated) VALUES (?, ?, ?, ?)",
      (current_user_name, gps_lat, gps_lon, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
  )
  conn.commit()

  all_locs_df = pd.read_sql_query("SELECT * FROM locations", conn)
  for _, p_row in all_locs_df.iterrows():
    dist_meters = math.sqrt((p_row["lat"] - gps_lat)**2 + (p_row["lon"] - gps_lon)**2) * 111000
    if dist_meters <= 42:
      c.execute("UPDATE orders SET status='Completed' WHERE party_name=? AND status='Pending'", (p_row["party_name"],))
      conn.commit()

if not gps_lat and st.session_state["user_role"] != "admin":
  c.execute("SELECT lat, lon FROM agent_live_locations WHERE username=?", (st.session_state["username"],))
  existing_ag = c.fetchone()
  if not existing_ag:
    c.execute(
        "INSERT OR REPLACE INTO agent_live_locations (username, lat, lon, last_updated) VALUES (?, ?, ?, ?)",
        (st.session_state["username"], 22.8620, 87.3320, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

menu = [
    "📍 নতুন লোকেশন এড করুন",
    "🔍 পার্টি ও লোকেশন সার্চ",
    "🗺️ রুট প্ল্যানিং ও ম্যাপ",
    "📦 পেন্ডিং অর্ডার ও বিলিং",
]

if st.session_state["user_role"] == "admin":
  menu.append("📊 অ্যাডমিন লাইভ ট্র্যাকিং ঘর")

with st.sidebar:
  st.write("---")
  st.markdown("### মেনু নির্বাচন করুন")
  choice = st.radio("মেনু সিলেক্ট করুন", menu, label_visibility="collapsed")


# =========================================================
# 1. ADD NEW LOCATION & ORDER ENTRY
# =========================================================

if choice == "📍 নতুন লোকেশন এড করুন":
  st.header("📍 নতুন পার্টির লোকেশন ও অর্ডার যোগ করুন")
  col1, col2 = st.columns(2)

  with col1:
    st.write("### 📍 কারেন্ট লোকেশন পিন")
    if st.button("🔄 কারেন্ট লোকেশনে পিন সেট করুন"):
      if gps_lat and gps_lon:
        st.session_state["selected_lat"] = gps_lat
        st.session_state["selected_lon"] = gps_lon
        st.success("✅ কারেন্ট লোকেশন সিলেক্ট হয়েছে!")
        st.rerun()
      else:
        st.warning("⚠️ GPS সিগন্যাল পাওয়া যায়নি। অনুগ্রহ করে ফোনের লোকেশন/GPS অন রাখুন।")

  with col2:
    st.write("### 📦 পার্টির নতুন অর্ডার এন্ট্রি")
    c.execute("SELECT DISTINCT party_name FROM locations ORDER BY party_name ASC")
    all_parties_db = [row[0] for row in c.fetchall()]

    with st.form("order_entry_form", clear_on_submit=True):
      order_party_name = st.selectbox("পার্টি নির্বাচন করুন", ["-- সিলেক্ট করুন --"] + all_parties_db)
      order_details_input = st.text_area("অর্ডারের বিবরণ")
      if st.form_submit_button("🛒 অর্ডার জমা দিন", type="primary"):
        if order_party_name != "-- সিলেক্ট করুন --" and order_details_input.strip():
          c.execute(
              "INSERT INTO orders (party_name, order_details, order_date, status) VALUES (?, ?, ?, ?)",
              (order_party_name, order_details_input, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Pending"),
          )
          conn.commit()
          st.success("✅ অর্ডার সফলভাবে সেভ হয়েছে!")

  map_center = [st.session_state["selected_lat"], st.session_state["selected_lon"]]
  m_click = folium.Map(
      location=map_center,
      zoom_start=16,
      tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
      attr="Google"
  )

  if gps_lat and gps_lon:
    folium.CircleMarker(
        location=[gps_lat, gps_lon],
        radius=9,
        color="white",
        weight=2,
        fill=True,
        fill_color="#1a73e8",
        fill_opacity=1.0,
        tooltip="আপনার কারেন্ট লোকেশন (Live)"
    ).add_to(m_click)

  folium.Marker(
      [st.session_state["selected_lat"], st.session_state["selected_lon"]],
      popup="সিলেক্টেড লোকেশন",
      icon=folium.Icon(color="red", icon="map-marker", prefix="fa")
  ).add_to(m_click)

  map_data = st_folium(m_click, width=900, height=450, key="interactive_map")

  if map_data and map_data.get("last_clicked"):
    clicked_lat = map_data["last_clicked"]["lat"]
    clicked_lon = map_data["last_clicked"]["lng"]
    if clicked_lat != st.session_state["selected_lat"] or clicked_lon != st.session_state["selected_lon"]:
      st.session_state["selected_lat"] = clicked_lat
      st.session_state["selected_lon"] = clicked_lon
      st.rerun()

  with st.form("new_location_form", clear_on_submit=True):
    party_name = st.text_input("পার্টির নাম")
    address = st.text_input("ঠিকানা")
    party_phone = st.text_input("ফোন নম্বর")
    if st.form_submit_button("💾 লোকেশন সেভ করুন", type="primary"):
      if party_name and party_phone:
        c.execute(
            "INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, ?, ?)",
            (party_name, address, party_phone, st.session_state["selected_lat"], st.session_state["selected_lon"]),
        )
        conn.commit()
        st.success("✅ লোকেশন সেভ হয়েছে!")


# =========================================================
# 2. SEARCH PARTY
# =========================================================

elif choice == "🔍 পার্টি ও লোকেশন সার্চ":
  st.header("🔍 পার্টি ও লোকেশন সার্চ")
  df = pd.read_sql_query("SELECT * FROM locations", conn)
  search_query = st.text_input("সার্চ করুন")
  if search_query:
    df = df[df["party_name"].str.contains(search_query, case=False, na=False)]
  st.dataframe(df, use_container_width=True, hide_index=True)


# =========================================================
# 3. ROUTE PLANNING
# =========================================================

elif choice == "🗺️ রুট প্ল্যানিং ও ম্যাপ":
  st.header("🗺️ স্মার্ট রুট প্ল্যানার")

  locations_df = pd.read_sql_query("SELECT * FROM locations", conn)
  if locations_df.empty:
    st.info("কোনো লোকেশন নেই।")
  else:
    selected_parties = st.multiselect("পার্টি সিলেক্ট করুন:", locations_df["party_name"].tolist(), default=locations_df["party_name"].tolist())

    if st.button("🚀 শর্টকাট রুট ও ম্যাপ তৈরি করুন", type="primary"):
      route_input_data = []
      for p_name in selected_parties:
        p_row = locations_df[locations_df["party_name"] == p_name].iloc[0]
        route_input_data.append({
            "party_name": p_name,
            "address": p_row["address"],
            "party_phone": p_row["party_phone"],
            "lat": float(p_row["lat"]),
            "lon": float(p_row["lon"]),
        })

      home_lat = gps_lat if gps_lat else route_input_data[0]["lat"]
      home_lon = gps_lon if gps_lon else route_input_data[0]["lon"]
      unvisited = route_input_data.copy()
      optimized_route = []
      curr_lat, curr_lon = home_lat, home_lon

      while unvisited:
        next_stop = min(unvisited, key=lambda x: math.sqrt((x["lat"] - curr_lat)**2 + (x["lon"] - curr_lon)**2))
        optimized_route.append(next_stop)
        curr_lat, curr_lon = next_stop["lat"], next_stop["lon"]
        unvisited.remove(next_stop)

      st.session_state["optimized_route"] = optimized_route
      st.success("✅ শর্টকাট রুট তৈরি হয়েছে!")
      st.rerun()

    if "optimized_route" in st.session_state:
      route = st.session_state["optimized_route"]
      st.subheader("📋 রুট লিস্ট ও লাইভ স্ট্যাটাস")
      for idx, stop in enumerate(route, 1):
        c.execute("SELECT status FROM orders WHERE party_name=?", (stop["party_name"],))
        ord_status = c.fetchone()
        status_text = ord_status[0] if ord_status else "Pending"
        badge = "🟢 সম্পন্ন (Completed)" if status_text == "Completed" else "⏳ বাকি আছে (Pending)"
        st.write(f"**{idx}. {stop['party_name']}** — {badge}")


# =========================================================
# 4. PENDING ORDERS & BILLING SECTION
# =========================================================

elif choice == "📦 পেন্ডিং অর্ডার ও বিলিং":
  st.header("📦 পেন্ডিং অর্ডার ও বিলিং ম্যানেজমেন্ট (অ্যাডমিন প্যানেল)")

  orders_df = pd.read_sql_query("SELECT * FROM orders ORDER BY order_date DESC", conn)
  if orders_df.empty:
    st.info("কোনো অর্ডার নেই।")
  else:
    for _, row in orders_df.iterrows():
      st.markdown(f"**পার্টি:** {row['party_name']} | **স্ট্যাটাস:** `{row['status']}` | **সময়:** {row['order_date']}")
      st.write(f" বিবরণ: {row['order_details']}")
      st.write("---")


# =========================================================
# 5. ADMIN LIVE TRACKING ROOM
# =========================================================

elif choice == "📊 অ্যাডমিন লাইভ ট্র্যাকিং ঘর":
  st.header("📊 ডেলিভারি এজেন্ট লাইভ ট্র্যাকিং ও মনিটর")
  st.info("এখানে আপনার সমস্ত ডেলিভারি বয় বা স্টাফদের নাম দেখতে পাবেন। যেকোনো একটি নামের ওপর ক্লিক করলেই তার বর্তমান লোকেশন দেখতে পাবেন।")

  col_ref1, col_ref2 = st.columns([1, 4])
  with col_ref1:
    if st.button("🔄 রিফ্রেশ করুন"):
      st.rerun()

  c.execute("SELECT username FROM users WHERE role='staff'")
  staff_rows = c.fetchall()
  staff_list = [row[0] for row in staff_rows]

  if not staff_list:
    st.warning("⚠️ কোনো ডেলিভারি স্টাফ ইউজার পাওয়া যায়নি।")
  else:
    st.write("### 👤 ডেলিভারি বয় তালিকা:")
    selected_agent = st.radio("স্টাফ নির্বাচন করুন:", staff_list, horizontal=True)

    if selected_agent:
      st.write("---")
      st.subheader(f"📌 স্টাফ: `{selected_agent}` -এর লাইভ লোকেশন ও স্ট্যাটাস")

      c.execute("SELECT lat, lon, last_updated FROM agent_live_locations WHERE username=?", (selected_agent,))
      agent_loc_data = c.fetchone()

      if agent_loc_data and agent_loc_data[0] is not None:
        ag_lat, ag_lon, ag_time = agent_loc_data[0], agent_loc_data[1], agent_loc_data[2]
        st.success(f"🟢 সর্বশেষ আপডেট সময়: {ag_time}")

        all_parties_df = pd.read_sql_query("SELECT * FROM locations", conn)
        
        if all_parties_df.empty:
          st.warning("⚠️ কোনো লোকেশন বা পার্টি ডেটাবেজে নেই।")
        else:
          party_distance_list = []
          for _, p in all_parties_df.iterrows():
            dist = math.sqrt((p["lat"] - ag_lat)**2 + (p["lon"] - ag_lon)**2) * 111000
            
            c.execute("SELECT status FROM orders WHERE party_name=?", (p["party_name"],))
            ord_res = c.fetchone()
            p_status = ord_res[0] if ord_res else "Pending"

            party_distance_list.append({
                "পার্টির নাম": p["party_name"],
                "ঠিকানা": p["address"],
                "ফোন": p["party_phone"],
                "দূরত্ব (মিটারে)": round(dist, 1),
                "অর্ডার স্ট্যাটাস": "🟢 সম্পন্ন" if p_status == "Completed" else "⏳ পেন্ডিং"
            })

          df_parties_dist = pd.DataFrame(party_distance_list)
          if not df_parties_dist.empty and "দূরত্ব (মিটারে)" in df_parties_dist.columns:
            df_parties_dist = df_parties_dist.sort_values(by="দূরত্ব (মিটারে)")
          st.dataframe(df_parties_dist, use_container_width=True, hide_index=True)

          m_agent = folium.Map(
              location=[ag_lat, ag_lon],
              zoom_start=15,
              tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
              attr="Google"
          )
          folium.Marker([ag_lat, ag_lon], tooltip=f"Agent: {selected_agent}", icon=folium.Icon(color="blue", icon="user", prefix="fa")).add_to(m_agent)
          
          for _, p in all_parties_df.iterrows():
            folium.Marker([p["lat"], p["lon"]], tooltip=p["party_name"], icon=folium.Icon(color="red", icon="shopping-cart", prefix="fa")).add_to(m_agent)

          st_folium(m_agent, width=900, height=400, key=f"map_{selected_agent}")

      else:
        st.warning(f"⚠️ '{selected_agent}' এখনো অ্যাপে জিপিএস পারমিশন দেয়নি অথবা সিগন্যাল পাওয়া যায়নি।")

st.write("---")
st.caption("P.S Mediseller Location App | Mobile UX Optimized")
