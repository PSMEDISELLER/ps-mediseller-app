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
            <b>(অ্যাপটি ব্যবহারের জন্য আপনার ফোনের জিপিএস লোকেশন অন করুন এবং পারমিশন দিন। লোকেশন বন্ধ রাখলে অ্যাপ ব্যবহার করা যাবে না।)</b>
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
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            localStorage.setItem('ps_user_lat', lat);
            localStorage.setItem('ps_user_lon', lon);
            const overlay = document.getElementById('loc-overlay');
            if (overlay) overlay.style.display = 'none';
        },
        function(error) {
            console.warn("Location error:", error.code, error.message);
            const overlay = document.getElementById('loc-overlay');
            if (overlay) overlay.style.display = 'flex';
            const status = document.getElementById('loc-status');
            if (status) {
                status.style.display = 'block';
                if (error.code === error.PERMISSION_DENIED) {
                    status.innerText = "⚠️ Location permission denied! Please enable it in browser & phone settings. (লোকেশন পারমিশন দিন)";
                } else if (error.code === error.POSITION_UNAVAILABLE) {
                    status.innerText = "⚠️ GPS signal unavailable. Please turn on phone GPS/Location. (জিপিএস অন করুন)";
                } else {
                    status.innerText = "⚠️ Please enable location to continue. (লোকেশন অন করুন)";
                }
            }
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
}
function requestLocation() {
    const status = document.getElementById('loc-status');
    if (status) {
        status.style.display = 'block';
        status.innerText = "⏳ Requesting location permission... (অনুমতি নেওয়া হচ্ছে...)";
    }
    checkAndRequestLocation();
}
window.addEventListener('load', function() { setTimeout(checkAndRequestLocation, 500); });
setInterval(checkAndRequestLocation, 15000);
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
div.stExpander details summary, 
div.stExpander details summary span, 
div.stExpander details summary p,
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary p {
    background-color: #1e293b !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    padding: 6px 10px !important;
}
div.stExpander details {
    background: #1e293b !important;
    border: 1px solid rgba(148, 163, 184, 0.35) !important;
    border-radius: 14px !important;
}
.stButton>button, div.stButton > button, button[kind="secondary"], button[kind="primary"], [data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
    color: #ffffff !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.2rem !important;
    font-weight: 600 !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important;
    transition: all 0.3s ease !important;
}
.stButton>button:hover, div.stButton > button:hover, button[kind="secondary"]:hover, button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button:hover {
    background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%) !important;
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6) !important;
    transform: translateY(-2px);
}
input, textarea, select, [data-baseweb="input"] input, [data-baseweb="textarea"] textarea, div[data-baseweb="input"], div[data-baseweb="select"] {
    background-color: #0f172a !important;
    color: #ffffff !important;
    border: 1px solid #3b82f6 !important;
    border-radius: 8px !important;
}
input::placeholder, textarea::placeholder {
    color: #60a5fa !important;
    font-weight: 700 !important;
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

c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
  c.execute("INSERT INTO users (username, password, role, fullname, phone, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", 
            ("admin", "admin123", "admin", "Admin", "8918740325", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1))
  c.execute("INSERT INTO users (username, password, role, fullname, phone, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", 
            ("delivery", "user123", "staff", "Delivery Agent", "8918740325", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1))
  conn.commit()

# =========================================================
# HTML/PDF REPORT GENERATOR HELPER
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
          .print-btn {{ display: block; width: 220px; margin: 20px auto; padding: 12px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: bold; cursor: pointer; text-align: center; box-shadow: 0 4px 10px rgba(37,99,235,0.3); }}
          .print-btn:hover {{ background: #1d4ed8; }}
          @media print {{
              .print-btn {{ display: none; }}
              body {{ background: white; margin: 0; }}
              table {{ box-shadow: none; }}
          }}
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
    st.markdown(f"""
    <script>
        localStorage.setItem('ps_mediseller_user', '{login_user}');
    </script>
    """, unsafe_allow_html=True)
elif saved_user_js and st.session_state.get("username") == "delivery":
    target_login = saved_user_js

if target_login:
    c.execute("SELECT fullname, role FROM users WHERE username=?", (target_login,))
    user_row = c.fetchone()
    if user_row:
        f_name, r_role = user_row
        st.session_state["username"] = target_login
        st.session_state["user_role"] = r_role
        if login_user:
            st.success(f"Welcome, {f_name}! Logged in. (স্বাগত, {f_name}!)")
            st.query_params.pop("login", None)
            st.rerun()

col_ht1, col_ht2 = st.columns([3, 1])
with col_ht1:
  st.markdown(f"""
  <div style="display: flex; align-items: center; gap: 12px;">
      <img src="data:image/jpeg;base64,{logo_b64}" style="width: 52px; height: 52px; border-radius: 10px; object-fit: cover; border: 1px solid rgba(255,255,255,0.2); box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
      <div>
          <h1 style="margin: 0; font-size: 19px !important; background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; line-height: 1.2;">P. S MEDISELLER</h1>
          <p style="margin: 2px 0 0 0; color: #cbd5e1 !important; font-size: 11px; font-weight: 500;">Allopathy & Ayurvedic Wholesaler | Ph: 8918740325</p>
      </div>
  </div>
  """, unsafe_allow_html=True)
with col_ht2:
  if st.session_state["user_role"] == "admin":
    if st.button("🚪 Logout (লগআউট)", key="logout_btn_top"):
      st.session_state["username"] = "delivery"
      st.session_state["user_role"] = "staff"
      st.markdown("""
      <script>
          localStorage.removeItem('ps_mediseller_user');
      </script>
      """, unsafe_allow_html=True)
      st.rerun()
  else:
    if st.button("🔐 Admin Login (এডমিন)", key="login_btn_top"):
      st.session_state["show_admin_login"] = True
      st.rerun()

c.execute("SELECT fullname FROM users WHERE username=?", (st.session_state['username'],))
curr_user_row = c.fetchone() 
current_fullname = curr_user_row[0] if curr_user_row and curr_user_row[0] else st.session_state['username']
st.write(f"👤 User: **{current_fullname}** (`{st.session_state['user_role']}`)")

if st.session_state.get("show_admin_login", False):
  with st.form("admin_login_popup_form"):
    st.write("#### 🔑 Admin Login (এডমিন লগইন)")
    admin_pass_input = st.text_input("Enter Admin Password (পাসওয়ার্ড দিন)", type="password")
    col_al1, col_al2 = st.columns(2)
    with col_al1:
      submit_admin = st.form_submit_button("Login (লগইন)", type="primary")
    with col_al2:
      cancel_admin = st.form_submit_button("Cancel (বাতিল)")
    if submit_admin:
      c.execute("SELECT password, role FROM users WHERE username='admin'")
      adm_row = c.fetchone()
      if adm_row and adm_row[0] == admin_pass_input:
        st.session_state["username"] = "admin"
        st.session_state["user_role"] = "admin"
        st.session_state["show_admin_login"] = False
        st.success("Admin login successful! (সফল!)")
        st.rerun()
      else:
        st.error("Incorrect Password! (ভুল পাসওয়ার্ড!)")
    if cancel_admin:
      st.session_state["show_admin_login"] = False
      st.rerun()

st.write("---")

loc = get_geolocation(component_key="hidden_background_gps_tracker")
gps_lat, gps_lon = None, None
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
selected_menu = st.radio("Select Menu (মেনু সিলেক্ট):", menu_options, index=default_index, horizontal=False, label_visibility="collapsed")
if selected_menu != current_page_param:
  st.query_params["page"] = selected_menu
  st.rerun()

st.write("---")

# =========================================================
# 1. ADD NEW LOCATION & ORDER / VISIT ENTRY
# =========================================================
if selected_menu == "📍 Add Location (লোকেশন যোগ)":
  st.write("### 📍 Add Location & Party (লোকেশন ও পার্টি)")
  selected_entry_tab = st.radio("Select Entry Mode (মড সিলেক্ট):", ["🏠 With Map Party (ম্যাপ সহ পার্টি)", "⚕️ Without Map Party (ম্যাপ ছাড়া পার্টি)"], label_visibility="collapsed")
  
  if "With Map Party" in selected_entry_tab:
    with st.form("location_details_form", clear_on_submit=True):
      st.write("#### 1. Enter Party Details (পার্টির বিবরণ)")
      col_f1, col_f2, col_f3 = st.columns(3)
      with col_f1: p_name = st.text_input("Party Name (পার্টির নাম)")
      with col_f2: p_addr = st.text_input("Address (ঠিকানা)")
      with col_f3: p_phone = st.text_input("Phone Number (ফোন নম্বর)")
      submitted_loc = st.form_submit_button("💾 Save Location (সেভ করুন)", type="primary")
    if submitted_loc:
      if p_name.strip() and p_phone.strip():
        c.execute("SELECT id FROM locations WHERE LOWER(party_name) = LOWER(?) OR party_phone = ?", (p_name.strip(), p_phone.strip()))
        if c.fetchone():
          st.error("Party name or phone already exists! (ইতিমধ্যে সেভ করা আছে!)")
        else:
          c.execute("INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, ?, ?)", (p_name.strip(), p_addr, p_phone.strip(), st.session_state["selected_lat"], st.session_state["selected_lon"]))
          c.execute("INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)", (p_name.strip(), "Visit (ভিজিট)", get_ist_time().strftime("%Y-%m-%d")))
          conn.commit()
          st.success("Location saved successfully! (সেভ হয়েছে!)")
          st.rerun()
      else:
        st.error("Party name and phone required. (নাম ও ফোন আবশ্যক।)")
  else:
    with st.form("doctor_details_form", clear_on_submit=True):
      st.write("#### 2. Without Map Party Details (ম্যাপ ছাড়া পার্টির বিবরণ)")
      col_d1, col_d2, col_d3 = st.columns(3)
      with col_d1: doc_name = st.text_input("Name (নাম)")
      with col_d2: doc_addr = st.text_input("Address (ঠিকানা/চেম্বার)")
      with col_d3: doc_phone = st.text_input("Phone (ফোন নম্বর)")
      submitted_doc = st.form_submit_button("💾 Save Without Map Party (সেভ করুন)", type="primary")
    if submitted_doc:
      if doc_name.strip() and doc_phone.strip():
        c.execute("SELECT id FROM locations WHERE LOWER(party_name) = LOWER(?) OR party_phone = ?", (doc_name.strip(), doc_phone.strip()))
        if c.fetchone():
          st.error("Party name or phone already exists! (ইতিমধ্যে সেভ করা আছে!)")
        else:
          c.execute("INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, NULL, NULL)", (doc_name.strip(), doc_addr, doc_phone.strip()))
          c.execute("INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)", (doc_name.strip(), "Visit (ভিজিট)", get_ist_time().strftime("%Y-%m-%d")))
          conn.commit()
          st.success("Saved successfully! (সফলভাবে সেভ হয়েছে!)")
          st.rerun()
      else:
        st.error("Name and phone required. (নাম ও ফোন আবশ্যক।)")

# =========================================================
# 2. SEARCH & DETAILS
# =========================================================
elif selected_menu == "🔍 Search & Details (অনুসন্ধান ও বিবরণ)":
  st.write("### 🔍 Search & Party Management (সার্চ ও ম্যানেজমেন্ট)")
  master_search_query = st.text_input("Search", placeholder="Type name, address or keyword...", label_visibility="collapsed")
  if master_search_query.strip():
    q_term = f"%{master_search_query.strip()}%"
    df = pd.read_sql_query("SELECT * FROM locations WHERE party_name LIKE ? OR address LIKE ? OR party_phone LIKE ? ORDER BY party_name ASC", conn, params=(q_term, q_term, q_term))
  else:
    df = pd.read_sql_query("SELECT * FROM locations ORDER BY party_name ASC", conn)
  st.dataframe(df, use_container_width=True)

# =========================================================
# 3. PENDING ORDERS & ORDER HISTORY
# =========================================================
elif selected_menu == "📦 Pending Orders (বাকি অর্ডার)":
  st.write("### 📦 Orders Management (অর্ডার ম্যানেজমেন্ট)")
  order_tab_p, order_tab_h = st.tabs(["⏳ Pending Orders (পেন্ডিং অর্ডার)", "📜 Order History & Details (অর্ডার ইতিহাস ও বিবরণ)"])
  
  with order_tab_p:
    orders_df = pd.read_sql_query("SELECT * FROM orders WHERE status='Pending' ORDER BY order_date DESC", conn)
    if not orders_df.empty:
      for index, row in orders_df.iterrows():
        cols = st.columns([2, 4, 2, 2])
        cols[0].write(f"**{row['party_name']}**")
        cols[1].write(row['order_details'])
        cols[2].write("⏳ Pending")
        if cols[3].button("✔️ Complete", key=f"ord_btn_{row['id']}"):
          c.execute("UPDATE orders SET status='Completed' WHERE id=?", (row['id'],))
          conn.commit()
          st.success("Order completed!")
          st.rerun()
        if st.session_state["user_role"] == "admin":
          if st.button("🗑️ Delete Order", key=f"del_ord_{row['id']}"):
            c.execute("DELETE FROM orders WHERE id=?", (row['id'],))
            conn.commit()
            st.success("Order deleted successfully!")
            st.rerun()
        st.write("---")
    else:
      st.info("No pending orders.")

  with order_tab_h:
    st.write("#### 📜 All Orders & Old History (সমস্ত অর্ডার এবং পুরোনো ইতিহাস)")
    all_orders_df = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    if not all_orders_df.empty:
      for index, row in all_orders_df.iterrows():
        st.write(f"ID: `{row['id']}` | Party: **{row['party_name']}** | Date: `{row['order_date']}` | Status: `{row['status']}`")
        st.write(f"Details: {row['order_details']}")
        if st.session_state["user_role"] == "admin":
          col_dh1, col_dh2 = st.columns([1, 4])
          with col_dh1:
            if st.button("🗑️ Delete History Entry", key=f"del_all_ord_{row['id']}"):
              c.execute("DELETE FROM orders WHERE id=?", (row['id'],))
              conn.commit()
              st.success("Order history entry deleted!")
              st.rerun()
        st.write("---")
      if st.session_state["user_role"] == "admin":
        if st.button("🗑️ Clear All Order History (সমস্ত অর্ডার হিস্ট্রি মুছুন)", type="secondary"):
          c.execute("DELETE FROM orders")
          conn.commit()
          st.success("All order history cleared!")
          st.rerun()
    else:
      st.info("No order history found.")

# =========================================================
# 4. DAILY & MONTHLY WORK
# =========================================================
elif selected_menu == "📋 Daily & Monthly Work (দৈনিক ও মাসিক কাজ)":
  st.write("### 📋 Daily & Monthly Work Report (দৈনিক ও মাসিক কাজের রিপোর্ট)")
  work_df = pd.read_sql_query("SELECT * FROM daily_work ORDER BY work_date DESC, id DESC", conn)
  if not work_df.empty:
    for index, row in work_df.iterrows():
      st.write(f"📌 **{row['party_name']}** — Activity: `{row['activity_type']}` | Date: `{row['work_date']}`")
      if st.session_state["user_role"] == "admin":
        if st.button("🗑️ Delete Work Entry", key=f"del_work_{row['id']}"):
          c.execute("DELETE FROM daily_work WHERE id=?", (row['id'],))
          conn.commit()
          st.success("Work entry deleted!")
          st.rerun()
      st.write("---")
    if st.session_state["user_role"] == "admin":
      if st.button("🗑️ Clear All Work History (সমস্ত কাজের হিস্ট্রি মুছুন)", type="secondary"):
        c.execute("DELETE FROM daily_work")
        conn.commit()
        st.success("All daily/monthly work history cleared!")
        st.rerun()
  else:
    st.info("No work history records found.")

# =========================================================
# 5. DUE & DELIVERY
# =========================================================
elif selected_menu == "📋 Due & Delivery (বকেয়া ও ডেলিভারি)":
  st.markdown('<div class="main-title">📋 ডেলিভারি ও ডিউ প্ল্যান (কর্মী সহায়ক মোড)</div>', unsafe_allow_html=True)
  
  c.execute("SELECT username, fullname FROM users")
  users_data = c.fetchall()
  all_agents = [r[0] for r in users_data]
  agent_name_map = {r[0]: (r[1] if r[1] else r[0]) for r in users_data}
  c.execute("SELECT party_name, lat, lon FROM locations ORDER BY party_name ASC")
  loc_data = c.fetchall()
  all_parties = [r[0] for r in loc_data]
  
  task_tab1, task_tab2, task_tab3 = st.tabs([
      "🎯 Active Tasks (চলমান কাজ)", 
      "📊 Agent Date-wise Summary (এজেন্ট ও তারিখ অনুযায়ী সামারি)",
      "📜 Completed Tasks History (সম্পন্ন কাজ)"
  ])
  
  with task_tab1:
    if st.session_state["user_role"] == "admin":
      with st.expander("➕ Assign New Task (নতুন কাজ দিন)", expanded=False):
        st.write("🔍 **Search & Select Party (পার্টি সার্চ ও সিলেক্ট করুন):**")
        task_search_text = st.text_input("Search Party for Task", placeholder="Type name, address or keyword...", key="task_party_search_text_input", label_visibility="collapsed")
        
        if task_search_text.strip():
          q_term = f"%{task_search_text.strip()}%"
          c.execute("SELECT party_name FROM locations WHERE party_name LIKE ? OR address LIKE ? OR party_phone LIKE ? ORDER BY party_name ASC", (q_term, q_term, q_term))
          filtered_task_parties = [r[0] for r in c.fetchall()]
        else:
          filtered_task_parties = all_parties
          
        if task_search_text.strip() and filtered_task_parties:
          sel_pt = st.radio("Matching Task Parties", filtered_task_parties[:10], key="task_floating_suggestions_radio", label_visibility="collapsed")    
        else:
          sel_pt = st.selectbox("Select Party", filtered_task_parties, label_visibility="collapsed", key="task_select_party_box") if filtered_task_parties else ""
            
        with st.form("easy_assign_form"):
          sel_ag = st.selectbox("Select Agent (এজেন্ট সিলেক্ট)", all_agents, format_func=lambda x: agent_name_map.get(x, x))
          col_chk1, col_chk2 = st.columns(2)
          with col_chk1: chk_delivery = st.checkbox("🚚 Delivery (ডেলিভারি)")
          with col_chk2: chk_due = st.checkbox("💰 Due Collection (ডিউ কালেকশন)")
          d_amount = st.text_input("Due Amount (ডিউ টাকা)", "0")
          submit_easy_task = st.form_submit_button("🎯 Add Task (কাজ যোগ)", type="primary")
          if submit_easy_task:
            if not sel_pt.strip():
              st.error("Please select a party. (পার্টি সিলেক্ট করুন।)")
            else:
              selected_tasks = []
              if chk_delivery: selected_tasks.append("Delivery (ডেলিভারি)")
              if chk_due: selected_tasks.append("Due Collection (ডিউ কালেকশন)")
              if selected_tasks:
                t_type_str = " & ".join(selected_tasks)
                c.execute("INSERT INTO task_assignments (agent_name, party_name, task_type, due_amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?)", (sel_ag, sel_pt.strip(), t_type_str, d_amount, "Pending", get_ist_time().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                st.success("Task assigned successfully! (কাজ দেওয়া হয়েছে!)")
                st.rerun()
              else:
                st.error("Please select at least one task type.")
                
    st.write("---")
    st.markdown("### 📋 Current Tasks Grouped by Worker (কর্মী অনুযায়ী বর্তমান কাজ)")
    
    c.execute("""
        SELECT t.id, t.agent_name, t.party_name, t.task_type, t.due_amount, t.created_at, l.address, l.lat, l.lon 
        FROM task_assignments t 
        LEFT JOIN locations l ON t.party_name = l.party_name 
        WHERE t.status='Pending' 
        ORDER BY t.id DESC
    """)
    pending_tasks = c.fetchall()
    
    if pending_tasks:
      tasks_by_agent = {}
      for row in pending_tasks:
        ag = row[1]
        if ag not in tasks_by_agent:
          tasks_by_agent[ag] = []
        tasks_by_agent[ag].append(row)
        
      for ag_username, ag_tasks in tasks_by_agent.items():
        ag_fullname = agent_name_map.get(ag_username, ag_username)
        del_count = sum(1 for t in ag_tasks if "Delivery" in t[3])
        due_count = sum(1 for t in ag_tasks if "Due" in t[3])
        tot_due = sum(float(t[4]) for t in ag_tasks if t[4] and str(t[4]).replace('.','',1).isdigit())
        
        with st.expander(f"👤 {ag_fullname} | ডেলিভারি: {del_count} | লেকশন/ডিউ: {due_count} | মোট ডিউ: টাকা {tot_due}", expanded=False):
          for t_row in ag_tasks:
            t_id, _, party_name, task_type, due_amount, created_at, address, lat, lon = t_row
            
            st.markdown(f"📦 **{party_name}** — `{task_type}`")
            if address:
              st.write(f"📍 ঠিকানা: {address}")
            if due_amount and float(due_amount) > 0:
              st.write(f"💰 ডিউ পরিমাণ: ₹{due_amount}")
              
            c.execute("SELECT order_details, order_date FROM orders WHERE party_name=? ORDER BY id DESC LIMIT 3", (party_name,))
            party_orders = c.fetchall()
            if party_orders:
              with st.expander(f"🛒 অর্ডারের বিবরণ ({party_name})"):
                for ord_det, ord_dt in party_orders:
                  st.write(f"- `{ord_dt}`: {ord_det}")
                  
            if lat and lon:
              maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
              st.markdown(f'<a href="{maps_url}" target="_blank" style="text-decoration:none;"><button style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color:white; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; font-weight:600; margin-bottom:10px;">🧭 ডিরেকশন (Direction)</button></a>', unsafe_allow_html=True)
              
            with st.form(key=f"complete_task_form_{t_id}"):
              st.write("💵 **এন্ট্রি দিন (Entry Details):**")
              col_s1, col_s2 = st.columns(2)
              with col_s1:
                todays_sale = st.text_input("আজকের সেল টাকা (Today's Sale)", "0", key=f"sale_{t_id}")
              with col_s2:
                todays_collection = st.text_input("আজকের কালেকশন টাকা (Today's Collection)", "0", key=f"coll_{t_id}")
                
              col_btn1, col_btn2 = st.columns(2)
              with col_btn1:
                submitted_complete = st.form_submit_button("✅ কাজ সম্পন্ন (Complete)", type="primary")
              with col_btn2:
                if st.session_state["user_role"] == "admin":
                  submitted_delete = st.form_submit_button("🗑️ Delete Task", type="secondary")
                else:
                  submitted_delete = False
                  
              if submitted_complete:
                c.execute("UPDATE task_assignments SET status='Completed' WHERE id=?", (t_id,))
                c.execute("UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?", (ag_username,))
                conn.commit()
                st.success(f"Task for {party_name} completed! Sale: ₹{todays_sale}, Collection: ₹{todays_collection}")
                st.rerun()
                
              if submitted_delete and st.session_state["user_role"] == "admin":
                c.execute("DELETE FROM task_assignments WHERE id=?", (t_id,))
                conn.commit()
                st.success("Task deleted successfully!")
                st.rerun()
            st.write("---")
    else:
      st.info("কোনো পেন্ডিং কাজ নেই (No pending tasks).")

  with task_tab2:
    st.write("#### 📊 Agent Summary")
    st.info("Summary view.")

  with task_tab3:
    st.write("#### 📜 Completed Tasks History")
    completed_tasks = pd.read_sql_query("SELECT * FROM task_assignments WHERE status='Completed' ORDER BY id DESC", conn)
    if not completed_tasks.empty:
      for index, row in completed_tasks.iterrows():
        st.markdown(f"✅ ID: `{row['id']}` | Party: **{row['party_name']}** | Agent: `{row['agent_name']}` | Task: `{row['task_type']}` | Due: ₹{row['due_amount']} | Date: `{row['created_at']}`")
        if st.session_state["user_role"] == "admin":
          if st.button("🗑️ Delete Completed Task Record", key=f"del_comp_task_{row['id']}"):
            c.execute("DELETE FROM task_assignments WHERE id=?", (row['id'],))
            conn.commit()
            st.success("Completed task record deleted!")
            st.rerun()
        st.write("---")
      if st.session_state["user_role"] == "admin":
        if st.button("🗑️ Clear All Completed Tasks History", type="secondary"):
          c.execute("DELETE FROM task_assignments WHERE status='Completed'")
          conn.commit()
          st.success("All completed tasks history cleared!")
          st.rerun()
    else:
      st.info("No completed tasks history.")

# =========================================================
# 6. ROUTE MAP & ATTENDANCE
# =========================================================
elif selected_menu == "🗺️ Route Map (রুট ম্যাপ)":
  st.write("### 🗺️ Route Map")

elif selected_menu == "📅 Attendance (উপস্থিতি)":
  st.write("### 📅 Attendance")

elif selected_menu == "📊 Live Tracking (লাইভ ট্র্যাকিং)" and st.session_state["user_role"] == "admin":
  st.write("### 📊 Live Tracking")

elif selected_menu == "⚙️ Settings & Agents (সেটিংস)" and st.session_state["user_role"] == "admin":
  st.write("### ⚙️ Settings")
