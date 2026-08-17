from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import urllib.parse
import base64
import os
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
    page_title="P. S MEDISELLER - Allopathy & Ayurvedic Wholesaler",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# IST TIME HELPER
# =========================================================
def get_ist_time():
  ist_offset = timezone(timedelta(hours=5, minutes=30))
  return datetime.now(ist_offset)

# =========================================================
# ADVANCED CUSTOM STYLING & PWA STANDALONE MANIFEST INJECTION
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
    ] 
  }};
  const stringManifest = JSON.stringify(manifest);
  const blob = new Blob([stringManifest], {{type: 'application/json'}});
  const manifestURL = URL.createObjectURL(blob);
  const targetHead = window.parent.document.head || document.head;
  let link = document.createElement('link');
  link.rel = 'manifest';
  link.href = manifestURL;
  targetHead.appendChild(link);
  let meta1 = document.createElement('meta');
  meta1.name = 'apple-mobile-web-app-capable';
  meta1.content = 'yes';
  targetHead.appendChild(meta1);
  let meta2 = document.createElement('meta');
  meta2.name = 'mobile-web-app-capable';
  meta2.content = 'yes';
  targetHead.appendChild(meta2);
}} catch(e) {{
  console.log("PWA injection error:", e);
}}
</script>
"""
st.components.v1.html(pwa_manifest_html, height=0)

# =========================================================
# MANDATORY LOCATION PERMISSION ENFORCEMENT COMPONENT
# =========================================================
mandatory_location_html = """
<div id="loc-overlay" style="display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(15, 23, 42, 0.98);
z-index: 999999; justify-content: center; align-items: center; padding: 20px; box-sizing: border-box; font-family: 'Poppins', sans-serif;">
    <div style="background: #1e293b; border: 2px solid #ef4444; border-radius: 16px; padding: 30px; max-width: 450px; width: 100%;
text-align: center; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
        <div style="font-size: 48px; margin-bottom: 15px;">📍</div>
        <h2 style="color: #f87171; margin-top: 0; font-size: 22px;">Location Permission Required<br>(লোকেশন পারমিশন আবশ্যক)</h2>
        <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin-bottom: 25px;">
            P.S Mediseller app requires your live GPS location to function properly. Please enable Location/GPS on your device and grant permission.<br><br>
            <b>(অ্যাপটি ব্যবহারের জন্য আপনার ফোনের জিপিএস লোকেশন অন করুন এবং পারমিশন দিন।)</b>
        </p>
        <button onclick="requestLocation()" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border: none; padding: 14px 28px; border-radius: 10px; font-weight: bold; font-size: 16px; cursor: pointer; width: 100%; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);">
            🔄 Grant Permission / Retry (অনুমতি দিন / রিফ্রেশ)
        </button>
        <p id="loc-status" style="color: #fbbf24; font-size: 13px; margin-top: 15px; display: none;"></p>
    </div>
</div>
<script>
function checkAndRequestLocation() {
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        return;
    }
    navigator.geolocation.getCurrentPosition(
        function(position) {
            localStorage.setItem('ps_user_lat', position.coords.latitude);
            localStorage.setItem('ps_user_lon', position.coords.longitude);
            const overlay = document.getElementById('loc-overlay');
            if (overlay) overlay.style.display = 'none';
        },
        function(error) {
            const overlay = document.getElementById('loc-overlay');
            if (overlay) overlay.style.display = 'flex';
            const status = document.getElementById('loc-status');
            if (status) {
                status.style.display = 'block';
                status.innerText = "⚠️ Please enable location to continue. (লোকেশন অন করুন)";
            }
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
}
function requestLocation() { checkAndRequestLocation(); }
window.addEventListener('load', function() { setTimeout(checkAndRequestLocation, 500); });
</script>
"""
st.components.v1.html(mandatory_location_html, height=0)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
html, body, [class*="css"], p, span, label, div {
    font-family: 'Poppins', sans-serif;
    color: #ffffff !important;
}
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    color: #ffffff !important;
}
div.stExpander, div[data-testid="stForm"] {
    background: #1e293b !important;
    border: 1px solid rgba(148, 163, 184, 0.35) !important;
    border-radius: 14px !important;
    padding: 20px !important;
    box-shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.4);
    color: #ffffff !important;
} 
div.stExpander details summary, [data-testid="stExpander"] summary {
    background-color: #1e293b !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    padding: 6px 10px !important;
}
.stButton>button, div.stButton > button {
    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
    color: #ffffff !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.2rem !important;
    font-weight: 600 !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important;
}
input, textarea, select, [data-baseweb="input"] input, [data-baseweb="textarea"] textarea {
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
.report-card {
    background: #1e293b;
    border: 1px solid #334155;
    padding: 16px;
    border-radius: 12px;
    margin-bottom: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.main-title {
    font-size: 24px;
    font-weight: bold;
    color: #ffffff;
    text-align: center;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE SETUP & CLEANUP
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

# Column checks
c.execute("PRAGMA table_info(task_assignments)")
existing_cols_task = [row[1] for row in c.fetchall()]
if "sale_amount" not in existing_cols_task:
  c.execute("ALTER TABLE task_assignments ADD COLUMN sale_amount TEXT DEFAULT '0'")
if "payment_collected_actual" not in existing_cols_task:
  c.execute("ALTER TABLE task_assignments ADD COLUMN payment_collected_actual TEXT DEFAULT '0'")
conn.commit()

c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
  c.execute("INSERT INTO users (username, password, role, fullname, phone, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", 
            ("admin", "admin123", "admin", "Admin", "8918740325", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1))
  c.execute("INSERT INTO users (username, password, role, fullname, phone, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", 
            ("delivery", "user123", "staff", "Delivery Agent", "8918740325", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1))
  conn.commit()

# =========================================================
# PROFESSIONAL HTML/PDF REPORT GENERATOR HELPER
# =========================================================
def generate_html_report(title, df):
  html = f"""
  <!DOCTYPE html>
  <html lang="bn">
  <head>
      <meta charset="UTF-8">
      <title>{title} - P. S MEDISELLER</title>
      <style>
          body {{ font-family: 'Poppins', Arial, sans-serif; margin: 20px; color: #1e293b; background: #f8fafc; }}
          .header {{ text-align: center; margin-bottom: 20px; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; }}
          h2 {{ color: #1e40af; margin: 0; }}
          p {{ color: #64748b; font-size: 14px; margin: 5px 0; }}
          table {{ width: 100%; border-collapse: collapse; margin-top: 15px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
          th, td {{ border: 1px solid #e2e8f0; padding: 12px 15px; text-align: left; font-size: 13px; }}
          th {{ background-color: #3b82f6; color: white; font-weight: 600; }}
          tr:nth-child(even) {{ background-color: #f1f5f9; }}
          .print-btn {{ display: block; width: 220px; margin: 20px auto; padding: 12px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: bold; cursor: pointer; text-align: center; }}
          @media print {{ .print-btn {{ display: none; }} body {{ background: white; margin: 0; }} }}
      </style>
  </head>
  <body>
      <div class="header">
          <h2>P. S MEDISELLER</h2>
          <p><b>Allopathy & Ayurvedic Wholesaler</b> | Address: Ledagama 1, Amlagora, Garhbeta, Paschim Medinipur</p>
          <p><b>{title}</b></p>
          <p>Generated on: {get_ist_time().strftime('%d-%m-%Y %H:%M:%S')} IST</p>
      </div>
      <button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF (প্রিন্ট / পিডিএফ)</button>
      {df.to_html(index=False, classes='table', border=0)}
  </body>
  </html>
  """
  return html.encode('utf-8')

if "selected_lat" not in st.session_state:
  st.session_state["selected_lat"] = 22.8620
if "selected_lon" not in st.session_state:
  st.session_state["selected_lon"] = 87.3320
if "username" not in st.session_state:
  st.session_state["username"] = "delivery"
if "user_role" not in st.session_state:
  st.session_state["user_role"] = "staff" 

query_params = st.query_params
login_user = query_params.get("login", None)
saved_user_js = streamlit_js_eval(js_expressions="localStorage.getItem('ps_mediseller_user')", key="get_saved_user_storage")
target_login = None
if login_user:
    target_login = login_user
    st.markdown(f"<script>localStorage.setItem('ps_mediseller_user', '{login_user}');</script>", unsafe_allow_html=True)
elif saved_user_js and st.session_state.get("username") == "delivery":
    target_login = saved_user_js

if target_login:
    c.execute("SELECT fullname, role FROM users WHERE username=?", (target_login,))
    user_row = c.fetchone()
    if user_row:
        st.session_state["username"] = target_login
        st.session_state["user_role"] = user_row[1]
        if login_user:
            st.query_params.pop("login", None)
            st.rerun()

col_ht1, col_ht2 = st.columns([3, 1])
with col_ht1:
  st.markdown(f"""
  <div style="display: flex; align-items: center; gap: 12px;">
      <img src="data:image/jpeg;base64,{logo_b64}" style="width: 52px; height: 52px; border-radius: 10px; object-fit: cover; border: 1px solid rgba(255,255,255,0.2);">
      <div>
          <h1 style="margin: 0; font-size: 19px !important; background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700;">P. S MEDISELLER</h1>
          <p style="margin: 2px 0 0 0; color: #cbd5e1 !important; font-size: 11px;">Allopathy & Ayurvedic Wholesaler | Ph: 8918740325</p>
      </div>
  </div>
  """, unsafe_allow_html=True)

with col_ht2:
  if st.session_state["user_role"] == "admin":
    if st.button("🚪 Logout (লগআউট)", key="logout_btn_top"):
      st.session_state["username"] = "delivery"
      st.session_state["user_role"] = "staff"
      st.markdown("<script>localStorage.removeItem('ps_mediseller_user');</script>", unsafe_allow_html=True)
      st.rerun()
  else:
    if st.button("🔐 Admin Login (অ্যাডমিন)", key="login_btn_top"):
      st.session_state["show_admin_login"] = True
      st.rerun()

c.execute("SELECT fullname FROM users WHERE username=?", (st.session_state['username'],))
curr_user_row = c.fetchone() 
current_fullname = curr_user_row[0] if curr_user_row and curr_user_row[0] else st.session_state['username']

st.write(f"👤 User: **{current_fullname}** (`{st.session_state['user_role']}`)")

if st.session_state.get("show_admin_login", False):
  with st.form("admin_login_popup_form"):
    st.write("#### 🔑 Admin Login (অ্যাডমিন লগইন)")
    admin_pass_input = st.text_input("Enter Admin Password (পাসওয়ার্ড দিন)", type="password")
    col_al1, col_al2 = st.columns(2)
    with col_al1:
      submit_admin = st.form_submit_button("Login (লগইন)", type="primary")
    with col_al2:
      cancel_admin = st.form_submit_button("Cancel (বাতিল)")
    if submit_admin:
      c.execute("SELECT password FROM users WHERE username='admin'")
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

loc = get_geolocation(component_key="hidden_background_gps_tracker")
if loc and "coords" in loc:
  gps_lat = loc["coords"]["latitude"]
  gps_lon = loc["coords"]["longitude"]
  c.execute(
      "UPDATE agent_live_locations SET lat=?, lon=?, last_updated=? WHERE username=?",
      (gps_lat, gps_lon, get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), st.session_state["username"]),
  )
  if c.rowcount == 0:
    c.execute(
        "INSERT INTO agent_live_locations (username, lat, lon, last_updated) VALUES (?, ?, ?, ?)",
        (st.session_state["username"], gps_lat, gps_lon, get_ist_time().strftime("%Y-%m-%d %H:%M:%S")),
    )
  conn.commit()

# =========================================================
# NAVIGATION MENU
# =========================================================
menu_options = [
    "📍 Add Location (লোকেশন যোগ)",
    "🔍 Search & Details (অনুসন্ধান ও বিবরণ)",
    "📦 Pending Orders (বাকি অর্ডার)",
    "📋 Daily & Monthly Work (দৈনিক ও মাসিক কাজ)",
    "📋 Due & Delivery (বকেয়া ও ডেলিভারি)",
    "🗺️ Route Map (রুট ম্যাপ)",
    "📅 Attendance (উপস্থিতি)",
]
if st.session_state["user_role"] == "admin":
  menu_options.extend([
      "📊 Live Tracking (লাইভ ট্র্যাকিং)", 
      "⚙️ Settings & Agents (সেটিংস)"
  ])

current_page_param = query_params.get("page", menu_options[0]) 
if current_page_param not in menu_options:
  current_page_param = menu_options[0]
default_index = menu_options.index(current_page_param)

selected_menu = st.radio("Select Menu:", menu_options, index=default_index, horizontal=False, label_visibility="collapsed")
if selected_menu != current_page_param:
  st.query_params["page"] = selected_menu
  st.rerun()

st.write("---")

# =========================================================
# 1. ADD NEW LOCATION & ORDER / VISIT ENTRY
# =========================================================
if selected_menu == "📍 Add Location (লোকেশন যোগ)":
  st.write("### 📍 Add Location & Party (লোকেশন ও পার্টি)")
  selected_entry_tab = st.radio("Select Entry Mode:", ["🏠 With Map Party", "👨‍⚕️ Without Map Party"], label_visibility="collapsed")
  
  if "With Map Party" in selected_entry_tab:
    with st.form("location_details_form", clear_on_submit=True):
      col_f1, col_f2, col_f3 = st.columns(3)
      p_name = col_f1.text_input("Party Name (পার্টির নাম)")
      p_addr = col_f2.text_input("Address (ঠিকানা)")
      p_phone = col_f3.text_input("Phone Number (ফোন নম্বর)")
      submitted_loc = st.form_submit_button("💾 Save Location", type="primary")
    if submitted_loc:
      if p_name.strip() and p_phone.strip():
        try:
          c.execute("INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, ?, ?)",
                    (p_name.strip(), p_addr, p_phone.strip(), st.session_state["selected_lat"], st.session_state["selected_lon"]))
          c.execute("INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
                    (p_name.strip(), "Visit (ভিজিট)", get_ist_time().strftime("%Y-%m-%d")))
          conn.commit()
          st.success("Location saved successfully!")
          st.rerun()
        except:
          st.error("Party name or phone already exists!")
      else:
        st.error("Name and Phone required.")
  else:
    with st.form("doctor_details_form", clear_on_submit=True):
      col_d1, col_d2, col_d3 = st.columns(3)
      doc_name = col_d1.text_input("Name (নাম)")
      doc_addr = col_d2.text_input("Address (ঠিকানা)")
      doc_phone = col_d3.text_input("Phone (ফোন নম্বর)")
      submitted_doc = st.form_submit_button("💾 Save Without Map Party", type="primary")
    if submitted_doc:
      if doc_name.strip() and doc_phone.strip():
        try:
          c.execute("INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, NULL, NULL)",
                    (doc_name.strip(), doc_addr, doc_phone.strip()))
          c.execute("INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
                    (doc_name.strip(), "Visit (ভিজিট)", get_ist_time().strftime("%Y-%m-%d")))
          conn.commit()
          st.success("Saved successfully!")
          st.rerun()
        except:
          st.error("Party already exists!")
      else:
        st.error("Name and Phone required.")

  st.write("---")
  advanced_map = folium.Map(location=[st.session_state["selected_lat"], st.session_state["selected_lon"]], zoom_start=17, tiles=None)
  folium.TileLayer(tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps", name="Street").add_to(advanced_map)
  folium.Marker([st.session_state["selected_lat"], st.session_state["selected_lon"]], icon=folium.Icon(color="red", icon="map-marker", prefix="fa")).add_to(advanced_map)
  map_data = st_folium(advanced_map, width="100%", height=350, key="interactive_map")
  if map_data and map_data.get("last_clicked"):
    st.session_state["selected_lat"] = map_data["last_clicked"]["lat"]
    st.session_state["selected_lon"] = map_data["last_clicked"]["lng"]
    st.rerun()

# =========================================================
# 2. SEARCH PARTY DETAILS
# =========================================================
elif selected_menu == "🔍 Search & Details (অনুসন্ধান ও বিবরণ)":
  st.write("### 🔍 Search & Party Management")
  q = st.text_input("Search Party", placeholder="Type name...", label_visibility="collapsed")
  df = pd.read_sql_query("SELECT * FROM locations WHERE party_name LIKE ? OR address LIKE ? OR party_phone LIKE ? ORDER BY party_name ASC", conn, params=(f"%{q}%", f"%{q}%", f"%{q}%")) if q else pd.read_sql_query("SELECT * FROM locations ORDER BY party_name ASC", conn)
  
  for idx, row in df.iterrows():
    st.markdown(f"""
    <div class="report-card">
        <b>🏢 {row['party_name']}</b><br>
        📞 Ph: {row['party_phone']} | 📍 {row['address']}
    </div>
    """, unsafe_allow_html=True)
    if st.session_state["user_role"] == "admin":
      if st.button("🗑️ Delete Party", key=f"del_loc_{row['id']}"):
        c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
        conn.commit()
        st.rerun()

# =========================================================
# 3. PENDING ORDERS
# =========================================================
elif selected_menu == "📦 Pending Orders (বাকি অর্ডার)":
  st.write("### 📦 Pending Orders")
  orders_df = pd.read_sql_query("SELECT * FROM orders WHERE status='Pending' ORDER BY order_date DESC", conn)
  if not orders_df.empty:
    for idx, row in orders_df.iterrows():
      st.markdown(f"""
      <div class="report-card">
          <b>🏢 {row['party_name']}</b><br>
          🛒 Order: {row['order_details']}<br>
          📅 Date: {row['order_date']}
      </div>
      """, unsafe_allow_html=True)
      if st.button("✔️ Complete Order", key=f"ord_comp_{row['id']}"):
        c.execute("UPDATE orders SET status='Completed' WHERE id=?", (row['id'],))
        conn.commit()
        st.rerun()
  else:
    st.info("No pending orders.")

# =========================================================
# 4. DAILY & MONTHLY WORK
# =========================================================
elif selected_menu == "📋 Daily & Monthly Work (দৈনিক ও মাসিক কাজ)":
  st.write("### 📋 Daily & Monthly Work Report")
  work_tab1, work_tab2 = st.tabs(["📅 Daily Work", "📊 Monthly Summary"])

  with work_tab1:
    work_df = pd.read_sql_query("SELECT * FROM daily_work ORDER BY work_date DESC, id DESC", conn)
    if not work_df.empty:
      if st.session_state["user_role"] == "admin":
        st.download_button("📥 Download Report (HTML/PDF)", data=generate_html_report("Daily Work Report", work_df), file_name="daily_work.html", mime="text/html")
      for idx, row in work_df.iterrows():
        st.markdown(f"""
        <div class="report-card">
            <b>🏢 {row['party_name']}</b> - <code>{row['activity_type']}</code><br>
            📅 Date: {row['work_date']}
        </div>
        """, unsafe_allow_html=True)
        if st.session_state["user_role"] == "admin":
          if st.button("🗑️ Delete Record", key=f"del_dw_{row['id']}"):
            c.execute("DELETE FROM daily_work WHERE id=?", (row['id'],))
            conn.commit()
            st.rerun()
    else:
      st.info("No records found.")

  with work_tab2:
    st.write("Monthly Summary Reports generated dynamically.")

# =========================================================
# 5. DUE & DELIVERY (CARD-BASED & ADMIN EDITABLE)
# =========================================================
elif selected_menu == "📋 Due & Delivery (বকেয়া ও ডেলিভারি)":
  st.markdown('<div class="main-title">📋 ডেলিভারি ও ডিউ প্ল্যান (কার্ড মোড)</div>', unsafe_allow_html=True)
  
  c.execute("SELECT username, fullname FROM users")
  users_data = c.fetchall()
  all_agents = [r[0] for r in users_data]
  agent_name_map = {r[0]: (r[1] if r[1] else r[0]) for r in users_data}

  c.execute("SELECT party_name FROM locations ORDER BY party_name ASC")
  all_parties = [r[0] for r in c.fetchall()]

  task_tab1, task_tab2 = st.tabs(["🎯 Active & Present Day Tasks", "📜 Completed Tasks History"])

  with task_tab1:
    if st.session_state["user_role"] == "admin":
      full_tasks_df = pd.read_sql_query("""
          SELECT t.id, u.fullname as agent_fullname, t.agent_name, t.party_name, t.task_type, t.due_amount, t.sale_amount, t.payment_collected_actual, t.status, t.created_at, l.address 
          FROM task_assignments t 
          LEFT JOIN users u ON t.agent_name = u.username 
          LEFT JOIN locations l ON t.party_name = l.party_name 
          WHERE t.status='Pending' ORDER BY t.id DESC
      """, conn)
      if not full_tasks_df.empty:
        st.download_button("📥 Download Active Tasks Report (PDF/HTML)", data=generate_html_report("Active Deliveries & Dues", full_tasks_df), file_name="active_tasks.html", mime="text/html", type="primary")

    with st.form("assign_task_form"):
      st.write("#### ➕ Assign Task / Delivery")
      sel_ag = st.selectbox("Select Agent", all_agents, format_func=lambda x: agent_name_map.get(x, x)) if st.session_state["user_role"] == "admin" else st.session_state["username"]
      sel_pt = st.selectbox("Select Party", all_parties) if all_parties else ""
      
      c1, c2 = st.columns(2)
      chk_del = c1.checkbox("🚚 Delivery")
      chk_due = c2.checkbox("💰 Due Collection")
      d_amt = st.text_input("Due Amount / Sale Details", "0")
      if st.form_submit_button("🎯 Add Task", type="primary"):
        if sel_pt:
          t_type = " & ".join([t for t, cond in [("Delivery", chk_del), ("Due Collection", chk_due)] if cond])
          c.execute("INSERT INTO task_assignments (agent_name, party_name, task_type, due_amount, status, created_at) VALUES (?, ?, ?, ?, 'Pending', ?)",
                    (sel_ag, sel_pt, t_type or "General", d_amt, get_ist_time().strftime("%Y-%m-%d %H:%M:%S")))
          conn.commit()
          st.success("Task assigned successfully!")
          st.rerun()

    st.write("---")
    st.write("#### 📋 Pending Tasks List (Card View)")
    pending_df = pd.read_sql_query("SELECT t.*, u.fullname FROM task_assignments t LEFT JOIN users u ON t.agent_name = u.username WHERE t.status='Pending' ORDER BY t.created_at DESC", conn)
    
    if not pending_df.empty:
      for idx, row in pending_df.iterrows():
        ag_show = row['fullname'] if pd.notna(row['fullname']) else row['agent_name']
        st.markdown(f"""
        <div class="report-card">
            <b>🏢 Party: {row['party_name']}</b><br>
            👤 Agent: <code>{ag_show}</code> | Task: <code>{row['task_type']}</code><br>
            💰 Due: ₹{row['due_amount']} | 📅 Date: {row['created_at']}
        </div>
        """, unsafe_allow_html=True)
        
        with st.form(key=f"complete_task_{row['id']}"):
          sc1, sc2 = st.columns(2)
          sale_val = sc1.text_input("Sale Amount (সেল টাকা)", "0", key=f"sale_{row['id']}")
          pay_val = sc2.text_input("Collection Amount (কালেকশন টাকা)", str(row['due_amount']), key=f"pay_{row['id']}")
          if st.form_submit_button("✔️ Complete Task (সম্পন্ন করুন)", type="primary"):
            c.execute("UPDATE task_assignments SET status='Completed', sale_amount=?, payment_collected_actual=? WHERE id=?", (sale_val, pay_val, row['id']))
            conn.commit()
            st.success("Task completed!")
            st.rerun()
        if st.session_state["user_role"] == "admin":
          if st.button("🗑️ Delete Task", key=f"del_task_{row['id']}"):
            c.execute("DELETE FROM task_assignments WHERE id=?", (row['id'],))
            conn.commit()
            st.rerun()
    else:
      st.info("No pending tasks.")

  with task_tab2:
    st.write("#### 📜 Completed Deliveries & Dues (Admin Editable)")
    comp_df = pd.read_sql_query("SELECT t.*, u.fullname FROM task_assignments t LEFT JOIN users u ON t.agent_name = u.username WHERE t.status='Completed' ORDER BY t.created_at DESC", conn)
    if not comp_df.empty:
      if st.session_state["user_role"] == "admin":
        st.download_button("📥 Download Completed Report", data=generate_html_report("Completed Tasks History", comp_df), file_name="completed_tasks.html", mime="text/html", type="primary")
      
      for idx, row in comp_df.iterrows():
        st.markdown(f"""
        <div class="report-card">
            <b>🏢 Party: {row['party_name']}</b><br>
            🛒 Sale: ₹{row['sale_amount']} | 💵 Collection: ₹{row['payment_collected_actual']}<br>
            📅 Date: {row['created_at']}
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state["user_role"] == "admin":
          with st.expander(f"✏️ Edit Task: {row['party_name']} (ID: {row['id']})"):
            with st.form(key=f"edit_comp_task_{row['id']}"):
              e_party = st.text_input("Party Name", value=row['party_name'])
              e_sale = st.text_input("Sale Amount", value=row['sale_amount'])
              e_pay = st.text_input("Collection Amount", value=row['payment_collected_actual'])
              if st.form_submit_button("💾 Save Changes", type="primary"):
                c.execute("UPDATE task_assignments SET party_name=?, sale_amount=?, payment_collected_actual=? WHERE id=?", (e_party, e_sale, e_pay, row['id']))
                conn.commit()
                st.success("Updated successfully!")
                st.rerun()
          if st.button("🗑️ Delete Completed Task", key=f"del_comp_{row['id']}"):
            c.execute("DELETE FROM task_assignments WHERE id=?", (row['id'],))
            conn.commit()
            st.rerun()
    else:
      st.info("No completed tasks history.")

# =========================================================
# 6. ROUTE MAP
# =========================================================
elif selected_menu == "🗺️ Route Map (রুট ম্যাপ)":
  st.write("### 🗺️ Delivery Route Map")
  mapped_locs = pd.read_sql_query("SELECT party_name, address, lat, lon FROM locations WHERE lat IS NOT NULL AND lon IS NOT NULL", conn)
  if not mapped_locs.empty:
    m = folium.Map(location=[mapped_locs.iloc[0]['lat'], mapped_locs.iloc[0]['lon']], zoom_start=13, tiles=None)
    folium.TileLayer(tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google", name="Street").add_to(m)
    for _, r in mapped_locs.iterrows():
      folium.Marker([r['lat'], r['lon']], popup=r['party_name']).add_to(m)
    st_folium(m, width="100%", height=450)
  else:
    st.info("No mapped locations.")

# =========================================================
# 7. ATTENDANCE
# =========================================================
elif selected_menu == "📅 Attendance (উপস্থিতি)":
  st.write("### 📅 Daily Attendance")
  today_str = get_ist_time().strftime("%Y-%m-%d")
  if st.button("✅ Give Today's Attendance", type="primary"):
    try:
      c.execute("INSERT INTO attendance (username, date, check_time, status) VALUES (?, ?, ?, 'Present')",
                (st.session_state["username"], today_str, get_ist_time().strftime("%Y-%m-%d %H:%M:%S")))
      conn.commit()
      st.success("Attendance recorded!")
    except:
      st.warning("Attendance already recorded for today!")

# =========================================================
# 8. LIVE TRACKING
# =========================================================
elif selected_menu == "📊 Live Tracking (লাইভ ট্র্যাকিং)":
  if st.session_state["user_role"] != "admin":
    st.error("Access Denied!")
    st.stop()
  st.write("### 📊 Agent Live Tracking")
  df_agents = pd.read_sql_query("SELECT * FROM agent_live_locations", conn)
  if not df_agents.empty:
    m = folium.Map(location=[22.8620, 87.3320], zoom_start=13, tiles=None)
    folium.TileLayer(tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google", name="Street").add_to(m)
    for _, r in df_agents.iterrows():
      if pd.notna(r['lat']):
        folium.Marker([r['lat'], r['lon']], popup=f"Agent: {r['username']}").add_to(m)
    st_folium(m, width="100%", height=450)

# =========================================================
# 9. SETTINGS & AGENTS
# =========================================================
elif selected_menu == "⚙️ Settings & Agents (সেটিংস)":
  if st.session_state["user_role"] != "admin":
    st.error("Access Denied!")
    st.stop()
  st.write("### ⚙️ Settings & User Management")
  with st.form("add_user_form"):
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    fn = st.text_input("Full Name")
    ph = st.text_input("Phone")
    role = st.selectbox("Role", ["staff", "admin"])
    if st.form_submit_button("➕ Create User", type="primary"):
      if u and p:
        try:
          c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, 1)", (u, p, role, fn, ph, get_ist_time().strftime("%Y-%m-%d %H:%M:%S")))
          conn.commit()
          st.success("User created!")
        except:
          st.error("User exists!")
