from datetime import datetime, timedelta
import json
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

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    role TEXT NOT NULL,
    fullname TEXT,
    phone TEXT,
    created_at TIMESTAMP,
    is_active INTEGER DEFAULT 1
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    party_name TEXT NOT NULL UNIQUE,
    address TEXT,
    party_phone TEXT UNIQUE,
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
c.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    date TEXT NOT NULL,
    check_time TEXT NOT NULL,
    status TEXT DEFAULT 'Present',
    UNIQUE(username, date)
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

c.execute("PRAGMA table_info(users)")
existing_user_cols = [row[1] for row in c.fetchall()]
if "fullname" not in existing_user_cols:
  c.execute("ALTER TABLE users ADD COLUMN fullname TEXT")
if "phone" not in existing_user_cols:
  c.execute("ALTER TABLE users ADD COLUMN phone TEXT")
if "created_at" not in existing_user_cols:
  c.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
if "is_active" not in existing_user_cols:
  c.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")

conn.commit()

# ডিফল্ট ইউজার তৈরি
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
  c.execute("INSERT INTO users (username, password, role, fullname, phone, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", 
            ("admin", "admin123", "admin", "Admin", "910000000000", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1))
  c.execute("INSERT INTO users (username, password, role, fullname, phone, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", 
            ("delivery", "user123", "staff", "Delivery Agent", "910000000000", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1))
  conn.commit()

# =========================================================
# AUTO DELETE SYSTEM (২৪ ঘণ্টা পর পেন্ডিং ও কমপ্লিট কাজ ও অর্ডার মুছা)
# =========================================================
current_dt_str = datetime.now()

c.execute("SELECT id, order_date, status FROM orders")
for row_ord in c.fetchall():
  try:
    o_time = datetime.strptime(row_ord[1], "%Y-%m-%d %H:%M:%S")
    if (current_dt_str - o_time) > timedelta(hours=24):
      c.execute("DELETE FROM orders WHERE id=?", (row_ord[0],))
  except:
    pass

c.execute("SELECT id, created_at, status FROM task_assignments")
for row_task in c.fetchall():
  try:
    t_time = datetime.strptime(row_task[1], "%Y-%m-%d %H:%M:%S")
    if (current_dt_str - t_time) > timedelta(hours=24):
      c.execute("DELETE FROM task_assignments WHERE id=?", (row_task[0],))
  except:
    pass
conn.commit()

# =========================================================
# SESSION STATE INITIALIZATION
# =========================================================
if "selected_lat" not in st.session_state:
  st.session_state["selected_lat"] = 22.8620
if "selected_lon" not in st.session_state:
  st.session_state["selected_lon"] = 87.3320

if "username" not in st.session_state:
  st.session_state["username"] = "delivery"
if "user_role" not in st.session_state:
  st.session_state["user_role"] = "staff"

# =========================================================
# DIRECT WHATSAPP LOGIN HANDLER (URL QUERY PARAM)
# =========================================================
query_params = st.query_params
login_user = query_params.get("login", None)

if login_user:
  c.execute("SELECT fullname, role FROM users WHERE username=?", (login_user,))
  user_row = c.fetchone()
  if user_row:
    f_name, r_role = user_row
    st.session_state["username"] = login_user
    st.session_state["user_role"] = r_role
    st.success(f"✅ স্বাগতম, {f_name}! আপনাকে সফলভাবে সরাসরি অ্যাপে লগইন করানো হয়েছে।")
    st.query_params.pop("login", None)
    st.rerun()
  else:
    st.error("❌ ভুল বা অসংগত লিংক!")
    st.stop()

# =========================================================
# MAIN APP HEADER & ADMIN LOGIN OPTION
# =========================================================
st.title("পি এস মেডিসেলার ডেলিভারি পার্টনার")

col_u1, col_u2 = st.columns([3, 1])
with col_u1:
  st.write(f"👤 ইউজার: **{st.session_state['username']}** (`{st.session_state['user_role']}`)")
with col_u2:
  if st.session_state["user_role"] == "admin":
    if st.button("🚪 অ্যাডমিন লগআউট"):
      st.session_state["username"] = "delivery"
      st.session_state["user_role"] = "staff"
      st.rerun()
  else:
    if st.button("🔐 অ্যাডমিন লগইন"):
      st.session_state["show_admin_login"] = True
      st.rerun()

if st.session_state.get("show_admin_login", False):
  with st.form("admin_login_popup_form"):
    st.write("#### 🔑 অ্যাডমিন লগইন")
    admin_pass_input = st.text_input("অ্যাডমিন পাসওয়ার্ড দিন", type="password")
    col_al1, col_al2 = st.columns(2)
    with col_al1:
      submit_admin = st.form_submit_button("লগইন করুন", type="primary")
    with col_al2:
      cancel_admin = st.form_submit_button("বাতিল")

    if submit_admin:
      c.execute("SELECT password, role FROM users WHERE username='admin'")
      adm_row = c.fetchone()
      if adm_row and adm_row[0] == admin_pass_input:
        st.session_state["username"] = "admin"
        st.session_state["user_role"] = "admin"
        st.session_state["show_admin_login"] = False
        st.success("অ্যাডমিন লগইন সফল হয়েছে!")
        st.rerun()
      else:
        st.error("❌ ভুল পাসওয়ার্ড!")
    if cancel_admin:
      st.session_state["show_admin_login"] = False
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
    "📅 উপস্থিতি (Attendance)",
]
if st.session_state["user_role"] == "admin":
  menu_options.extend(["📊 লাইভ ট্র্যাকিং", "⚙️ সেটিংস ও এজেন্ট ম্যানেজমেন্ট"])

current_page_param = query_params.get("page", menu_options[0])
if current_page_param not in menu_options:
  current_page_param = menu_options[0]

default_index = menu_options.index(current_page_param)

selected_menu = st.radio("মেনু সিলেক্ট করুন:", menu_options, index=default_index, horizontal=True, label_visibility="collapsed")

if selected_menu != current_page_param:
  st.query_params["page"] = selected_menu
  st.rerun()

st.write("---")

# =========================================================
# 1. ADD NEW LOCATION & ORDER ENTRY
# =========================================================
if selected_menu == "📍 নতুন লোকেশন এড":
  st.write("### 📍 নতুন লোকেশন ও ডক্টর/পার্টি এন্ট্রি ফর্ম")
  
  col_tab1, col_tab2 = st.tabs(["🏠 সাধারণ লোকেশন (ম্যাপসহ)", "👨‍⚕️ ডক্টর / ম্যাপ ছাড়া পার্টি এন্ট্রি"])
  
  with col_tab1:
    with st.form("location_details_form", clear_on_submit=True):
      st.write("#### ১. পার্টির বিবরণ দিন (ম্যাপে সেভ হবে)")
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
        c.execute("SELECT id FROM locations WHERE LOWER(party_name) = LOWER(?) OR party_phone = ?", (p_name.strip(), p_phone.strip()))
        existing_check = c.fetchone()
        
        if existing_check:
          st.error(f"❌ এলার্ট: '{p_name.strip()}' নামের অথবা এই ফোন নম্বরের পার্টি ইতিমধ্যে ডাটাবেসে সেভ করা আছে! পুনরায় সেভ করা যাবে না।")
        else:
          try:
            c.execute(
                "INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, ?, ?)",
                (p_name.strip(), p_addr, p_phone.strip(), st.session_state["selected_lat"], st.session_state["selected_lon"]),
            )
            conn.commit()
            st.success("✅ লোকেশন সফলভাবে সেভ হয়েছে!")
            st.rerun()
          except sqlite3.IntegrityError:
            st.error("❌ এলার্ট: এই নামের অথবা এই ফোন নম্বরের পার্টি ইতিমধ্যে সেভ করা আছে!")
      else:
        st.error("পার্টির নাম এবং ফোন নম্বর আবশ্যক।")

  with col_tab2:
    with st.form("doctor_details_form", clear_on_submit=True):
      st.write("#### ২. ডক্টর বা স্পেশাল পার্টির বিবরণ (ম্যাপ ছাড়াই)")
      col_d1, col_d2, col_d3 = st.columns(3)
      with col_d1:
        doc_name = st.text_input("ডাক্তার/পার্টির নাম", key="input_doc_name")
      with col_d2:
        doc_addr = st.text_input("ঠিকানা/চেম্বার", key="input_doc_addr")
      with col_d3:
        doc_phone = st.text_input("ফোন নম্বর", key="input_doc_phone")
      
      submitted_doc = st.form_submit_button("💾 ডক্টর/পার্টি সেভ করুন (ম্যাপ ছাড়া)", type="primary")

    if submitted_doc:
      if doc_name.strip() and doc_phone.strip():
        c.execute("SELECT id FROM locations WHERE LOWER(party_name) = LOWER(?) OR party_phone = ?", (doc_name.strip(), doc_phone.strip()))
        existing_check_doc = c.fetchone()

        if existing_check_doc:
          st.error(f"❌ এলার্ট: '{doc_name.strip()}' নামের অথবা এই ফোন নম্বরের পার্টি ইতিমধ্যে ডাটাবেসে সেভ করা আছে! পুনরায় সেভ করা যাবে না।")
        else:
          try:
            c.execute(
                "INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, NULL, NULL)",
                (doc_name.strip(), doc_addr, doc_phone.strip()),
            )
            conn.commit()
            st.success("✅ ডক্টর/পার্টি সফলভাবে সেভ হয়েছে! (ম্যাপে যুক্ত করতে সার্চ অপশন ব্যবহার করুন)")
            st.rerun()
          except sqlite3.IntegrityError:
            st.error("❌ এলার্ট: এই নামের অথবা এই ফোন নম্বরের পার্টি ইতিমধ্যে সেভ করা আছে!")
      else:
        st.error("ডাক্তার/পার্টির নাম এবং ফোন নম্বর আবশ্যক।")

  st.write("---")
  st.write("#### ম্যাপ থেকে লোকেশন সিলেক্ট করুন (ম্যাপে যেকোনো জায়গায় ক্লিক করুন)")
  
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
  
  c.execute("SELECT party_name FROM locations ORDER BY party_name ASC")
  all_parties_db = [row[0] for row in c.fetchall()]

  parties_json = json.dumps(all_parties_db)

  search_html = f"""
  <div style="position: relative; width: 100%; margin-bottom: 15px; box-sizing: border-box;">
    <label style="font-weight: 600; font-size: 14px; color: #ffffff; display: block; margin-bottom: 5px;">পার্টি সার্চ করুন (নামের অক্ষর লিখুন)</label>
    <input type="text" id="party_search_box" placeholder="এখানে টাইপ করুন..." style="width: 100%; max-width: 100%; padding: 12px; border: 1px solid #cccccc; border-radius: 6px; font-size: 16px; background-color: #1e1e1e; color: #ffffff; box-sizing: border-box;" autocomplete="off">
    <div id="suggestions_list" style="position: absolute; width: 100%; max-height: 200px; overflow-y: auto; background: #262730; border: 1px solid #444444; border-top: none; border-radius: 0 0 6px 6px; z-index: 9999; display: none; box-sizing: border-box; box-shadow: 0px 4px 6px rgba(0,0,0,0.3);"></div>
  </div>

  <script>
    const allParties = {parties_json};
    const searchBox = document.getElementById("party_search_box");
    const suggestionsList = document.getElementById("suggestions_list");

    searchBox.addEventListener("input", function() {{
      const query = this.value.toLowerCase().trim();
      suggestionsList.innerHTML = "";
      if (query === "") {{
        suggestionsList.style.display = "none";
        return;
      }}
      const filtered = allParties.filter(p => p.toLowerCase().includes(query));
      if (filtered.length > 0) {{
        suggestionsList.style.display = "block";
        filtered.forEach(party => {{
          const item = document.createElement("div");
          item.innerText = party;
          item.style.padding = "10px 12px";
          item.style.cursor = "pointer";
          item.style.borderBottom = "1px solid #333333";
          item.style.color = "#ffffff";
          item.onmouseover = function() {{ this.style.backgroundColor = "#333333"; }};
          item.onmouseout = function() {{ this.style.backgroundColor = "#262730"; }};
          item.onclick = function() {{
            searchBox.value = party;
            suggestionsList.style.display = "none";
          }};
          suggestionsList.appendChild(item);
        }});
      }} else {{
        suggestionsList.style.display = "none";
      }}
    }});

    document.addEventListener("click", function(e) {{
      let path = e.composedPath();
      if (!path.includes(searchBox) && !path.includes(suggestionsList)) {{
        suggestionsList.style.display = "none";
      }}
    }});
  </script>
  """
  st.components.v1.html(search_html, height=115)

  ord_details = st.text_area("অর্ডারের বিবরণ")
  
  if st.button("🛒 অর্ডার জমা দিন", type="primary"):
    st.info("দয়া করে সার্চ বক্স থেকে পার্টির নামটি লিখে বা ড্রপডাউন থেকে সিলেক্ট করে নিশ্চিত করুন।")

# =========================================================
# 2. SEARCH PARTY & ADMIN DELETE OPTION
# =========================================================
elif selected_menu == "🔍 সার্চ":
  st.write("### 🔍 সার্চ ও পার্টি/ডক্টর ম্যানেজমেন্ট পোর্টাল")

  if st.session_state.get("mapping_party_id"):
    st.markdown(f"### 📍 **{st.session_state['mapping_party_name']}** এর জন্য ম্যাপ সেট করুন")
    st.write("ম্যাপে সঠিক জায়গায় ক্লিক করে লোকেশন সিলেক্ট করুন এবং নিচের **'✅ লোকেশন সেভ করুন (OK)'** বাটনে ক্লিক করুন।")
    
    if "temp_map_lat" not in st.session_state:
      st.session_state["temp_map_lat"] = 22.8620
    if "temp_map_lon" not in st.session_state:
      st.session_state["temp_map_lon"] = 87.3320

    col_tm1, col_tm2 = st.columns([1, 4])
    with col_tm1:
      if st.button("📍 কারেন্ট জিপিএস নিন", key="btn_curr_gps_temp"):
        if gps_lat and gps_lon:
          st.session_state["temp_map_lat"] = gps_lat
          st.session_state["temp_map_lon"] = gps_lon
          st.success("কারেন্ট জিপিএস নেওয়া হয়েছে!")
          st.rerun()
        else:
          st.warning("জিপিএস পাওয়া যায়নি!")
    with col_tm2:
      st.write(f"নির্বাচিত স্থানাঙ্ক: `{st.session_state['temp_map_lat']:.5f}, {st.session_state['temp_map_lon']:.5f}`")

    pick_map = folium.Map(
        location=[st.session_state["temp_map_lat"], st.session_state["temp_map_lon"]],
        zoom_start=17,
        tiles=None
    )
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google Maps Street",
        name="স্ট্রিট ভিউ",
        show=True
    ).add_to(pick_map)
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google Maps Satellite",
        name="স্যাটেলাইট ভিউ",
        show=False
    ).add_to(pick_map)

    folium.Marker(
        [st.session_state["temp_map_lat"], st.session_state["temp_map_lon"]],
        popup="<b>এখানে সেট হবে</b>",
        icon=folium.Icon(color="red", icon="map-marker", prefix="fa")
    ).add_to(pick_map)

    if gps_lat and gps_lon:
      folium.CircleMarker(
          location=[gps_lat, gps_lon],
          radius=8,
          color="#0056b3",
          fill=True,
          fill_color="#1a73e8",
          fill_opacity=0.9,
          popup="আপনার বর্তমান লোকেশন"
      ).add_to(pick_map)

    folium.LayerControl().add_to(pick_map)
    p_map_data = st_folium(pick_map, width="100%", height=400, key="party_location_picker_map")

    if p_map_data and p_map_data.get("last_clicked"):
      clat = p_map_data["last_clicked"]["lat"]
      clon = p_map_data["last_clicked"]["lng"]
      if clat != st.session_state["temp_map_lat"] or clon != st.session_state["temp_map_lon"]:
        st.session_state["temp_map_lat"] = clat
        st.session_state["temp_map_lon"] = clon
        st.rerun()

    col_b1, col_b2 = st.columns(2)
    with col_b1:
      if st.button("✅ লোকেশন সেভ করুন (OK)", type="primary", key="save_party_map_ok"):
        target_id = st.session_state["mapping_party_id"]
        t_lat = st.session_state["temp_map_lat"]
        t_lon = st.session_state["temp_map_lon"]
        c.execute("UPDATE locations SET lat=?, lon=? WHERE id=?", (t_lat, t_lon, target_id))
        conn.commit()
        p_name_saved = st.session_state["mapping_party_name"]
        st.session_state.pop("mapping_party_id", None)
        st.session_state.pop("mapping_party_name", None)
        st.success(f"✅ '{p_name_saved}'-এর ম্যাপ সফলভাবে সেভ করা হয়েছে!")
        st.rerun()
    with col_b2:
      if st.button("❌ বাতিল (Cancel)", key="cancel_party_map"):
        st.session_state.pop("mapping_party_id", None)
        st.session_state.pop("mapping_party_name", None)
        st.rerun()

    st.markdown("---")
    st.stop()

  c.execute("SELECT party_name, address, party_phone FROM locations")
  all_records = c.fetchall()
  
  search_items = []
  for r in all_records:
    if r[0]: search_items.append(r[0])
    if r[2]: search_items.append(r[2])
    if r[1]: search_items.append(r[1])
  
  unique_search_items = sorted(list(set(search_items)))

  search_items_json = json.dumps(unique_search_items)

  q_params = st.query_params
  js_search_val = q_params.get("search_keyword", "")

  search_bar_html = f"""
  <div style="position: relative; width: 100%; margin-bottom: 20px; box-sizing: border-box;">
    <label style="font-weight: 600; font-size: 14px; color: #ffffff; display: block; margin-bottom: 5px;">সার্চ করুন (পার্টির নাম, ফোন নম্বর বা ঠিকানা দিয়ে)</label>
    <input type="text" id="master_search_box" value="{js_search_val}" placeholder="নাম, ফোন বা ঠিকানা লিখে সার্চ করুন..." style="width: 100%; max-width: 100%; padding: 12px; border: 1px solid #cccccc; border-radius: 6px; font-size: 16px; background-color: #1e1e1e; color: #ffffff; box-sizing: border-box;" autocomplete="off">
    <div id="master_suggestions_list" style="position: absolute; width: 100%; max-height: 220px; overflow-y: auto; background: #262730; border: 1px solid #444444; border-top: none; border-radius: 0 0 6px 6px; z-index: 9999; display: none; box-sizing: border-box; box-shadow: 0px 4px 6px rgba(0,0,0,0.3);"></div>
  </div>

  <script>
    const allSearchItems = {search_items_json};
    const mSearchBox = document.getElementById("master_search_box");
    const mSuggestionsList = document.getElementById("master_suggestions_list");

    function triggerSearch(val) {{
      const url = new URL(window.location.href);
      url.searchParams.set('search_keyword', val);
      window.history.replaceState({{}}, '', url);
      window.location.reload();
    }}

    mSearchBox.addEventListener("input", function() {{
      const query = this.value.toLowerCase().trim();
      mSuggestionsList.innerHTML = "";
      if (query === "") {{
        mSuggestionsList.style.display = "none";
        triggerSearch("");
        return;
      }}
      const filtered = allSearchItems.filter(item => item.toLowerCase().includes(query));
      if (filtered.length > 0) {{
        mSuggestionsList.style.display = "block";
        filtered.forEach(itemText => {{
          const div = document.createElement("div");
          div.innerText = itemText;
          div.style.padding = "10px 12px";
          div.style.cursor = "pointer";
          div.style.borderBottom = "1px solid #333333";
          div.style.color = "#ffffff";
          div.onmouseover = function() {{ this.style.backgroundColor = "#333333"; }};
          div.onmouseout = function() {{ this.style.backgroundColor = "#262730"; }};
          div.onclick = function() {{
            mSearchBox.value = itemText;
            mSuggestionsList.style.display = "none";
            triggerSearch(itemText);
          }};
          mSuggestionsList.appendChild(div);
        }});
      }} else {{
        mSuggestionsList.style.display = "none";
      }}
      triggerSearch(this.value);
    }});

    document.addEventListener("click", function(e) {{
      let path = e.composedPath();
      if (!path.includes(mSearchBox) && !path.includes(mSuggestionsList)) {{
        mSuggestionsList.style.display = "none";
      }}
    }});
  </script>
  """
  st.components.v1.html(search_bar_html, height=115)

  df = pd.read_sql_query("SELECT * FROM locations", conn)
  
  if js_search_val:
    q = js_search_val.lower()
    df = df[
        df["party_name"].str.lower().str.contains(q, na=False) |
        df["party_phone"].str.lower().str.contains(q, na=False) |
        df["address"].str.lower().str.contains(q, na=False)
    ]
  
  doc_df = df[df["lat"].isna() | df["lon"].isna()]
  mapped_df = df[df["lat"].notna() & df["lon"].notna()]

  with st.expander(f"👨‍⚕️ ম্যাপবিহীন ডক্টর ও পার্টি তালিকা ({len(doc_df)} টি)", expanded=True):
    if not doc_df.empty:
      for index, row in doc_df.iterrows():
        cols = st.columns([3, 2, 2, 2, 1.5])
        cols[0].write(f"**{row['party_name']}**")
        cols[1].write(row['party_phone'] if row['party_phone'] else "নম্বার নেই")
        cols[2].write(row['address'] if row['address'] else "ঠিকানা নেই")
        
        if cols[3].button("📍 ম্যাপ যুক্ত করুন", key=f"map_add_search_{row['id']}"):
          st.session_state["mapping_party_id"] = row['id']
          st.session_state["mapping_party_name"] = row['party_name']
          st.session_state["temp_map_lat"] = st.session_state.get("selected_lat", 22.8620)
          st.session_state["temp_map_lon"] = st.session_state.get("selected_lon", 87.3320)
          st.rerun()

        if st.session_state["user_role"] == "admin":
          if cols[4].button("🗑️ ডিলিট", key=f"del_doc_search_{row['id']}"):
            c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
            conn.commit()
            st.success(f"✅ সফলভাবে ডিলিট করা হয়েছে!")
            st.rerun()
        st.write("---")
    else:
      st.info("কোনো ম্যাপবিহীন ডক্টর বা পার্টি পাওয়া যায়নি।")

  st.write("---")
  st.write("#### 📍 ম্যাপে যুক্ত পার্টি ও ডক্টর তালিকা")
  if not mapped_df.empty:
    for index, row in mapped_df.iterrows():
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
        if cols[4].button("🗑️ ডিলিট", key=f"del_loc_search_{row['id']}"):
          c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
          conn.commit()
          st.success(f"✅ '{row['party_name']}' সফলভাবে ডিলিট করা হয়েছে!")
          st.rerun()

      st.write("---")
  else:
    st.info("ম্যাপে যুক্ত কোনো পার্টি পাওয়া যায়নি।")

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
        st.success("অর্ডার কমপ্লিট করা হয়েছে! এটি ২৪ ঘণ্টা পর স্বয়ংক্রিয়ভাবে মুছে যাবে।")
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
  c.execute("SELECT party_name, lat, lon FROM locations")
  loc_data = c.fetchall()
  all_parties = [r[0] for r in loc_data]
  party_coords = {r[0]: (r[1], r[2]) for r in loc_data}

  parties_json = json.dumps(all_parties)

  q_params = st.query_params
  js_selected_party = q_params.get("selected_task_party", "")

  search_html_task = f"""
  <div style="position: relative; width: 100%; margin-bottom: 15px; box-sizing: border-box;">
    <label style="font-weight: 600; font-size: 14px; color: #ffffff; display: block; margin-bottom: 5px;">সার্চ করুন (পার্টির নাম)</label>
    <input type="text" id="task_party_search_box" value="{js_selected_party}" placeholder="পার্টির নাম লিখে সার্চ করুন..." style="width: 100%; max-width: 100%; padding: 12px; border: 1px solid #cccccc; border-radius: 6px; font-size: 16px; background-color: #1e1e1e; color: #ffffff; box-sizing: border-box;" autocomplete="off">
    <div id="task_suggestions_list" style="position: absolute; width: 100%; max-height: 200px; overflow-y: auto; background: #262730; border: 1px solid #444444; border-top: none; border-radius: 0 0 6px 6px; z-index: 9999; display: none; box-sizing: border-box; box-shadow: 0px 4px 6px rgba(0,0,0,0.3);"></div>
  </div>

  <script>
    const allPartiesTask = {parties_json};
    const searchBoxTask = document.getElementById("task_party_search_box");
    const suggestionsListTask = document.getElementById("task_suggestions_list");

    searchBoxTask.addEventListener("input", function() {{
      const query = this.value.toLowerCase().trim();
      suggestionsListTask.innerHTML = "";
      if (query === "") {{
        suggestionsListTask.style.display = "none";
        return;
      }}
      const filtered = allPartiesTask.filter(p => p.toLowerCase().includes(query));
      if (filtered.length > 0) {{
        suggestionsListTask.style.display = "block";
        filtered.forEach(party => {{
          const item = document.createElement("div");
          item.innerText = party;
          item.style.padding = "10px 12px";
          item.style.cursor = "pointer";
          item.style.borderBottom = "1px solid #333333";
          item.style.color = "#ffffff";
          item.onmouseover = function() {{ this.style.backgroundColor = "#333333"; }};
          item.onmouseout = function() {{ this.style.backgroundColor = "#262730"; }};
          item.onclick = function() {{
            searchBoxTask.value = party;
            suggestionsListTask.style.display = "none";
            const url = new URL(window.location.href);
            url.searchParams.set('selected_task_party', party);
            window.history.replaceState({{}}, '', url);
            window.location.reload();
          }};
          suggestionsListTask.appendChild(item);
        }});
      }} else {{
        suggestionsListTask.style.display = "none";
      }}
    }});

    document.addEventListener("click", function(e) {{
      let path = e.composedPath();
      if (!path.includes(searchBoxTask) && !path.includes(suggestionsListTask)) {{
        suggestionsListTask.style.display = "none";
      }}
    }});
  </script>
  """
  st.components.v1.html(search_html_task, height=115)

  sel_pt = js_selected_party

  if sel_pt:
    st.success(f"✅ নির্বাচিত পার্টি: **{sel_pt}**")
  else:
    st.warning("⚠️ দয়া করে উপরের সার্চ বক্সে পার্টির নাম লিখে সিলেক্ট করুন।")

  with st.form("easy_assign_form", clear_on_submit=True):
    sel_ag = st.selectbox("এজেন্ট নির্বাচন করুন", all_agents)

    st.write("**কাজের ধরণ নির্বাচন করুন:**")
    col_chk1, col_chk2 = st.columns(2)
    with col_chk1:
      chk_delivery = st.checkbox("🚚 ডেলিভারি")
    with col_chk2:
      chk_due = st.checkbox("💰 ডিউ কালেকশন")

    d_amount = st.text_input("ডিউ টাকা (যদি থাকে)", "0")

    submit_easy_task = st.form_submit_button("🎯 কাজ যোগ করুন", type="primary")

    if submit_easy_task:
      if not sel_pt or sel_pt not in all_parties:
        st.error("দয়া করে প্রথমে ওপরের সার্চ বক্স থেকে সঠিক একটি পার্টি সিলেক্ট করুন।")
      else:
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
          st.query_params.pop("selected_task_party", None)
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
        p_coords = party_coords[p_name]
        if p_coords[0] is not None and p_coords[1] is not None:
          p_lat, p_lon = p_coords
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
        st.success(f"{p_name}-এর কাজ সম্পন্ন! এটি ২৪ ঘণ্টা পর তালিকা থেকে সম্পূর্ণ মুছে যাবে।")
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

  locs_df = pd.read_sql_query("SELECT * FROM locations WHERE lat IS NOT NULL AND lon IS NOT NULL ORDER BY id ASC", conn)
  
  if not locs_df.empty:
    m_center_lat = locs_df.iloc[0]["lat"]
    m_center_lon = locs_df.iloc[0]["lon"]

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
    st.info("রুট দেখানোর জন্য ম্যাপে কোনো লোকেশন সেভ করা নেই।")

# =========================================================
# 6. ATTENDANCE SYSTEM (ডেইলি ও মাসিক অ্যাটেনডেন্স)
# =========================================================
elif selected_menu == "📅 উপস্থিতি (Attendance)":
  st.write("### 📅 স্টাফ ও এজেন্ট উপস্থিতি (Daily & Monthly Attendance)")

  att_tab1, att_tab2 = st.tabs(["📝 আজকের উপস্থিতি দিন", "📊 মাসিক উপস্থিতি ও টোটাল সামারি"])

  with att_tab1:
    st.write(f"#### আজকের তারিখ: `{datetime.now().strftime('%Y-%m-%d')}`")
    
    current_user = st.session_state["username"]
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    c.execute("SELECT check_time FROM attendance WHERE username=? AND date=?", (current_user, today_str))
    already_checked = c.fetchone()

    if already_checked:
      st.success(f"✅ আপনার আজকের উপস্থিতি গ্রহণ করা হয়েছে। (সময়: `{already_checked[0]}`)")
    else:
      if st.button("🙋‍♂️ আমার আজকের উপস্থিতি দিন (Present)", type="primary"):
        check_time_str = datetime.now().strftime("%H:%M:%S")
        try:
          c.execute("INSERT INTO attendance (username, date, check_time, status) VALUES (?, ?, ?, ?)",
                    (current_user, today_str, check_time_str, "Present"))
          conn.commit()
          st.success("উপস্থিতি সফলভাবে রেকর্ড করা হয়েছে!")
          st.rerun()
        except sqlite3.IntegrityError:
          st.error("ইতিমধ্যে উপস্থিতি দেওয়া হয়েছে।")

    st.write("---")
    st.write("#### আজকের উপস্থিতির তালিকা (সকলের জন্য)")
    today_att_df = pd.read_sql_query("SELECT username, check_time, status FROM attendance WHERE date=?", conn, params=(today_str,))
    if not today_att_df.empty:
      st.dataframe(today_att_df, use_container_width=True)
    else:
      st.info("আজ এখনো কেউ উপস্থিতি দেয়নি।")

  with att_tab2:
    st.write("#### 📊 মাসিক উপস্থিতি রিপোর্ট ও টোটাল সামারি")
    
    current_month_str = datetime.now().strftime("%Y-%m")
    st.write(f"বর্তমান মাস: **{current_month_str}** (মাস শেষের ৩০/৩১ তারিখে টোটাল স্বয়ংক্রিয়ভাবে হিসাব হচ্ছে)")

    # Monthly Summary Query
    summary_df = pd.read_sql_query("""
        SELECT username, COUNT(*) as total_present 
        FROM attendance 
        WHERE strftime('%Y-%m', date) = ? 
        GROUP BY username
    """, conn, params=(current_month_str,))

    if not summary_df.empty:
      st.dataframe(summary_df, use_container_width=True)
    else:
      st.info("এই মাসের কোনো উপস্থিতি রেকর্ড পাওয়া যায়নি।")

    # Detailed history and admin edit controls
    st.write("---")
    st.write("#### 📋 বিস্তারিত রেকর্ড ও অ্যাডমিন এডিট প্যানেল")
    
    all_att_df = pd.read_sql_query("SELECT * FROM attendance ORDER BY date DESC, check_time DESC", conn)
    
    if not all_att_df.empty:
      for idx, row in all_att_df.iterrows():
        cols = st.columns([2, 2, 2, 1.5, 1.5])
        cols[0].write(f"ইউজার: **{row['username']}**")
        cols[1].write(f"তারিখ: {row['date']}")
        cols[2].write(f"সময়: {row['check_time']}")
        cols[3].write(f"স্ট্যাটাস: {row['status']}")

        if st.session_state["user_role"] == "admin":
          if cols[4].button("🗑️ ডিলিট", key=f"del_att_{row['id']}"):
            c.execute("DELETE FROM attendance WHERE id=?", (row['id'],))
            conn.commit()
            st.success("উপস্থিতি রেকর্ড মুছে ফেলা হয়েছে!")
            st.rerun()
        else:
          cols[4].write("🔒 লকড")
    else:
      st.info("কোনো উপস্থিতির রেকর্ড নেই।")

# =========================================================
# 7. ADMIN LIVE TRACKING
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
# 8. সেটিংস ও এজেন্ট ম্যানেজমেন্ট
# =========================================================
elif selected_menu == "⚙️ সেটিংস ও এজেন্ট ম্যানেজমেন্ট":
  if st.session_state["user_role"] != "admin":
    st.error("এই পেজটি শুধুমাত্র অ্যাডমিনের জন্য।")
  else:
    st.write("### 👥 ডেলিভারি এজেন্ট তালিকা ও ম্যানেজমেন্ট")
    
    c.execute("SELECT username, role, fullname, phone, created_at, is_active FROM users")
    agents = c.fetchall()
    st.write(f"মোট রেজিস্টার্ড ইউজার/এজেন্ট সংখ্যা: **{len(agents)}**")

    for ag in agents:
      u_name, u_role, f_name, u_phone, c_date, is_act = ag
      display_name = f_name if f_name else "নাম নেই"
      join_date = c_date if c_date else "অজানা"
      phone_disp = u_phone if u_phone else "নম্বর নেই"
      
      with st.expander(f"👤 {display_name} (ইউজারনেম: {u_name})"):
        st.write(f"📞 ফোন নম্বর: `{phone_disp}`")
        st.write(f"📅 যোগদানের তারিখ: `{join_date}`")
        
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
          with st.form(f"edit_form_{u_name}"):
            new_name = st.text_input("প্রকৃত নাম এডিট করুন", value=display_name, key=f"fname_{u_name}")
            new_phone = st.text_input("ফোন নম্বর এডিট করুন", value=phone_disp if phone_disp != "নম্বর নেই" else "", key=f"fphone_{u_name}")
            update_btn = st.form_submit_button("পরিবর্তন সেভ করুন")
            
            if update_btn:
              c.execute("UPDATE users SET fullname=?, phone=? WHERE username=?", (new_name, new_phone, u_name))
              conn.commit()
              st.success("সফলভাবে আপডেট হয়েছে!")
              st.rerun()

        with col_ed2:
          if u_name != "admin":
            if st.button("🗑️ এজেন্ট ডিলিট করুন", key=f"del_ag_{u_name}", type="secondary"):
              c.execute("DELETE FROM users WHERE username=?", (u_name,))
              c.execute("DELETE FROM agent_live_locations WHERE username=?", (u_name,))
              conn.commit()
              st.success(f"✅ এজেন্ট '{u_name}' সফলভাবে ডিলিট করা হয়েছে!")
              st.rerun()

    st.write("---")
    st.write("### ➕ নতুন এজেন্ট যোগ করুন ও ডাইরেক্ট লগইন লিংক জেনারেট করুন")
    with st.form("new_agent_form"):
      n_fullname = st.text_input("এজেন্টের প্রকৃত নাম (পুরো নাম)")
      n_user = st.text_input("ইউজারনেম (লগইন আইডি বা শর্ট নাম)")
      n_role = st.selectbox("রোল", ["staff", "admin"])
      add_agent_btn = st.form_submit_button("এজেন্ট যুক্ত করুন ও ডাইরেক্ট লিংক তৈরি করুন")

      if add_agent_btn:
        if n_fullname and n_user:
          try:
            c.execute("INSERT INTO users (username, password, role, fullname, phone, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                      (n_user, "direct_login", n_role, n_fullname, "", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1))
            conn.commit()
            st.session_state["last_created_agent_user"] = n_user
            st.session_state["last_created_agent_name"] = n_fullname
            st.success(f"নতুন এজেন্ট '{n_fullname}' সফলভাবে যোগ করা হয়েছে!")
            st.rerun()
          except sqlite3.IntegrityError:
            st.error("❌ এই ইউজারনেমটি আগেই রয়েছে।")
        else:
          st.error("নাম এবং ইউজারনেম পূরণ করুন।")

    if st.session_state.get("last_created_agent_user"):
      created_u = st.session_state["last_created_agent_user"]
      created_n = st.session_state["last_created_agent_name"]
      
      st.markdown("---")
      st.write(f"#### 🔗 '{created_n}'-এর ডাইরেক্ট লগইন লিংক ও কপি অপশন")
      
      direct_msg = f"হ্যালো {created_n}, P.S Mediseller ডেলিভারি অ্যাপে আপনার জন্য নির্দিষ্ট একাউন্ট তৈরি করা হয়েছে। নিচের লিংকে টাচ করলেই আপনি সরাসরি আপনার নামে অ্যাপে প্রবেশ করতে পারবেন:\n"
      
      copy_html = f"""
      <div style="background: #262730; padding: 15px; border-radius: 8px; border: 1px solid #444; margin-top: 10px;">
        <p style="color: #fff; margin-bottom: 8px; font-weight: 600;">জেনারেট হওয়া ডাইরেক্ট লিংক:</p>
        <input type="text" id="generated_link" readonly style="width: 100%; padding: 10px; border-radius: 5px; border: 1px solid #555; background: #1e1e1e; color: #fff; font-size: 14px; margin-bottom: 10px; box-sizing: border-box;">
        <button onclick="copyLink()" id="copy_btn" style="background-color: #1a73e8; color: white; padding: 10px 20px; border: none; border-radius: 5px; font-weight: bold; cursor: pointer;">📋 লিংক কপি করুন</button>
        <span id="copy_status" style="color: #25D366; margin-left: 10px; font-weight: bold; display: none;">✓ কপি হয়েছে!</span>
      </div>
      <script>
        let currentUrl = "";
        try {{
          currentUrl = window.parent.location.href.split('?')[0];
        }} catch(e) {{
          try {{
            currentUrl = document.referrer.split('?')[0];
          }} catch(e2) {{
            currentUrl = window.location.origin + window.location.pathname;
          }}
        }}
        
        if (!currentUrl || currentUrl.includes('srcdoc') || currentUrl.startsWith('about:') || currentUrl.includes('null')) {{
          currentUrl = document.referrer ? document.referrer.split('?')[0] : (window.location.origin + window.location.pathname);
        }}

        const link = currentUrl + "?login={created_u}";
        const fullText = `{direct_msg}` + link;
        document.getElementById("generated_link").value = fullText;

        function copyLink() {{
          const copyText = document.getElementById("generated_link");
          copyText.select();
          copyText.setSelectionRange(0, 99999);
          navigator.clipboard.writeText(copyText.value);
          
          const status = document.getElementById("copy_status");
          status.style.display = "inline";
          setTimeout(() => {{ status.style.display = "none"; }}, 2000);
        }}
      </script>
      """
      st.components.v1.html(copy_html, height=160)
      if st.button("✖️ উইন্ডো বন্ধ করুন"):
        st.session_state.pop("last_created_agent_user", None)
        st.session_state.pop("last_created_agent_name", None)
        st.rerun()
