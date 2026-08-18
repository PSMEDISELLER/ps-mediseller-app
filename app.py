
Himadri Dhali <dhalihimadri1998@gmail.com>
18:23 (6 minutes ago)
to Himadri

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
# IST TIME & DATE FORMAT HELPERS
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
    ] }};
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
            const overlay = document.getElementById('loc-overlay');
            if (overlay) overlay.style.display = 'flex';            
            const status = document.getElementById('loc-status');
            if (status) {
                status.style.display = 'block';
                if (error.code === error.PERMISSION_DENIED) {
                    status.innerText = "⚠️ Location permission denied! Please enable it in browser & phone settings. (লোকেশন পারমিশন দিন)";
                } else {
                    status.innerText = "⚠️ Please enable location to continue. (লোকেশন অন করুন)";
                }
            }
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
}
function requestLocation() {
    checkAndRequestLocation();
}
window.addEventListener('load', function() {
    setTimeout(checkAndRequestLocation, 300);
});
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
""", unsafe_allow_html=True)

# =========================================================
# DATABASE SETUP & CLEANUP
# =========================================================
DB_FILE = "mediseller_delivery.db"
def get_db_connection(): return sqlite3.connect(DB_FILE, check_same_thread=False)
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
          table {{ width: 100%; border-collapse: collapse; margin-top: 15px; background: white; border-radius: 8px; overflow: hidden; }}
          th, td {{ border: 1px solid #e2e8f0; padding: 12px 15px; text-align: left; font-size: 13px; }}
          th {{ background-color: #3b82f6; color: white; font-weight: 600; }}
          .print-btn {{ display: block; width: 220px; margin: 20px auto; padding: 12px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: bold; cursor: pointer; text-align: center; }}
      </style>
  </head>
  <body>
      <div class="header">
          <h2>P. S MEDISELLER</h2>
          <p><b>Allopathy & Ayurvedic Wholesaler</b> | Address: Ledagama 1, Amlagora, Garhbeta, Paschim Medinipur</p>
          <p><b>{title}</b></p>
          <p>Generated on: {get_ist_time().strftime('%d.%m.%y %H:%M:%S')} IST</p>
      </div>
      <button class="print-btn" onclick="window.print()">Print / Save as PDF (প্রিন্ট / পিডিএফ)</button>
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

if login_user:
    c.execute("SELECT fullname, role FROM users WHERE username=?", (login_user,))
    user_row = c.fetchone()
    if user_row:
        f_name, r_role = user_row
        st.session_state["username"] = login_user
        st.session_state["user_role"] = r_role

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
    "📋 Due & Delivery (বকেয়া ও ডেলিভারি)",
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
  selected_entry_tab = st.radio(
      "Select Entry Mode (মোড সিলেক্ট):",
      ["🏠 With Map Party (ম্যাপ সহ পার্টি)", "🩺 Without Map Party (ম্যাপ ছাড়া পার্টি)"],
      label_visibility="collapsed"
  )
  st.write("")
  if "With Map Party" in selected_entry_tab:
    with st.form("location_details_form", clear_on_submit=True):
      st.write("#### 1. Enter Party Details (পার্টির বিবরণ)")
      col_f1, col_f2, col_f3 = st.columns(3)
      with col_f1:
        p_name = st.text_input("Party Name (পার্টির নাম)", key="input_p_name")
      with col_f2:
        p_addr = st.text_input("Address (ঠিকানা)", key="input_p_addr")
      with col_f3:
        p_phone = st.text_input("Phone Number (ফোন নম্বর)", key="input_p_phone")
      submitted_loc = st.form_submit_button("💾 Save Location (সেভ করুন)", type="primary")
    if submitted_loc:
      if p_name.strip() and p_phone.strip():
        c.execute("SELECT id FROM locations WHERE LOWER(party_name) = LOWER(?) OR party_phone = ?", (p_name.strip(), p_phone.strip()))
        if c.fetchone():
          st.error("Party name or phone already exists! (ইতিমধ্যে সেভ করা আছে!)")
        else:
          try:
            current_date_str = get_ist_time().strftime("%Y-%m-%d")
            c.execute(
                "INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, ?, ?)",
                (p_name.strip(), p_addr, p_phone.strip(), st.session_state["selected_lat"], st.session_state["selected_lon"]),
            )
            c.execute(
                "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
                (p_name.strip(), "Visit (ভিজিট)", current_date_str)
            )
            conn.commit()
            st.success("Location saved and visit recorded successfully! (সেভ হয়েছে!)")
            st.rerun()
          except sqlite3.IntegrityError:
            st.error("Party already exists! (ইতিমধ্যে আছে!)")
      else:
        st.error("Party name and phone required. (নাম ও ফোন আবশ্যক।)")
  else:
    with st.form("doctor_details_form", clear_on_submit=True):
      st.write("#### 2. Without Map Party Details (ম্যাপ ছাড়া পার্টির বিবরণ)")
      col_d1, col_d2, col_d3 = st.columns(3)
      with col_d1:
        doc_name = st.text_input("Name (নাম)", key="input_doc_name")
      with col_d2:
        doc_addr = st.text_input("Address (ঠিকানা/চেম্বার)", key="input_doc_addr")
      with col_d3:
        doc_phone = st.text_input("Phone (ফোন নম্বর)", key="input_doc_phone")
      submitted_doc = st.form_submit_button("💾 Save Without Map Party (সেভ করুন)", type="primary")
    if submitted_doc:
      if doc_name.strip() and doc_phone.strip():
        c.execute("SELECT id FROM locations WHERE LOWER(party_name) = LOWER(?) OR party_phone = ?", (doc_name.strip(), doc_phone.strip()))
        if c.fetchone():
          st.error("Party name or phone already exists! (ইতিমধ্যে সেভ করা আছে!)")
        else:
          try:
            c.execute(
                "INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, NULL, NULL)",
                (doc_name.strip(), doc_addr, doc_phone.strip()),
            )
            c.execute(
                "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
                (doc_name.strip(), "Visit (ভিজিট)", get_ist_time().strftime("%Y-%m-%d"))
            )
            conn.commit()
            st.success("Saved successfully! (সফলভাবে সেভ হয়েছে!)")
            st.rerun()
          except sqlite3.IntegrityError:
            st.error("Party already exists! (ইতিমধ্যে আছে!)")
      else:
        st.error("Name and phone required. (নাম ও ফোন আবশ্যক।)")

  st.write("---")
  st.write("#### Select Location from Map (ম্যাপ থেকে সিলেক্ট করুন)")
  col_m1, col_m2 = st.columns([1, 4])
  with col_m1:
    if st.button("📍 Current Loc (কারেন্ট লোকেশন)"):
      if gps_lat and gps_lon:
        st.session_state["selected_lat"] = gps_lat
        st.session_state["selected_lon"] = gps_lon
        st.success("GPS location taken! (নেওয়া হয়েছে!)")
        st.rerun()
      else:
        st.warning("GPS not found! (নেই!)")
  with col_m2:
    st.write(f"Coordinates (স্থানাঙ্ক): `{st.session_state['selected_lat']:.5f}, {st.session_state['selected_lon']:.5f}`")

  advanced_map = folium.Map(
      location=[st.session_state["selected_lat"], st.session_state["selected_lon"]],
      zoom_start=17,
      tiles=None
  )
  folium.TileLayer(
      tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
      attr="Google Maps Street",
      name="Street View (স্ট্রিট ভিউ)",
      show=True
  ).add_to(advanced_map)
  folium.TileLayer(
      tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
      attr="Google Maps Satellite",
      name="Satellite View (স্যাটেলাইট ভিউ)",
      show=False
  ).add_to(advanced_map)
  folium.Marker(
      [st.session_state["selected_lat"], st.session_state["selected_lon"]],
      popup="<b>Selected Point (নির্বাচিত পয়েন্ট)</b>",
      icon=folium.Icon(color="red", icon="map-marker", prefix="fa"),
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
  st.write("### 📦 Orders & Visits (অর্ডার ও ভিজিট)")
  order_search_text = st.text_input("Search Party", placeholder="Type name, address...", key="order_party_search_text_input", label_visibility="collapsed")
  if order_search_text.strip():
    q_term = f"%{order_search_text.strip()}%"
    c.execute("SELECT party_name FROM locations WHERE party_name LIKE ? OR address LIKE ? OR party_phone LIKE ? ORDER BY party_name ASC", (q_term, q_term, q_term))
    filtered_parties_list = [r[0] for r in c.fetchall()]
  else:
    c.execute("SELECT party_name FROM locations ORDER BY party_name ASC")
    filtered_parties_list = [r[0] for r in c.fetchall()]

  if order_search_text.strip() and filtered_parties_list:
    selected_order_party_native = st.radio("Matching Parties", filtered_parties_list[:10], key="order_floating_suggestions_radio", label_visibility="collapsed")
  else:
    selected_order_party_native = st.selectbox("Select Party", filtered_parties_list, label_visibility="collapsed", key="order_select_party_box") if filtered_parties_list else ""

  with st.form("order_visit_entry_form"):
    ord_details = st.text_area("Order Details (অর্ডার বিবরণ)")
    col_ob1, col_ob2 = st.columns(2)
    with col_ob1:
      submitted_order = st.form_submit_button("🛒 Submit Order (অর্ডার জমা)", type="primary")
    with col_ob2:
      submitted_visit = st.form_submit_button("📍 Save Visit (ভিজিট সেভ)")
    if submitted_order:
      if selected_order_party_native.strip():
        current_date_str = get_ist_time().strftime("%Y-%m-%d")
        c.execute("INSERT INTO orders (party_name, order_details, order_date, status, payment_collected) VALUES (?, ?, ?, ?, ?)", (selected_order_party_native.strip(), ord_details.strip(), get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), "Pending", "0"))
        c.execute("INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)", (selected_order_party_native.strip(), "Order (অর্ডার)", current_date_str))
        conn.commit()
        st.success("Order submitted successfully! (জমা দেওয়া হয়েছে!)")
        st.rerun()
    if submitted_visit:
      if selected_order_party_native.strip():
        c.execute("INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)", (selected_order_party_native.strip(), "Visit (ভিজিট)", get_ist_time().strftime("%Y-%m-%d")))
        conn.commit()
        st.success("Visit saved successfully! (সেভ হয়েছে!)")
        st.rerun()

# =========================================================
# 2. SEARCH PARTY DETAILS & ADMIN DELETE OPTION
# =========================================================
elif selected_menu == "🔍 Search & Details (অনুসন্ধান ও বিবরণ)":
  st.write("### 🔍 Search & Party Management (সার্চ ও ম্যানেজমেন্ট)")
  if st.session_state.get("mapping_party_id"):
    st.markdown(f"### 📍 Set Map for **{st.session_state['mapping_party_name']}**")
    if "temp_map_lat" not in st.session_state:
      st.session_state["temp_map_lat"] = 22.8620
    if "temp_map_lon" not in st.session_state:
      st.session_state["temp_map_lon"] = 87.3320
    
    pick_map = folium.Map(location=[st.session_state["temp_map_lat"], st.session_state["temp_map_lon"]], zoom_start=17, tiles=None)
    folium.TileLayer(tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps", name="Street").add_to(pick_map)
    folium.Marker([st.session_state["temp_map_lat"], st.session_state["temp_map_lon"]], icon=folium.Icon(color="red", icon="map-marker", prefix="fa")).add_to(pick_map)
    p_map_data = st_folium(pick_map, width="100%", height=400, key="party_location_picker_map")
    
    if p_map_data and p_map_data.get("last_clicked"):
      st.session_state["temp_map_lat"] = p_map_data["last_clicked"]["lat"]
      st.session_state["temp_map_lon"] = p_map_data["last_clicked"]["lng"]
      st.rerun()
      
    col_b1, col_b2 = st.columns(2)
    with col_b1:
      if st.button("✅ Save Location (সেভ করুন)", type="primary"):
        c.execute("UPDATE locations SET lat=?, lon=? WHERE id=?", (st.session_state["temp_map_lat"], st.session_state["temp_map_lon"], st.session_state["mapping_party_id"]))
        conn.commit()
        st.session_state.pop("mapping_party_id", None)
        st.rerun()
    with col_b2:
      if st.button("❌ Cancel (বাতিল)"):
        st.session_state.pop("mapping_party_id", None)
        st.rerun()
    st.stop()

  master_search_query = st.text_input("Search", placeholder="Type name...", key="master_search_input_box", label_visibility="collapsed")
  if master_search_query.strip():
    q_term = f"%{master_search_query.strip()}%"
    df = pd.read_sql_query("SELECT * FROM locations WHERE party_name LIKE ? OR address LIKE ? OR party_phone LIKE ? ORDER BY party_name ASC", conn, params=(q_term, q_term, q_term))
  else:
    df = pd.read_sql_query("SELECT * FROM locations ORDER BY party_name ASC", conn)

  doc_df = df[df["lat"].isna() | df["lon"].isna()]
  mapped_df = df[df["lat"].notna() & df["lon"].notna()]
  
  with st.expander(f"🩺 Non-Map List ({len(doc_df)})", expanded=True):
    for index, row in doc_df.iterrows():
      cols = st.columns([3, 2, 2, 2, 1.5])
      cols[0].write(f"**{row['party_name']}**")
      cols[1].write(row['party_phone'] or "-")
      cols[2].write(row['address'] or "-")
      if cols[3].button("📍 Add Map", key=f"map_add_{row['id']}"):
        st.session_state["mapping_party_id"] = row['id']
        st.session_state["mapping_party_name"] = row['party_name']
        st.rerun()
      if st.session_state["user_role"] == "admin":
        if cols[4].button("Delete", key=f"del_doc_{row['id']}"):
          c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
          conn.commit()
          st.rerun()

  with st.expander(f"📍 Mapped List ({len(mapped_df)})", expanded=True):
    for index, row in mapped_df.iterrows():
      cols = st.columns([3, 2, 2, 2, 1.5] if st.session_state["user_role"] == "admin" else [3, 2, 2, 2])
      cols[0].write(f"**{row['party_name']}**")
      cols[1].write(row['party_phone'] or "-")
      cols[2].write(row['address'] or "-")
      maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}"
      cols[3].markdown(f'<a href="{maps_url}" target="_blank"><button style="background:#3b82f6;color:white;border:none;padding:6px 12px;border-radius:6px;">🧭 Direction</button></a>', unsafe_allow_html=True)
      if st.session_state["user_role"] == "admin":
        if cols[4].button("Delete", key=f"del_loc_{row['id']}"):
          c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
          conn.commit()
          st.rerun()

# =========================================================
# 3. PENDING ORDERS
# =========================================================
elif selected_menu == "📦 Pending Orders (বাকি অর্ডার)":
  st.write("### 📦 Orders Management (অর্ডার ম্যানেজমেন্ট)")
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
        st.success("Completed!")
        st.rerun()
  else:
    st.info("No pending orders.")

# =========================================================
# 4. DAILY & MONTHLY WORK
# =========================================================
elif selected_menu == "📋 Daily & Monthly Work (দৈনিক ও মাসিক কাজ)":
  st.write("### 📋 Daily & Monthly Work Report")
  work_df = pd.read_sql_query("SELECT * FROM daily_work ORDER BY work_date DESC, id DESC LIMIT 50", conn)
  if not work_df.empty:
    st.dataframe(work_df, use_container_width=True)
  else:
    st.info("No records found.")

# =========================================================
# 5. DUE & DELIVERY
# =========================================================
elif selected_menu == "📋 Due & Delivery (বকেয়া ও ডেলিভারি)":
  st.write("### 🚚 Delivery & Due Plan")
  c.execute("SELECT username, fullname FROM users")
  users_data = c.fetchall()
  all_agents = [r[0] for r in users_data]
  agent_name_map = {r[0]: (r[1] or r[0]) for r in users_data}
  
  c.execute("SELECT party_name FROM locations ORDER BY party_name ASC")
  all_parties = [r[0] for r in c.fetchall()]

  with st.form("assign_task_form"):
    st.write("#### ➕ Assign New Task")
    col_as1, col_as2 = st.columns(2)
    with col_as1:
      assigned_agent = st.selectbox("Agent", all_agents, format_func=lambda x: agent_name_map.get(x, x))
    with col_as2:
      selected_task_party = st.selectbox("Party", all_parties)
    
    task_type_sel = st.selectbox("Task Type", ["Delivery & Due Collection", "Only Delivery", "Only Due Collection"])
    due_amt_input = st.text_input("Due Amount (₹)", "0")
    
    if st.form_submit_button("🚀 Assign Task", type="primary"):
      c.execute("INSERT INTO task_assignments (agent_name, party_name, task_type, due_amount, status, created_at) VALUES (?, ?, ?, ?, 'Pending', ?)", 
                (assigned_agent, selected_task_party, task_type_sel, due_amt_input, get_ist_time().strftime("%Y-%m-%d %H:%M:%S")))
      conn.commit()
      st.success("Assigned successfully!")
      st.rerun()

  tasks_df = pd.read_sql_query("SELECT * FROM task_assignments WHERE status='Pending' ORDER BY id DESC", conn)
  if not tasks_df.empty:
    for idx, t_row in tasks_df.iterrows():
      st.markdown(f"""
      <div class="card">
          <div class="party-title">📍 {t_row['party_name']}</div>
          <div class="card-text"><b>Agent:</b> {agent_name_map.get(t_row['agent_name'], t_row['agent_name'])}</div>
          <div class="card-text"><b>Task:</b> {t_row['task_type']} | <b>Due:</b> ₹{t_row['due_amount']}</div>
      </div>
      """, unsafe_allow_html=True)

# =========================================================
# 6. ATTENDANCE
# =========================================================
elif selected_menu == "📅 Attendance (উপস্থিতি)":
  st.write("### 📅 Daily Attendance")
  if st.button("✋ Mark Present", type="primary"):
    try:
      c.execute("INSERT INTO attendance (username, date, check_time, status) VALUES (?, ?, ?, 'Present')", 
                (st.session_state["username"], get_ist_time().strftime("%Y-%m-%d"), get_ist_time().strftime("%H:%M:%S")))
      conn.commit()
      st.success("Attendance marked!")
    except:
      st.warning("Already marked for today!")

# =========================================================
# 7. ADMIN TRACKING & SETTINGS
# =========================================================
elif selected_menu == "📊 Live Tracking (লাইভ ট্র্যাকিং)" and st.session_state["user_role"] == "admin":
  st.write("### 📊 Agent Live Tracking")
  tracking_df = pd.read_sql_query("SELECT l.username, u.fullname, l.lat, l.lon, l.last_updated FROM agent_live_locations l LEFT JOIN users u ON l.username = u.username", conn)
  if not tracking_df.empty:
    st.dataframe(tracking_df, use_container_width=True)

elif selected_menu == "⚙️ Settings & Agents (সেটিংস)" and st.session_state["user_role"] == "admin":
  st.write("### ⚙️ Agent Management")
  with st.form("create_agent_form"):
    name_input = st.text_input("Full Name")
    phone_input = st.text_input("Phone Number")
    submitted_agent = st.form_submit_button("Create Agent", type="primary")
    if submitted_agent:
      if name_input and phone_input:
        uname = f"agent_{phone_input}"
        c.execute("INSERT OR IGNORE INTO users (username, password, role, fullname, phone, created_at) VALUES (?, '1234', 'staff', ?, ?, ?)", 
                  (uname, name_input, phone_input, get_ist_time().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        
        # Fixed: Get precise active app URL dynamically using JavaScript
        base_url = streamlit_js_eval(js_expressions="window.location.href.split('?')[0]", key=f"url_{uname}", default="")
        if not base_url:
          base_url = "https://p-s-mediseller.streamlit.app"
        
        link = f"{base_url}?login={uname}"
        st.success("Agent created successfully! Share this login link:")
        st.code(link, language="text")
        st.markdown(f"🔗 [Click here to open login link]({link})")
