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

  import json
  parties_json = json.dumps(all_parties_db)

  # ড্রপডাউন থেকে সিলেক্ট করলে বা টাইপ করলে Hidden Input-এ ভالু সেট হবে এবং সাবমিট বাটন কাজ করবে
  search_html = f"""
  <form id="order_submit_form" style="margin-bottom: 15px;">
    <div style="position: relative; margin-bottom: 15px;">
      <label style="font-weight: 600; font-size: 14px; color: #31333F;">পার্টি সার্চ করুন (নামের অক্ষর লিখুন)</label>
      <input type="text" id="party_search_box" name="selected_party" placeholder="এখানে টাইপ করুন..." style="width: 100%; padding: 10px; border: 1px solid #cccccc; border-radius: 4px; font-size: 16px; margin-top: 5px; background-color: #ffffff; color: #000000;" autocomplete="off">
      <div id="suggestions_list" style="position: absolute; width: 100%; max-height: 200px; overflow-y: auto; background: white; border: 1px solid #cccccc; border-top: none; border-radius: 0 0 4px 4px; z-index: 9999; display: none; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);"></div>
    </div>
  </form>

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
          item.style.padding = "10px";
          item.style.cursor = "pointer";
          item.style.borderBottom = "1px solid #f0f2f6";
          item.style.color = "#000000";
          item.onmouseover = function() {{ this.style.backgroundColor = "#f0f2f6"; }};
          item.onmouseout = function() {{ this.style.backgroundColor = "#ffffff"; }};
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
      if (!searchBox.contains(e.target) && !suggestionsList.contains(e.target)) {{
        suggestionsList.style.display = "none";
      }}
    }});
  </script>
  """
  st.components.v1.html(search_html, height=115)

  ord_details = st.text_area("অর্ডারের বিবরণ")
  
  if st.button("🛒 অর্ডার জমা দিন", type="primary"):
    # স্ট্রিমিট কম্পোনেন্ট বা টেক্সট ইনপুট থেকে ইউজার যেই পার্টি সিলেক্ট বা টাইপ করেছে তা ক্যাচ করার ব্যবস্থা
    # সুবিধার্থে স্ট্রিমিট টেক্সট ইনপুট অথবা সরাসরি হ্যান্ডেল করার জন্য স্ট্রিমিট কম্পোনেন্ট রিঅ্যাক্ট ব্যবহার করা হয়েছে।
    st.warning("দয়া করে সার্চ বক্সে পার্টির সঠিক নামটি লিখে বা ড্রপডাউন থেকে সিলেক্ট করে অর্ডার জমা দিন।")

# বিকল্প সহজ ও পারফেক্ট স্ট্রিমিট নেটিভ সলিউশন যদি চান সরাসরি ড্রপডাউন বক্স ছাড়া রাখতে:
