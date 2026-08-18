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
<script>
function checkAndRequestLocation() {
    if (!navigator.geolocation) {
        return;
    }
    navigator.geolocation.getCurrentPosition(
        function(position) {
            localStorage.setItem('ps_user_lat', position.coords.latitude);
            localStorage.setItem('ps_user_lon', position.coords.longitude);
        },
        function(error) {},
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
}
window.addEventListener('load', function() {
    setTimeout(checkAndRequestLocation, 500);
});
setInterval(checkAndRequestLocation, 15000);
</script>
"""
st.components.v1.html(mandatory_location_html, height=0)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
html, body, [class*="css"], p, span, label {
    font-family: 'Poppins', sans-serif;
    color: #ffffff !important;
}
body {
    background-color: #0f172a !important;
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
div[data-testid="stTextInput"] small,
div[data-testid="stTextArea"] small,
div[data-testid="stTextInput"] div p,
div[data-testid="stTextArea"] div p,
.stTextInput small,
.stTextArea small {
    background: rgba(37, 99, 235, 0.25) !important;
    color: #60a5fa !important;
    border: 1px solid #3b82f6 !important;
    padding: 6px 12px !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    display: inline-block !important;
    margin-top: 6px !important;
}
.stRadio > div {
    background: transparent !important;
    padding: 0px !important;
    border: none !important;
    box-shadow: none !important;
}
.stRadio div[role="radiogroup"] label {
    background: #1e293b !important;
    border: 1px solid rgba(129, 140, 248, 0.35) !important;
    border-radius: 12px !important;
    padding: 10px 14px !important;
    margin-bottom: 8px !important;    
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
    transition: all 0.3s ease !important;
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
}
.stRadio div[role="radiogroup"] label:hover {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%) !important;
    border-color: #60a5fa !important;
    box-shadow: 0 6px 18px rgba(59, 130, 246, 0.3) !important;
    transform: translateY(-2px);
}
.stRadio div[role="radiogroup"] label p {
    color: #ffffff !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    margin: 0 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
.stSuccess {
    background: rgba(16, 185, 129, 0.25) !important;
    border: 1px solid #10b981 !important;
    color: #34d399 !important;
    border-radius: 10px !important;
}
.stWarning {
    background: rgba(245, 158, 11, 0.25) !important;
    border: 1px solid #f59e0b !important;
    color: #fbbf24 !important;
    border-radius: 10px !important;
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
conn.commit()

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
# PURE STREAMLIT DIRECT LINK LOGIN (ZERO WHITE-SCREEN/CRASH)
# =========================================================
if "login" in st.query_params:
  login_target = st.query_params["login"]
  c.execute(
      "SELECT fullname, role FROM users WHERE username=?", (login_target,)
  )
  user_match = c.fetchone()
  if user_match:
    st.session_state["username"] = login_target
    st.session_state["user_role"] = user_match[1]
    st.toast(
        f"✅ Welcome, {user_match[0]}! Logged in successfully.", icon="🔓"
    )
  else:
    st.error("Invalid Login Link!")
  # Safe parameter cleanup without loop issues
  del st.query_params["login"]


# =========================================================
# PROFESSIONAL HTML REPORT GENERATOR HELPER
# =========================================================
def generate_html_report(title, df):
  html = f"""
  <!DOCTYPE html>
  <html>
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
          .print-btn {{ display: block; width: 220px; margin: 20px auto; padding: 12px; background: #2563eb; color: white; border: none;
border-radius: 8px; font-size: 15px; font-weight: bold; cursor: pointer; text-align: center; }}
          @media print {{
              .print-btn {{ display: none; }}
              body {{ background: white; margin: 0; }}
          }}
      </style>
  </head>
  <body>
      <div class="header">
          <h2>P. S MEDISELLER</h2>
          <p><b>Allopathy & Ayurvedic Wholesaler</b> | Address: Ledagama 1, Amlagora, Garhbeta, Paschim Medinipur</p>
          <p><b>{title}</b></p>
          <p>Generated on: {get_ist_time().strftime('%d.%m.%y %H:%M:%S')} IST</p>
      </div>
      <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>
      {df.to_html(index=False, classes='table', border=0)}
  </body>
  </html>
  """
  return html.encode("utf-8")


col_ht1, col_ht2 = st.columns([3, 1])
with col_ht1:
  st.markdown(
      f"""
  <div style="display: flex; align-items: center; gap: 12px;">
      <img src="data:image/jpeg;base64,{logo_b64}" style="width: 52px; height: 52px; border-radius: 10px; object-fit: cover; border: 1px solid rgba(255,255,255,0.2); box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
      <div>
          <h1 style="margin: 0; font-family: 'Poppins', sans-serif; font-size: 19px !important; background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; line-height: 1.2;">P. S MEDISELLER</h1>
          <p style="margin: 2px 0 0 0; color: #cbd5e1 !important; font-size: 11px; font-weight: 500;">Allopathy & Ayurvedic Wholesaler | Ph: 8918740325</p>
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
col_u1, _ = st.columns([3, 1])
with col_u1:
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
  menu_options.extend(
      ["📊 Live Tracking (লাইভ ট্র্যাকিং)", "⚙️ Settings & Agents (সেটিংস)"]
  )

selected_menu = st.radio(
    "Select Menu (মেনু সিলেক্ট):",
    menu_options,
    index=0,
    horizontal=False,
    label_visibility="collapsed",
)
st.write("---")

# =========================================================
# 1. ADD NEW LOCATION & ORDER / VISIT ENTRY
# =========================================================
if selected_menu == "📍 Add Location (লোকেশন যোগ)":
  st.write("### 📍 Add Location & Party (লোকেশন ও পার্টি)")
  selected_entry_tab = st.radio(
      "Select Entry Mode (মোড সিলেক্ট):",
      [
          "🏠 With Map Party (ম্যাপ সহ পার্টি)",
          "🩺 Without Map Party (ম্যাপ ছাড়া পার্টি)",
      ],
      label_visibility="collapsed",
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
        p_phone = st.text_input(
            "Phone Number (ফোন নম্বর)", key="input_p_phone"
        )

      submitted_loc = st.form_submit_button(
          "💾 Save Location (সেভ করুন)", type="primary"
      )
    if submitted_loc:
      if p_name.strip() and p_phone.strip():
        c.execute(
            "SELECT id FROM locations WHERE LOWER(party_name) = LOWER(?) OR"
            " party_phone = ?",
            (p_name.strip(), p_phone.strip()),
        )
        if c.fetchone():
          st.error("Party name or phone already exists! (ইতিমধ্যে সেভ করা আছে!)")
        else:
          current_date_str = get_ist_time().strftime("%Y-%m-%d")
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
              (p_name.strip(), "Visit (ভিজিট)", current_date_str),
          )
          conn.commit()
          st.success(
              "Location saved and visit recorded successfully! (সেভ হয়েছে!)"
          )
          st.rerun()
      else:
        st.error("Party name and phone required. (নাম ও ফোন আবশ্যক।)")
  else:
    with st.form("doctor_details_form", clear_on_submit=True):
      st.write("#### 2. Without Map Party Details (ম্যাপ ছাড়া পার্টির বিবরণ)")
      col_d1, col_d2, col_d3 = st.columns(3)
      with col_d1:
        doc_name = st.text_input("Name (নাম)", key="input_doc_name")
      with col_d2:
        doc_addr = st.text_input(
            "Address (ঠিকানা/চেম্বার)", key="input_doc_addr"
        )
      with col_d3:
        doc_phone = st.text_input("Phone (ফোন নম্বর)", key="input_doc_phone")

      submitted_doc = st.form_submit_button(
          "💾 Save Without Map Party (সেভ করুন)", type="primary"
      )
    if submitted_doc:
      if doc_name.strip() and doc_phone.strip():
        c.execute(
            "SELECT id FROM locations WHERE LOWER(party_name) = LOWER(?) OR"
            " party_phone = ?",
            (doc_name.strip(), doc_phone.strip()),
        )
        if c.fetchone():
          st.error("Party name or phone already exists! (ইতিমধ্যে সেভ করা আছে!)")
        else:
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
          st.success("Saved successfully! (সফলভাবে সেভ হয়েছে!)")
          st.rerun()
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
  with col_m2:
    st.write(
        f"Coordinates (স্থানাঙ্ক): `{st.session_state['selected_lat']:.5f},"
        f" {st.session_state['selected_lon']:.5f}`"
    )

  advanced_map = folium.Map(
      location=[
          st.session_state["selected_lat"],
          st.session_state["selected_lon"],
      ],
      zoom_start=17,
  )
  folium.TileLayer(
      tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
      attr="Google Maps Street",
      name="Street View",
      show=True,
  ).add_to(advanced_map)
  folium.Marker(
      [st.session_state["selected_lat"], st.session_state["selected_lon"]],
      popup="<b>Selected Point</b>",
      icon=folium.Icon(color="red", icon="map-marker", prefix="fa"),
  ).add_to(advanced_map)

  map_data = st_folium(
      advanced_map, width="100%", height=380, key="interactive_map"
  )
  if map_data and map_data.get("last_clicked"):
    clat = map_data["last_clicked"]["lat"]
    clon = map_data["last_clicked"]["lng"]
    if (
        clat != st.session_state["selected_lat"]
        or clon != st.session_state["selected_lon"]
    ):
      st.session_state["selected_lat"] = clat
      st.session_state["selected_lon"] = clon
      st.rerun()

# =========================================================
# 5. DUE CLEAR, DELIVERY PLAN & AGENT LINK CREATION
# =========================================================
elif (
    selected_menu == "⚙️ Settings & Agents (সেটিংস)"
    and st.session_state["user_role"] == "admin"
):
  st.write("### ⚙️ System Settings & Agent Management (সেটিংস ও ইউজার)")

  with st.form("create_agent_form"):
    st.write(
        "#### ➕ Create Agent & Generate WhatsApp Login Link (এজেন্ট তৈরি ও লিংক"
        " জেনারেট)"
    )
    agent_full_name_input = st.text_input("Agent Full Name (এজেন্টের পুরো নাম)")
    agent_phone_input = st.text_input("Agent Phone Number (ফোন নম্বর)")
    agent_password_input = st.text_input(
        "Password (পাসওয়ার্ড)", value="1234", type="password"
    )

    submit_new_user = st.form_submit_button(
        "🚀 Create & Generate Link (তৈরি করুন ও লিংক পান)", type="primary"
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
          st.error("Phone number or agent already exists!")
        else:
          try:
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

            # Dynamic Base URL detection via Javascript fallback or standard server URL
            base_app_url = "https://psmediseller.streamlit.app"
            st.session_state["last_generated_agent_name"] = (
                agent_full_name_input.strip()
            )
            st.session_state["last_generated_link"] = (
                f"{base_app_url}/?login={generated_username}"
            )
            st.success(
                f"Agent '{agent_full_name_input}' created successfully!"
            )
          except Exception as e:
            st.error(f"Error creating agent: {e}")

  if st.session_state.get("last_generated_link"):
    st.write("---")
    st.markdown(
        f"#### 🔗 WhatsApp Shareable Link for"
        f" **{st.session_state.get('last_generated_agent_name')}**"
    )

    share_url = st.session_state["last_generated_link"]
    st.code(share_url, language="text")

    whatsapp_msg = urllib.parse.quote(
        f"নমস্কার {st.session_state.get('last_generated_agent_name')}! P.S"
        f" Mediseller অ্যাপে লগইন করার সরাসরি লিংক:\n\n{share_url}\n\nলিংকে টাচ"
        " করে অ্যাপ চালু করুন।"
    )
    whatsapp_url = f"https://api.whatsapp.com/send?text={whatsapp_msg}"

    st.markdown(
        f"""
    <a href="{whatsapp_url}" target="_blank">
        <button style="background: #22c55e; color: white; border: none; padding: 12px 20px; border-radius: 10px; font-weight: bold; cursor: pointer;">
            🟢 Share via WhatsApp (হোয়াটসঅ্যাপে পাঠান)
        </button>
    </a>
    """,
        unsafe_allow_html=True,
    )

  st.write("---")
  users_list_df = pd.read_sql_query(
      "SELECT username AS 'Username', role AS 'Role', fullname AS 'Full Name',"
      " phone AS 'Phone' FROM users",
      conn,
  )
  st.dataframe(users_list_df, use_container_width=True)

else:
  st.info("Select options from navigation menu above.")
