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

conn.commit()

# ডিফল্ট ইউজার তৈরি
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
  c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin123", "admin"))
  c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("delivery", "user123", "staff"))
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
# MAIN APP HEADER & ROBUST FLOATING SCROLL-TO-TOP BUTTON
# =========================================================
st.title("পি এস মেডিসেলার ডেলিভারি পার্টনার")

col_u1, col_u2 = st.columns([3, 1])
with col_u1:
  st.write(f"👤 ইউজার: **{st.session_state['username']}** (`{st.session_state['user_role']}`)")
with col_u2:
  if st.button("🚪 লগআউট"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = None
    st.session_state["user_role"] = None
    streamlit_js_eval(js_expressions="localStorage.removeItem('ps_perma_user')", key="clear_local_user")
    st.rerun()

floating_top_badge = """
<style>
  #floatingTopBtn {
    position: fixed;
    left: 20px;
    bottom: 90px;
    z-index: 999999;
    background-color: rgba(26, 115, 232, 0.2);
    color: white;
    width: 50px;
    height: 50px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.15);
    text-decoration: none;
    font-size: 22px;
    cursor: pointer;
    border: 1px solid rgba(255, 255, 255, 0.15);
    opacity: 0.35;
    transition: transform 0.2s ease, opacity 0.2s ease, background-color 0.2s ease;
  }
  #floatingTopBtn:hover, #floatingTopBtn:active {
    transform: scale(1.1);
    opacity: 0.9;
    background-color: rgba(26, 115, 232, 0.6);
    color: white;
  }
</style>
<div id="floatingTopBtn" title="উপরে চলুন">⬆️</div>
<script>
  (function() {
    const btn = document.getElementById('floatingTopBtn');
    if (btn) {
      const handleScrollTop = function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        // 1. Window scroll
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        // 2. Streamlit container scroll targets
        const containers = document.querySelectorAll('[data-testid="stAppViewContainer"], .main, section.main, div[tabindex="0"]');
        containers.forEach(function(el) {
          el.scrollTo({ top: 0, behavior: 'smooth' });
        });

        // 3. Parent frame scroll if inside iframe
        try {
          if (window.parent && window.parent !== window) {
            window.parent.scrollTo({ top: 0, behavior: 'smooth' });
            const parentContainers = window.parent.document.querySelectorAll('[data-testid="stAppViewContainer"], .main, section.main');
            parentContainers.forEach(function(el) {
              el.scrollTo({ top: 0, behavior: 'smooth' });
            });
          }
        } catch(err) {}
      };

      btn.addEventListener('click', handleScrollTop);
      btn.addEventListener('touchend', handleScrollTop);
    }
  })();
</script>
"""
st.markdown(floating_top_badge, unsafe_allow_html=True)

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
# NAVIGATION MENU (WITH NATIVE BROWSER BACK BUTTON SUPPORT)
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

query_params = st.query_params
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
        try:
          c.execute(
              "INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, ?, ?)",
              (p_name.strip(), p_addr, p_phone.strip(), st.session_state["selected_lat"], st.session_state["selected_lon"]),
          )
          conn.commit()
          st.success("✅ লোকেশন সফলভাবে সেভ হয়েছে!")
          st.rerun()
        except sqlite3.IntegrityError:
          st.error("❌ এরর: এই নামের অথবা এই ফোন নম্বরের পার্টি ইতিমধ্যে সেভ করা আছে! একই পার্টি দুবার এন্ট্রি করা যাবে না।")
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
        try:
          c.execute(
              "INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, NULL, NULL)",
              (doc_name.strip(), doc_addr, doc_phone.strip()),
          )
          conn.commit()
          st.success("✅ ডক্টর/পার্টি সফলভাবে সেভ হয়েছে! (ম্যাপে যুক্ত করতে সার্চ অপশন ব্যবহার করুন)")
          st.rerun()
        except sqlite3.IntegrityError:
          st.error("❌ এরর: এই নামের অথবা এই ফোন নম্বরের পার্টি ইতিমধ্যে সেভ করা আছে!")
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

  import json
  parties_json = json.dumps(all_parties_db)

  search_html = f"""
  <div style="position: relative; width: 100%; margin-bottom: 15px; box-sizing: border-box;">
    <label style="font-weight: 600; font-size: 14px; color: #31333F; display: block; margin-bottom: 5px;">পার্টি সার্চ করুন (নামের অক্ষর লিখুন)</label>
    <input type="text" id="party_search_box" placeholder="এখানে টাইপ করুন..." style="width: 100%; max-width: 100%; padding: 10px 12px; border: 1px solid #cccccc; border-radius: 4px; font-size: 16px; background-color: #ffffff; color: #000000; box-sizing: border-box;" autocomplete="off">
    <div id="suggestions_list" style="position: absolute; width: 100%; max-height: 200px; overflow-y: auto; background: white; border: 1px solid #cccccc; border-top: none; border-radius: 0 0 4px 4px; z-index: 9999; display: none; box-shadow: 0px 4px 6px rgba(0,0,0,0.1); box-sizing: border-box;"></div>
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
  st.components.v1.html(search_html, height=105)

  ord_details = st.text_area("অর্ডারের বিবরণ")
  
  if st.button("🛒 অর্ডার জমা দিন", type="primary"):
    st.info("দয়া করে সার্চ বক্স থেকে পার্টির নামটি লিখে বা ড্রপডাউন থেকে সিলেক্ট করে নিশ্চিত করুন।")

# =========================================================
# 2. SEARCH PARTY & ADMIN DELETE OPTION (নাম, ফোন বা ঠিকানা দিয়ে সার্চ)
# =========================================================
elif selected_menu == "🔍 সার্চ":
  st.write("### 🔍 সার্চ ও পার্টি/ডক্টর ম্যানেজমেন্ট পোর্টাল")
  df = pd.read_sql_query("SELECT * FROM locations", conn)
  
  search_query = st.text_input("সার্চ করুন (পার্টির নাম, ফোন নম্বর বা ঠিকানা)", placeholder="নাম, ফোন বা ঠিকানা লিখে সার্চ করুন...")
  
  if search_query:
    q = search_query.lower()
    df = df[
        df["party_name"].str.lower().str.contains(q, na=False) |
        df["party_phone"].str.lower().str.contains(q, na=False) |
        df["address"].str.lower().str.contains(q, na=False)
    ]
  
  doc_df = df[df["lat"].isna() | df["lon"].isna()]
  mapped_df = df[df["lat"].notna() & df["lon"].notna()]

  with st.expander(f"👨‍⚕️ ম্যাপবিহীন ডক্টর ও পার্টি তালিকা ({len(doc_df)} টি বাকি)", expanded=True):
    if not doc_df.empty:
      for index, row in doc_df.iterrows():
        cols = st.columns([3, 2, 2, 2, 1.5])
        cols[0].write(f"**{row['party_name']}**")
        cols[1].write(row['party_phone'] if row['party_phone'] else "নম্বার নেই")
        cols[2].write(row['address'] if row['address'] else "ঠিকানা নেই")
        
        if cols[3].button("📍 ম্যাপ যুক্ত করুন", key=f"map_add_search_{row['id']}"):
          c.execute("UPDATE locations SET lat=?, lon=? WHERE id=?", (st.session_state["selected_lat"], st.session_state["selected_lon"], row['id']))
          conn.commit()
          st.success(f"✅ '{row['party_name']}' সফলভাবে ম্যাপে যুক্ত হয়েছে এবং তালিকা থেকে সরিয়ে নেওয়া হয়েছে!")
          st.rerun()

        if st.session_state["user_role"] == "admin":
          if cols[4].button("🗑️ ডিলিট", key=f"del_doc_search_{row['id']}"):
            c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
            conn.commit()
            st.success(f"✅ সফলভাবে ডিলিট করা হয়েছে!")
            st.rerun()
        st.write("---")
    else:
      st.info("সব ডক্টর ও পার্টির ম্যাপ সফলভাবে যুক্ত করা হয়েছে!")

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
