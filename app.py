import base64
from datetime import datetime, timedelta, timezone
import json
import os
import sqlite3
import time
import urllib.parse
from zoneinfo import ZoneInfo

import folium
from folium.plugins import MousePosition
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation, streamlit_js_eval

# =========================================================
# 1. PAGE CONFIGURATION (MUST BE FIRST STREAMLIT CALL)
# =========================================================
st.set_page_config(
    page_title="P. S MEDISELLER - Allopathy & Ayurvedic Wholesaler",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# 2. IST TIME & DATE HELPERS
# =========================================================
def get_ist_time():
  ist_offset = timezone(timedelta(hours=5, minutes=30))
  return datetime.now(ist_offset)


def format_date_display(date_str):
  if not date_str:
    return ""
  try:
    cleaned = str(date_str).strip()
    if " " in cleaned:
      dt = datetime.strptime(cleaned.split(" ")[0], "%Y-%m-%d")
    else:
      dt = datetime.strptime(cleaned, "%Y-%m-%d")
    return dt.strftime("%d.%m.%y")
  except:
    return date_str


# =========================================================
# 3. DATABASE SETUP
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
CREATE TABLE IF NOT EXISTS daily_work (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    party_name TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    work_date TEXT NOT NULL
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
    sale_amount TEXT DEFAULT '0',
    payment_collected_actual TEXT DEFAULT '0',
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
conn.commit()

# Default admin & user setup
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
  c.execute(
      "INSERT INTO users (username, password, role, fullname, phone, created_at,"
      " is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
      (
          "admin",
          "admin123",
          "admin",
          "Admin",
          "8918740325",
          get_ist_time().strftime("%Y-%m-%d %H:%M:%S"),
          1,
      ),
  )
  c.execute(
      "INSERT INTO users (username, password, role, fullname, phone, created_at,"
      " is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
      (
          "delivery",
          "user123",
          "staff",
          "Delivery Agent",
          "8918740325",
          get_ist_time().strftime("%Y-%m-%d %H:%M:%S"),
          1,
      ),
  )
  conn.commit()

# =========================================================
# 4. SESSION STATE & SAFE LOGIN HANDLER (FIXES WHITE SCREEN)
# =========================================================
if "selected_lat" not in st.session_state:
  st.session_state["selected_lat"] = 22.8620
if "selected_lon" not in st.session_state:
  st.session_state["selected_lon"] = 87.3320
if "username" not in st.session_state:
  st.session_state["username"] = "delivery"
if "user_role" not in st.session_state:
  st.session_state["user_role"] = "staff"

# SAFE URL AUTO LOGIN
if "login" in st.query_params:
  target_user = st.query_params["login"]
  if st.session_state.get("username") != target_user:
    c.execute(
        "SELECT username, fullname, role FROM users WHERE username=?",
        (target_user,),
    )
    u_data = c.fetchone()
    if u_data:
      st.session_state["username"] = u_data[0]
      st.session_state["user_role"] = u_data[2]
      # Clear query params safely to stop infinite rerun loop
      st.query_params.clear()
      st.rerun()

# =========================================================
# 5. LOGO & PWA MANIFEST INJECTION
# =========================================================
logo_b64 = ""
for logo_name in ["1000135057_2.jpg", "1000204449.jpg", "1000135057.jpg"]:
  if os.path.exists(logo_name):
    with open(logo_name, "rb") as f:
      logo_b64 = base64.b64encode(f.read()).decode()
    break

pwa_manifest_html = f"""
<script>
try {{
  const manifest = {{ 
    "name": "P.S MEDISELLER",
    "short_name": "Mediseller",
    "start_url": "./",
    "display": "standalone",
    "background_color": "#0f172a",
    "theme_color": "#0f172a",
    "icons": [
      {{
        "src": "data:image/jpeg;base64,{logo_b64}",
        "sizes": "192x192",
        "type": "image/jpeg"
      }}
    ] }};
  const stringManifest = JSON.stringify(manifest);
  const blob = new Blob([stringManifest], {{type: 'application/json'}});
  const manifestURL = URL.createObjectURL(blob);
  const targetHead = document.head;
  let link = document.createElement('link');
  link.rel = 'manifest';
  link.href = manifestURL;
  targetHead.appendChild(link);
}} catch(e) {{
  console.log("PWA injection error:", e);
}}
</script>
"""
st.components.v1.html(pwa_manifest_html, height=0)

# =========================================================
# 6. STYLING (DARK THEME)
# =========================================================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
html, body, [class*="css"], p, span, label {
    font-family: 'Poppins', sans-serif;
    color: #ffffff !important;
}
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    color: #ffffff !important;
}
[data-testid="stDataFrame"] *, [data-testid="stTable"] *, .dataframe *, table *, th, td {
    color: #0f172a !important;
}
div.stExpander, div[data-testid="stForm"] {
    background: #1e293b !important;
    border: 1px solid rgba(148, 163, 184, 0.35) !important;
    border-radius: 14px !important;
    padding: 20px !important;
    box-shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.4);
    color: #ffffff !important;
} 
.stButton>button, div.stButton > button, button[kind="secondary"], button[kind="primary"], [data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
    color: #ffffff !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.2rem !important;
    font-weight: 600 !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important;
}
input, textarea, select, [data-baseweb="input"] input, [data-baseweb="textarea"] textarea, div[data-baseweb="input"], div[data-baseweb="select"] {
    background-color: #0f172a !important;
    color: #ffffff !important;
    border: 1px solid #3b82f6 !important;
    border-radius: 8px !important;
}
.stRadio div[role="radiogroup"] label {
    background: #1e293b !important;
    border: 1px solid rgba(129, 140, 248, 0.35) !important;
    border-radius: 12px !important;
    padding: 10px 14px !important;
    margin-bottom: 8px !important;
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
}
.stRadio div[role="radiogroup"] label p {
    color: #ffffff !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    margin: 0 !important;
}
.card {
    background-color: #1e1e2f;
    padding: 18px;
    border-radius: 12px;
    margin-bottom: 15px;
    border: 1px solid #33334d;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}
.party-title {
    color: #00ffcc;
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 8px;
}
.card-text {
    color: #e0e0e0;
    font-size: 16px;
    margin: 4px 0;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# 7. HEADER & USER BAR
# =========================================================
col_ht1, col_ht2 = st.columns([3, 1])
with col_ht1:
  st.markdown(
      f"""
  <div style="display: flex; align-items: center; gap: 12px;">
      <img src="data:image/jpeg;base64,{logo_b64}" style="width: 52px; height: 52px; border-radius: 10px; object-fit: cover; border: 1px solid rgba(255,255,255,0.2);">
      <div>
          <h1 style="margin: 0; font-size: 19px !important; background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700;">P. S MEDISELLER</h1>
          <p style="margin: 2px 0 0 0; color: #cbd5e1 !important; font-size: 11px;">Allopathy & Ayurvedic Wholesaler | Ph: 8918740325</p>
      </div>
  </div>
  """,
      unsafe_allow_html=True,
  )

with col_ht2:
  if st.session_state["user_role"] == "admin":
    if st.button("🚪 Logout (লগআউট)", key="logout_btn_top"):
      st.session_state["username"] = "delivery"
      st.session_state["user_role"] = "staff"
      st.rerun()
  else:
    if st.button("🔐 Admin Login (অ্যাডমিন)", key="login_btn_top"):
      st.session_state["show_admin_login"] = True
      st.rerun()

c.execute(
    "SELECT fullname FROM users WHERE username=?",
    (st.session_state["username"],),
)
curr_user_row = c.fetchone()
current_fullname = (
    curr_user_row[0]
    if curr_user_row and curr_user_row[0]
    else st.session_state["username"]
)
st.write(
    f"👤 User: **{current_fullname}** (`{st.session_state['user_role']}`)"
)

if st.session_state.get("show_admin_login", False):
  with st.form("admin_login_popup_form"):
    st.write("#### 🔑 Admin Login (অ্যাডমিন লগইন)")
    admin_pass_input = st.text_input(
        "Enter Admin Password (পাসওয়ার্ড দিন)", type="password"
    )
    col_al1, col_al2 = st.columns(2)
    submit_admin = col_al1.form_submit_button("Login (লগইন)", type="primary")
    cancel_admin = col_al2.form_submit_button("Cancel (বাতিল)")
    if submit_admin:
      c.execute("SELECT password, role FROM users WHERE username='admin'")
      adm_row = c.fetchone()
      if adm_row and adm_row[0] == admin_pass_input:
        st.session_state["username"] = "admin"
        st.session_state["user_role"] = "admin"
        st.session_state["show_admin_login"] = False
        st.success("Admin login successful!")
        st.rerun()
      else:
        st.error("Incorrect Password!")
    if cancel_admin:
      st.session_state["show_admin_login"] = False
      st.rerun()

st.write("---")

# BACKGROUND GPS CAPTURE
loc = get_geolocation(component_key="hidden_background_gps_tracker")
gps_lat, gps_lon = None, None
if loc and "coords" in loc:
  gps_lat = loc["coords"]["latitude"]
  gps_lon = loc["coords"]["longitude"]
  c.execute(
      "UPDATE agent_live_locations SET lat=?, lon=?, last_updated=? WHERE"
      " username=?",
      (
          gps_lat,
          gps_lon,
          get_ist_time().strftime("%Y-%m-%d %H:%M:%S"),
          st.session_state["username"],
      ),
  )
  if c.rowcount == 0:
    c.execute(
        "INSERT INTO agent_live_locations (username, lat, lon, last_updated)"
        " VALUES (?, ?, ?, ?)",
        (
            st.session_state["username"],
            gps_lat,
            gps_lon,
            get_ist_time().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
  conn.commit()

# =========================================================
# 8. NAVIGATION MENU
# =========================================================
menu_options = [
    "📍 Add Location (লোকেশন যোগ)",
    "🔍 Search & Details (অনুসন্ধান ও বিবরণ)",
    "📦 Pending Orders (বাকি অর্ডার)",
    "📋 Daily & Monthly Work (দৈনিক ও মাসিক কাজ)",
    "📋 Due & Delivery (বকেয়া ও ডেলিভারি)",
    "📅 Attendance (উপস্থিতি)",
]
if st.session_state["user_role"] == "admin":
  menu_options.extend(
      ["📊 Live Tracking (লাইভ ট্র্যাকিং)", "⚙️ Settings & Agents (সেটিংস)"]
  )

current_page_param = st.query_params.get("page", menu_options[0])
if current_page_param not in menu_options:
  current_page_param = menu_options[0]
default_index = menu_options.index(current_page_param)

selected_menu = st.radio(
    "Select Menu (মেনু সিলেক্ট):",
    menu_options,
    index=default_index,
    horizontal=False,
    label_visibility="collapsed",
)
if selected_menu != current_page_param:
  st.query_params["page"] = selected_menu
  st.rerun()

st.write("---")

# =========================================================
# 9. PAGE 1: ADD LOCATION & PARTY / ORDERS
# =========================================================
if selected_menu == "📍 Add Location (লোকেশন যোগ)":
  st.write("### 📍 Add Location & Party (লোকেশন ও পার্টি)")
  selected_entry_tab = st.radio(
      "Select Entry Mode:",
      [
          "🏠 With Map Party (ম্যাপ সহ পার্টি)",
          "🩺 Without Map Party (ম্যাপ ছাড়া পার্টি)",
      ],
      label_visibility="collapsed",
  )

  if "With Map Party" in selected_entry_tab:
    with st.form("location_details_form", clear_on_submit=True):
      st.write("#### 1. Enter Party Details (পার্টির বিবরণ)")
      col_f1, col_f2, col_f3 = st.columns(3)
      p_name = col_f1.text_input("Party Name (পার্টির নাম)")
      p_addr = col_f2.text_input("Address (ঠিকানা)")
      p_phone = col_f3.text_input("Phone Number (ফোন নম্বর)")
      submitted_loc = st.form_submit_button(
          "💾 Save Location (সেভ করুন)", type="primary"
      )
    if submitted_loc:
      if p_name.strip() and p_phone.strip():
        try:
          c.execute(
              "INSERT INTO locations (party_name, address, party_phone, lat,"
              " lon) VALUES (?, ?, ?, ?, ?)",
              (
                  p_name.strip(),
                  p_addr,
                  p_phone.strip(),
                  st.session_state["selected_lat"],
                  st.session_state["selected_lon"],
              ),
          )
          c.execute(
              "INSERT INTO daily_work (party_name, activity_type, work_date)"
              " VALUES (?, ?, ?)",
              (
                  p_name.strip(),
                  "Visit (ভিজিট)",
                  get_ist_time().strftime("%Y-%m-%d"),
              ),
          )
          conn.commit()
          st.success("Saved successfully! (সেভ হয়েছে!)")
          st.rerun()
        except sqlite3.IntegrityError:
          st.error("Party or phone already exists! (ইতিমধ্যে সেভ করা আছে!)")
      else:
        st.error("Party name and phone required. (নাম ও ফোন আবশ্যক।)")
  else:
    with st.form("doctor_details_form", clear_on_submit=True):
      st.write("#### 2. Without Map Party Details (ম্যাপ ছাড়া পার্টি)")
      col_d1, col_d2, col_d3 = st.columns(3)
      doc_name = col_d1.text_input("Name (নাম)")
      doc_addr = col_d2.text_input("Address (ঠিকানা)")
      doc_phone = col_d3.text_input("Phone (ফোন নম্বর)")
      submitted_doc = st.form_submit_button(
          "💾 Save Without Map Party (সেভ করুন)", type="primary"
      )
    if submitted_doc:
      if doc_name.strip() and doc_phone.strip():
        try:
          c.execute(
              "INSERT INTO locations (party_name, address, party_phone, lat,"
              " lon) VALUES (?, ?, ?, NULL, NULL)",
              (doc_name.strip(), doc_addr, doc_phone.strip()),
          )
          c.execute(
              "INSERT INTO daily_work (party_name, activity_type, work_date)"
              " VALUES (?, ?, ?)",
              (
                  doc_name.strip(),
                  "Visit (ভিজিট)",
                  get_ist_time().strftime("%Y-%m-%d"),
              ),
          )
          conn.commit()
          st.success("Saved successfully!")
          st.rerun()
        except sqlite3.IntegrityError:
          st.error("Party already exists!")
      else:
        st.error("Name and phone required.")

  st.write("---")
  st.write("#### Select Location from Map (ম্যাপ থেকে সিলেক্ট করুন)")
  col_m1, col_m2 = st.columns([1, 4])
  if col_m1.button("📍 Current GPS"):
    if gps_lat and gps_lon:
      st.session_state["selected_lat"] = gps_lat
      st.session_state["selected_lon"] = gps_lon
      st.rerun()
  col_m2.write(
      f"Coordinates: `{st.session_state['selected_lat']:.5f},"
      f" {st.session_state['selected_lon']:.5f}`"
  )

  advanced_map = folium.Map(
      location=[st.session_state["selected_lat"], st.session_state["selected_lon"]],
      zoom_start=17,
      tiles=None,
  )
  folium.TileLayer(
      tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
      attr="Google",
      name="Street View",
      show=True,
  ).add_to(advanced_map)
  folium.TileLayer(
      tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
      attr="Google",
      name="Satellite View",
      show=False,
  ).add_to(advanced_map)
  folium.Marker(
      [st.session_state["selected_lat"], st.session_state["selected_lon"]],
      popup="Selected Point",
      icon=folium.Icon(color="red"),
  ).add_to(advanced_map)
  folium.LayerControl().add_to(advanced_map)

  map_data = st_folium(
      advanced_map, width="100%", height=400, key="interactive_map"
  )
  if map_data and map_data.get("last_clicked"):
    clat, clon = (
        map_data["last_clicked"]["lat"],
        map_data["last_clicked"]["lng"],
    )
    if (
        clat != st.session_state["selected_lat"]
        or clon != st.session_state["selected_lon"]
    ):
      st.session_state["selected_lat"], st.session_state["selected_lon"] = (
          clat,
          clon,
      )
      st.rerun()

  st.write("---")
  st.write("### 📦 Orders & Visits (অর্ডার ও ভিজিট)")
  c.execute("SELECT party_name FROM locations ORDER BY party_name ASC")
  all_parties_list = [r[0] for r in c.fetchall()]

  selected_order_party = (
      st.selectbox("Select Party for Order/Visit", all_parties_list)
      if all_parties_list
      else ""
  )
  with st.form("order_visit_entry_form"):
    ord_details = st.text_area("Order Details (অর্ডার বিবরণ)")
    col_ob1, col_ob2 = st.columns(2)
    submitted_order = col_ob1.form_submit_button(
        "🛒 Submit Order", type="primary"
    )
    submitted_visit = col_ob2.form_submit_button("📍 Save Visit")
    if submitted_order and selected_order_party:
      c.execute(
          "INSERT INTO orders (party_name, order_details, order_date, status)"
          " VALUES (?, ?, ?, 'Pending')",
          (
              selected_order_party,
              ord_details.strip(),
              get_ist_time().strftime("%Y-%m-%d %H:%M:%S"),
          ),
      )
      c.execute(
          "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES"
          " (?, 'Order (অর্ডার)', ?)",
          (selected_order_party, get_ist_time().strftime("%Y-%m-%d")),
      )
      conn.commit()
      st.success("Order submitted!")
      st.rerun()
    if submitted_visit and selected_order_party:
      c.execute(
          "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES"
          " (?, 'Visit (ভিজিট)', ?)",
          (selected_order_party, get_ist_time().strftime("%Y-%m-%d")),
      )
      conn.commit()
      st.success("Visit saved!")
      st.rerun()

# =========================================================
# 10. PAGE 2: SEARCH & DETAILS
# =========================================================
elif selected_menu == "🔍 Search & Details (অনুসন্ধান ও বিবরণ)":
  st.write("### 🔍 Search & Party Management")

  # Add Map Handler for Non-Mapped Parties
  if st.session_state.get("mapping_party_id"):
    st.markdown(
        f"### 📍 Set Map for **{st.session_state['mapping_party_name']}**"
    )
    if "temp_map_lat" not in st.session_state:
      st.session_state["temp_map_lat"] = 22.8620
    if "temp_map_lon" not in st.session_state:
      st.session_state["temp_map_lon"] = 87.3320

    pick_map = folium.Map(
        location=[
            st.session_state["temp_map_lat"],
            st.session_state["temp_map_lon"],
        ],
        zoom_start=17,
        tiles=None,
    )
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google Maps",
        name="Street",
    ).add_to(pick_map)
    folium.Marker(
        [st.session_state["temp_map_lat"], st.session_state["temp_map_lon"]],
        icon=folium.Icon(color="red"),
    ).add_to(pick_map)
    p_map_data = st_folium(
        pick_map, width="100%", height=400, key="party_location_picker_map"
    )

    if p_map_data and p_map_data.get("last_clicked"):
      st.session_state["temp_map_lat"] = p_map_data["last_clicked"]["lat"]
      st.session_state["temp_map_lon"] = p_map_data["last_clicked"]["lng"]
      st.rerun()

    col_b1, col_b2 = st.columns(2)
    if col_b1.button("✅ Save Location", type="primary"):
      c.execute(
          "UPDATE locations SET lat=?, lon=? WHERE id=?",
          (
              st.session_state["temp_map_lat"],
              st.session_state["temp_map_lon"],
              st.session_state["mapping_party_id"],
          ),
      )
      conn.commit()
      st.session_state.pop("mapping_party_id", None)
      st.rerun()
    if col_b2.button("❌ Cancel"):
      st.session_state.pop("mapping_party_id", None)
      st.rerun()
    st.stop()

  master_search_query = st.text_input(
      "Search Party", placeholder="Type name or phone..."
  )
  if master_search_query.strip():
    q = f"%{master_search_query.strip()}%"
    df = pd.read_sql_query(
        "SELECT * FROM locations WHERE party_name LIKE ? OR party_phone LIKE ?"
        " ORDER BY party_name ASC",
        conn,
        params=(q, q),
    )
  else:
    df = pd.read_sql_query("SELECT * FROM locations ORDER BY party_name ASC", conn)

  doc_df = df[df["lat"].isna() | df["lon"].isna()]
  mapped_df = df[df["lat"].notna() & df["lon"].notna()]

  with st.expander(f"🩺 Non-Map List ({len(doc_df)})", expanded=True):
    for index, row in doc_df.iterrows():
      cols = st.columns([3, 2, 2, 2, 1.5])
      cols[0].write(f"**{row['party_name']}**")
      cols[1].write(row["party_phone"] or "-")
      cols[2].write(row["address"] or "-")
      if cols[3].button("📍 Add Map", key=f"map_add_{row['id']}"):
        st.session_state["mapping_party_id"] = row["id"]
        st.session_state["mapping_party_name"] = row["party_name"]
        st.rerun()
      if st.session_state["user_role"] == "admin":
        if cols[4].button("Delete", key=f"del_doc_{row['id']}"):
          c.execute("DELETE FROM locations WHERE id=?", (row["id"],))
          conn.commit()
          st.rerun()

  with st.expander(f"📍 Mapped List ({len(mapped_df)})", expanded=True):
    for index, row in mapped_df.iterrows():
      cols = st.columns(
          [3, 2, 2, 2, 1.5]
          if st.session_state["user_role"] == "admin"
          else [3, 2, 2, 2]
      )
      cols[0].write(f"**{row['party_name']}**")
      cols[1].write(row["party_phone"] or "-")
      cols[2].write(row["address"] or "-")
      maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}"
      cols[3].markdown(
          f'<a href="{maps_url}" target="_blank"><button'
          ' style="background:#3b82f6;color:white;border:none;padding:6px'
          ' 12px;border-radius:6px;">🧭 Direction</button></a>',
          unsafe_allow_html=True,
      )
      if st.session_state["user_role"] == "admin":
        if cols[4].button("Delete", key=f"del_loc_{row['id']}"):
          c.execute("DELETE FROM locations WHERE id=?", (row["id"],))
          conn.commit()
          st.rerun()

# =========================================================
# 11. PAGE 3: PENDING ORDERS
# =========================================================
elif selected_menu == "📦 Pending Orders (বাকি অর্ডার)":
  st.write("### 📦 Orders Management")
  orders_df = pd.read_sql_query(
      "SELECT * FROM orders WHERE status='Pending' ORDER BY order_date DESC",
      conn,
  )
  if not orders_df.empty:
    for idx, row in orders_df.iterrows():
      cols = st.columns([3, 4, 2])
      cols[0].write(f"**{row['party_name']}**")
      cols[1].write(row["order_details"])
      if cols[2].button("✔️ Complete", key=f"ord_btn_{row['id']}"):
        c.execute(
            "UPDATE orders SET status='Completed' WHERE id=?", (row["id"],)
        )
        conn.commit()
        st.success("Completed!")
        st.rerun()
  else:
    st.info("No pending orders.")

# =========================================================
# 12. PAGE 4: DAILY & MONTHLY WORK
# =========================================================
elif selected_menu == "📋 Daily & Monthly Work (দৈনিক ও মাসিক কাজ)":
  st.write("### 📋 Daily & Monthly Work Report")
  work_df = pd.read_sql_query(
      "SELECT * FROM daily_work ORDER BY work_date DESC, id DESC LIMIT 50", conn
  )
  if not work_df.empty:
    st.dataframe(work_df, use_container_width=True)
  else:
    st.info("No work records found.")

# =========================================================
# 13. PAGE 5: DUE & DELIVERY
# =========================================================
elif selected_menu == "📋 Due & Delivery (বকেয়া ও ডেলিভারি)":
  st.write("### 🚚 Delivery & Due Plan")
  c.execute("SELECT username, fullname FROM users")
  users_data = c.fetchall()
  all_agents = [r[0] for r in users_data]
  agent_name_map = {r[0]: (r[1] if r[1] else r[0]) for r in users_data}

  c.execute("SELECT party_name FROM locations ORDER BY party_name ASC")
  all_parties = [r[0] for r in c.fetchall()]

  with st.form("assign_task_form"):
    st.write("#### ➕ Assign New Task")
    col_as1, col_as2 = st.columns(2)
    assigned_agent = col_as1.selectbox(
        "Select Agent", all_agents, format_func=lambda x: agent_name_map.get(x, x)
    )
    selected_task_party = (
        col_as2.selectbox("Select Party", all_parties) if all_parties else ""
    )
    task_type_sel = st.selectbox(
        "Task Type",
        [
            "Delivery & Due Collection",
            "Only Delivery",
            "Only Due Collection",
        ],
    )
    col_s1, col_s2 = st.columns(2)
    sale_amt_input = col_s1.text_input("Sale Amount (₹)", "0")
    due_amt_input = col_s2.text_input("Due Amount (₹)", "0")

    if (
        st.form_submit_button("🚀 Assign Task", type="primary")
        and selected_task_party
    ):
      c.execute(
          """
          INSERT INTO task_assignments (agent_name, party_name, task_type, due_amount, sale_amount, status, created_at)
          VALUES (?, ?, ?, ?, ?, 'Pending', ?)
      """,
          (
              assigned_agent,
              selected_task_party,
              task_type_sel,
              due_amt_input,
              sale_amt_input,
              get_ist_time().strftime("%Y-%m-%d %H:%M:%S"),
          ),
      )
      conn.commit()
      st.success("Task assigned successfully!")
      st.rerun()

  st.write("---")
  st.write("#### 📋 Active Tasks")
  if st.session_state["user_role"] == "admin":
    tasks_df = pd.read_sql_query(
        "SELECT * FROM task_assignments WHERE status='Pending' ORDER BY id"
        " DESC",
        conn,
    )
  else:
    tasks_df = pd.read_sql_query(
        "SELECT * FROM task_assignments WHERE agent_name=? AND status='Pending'"
        " ORDER BY id DESC",
        conn,
        params=(st.session_state["username"],),
    )

  if not tasks_df.empty:
    for idx, t_row in tasks_df.iterrows():
      st.markdown(
          f"""
      <div class="card">
          <div class="party-title">📍 {t_row['party_name']}</div>
          <div class="card-text"><b>Agent:</b> {agent_name_map.get(t_row['agent_name'], t_row['agent_name'])}</div>
          <div class="card-text"><b>Type:</b> {t_row['task_type']} | <b>Sale:</b> ₹{t_row['sale_amount']} | <b>Due:</b> ₹{t_row['due_amount']}</div>
      </div>
      """,
          unsafe_allow_html=True,
      )
      with st.form(key=f"comp_task_{t_row['id']}"):
        collected_input = st.text_input(
            "Payment Collected (₹)", "0", key=f"coll_{t_row['id']}"
        )
        if st.form_submit_button("✔️ Complete Task", type="primary"):
          c.execute(
              "UPDATE task_assignments SET status='Completed',"
              " payment_collected_actual=? WHERE id=?",
              (collected_input, t_row["id"]),
          )
          conn.commit()
          st.success("Task marked complete!")
          st.rerun()
  else:
    st.info("No active pending tasks.")

# =========================================================
# 14. PAGE 6: ATTENDANCE
# =========================================================
elif selected_menu == "📅 Attendance (উপস্থিতি)":
  st.write("### 📅 Daily Attendance")
  current_date_str = get_ist_time().strftime("%Y-%m-%d")
  if st.button("✋ Check-In / Mark Present", type="primary"):
    try:
      c.execute(
          "INSERT INTO attendance (username, date, check_time, status) VALUES"
          " (?, ?, ?, 'Present')",
          (
              st.session_state["username"],
              current_date_str,
              get_ist_time().strftime("%H:%M:%S"),
          ),
      )
      conn.commit()
      st.success("Attendance marked!")
    except sqlite3.IntegrityError:
      st.warning("Already marked for today!")

  att_df = pd.read_sql_query(
      "SELECT username, date, check_time, status FROM attendance ORDER BY date"
      " DESC",
      conn,
  )
  st.dataframe(att_df, use_container_width=True)

# =========================================================
# 15. PAGE 7 & 8: LIVE TRACKING & ADMIN SETTINGS
# =========================================================
elif (
    selected_menu == "📊 Live Tracking (লাইভ ট্র্যাকিং)"
    and st.session_state["user_role"] == "admin"
):
  st.write("### 📊 Agent Live Tracking")
  tracking_df = pd.read_sql_query(
      "SELECT l.username, u.fullname, l.lat, l.lon, l.last_updated FROM"
      " agent_live_locations l LEFT JOIN users u ON l.username = u.username",
      conn,
  )
  st.dataframe(tracking_df, use_container_width=True)

elif (
    selected_menu == "⚙️ Settings & Agents (সেটিংস)"
    and st.session_state["user_role"] == "admin"
):
  st.write("### ⚙️ System Settings & Agent Management")

  st.markdown("#### 🌐 App Public Domain Settings")
  if "app_public_domain" not in st.session_state:
    st.session_state["app_public_domain"] = (
        "https://your-app-name.streamlit.app"
    )

  configured_domain = st.text_input(
      "Your Streamlit Public App URL:",
      value=st.session_state["app_public_domain"],
  )
  if st.button("💾 Save Domain URL"):
    clean_domain = configured_domain.strip().rstrip("/")
    st.session_state["app_public_domain"] = clean_domain
    st.success(f"Domain URL set to: {clean_domain}")

  st.write("---")

  with st.form("create_agent_form"):
    st.write("#### ➕ Create Agent & Generate Link")
    agent_full_name_input = st.text_input("Agent Full Name")
    agent_phone_input = st.text_input("Agent Phone Number")
    agent_password_input = st.text_input(
        "Password", value="1234", type="password"
    )

    submit_new_user = st.form_submit_button(
        "🚀 Create & Generate Link", type="primary"
    )

    if submit_new_user:
      if agent_full_name_input.strip() and agent_phone_input.strip():
        clean_phone = "".join(filter(str.isdigit, agent_phone_input.strip()))
        generated_username = f"agent_{clean_phone}"

        c.execute(
            "SELECT username FROM users WHERE username=? OR phone=?",
            (generated_username, agent_phone_input.strip()),
        )
        if c.fetchone():
          st.error("This agent or phone number already exists!")
        else:
          c.execute(
              "INSERT INTO users (username, password, role, fullname, phone,"
              " created_at, is_active) VALUES (?, ?, 'staff', ?, ?, ?, 1)",
              (
                  generated_username,
                  agent_password_input.strip(),
                  agent_full_name_input.strip(),
                  agent_phone_input.strip(),
                  get_ist_time().strftime("%Y-%m-%d %H:%M:%S"),
              ),
          )
          conn.commit()

          base_url = st.session_state["app_public_domain"]
          st.session_state["last_generated_agent_name"] = (
              agent_full_name_input.strip()
          )
          st.session_state["last_generated_link"] = (
              f"{base_url}/?login={generated_username}"
          )
          st.success(f"Agent '{agent_full_name_input}' created successfully!")
      else:
        st.error("Provide Full Name and Phone Number.")

  if st.session_state.get("last_generated_link"):
    st.write("---")
    st.markdown(
        "#### 🔗 WhatsApp Link for"
        f" **{st.session_state.get('last_generated_agent_name')}**"
    )
    share_url = st.session_state["last_generated_link"]
    st.code(share_url, language="text")

    whatsapp_msg = urllib.parse.quote(
        f"নমস্কার {st.session_state.get('last_generated_agent_name')}! P.S"
        " Mediseller অ্যাপে কাজের জন্য আপনার লগইন"
        f" লিংক:\n\n{share_url}\n\nলিংকে টাচ করে ব্রাউজার থেকে ওপেন করুন।"
    )
    whatsapp_url = f"https://api.whatsapp.com/send?text={whatsapp_msg}"

    st.markdown(
        f"""
    <a href="{whatsapp_url}" target="_blank">
        <button style="background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: white; border: none; padding: 12px 20px; border-radius: 10px; font-weight: bold; cursor: pointer; font-size: 15px;">
            🟢 Share via WhatsApp (হোয়াটসঅ্যাপে পাঠান)
        </button>
    </a>
    """,
        unsafe_allow_html=True,
    )

  st.write("---")
  st.write("#### 👥 Registered Users / Agents")
  users_list_df = pd.read_sql_query(
      "SELECT username, role, fullname, phone, created_at FROM users", conn
  )
  st.dataframe(users_list_df, use_container_width=True)

