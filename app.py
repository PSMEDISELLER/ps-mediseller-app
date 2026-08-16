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
<div id="loc-overlay" style="display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(15, 23, 42, 0.98); z-index: 999999; justify-content: center; align-items: center; padding: 20px; box-sizing: border-box; font-family: 'Poppins', sans-serif;">
    <div style="background: #1e293b; border: 2px solid #ef4444; border-radius: 16px; padding: 30px; max-width: 450px; width: 100%; text-align: center; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
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
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
}

function requestLocation() {
    const status = document.getElementById('loc-status');
    if (status) {
        status.style.display = 'block';
        status.innerText = "⏳ Requesting location permission... (অনুমতি নেওয়া হচ্ছে...)";
    }
    checkAndRequestLocation();
}

window.addEventListener('load', function() {
    setTimeout(checkAndRequestLocation, 500);
});
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
.agent-card {
    background: #161b22;
    border: 1px solid #30363d;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 20px;
}
.status-active {
    background-color: #238636;
    color: white;
    padding: 6px 12px;
    border-radius: 6px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE SETUP & 48-HOUR / 7-DAY RETENTION CLEANUP
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

c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
  c.execute("INSERT INTO users (username, password, role, fullname, phone, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", 
            ("admin", "admin123", "admin", "Admin", "8918740325", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1))
  c.execute("INSERT INTO users (username, password, role, fullname, phone, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", 
            ("delivery", "user123", "staff", "Delivery Agent", "8918740325", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1))
  conn.commit()

current_dt_str = get_ist_time()

# 7-day cleanup for orders
c.execute("SELECT id, order_date, status FROM orders")
for row_ord in c.fetchall():
  try:
    o_time = datetime.strptime(row_ord[1], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    if (current_dt_str - o_time) > timedelta(days=7):
      c.execute("DELETE FROM orders WHERE id=?", (row_ord[0],))
  except:
    pass

# 48-hour auto cleanup for task assignments
c.execute("SELECT id, created_at, status FROM task_assignments")
for row_task in c.fetchall():
  try:
    t_time = datetime.strptime(row_task[1], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    if (current_dt_str - t_time) > timedelta(hours=48):
      c.execute("DELETE FROM task_assignments WHERE id=?", (row_task[0],))
  except:
    pass
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
            st.success(f"Welcome, {f_name}! Logged in. (স্বাগতম, {f_name}!)")
            st.query_params.pop("login", None)
            st.rerun()
    else:
        st.markdown("""
        <script>
            localStorage.removeItem('ps_mediseller_user');
        </script>
        """, unsafe_allow_html=True)

col_ht1, col_ht2 = st.columns([3, 1])

with col_ht1:
  st.markdown(f"""
  <div style="display: flex; align-items: center; gap: 12px;">
      <img src="data:image/jpeg;base64,{logo_b64}" style="width: 52px; height: 52px; border-radius: 10px; object-fit: cover; border: 1px solid rgba(255,255,255,0.2); box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
      <div>
          <h1 style="margin: 0; font-family: 'Poppins', sans-serif; font-size: 19px !important; background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; line-height: 1.2;">P. S MEDISELLER</h1>
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
    if st.button("🔐 Admin Login (অ্যাডমিন)", key="login_btn_top"):
      st.session_state["show_admin_login"] = True
      st.rerun()

col_u1, _ = st.columns([3, 1])
with col_u1:
  st.write(f"👤 User: **{st.session_state['username']}** (`{st.session_state['user_role']}`)")

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
  
  selected_entry_tab = st.radio(
      "Select Entry Mode (মোড সিলেক্ট):",
      [
          "🏠 With Map Party (ম্যাপ সহ পার্টি)",
          "👨‍⚕️ Without Map Party (ম্যাপ ছাড়া পার্টি)"
      ],
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
        existing_check = c.fetchone()
        
        if existing_check:
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
        existing_check_doc = c.fetchone()

        if existing_check_doc:
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

  street_layer = folium.TileLayer(
      tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
      attr="Google Maps Street",
      name="Street View (স্ট্রিট ভিউ)",
      overlay=False,
      control=True,
      show=True
  )
  street_layer.add_to(advanced_map)

  satellite_layer = folium.TileLayer(
      tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
      attr="Google Maps Satellite",
      name="Satellite View (স্যাটেলাইট ভিউ)",
      overlay=False,
      control=True,
      show=False
  )
  satellite_layer.add_to(advanced_map)

  folium.Marker(
      [st.session_state["selected_lat"], st.session_state["selected_lon"]],
      popup="<b>Selected Point (নির্বাচিত পয়েন্ট)</b>",
      tooltip="Will save here (এখানে সেভ হবে)",
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
        popup="Your GPS Location (জিপিএস লোকেশন)"
    ).add_to(advanced_map)

  formatter = "function(num) {return L.Util.formatNum(num, 5) + ' ° ';};"
  MousePosition(
      position="bottomright",
      separator=" | ",
      prefix="Lat/Lng: ",
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
  st.write("### 📦 Orders & Visits (অর্ডার ও ভিজিট)")

  with st.form("order_visit_entry_form", clear_on_submit=True):
    st.write("🔍 **Enter Party/Doctor Name (পার্টির নাম লিখুন):**")
    selected_order_party_native = st.text_input("Party Name", placeholder="পার্টির নাম লিখুন...", label_visibility="collapsed", key="order_party_input_text")

    ord_details = st.text_area("Order Details (অর্ডার বিবরণ)")
    
    col_ob1, col_ob2 = st.columns(2)
    with col_ob1:
      submitted_order = st.form_submit_button("🛒 Submit Order (অর্ডার জমা)", type="primary")
    with col_ob2:
      submitted_visit = st.form_submit_button("📍 Save Visit (ভিজিট সেভ)")

    if submitted_order:
      if not selected_order_party_native.strip():
        st.error("Please enter party name. (পার্টির নাম লিখুন।)")
      else:
        current_date_str = get_ist_time().strftime("%Y-%m-%d")
        c.execute(
            "INSERT INTO orders (party_name, order_details, order_date, status, payment_collected) VALUES (?, ?, ?, ?, ?)",
            (selected_order_party_native.strip(), ord_details.strip(), get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), "Pending", "0")
        )
        c.execute(
            "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
            (selected_order_party_native.strip(), "Order (অর্ডার)", current_date_str)
        )
        conn.commit()
        st.success("Order submitted successfully! (জমা দেওয়া হয়েছে!)")
        st.rerun()

    if submitted_visit:
      if not selected_order_party_native.strip():
        st.error("Please enter party name. (পার্টির নাম লিখুন।)")
      else:
        current_date_str = get_ist_time().strftime("%Y-%m-%d")
        c.execute(
            "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
            (selected_order_party_native.strip(), "Visit (ভিজিট)", current_date_str)
        )
        conn.commit()
        st.success("Visit saved successfully! (সেভ হয়েছে!)")
        st.rerun()

  st.write("---")
  st.write("#### 📋 Recent Orders & Visits (সাম্প্রতিক রিপোর্ট)")
  report_df = pd.read_sql_query("SELECT * FROM daily_work ORDER BY work_date DESC, id DESC LIMIT 20", conn)
  if not report_df.empty:
    if st.session_state["user_role"] == "admin":
      full_report_df = pd.read_sql_query("SELECT * FROM daily_work ORDER BY work_date DESC, id DESC", conn)
      html_all_report = generate_html_report("Daily Work & Visit Report", full_report_df)
      st.download_button(
          label="📥 Download Daily Work Report (PDF/HTML)",
          data=html_all_report,
          file_name=f"mediseller_daily_work_report.html",
          mime="text/html",
          type="primary"
      )
      st.write("---")

    for idx, r_row in report_df.iterrows():
      cols = st.columns([3, 2, 2])
      cols[0].write(f"Party: **{r_row['party_name']}**")
      cols[1].write(f"Activity: `{r_row['activity_type']}`")
      cols[2].write(f"Date: `{r_row['work_date']}`")
      st.write("---")
  else:
    st.info("No reports found. (কোনো রিপোর্ট নেই।)")

# =========================================================
# 2. SEARCH PARTY DETAILS & ADMIN DELETE OPTION
# =========================================================
elif selected_menu == "🔍 Search & Details (অনুসন্ধান ও বিবরণ)":
  st.write("### 🔍 Search & Party Management (সার্চ ও ম্যানেজমেন্ট)")

  if st.session_state.get("mapping_party_id"):
    st.markdown(f"### 📍 Set Map for **{st.session_state['mapping_party_name']}**")
    st.write("Click correct location on map and click **'Save Location'** below.")
    
    if "temp_map_lat" not in st.session_state:
      st.session_state["temp_map_lat"] = 22.8620
    if "temp_map_lon" not in st.session_state:
      st.session_state["temp_map_lon"] = 87.3320

    col_tm1, col_tm2 = st.columns([1, 4])
    with col_tm1:
      if st.button("📍 Current GPS (কারেন্ট জিপিএস)", key="btn_curr_gps_temp"):
        if gps_lat and gps_lon:
          st.session_state["temp_map_lat"] = gps_lat
          st.session_state["temp_map_lon"] = gps_lon
          st.success("GPS taken! (নেওয়া হয়েছে!)")
          st.rerun()
        else:
          st.warning("GPS not found! (নেই!)")
    with col_tm2:
      st.write(f"Coordinates: `{st.session_state['temp_map_lat']:.5f}, {st.session_state['temp_map_lon']:.5f}`")

    pick_map = folium.Map(
        location=[st.session_state["temp_map_lat"], st.session_state["temp_map_lon"]],
        zoom_start=17,
        tiles=None
    )
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google Maps Street",
        name="Street View (স্ট্রিট ভিউ)",
        show=True
    ).add_to(pick_map)
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google Maps Satellite",
        name="Satellite View (স্যাটেলাইট ভিউ)",
        show=False
    ).add_to(pick_map)

    folium.Marker(
        [st.session_state["temp_map_lat"], st.session_state["temp_map_lon"]],
        popup="<b>Set Here (এখানে সেট)</b>",
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
          popup="Your Location (আপনার লোকেশন)"
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
      if st.button("✅ Save Location (সেভ করুন)", type="primary", key="save_party_map_ok"):
        target_id = st.session_state["mapping_party_id"]
        t_lat = st.session_state["temp_map_lat"]
        t_lon = st.session_state["temp_map_lon"]
        c.execute("UPDATE locations SET lat=?, lon=? WHERE id=?", (t_lat, t_lon, target_id))
        conn.commit()
        st.session_state.pop("mapping_party_id", None)
        st.session_state.pop("mapping_party_name", None)
        st.success(f"Map saved successfully! (সেভ হয়েছে!)")
        st.rerun()
    with col_b2:
      if st.button("❌ Cancel (বাতিল)", key="cancel_party_map"):
        st.session_state.pop("mapping_party_id", None)
        st.session_state.pop("mapping_party_name", None)
        st.rerun()

    st.markdown("---")
    st.stop()

  st.write("🔍 **Search Party/Doctor (পার্টি খুঁজুন):**")
  master_search_query = st.text_input("Search (সার্চ)", placeholder="Search here (সার্চ)", key="master_search_input_box", label_visibility="collapsed")

  if master_search_query.strip():
    df = pd.read_sql_query("SELECT * FROM locations WHERE party_name LIKE ? ORDER BY party_name ASC", conn, params=(f"%{master_search_query.strip()}%",))
  else:
    df = pd.read_sql_query("SELECT * FROM locations ORDER BY party_name ASC", conn)

  if st.session_state["user_role"] == "admin" and not df.empty:
    html_locs_df = generate_html_report("Locations & Parties Directory", df)
    st.download_button(
        label="📥 Download Locations Report (PDF/HTML)",
        data=html_locs_df,
        file_name="mediseller_locations_report.html",
        mime="text/html",
        type="primary"
    )
    st.write("---")

  doc_df = df[df["lat"].isna() | df["lon"].isna()]
  mapped_df = df[df["lat"].notna() & df["lon"].notna()]

  with st.expander(f"👨‍⚕️ Non-Map List ({len(doc_df)} Entries) (ম্যাপবিহীন তালিকা)", expanded=True):
    if not doc_df.empty:
      for index, row in doc_df.iterrows():
        cols = st.columns([3, 2, 2, 2, 1.5])
        cols[0].write(f"**{row['party_name']}**")
        cols[1].write(row['party_phone'] if row['party_phone'] else "No number (নম্বর নেই)")
        cols[2].write(row['address'] if row['address'] else "No address (ঠিকানা নেই)")
        
        if cols[3].button("📍 Add Map (ম্যাপ যুক্ত)", key=f"map_add_search_{row['id']}"):
          st.session_state["mapping_party_id"] = row['id']
          st.session_state["mapping_party_name"] = row['party_name']
          st.session_state["temp_map_lat"] = st.session_state.get("selected_lat", 22.8620)
          st.session_state["temp_map_lon"] = st.session_state.get("selected_lon", 87.3320)
          st.rerun()

        if st.session_state["user_role"] == "admin":
          if cols[4].button("🗑️ Delete (ডিলিট)", key=f"del_doc_search_{row['id']}"):
            c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
            conn.commit()
            st.success("Deleted! (ডিলিট হয়েছে!)")
            st.rerun()
        st.write("---")
    else:
      st.info("No non-map parties found. (ম্যাপবিহীন পার্টি নেই।)")

  st.write("---")
  st.write(f"#### 📍 Mapped List ({len(mapped_df)} Records) (ম্যাপযুক্ত তালিকা)")
  if not mapped_df.empty:
    for index, row in mapped_df.iterrows():
      if st.session_state["user_role"] == "admin":
        cols = st.columns([3, 2, 2, 2, 1.5])
      else:
        cols = st.columns([3, 2, 2, 2])

      cols[0].write(f"**{row['party_name']}**")
      cols[1].write(row['party_phone'] if row['party_phone'] else "No number (নম্বর নেই)")
      cols[2].write(row['address'] if row['address'] else "No address (ঠিকানা নেই)")
      
      maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}"
      cols[3].markdown(f'<a href="{maps_url}" target="_blank" style="text-decoration:none;"><button style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color:white; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; font-weight:600;">🧭 Direction (ডিরেকশন)</button></a>', unsafe_allow_html=True)

      if st.session_state["user_role"] == "admin":
        if cols[4].button("🗑️ Delete (ডিলিট)", key=f"del_loc_search_{row['id']}"):
          c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
          conn.commit()
          st.success("Deleted! (ডিলিট হয়েছে!)")
          st.rerun()

      st.write("---")
  else:
    st.info("No mapped parties found. (ম্যাপযুক্ত পার্টি নেই।)")

# =========================================================
# 3. PENDING ORDERS & COMPLETED ORDERS HISTORY
# =========================================================
elif selected_menu == "📦 Pending Orders (বাকি অর্ডার)":
  st.write("### 📦 Orders Management (অর্ডার ম্যানেজমেন্ট)")
  
  if st.session_state["user_role"] == "admin":
    ord_tab1, ord_tab2 = st.tabs(["⏳ Pending Orders (পেন্ডিং)", "📜 Completed History (সম্পন্ন অর্ডার)"])
  else:
    ord_tab1 = st.container()
    ord_tab2 = None

  with ord_tab1:
    st.write("#### ⏳ Active Pending Orders")
    if st.session_state["user_role"] == "admin":
      all_ord_df = pd.read_sql_query("SELECT * FROM orders WHERE status='Pending' ORDER BY order_date DESC", conn)
      if not all_ord_df.empty:
        html_ord_report = generate_html_report("Pending Orders Report", all_ord_df)
        st.download_button(
            label="📥 Download Pending Orders Report (PDF/HTML)",
            data=html_ord_report,
            file_name="mediseller_pending_orders_report.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")

    orders_df = pd.read_sql_query("SELECT * FROM orders WHERE status='Pending' ORDER BY order_date DESC", conn)
    if not orders_df.empty:
      for index, row in orders_df.iterrows():
        cols = st.columns([2, 4, 2, 2])
        cols[0].write(f"**{row['party_name']}**")
        cols[1].write(row['order_details'])
        cols[2].write("⏳ Pending (পেন্ডিং)")

        if cols[3].button("✔️ Complete (কমপ্লিট)", key=f"ord_btn_{row['id']}"):
          c.execute("UPDATE orders SET status='Completed' WHERE id=?", (row['id'],))
          conn.commit()
          c.execute("UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?", (st.session_state["username"],))
          conn.commit()
          st.success("Order completed! (কমপ্লিট করা হয়েছে!)")
          st.rerun()
        st.write("---")
    else:
      st.info("No pending orders. (পেন্ডিং অর্ডার নেই।)")

  if ord_tab2 is not None:
    with ord_tab2:
      st.write("#### 📜 Completed Orders History")
      completed_ord_df = pd.read_sql_query("SELECT * FROM orders WHERE status='Completed' ORDER BY order_date DESC", conn)
      if not completed_ord_df.empty:
        html_comp_ord = generate_html_report("Completed Orders History", completed_ord_df)
        st.download_button(
            label="📥 Download Completed Orders Report (PDF/HTML)",
            data=html_comp_ord,
            file_name="mediseller_completed_orders_history.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")
        for idx, row in completed_ord_df.iterrows():
          cols = st.columns([2, 4, 2])
          cols[0].write(f"**{row['party_name']}**")
          cols[1].write(row['order_details'])
          cols[2].write("✅ Completed (সম্পন্ন)")
          st.write("---")
      else:
        st.info("No completed orders history.")

# =========================================================
# 4. DAILY & MONTHLY WORK
# =========================================================
elif selected_menu == "📋 Daily & Monthly Work (দৈনিক ও মাসিক কাজ)":
  st.write("### 📋 Daily & Monthly Work Report (দৈনিক ও মাসিক কাজের রিপোর্ট)")

  work_tab1, work_tab2 = st.tabs([
      "📅 Daily Work (দৈনিক কাজ)", 
      "📊 Monthly Summary & Zero Activity (মাসিক সামারি ও জিরো অ্যাক্টিভিটি)"
  ])

  with work_tab1:
    st.write("#### 📅 Visit & Order List (তারিখ অনুযায়ী)")

    if st.session_state["user_role"] == "admin":
      full_dw_df = pd.read_sql_query("SELECT * FROM daily_work ORDER BY work_date DESC, id DESC", conn)
      if not full_dw_df.empty:
        html_dw_report = generate_html_report("Daily Work Report", full_dw_df)
        st.download_button(
            label="📥 Download Daily Work Report (PDF/HTML)",
            data=html_dw_report,
            file_name="mediseller_daily_work_report.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")

    work_df = pd.read_sql_query("SELECT * FROM daily_work ORDER BY work_date DESC, id DESC", conn)
    if not work_df.empty:
      unique_dates = work_df['work_date'].unique()
      for d_str in unique_dates:
        date_records = work_df[work_df['work_date'] == d_str]
        count_parties = len(date_records)
        
        try:
          formatted_d = datetime.strptime(d_str, "%Y-%m-%d").strftime("%d-%m-%Y")
        except:
          formatted_d = d_str

        with st.expander(f"📅 Date: {formatted_d} (Total: {count_parties})", expanded=False):
          if st.session_state["user_role"] == "admin":
            if st.button(f"🗑️ Delete Date Data ({formatted_d}) (সব ডিলিট)", key=f"del_date_{d_str}", type="secondary"):
              c.execute("DELETE FROM daily_work WHERE work_date=?", (d_str,))
              conn.commit()
              st.success("Deleted! (মুছে ফেলা হয়েছে!)")
              st.rerun()
            st.write("---")

          for idx, w_row in date_records.iterrows():
            cols = st.columns([3, 2, 1.5])
            cols[0].write(f"Party: **{w_row['party_name']}**")
            cols[1].write(f"Status: `{w_row['activity_type']}`")
            
            if st.session_state["user_role"] == "admin":
              if cols[2].button("🗑️ Delete (ডিলিট)", key=f"del_dw_{w_row['id']}"):
                c.execute("DELETE FROM daily_work WHERE id=?", (w_row['id'],))
                conn.commit()
                st.success("Deleted! (ডিলিট হয়েছে!)")
                st.rerun()
            else:
              cols[2].write("🔒 Locked (লকড)")
            st.write("---")
    else:
      st.info("No records found. (কোনো রেকর্ড নেই।)")

  with work_tab2:
    st.write("#### 📊 Monthly Doctor/Party Activity Report (মাসিক ডাক্তার ও পার্টি রিপোর্ট)")
    
    st.write("🗓️ **Select Year & Month (বছর ও মাস সিলেক্ট করুন):**")
    col_yr, col_mo = st.columns(2)
    with col_yr:
      selected_year = st.selectbox("Select Year (বছর)", [2026, 2025, 2024], index=0)
    with col_mo:
      months_dict = {
          "01": "January (জানুয়ারি)", "02": "February (ফেব্রুয়ারি)", "03": "March (মার্চ)", 
          "04": "April (এপ্রিল)", "05": "May (মে)", "06": "June (জুন)", 
          "07": "July (জুলাই)", "08": "August (আগস্ট)", "09": "September (সেপ্টেম্বর)", 
          "10": "October (অক্টোবর)", "11": "November (নভেম্বর)", "12": "December (ডিসেম্বর)"
      }
      current_mo_num = get_ist_time().strftime("%m")
      selected_mo_key = st.selectbox("Select Month (মাস)", list(months_dict.keys()), format_func=lambda x: months_dict[x], index=list(months_dict.keys()).index(current_mo_num) if current_mo_num in months_dict else 7)
    
    selected_month = f"{selected_year}-{selected_mo_key}"

    if selected_month.strip():
      all_locs_df = pd.read_sql_query("SELECT party_name, address, lat, lon FROM locations ORDER BY party_name ASC", conn)
      
      if not all_locs_df.empty:
        report_data = []
        
        for idx, loc_row in all_locs_df.iterrows():
          p_name = loc_row['party_name']
          is_mapped = "Mapped (ম্যাপযুক্ত)" if pd.notna(loc_row['lat']) and pd.notna(loc_row['lon']) else "Non-Map (ম্যাপবিহীন)"
          
          c.execute("""
            SELECT COUNT(*) FROM daily_work 
            WHERE party_name = ? AND work_date LIKE ? AND activity_type LIKE '%Visit%'
          """, (p_name, f"{selected_month}%"))
          v_count = c.fetchone()[0]

          c.execute("""
            SELECT COUNT(*) FROM daily_work 
            WHERE party_name = ? AND work_date LIKE ? AND activity_type LIKE '%Order%'
          """, (p_name, f"{selected_month}%"))
          o_count = c.fetchone()[0]

          report_data.append({
              "Party Name": p_name,
              "Type": is_mapped,
              "Total Visits": v_count,
              "Total Orders": o_count
          })

        report_summary_df = pd.DataFrame(report_data)

        st.write(f"##### 📋 Complete Activity Summary for `{selected_month}`")
        
        if st.session_state["user_role"] == "admin":
          html_summary = generate_html_report(f"Monthly Summary - {selected_month}", report_summary_df)
          st.download_button(
              label="📥 Download Monthly Summary Report (PDF/HTML)",
              data=html_summary,
              file_name=f"mediseller_monthly_summary_{selected_month}.html",
              mime="text/html",
              type="primary"
          )
          st.write("---")

        st.dataframe(report_summary_df, use_container_width=True)

        zero_activity_df = report_summary_df[(report_summary_df["Total Visits"] == 0) & (report_summary_df["Total Orders"] == 0)]
        
        st.write(f"⚠️ **Doctors/Parties with ZERO Visits & ZERO Orders ({len(zero_activity_df)}):**")
        if not zero_activity_df.empty:
          st.dataframe(zero_activity_df, use_container_width=True)
        else:
          st.success("All parties/doctors had at least one visit or order this month! (সব ডাক্তারের ভিজিট বা অর্ডার হয়েছে!)")

        if st.session_state["user_role"] == "admin":
          st.write("---")
          st.write("#### ⚙️ Admin Actions for this Month")
          if st.button(f"🗑️ Delete All Work Records for Month: {selected_month} (এই মাসের সব ডাটা মুছুন)", type="secondary"):
            c.execute("DELETE FROM daily_work WHERE work_date LIKE ?", (f"{selected_month}%",))
            conn.commit()
            st.success(f"All records for {selected_month} deleted successfully! (মুছে ফেলা হয়েছে!)")
            st.rerun()
      else:
        st.info("No parties/doctors found in database. (কোনো পার্টি নেই।)")

# =========================================================
# 5. DUE CLEAR, DELIVERY PLAN & 48-HOUR AUTO-EXPIRING TASKS
# =========================================================
elif selected_menu == "📋 Due & Delivery (বকেয়া ও ডেলিভারি)":
  st.write("### 📋 Due & Delivery Plan (ডেলিভারি ও ডিউ প্ল্যান)")
  
  c.execute("SELECT username FROM users")
  all_agents = [r[0] for r in c.fetchall()]
  c.execute("SELECT party_name, lat, lon FROM locations ORDER BY party_name ASC")
  loc_data = c.fetchall()
  party_coords = {r[0]: (r[1], r[2]) for r in loc_data}
  all_parties = [r[0] for r in loc_data]

  task_tab1, task_tab2, task_tab3 = st.tabs([
      "🎯 Active Tasks (চলমান কাজ)", 
      "📊 Agent Date-wise Summary (এজেন্ট ও তারিখ অনুযায়ী সামারি)",
      "📜 Completed Tasks History (সম্পন্ন কাজ)"
  ])

  with task_tab1:
    if st.session_state["user_role"] == "admin":
      full_tasks_df = pd.read_sql_query("SELECT * FROM task_assignments WHERE status='Pending' ORDER BY id DESC", conn)
      if not full_tasks_df.empty:
        html_tasks_report = generate_html_report("Active Tasks & Deliveries Report", full_tasks_df)
        st.download_button(
            label="📥 Download Tasks Report (PDF/HTML)",
            data=html_tasks_report,
            file_name="mediseller_due_delivery_report.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")

    with st.form("easy_assign_form", clear_on_submit=True):
      st.write("🔍 **Enter Party / Doctor Name (পার্টি বা ডাক্তারের নাম লিখুন):**")
      sel_pt = st.text_input("Party Name", placeholder="পার্টির নাম লিখুন...", label_visibility="collapsed", key="task_party_input_text")
      
      sel_ag = st.selectbox("Select Agent (এজেন্ট সিলেক্ট)", all_agents)

      st.write("**Work Type (কাজের ধরণ):**")
      col_chk1, col_chk2 = st.columns(2)
      with col_chk1:
        chk_delivery = st.checkbox("🚚 Delivery (ডেলিভারি)")
      with col_chk2:
        chk_due = st.checkbox("💰 Due Collection (ডিউ কালেকশন)")

      d_amount = st.text_input("Due Amount (ডিউ টাকা)", "0")

      submit_easy_task = st.form_submit_button("🎯 Add Task (কাজ যোগ)", type="primary")

      if submit_easy_task:
        if not sel_pt.strip():
          st.error("Enter a valid party name. (পার্টির নাম লিখুন।)")
        else:
          selected_tasks = []
          if chk_delivery:
            selected_tasks.append("Delivery (ডেলিভারি)")
          if chk_due:
            selected_tasks.append("Due Collection (ডিউ কালেকশন)")

          if selected_tasks:
            t_type_str = " & ".join(selected_tasks)
            current_date_str = get_ist_time().strftime("%Y-%m-%d")
            c.execute(
                "INSERT INTO task_assignments (agent_name, party_name, task_type, due_amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (sel_ag, sel_pt.strip(), t_type_str, d_amount, "Pending", get_ist_time().strftime("%Y-%m-%d %H:%M:%S")),
            )
            c.execute(
                "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
                (sel_pt.strip(), "Visit (ভিজিট)", current_date_str)
            )
            conn.commit()
            st.success("Task assigned! (কাজ অ্যাসাইন করা হয়েছে!)")
            st.rerun()
          else:
            st.warning("Select at least one work type. (কাজের ধরণ সিলেক্ট করুন।)")

    st.write("---")
    st.write("### 📋 Current Tasks (বর্তমান কাজ)")

    if st.session_state["user_role"] == "admin":
      tasks_df = pd.read_sql_query("SELECT * FROM task_assignments WHERE status='Pending' ORDER BY id DESC", conn)
    else:
      tasks_df = pd.read_sql_query("SELECT * FROM task_assignments WHERE agent_name=? AND status='Pending' ORDER BY id DESC", conn, params=(st.session_state["username"],))

    if not tasks_df.empty:
      for idx, row in tasks_df.iterrows():
        p_name = row['party_name']
        cols = st.columns([2, 2, 2, 2])
        cols[0].write(f"Agent: **{row['agent_name']}**\n\nParty: **{p_name}**")
        cols[1].write(f"Work: {row['task_type']}\n\nDue: {row['due_amount']} INR")

        auto_completed = False
        if gps_lat and gps_lon and p_name in party_coords:
          p_coords = party_coords[p_name]
          if p_coords[0] is not None and p_coords[1] is not None:
            p_lat, p_lon = p_coords
            import math
            dist = math.sqrt((gps_lat - p_lat)**2 + (gps_lon - p_lon)**2) * 111000
            if dist <= 30:
              auto_completed = True

        if cols[2].button("✅ Complete (সম্পন্ন)", key=f"comp_task_{row['id']}") or auto_completed:
          c.execute("UPDATE task_assignments SET status='Completed' WHERE id=?", (row['id'],))
          if "Delivery" in row['task_type']:
            c.execute("UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?", (row['agent_name'],))
          if "Due" in row['task_type']:
            c.execute("UPDATE agent_live_locations SET completed_dues = completed_dues + 1 WHERE username=?", (row['agent_name'],))
          conn.commit()
          st.success("Task completed! (সম্পন্ন!)")
          st.rerun()

        if st.session_state["user_role"] == "admin":
          if cols[3].button("🗑️ Delete (ডিলিট)", key=f"del_task_admin_{row['id']}"):
            c.execute("DELETE FROM task_assignments WHERE id=?", (row['id'],))
            conn.commit()
            st.success("Deleted by admin! (ডিলিট হয়েছে!)")
            st.rerun()
        else:
          cols[3].write("Pending (পেন্ডিং)\n\n*(Admin only delete)*")
        st.write("---")
    else:
      st.info("No tasks assigned. (কোনো কাজ নেই।)")

  with task_tab2:
    st.write("#### 📊 Agent Date-wise & Party Summary (এজেন্ট ও তারিখ অনুযায়ী কাজের বিবরণ)")
    
    agent_summary_df = pd.read_sql_query("""
        SELECT agent_name, substr(created_at, 1, 10) as task_date, task_type, COUNT(DISTINCT party_name) as party_count, SUM(CAST(due_amount AS REAL)) as total_due
        FROM task_assignments
        GROUP BY agent_name, task_date, task_type
        ORDER BY task_date DESC, agent_name ASC
    """, conn)

    if not agent_summary_df.empty:
      st.dataframe(agent_summary_df, use_container_width=True)
      
      if st.session_state["user_role"] == "admin":
        html_agent_sum = generate_html_report("Agent Date-wise Task Summary", agent_summary_df)
        st.download_button(
            label="📥 Download Agent Summary Report (PDF/HTML)",
            data=html_agent_sum,
            file_name="mediseller_agent_datewise_summary.html",
            mime="text/html",
            type="primary"
        )
    else:
      st.info("No summary data available yet.")

  if task_tab3 is not None:
    with task_tab3:
      st.write("#### 📜 Completed Tasks History (Auto expires after 48 hours)")
      completed_tasks_df = pd.read_sql_query("SELECT * FROM task_assignments WHERE status='Completed' ORDER BY id DESC", conn)
      if not completed_tasks_df.empty:
        html_comp_tasks = generate_html_report("Completed Tasks History", completed_tasks_df)
        st.download_button(
            label="📥 Download Completed Tasks Report (PDF/HTML)",
            data=html_comp_tasks,
            file_name="mediseller_completed_tasks_history.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")
        for idx, row in completed_tasks_df.iterrows():
          cols = st.columns([2, 2, 2, 1.5])
          cols[0].write(f"Agent: **{row['agent_name']}**\n\nParty: **{row['party_name']}**")
          cols[1].write(f"Work: {row['task_type']}\n\nDue: {row['due_amount']} INR")
          cols[2].write("✅ Completed (সম্পন্ন)")
          
          if st.session_state["user_role"] == "admin":
            if cols[3].button("🗑️ Delete (ডিলিট)", key=f"del_comp_task_{row['id']}"):
              c.execute("DELETE FROM task_assignments WHERE id=?", (row['id'],))
              conn.commit()
              st.success("Deleted! (ডিলিট হয়েছে!)")
              st.rerun()
          else:
            cols[3].write("🔒 Locked")
          st.write("---")
      else:
        st.info("No completed tasks history.")

# =========================================================
# 6. HOME-TO-HOME AUTO ROUTE & MAP
# =========================================================
elif selected_menu == "🗺️ Route Map (রুট ম্যাপ)":
  st.write("### 🗺️ Route Planning (রুট প্ল্যানিং)")

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
        name="Google Maps (গুগল ম্যাপ)"
    ).add_to(route_map)

    coordinates_list = []
    seq_num = 1
    for idx, row in locs_df.iterrows():
      lat, lon = row["lat"], row["lon"]
      coordinates_list.append([lat, lon])
      
      folium.Marker(
          [lat, lon],
          popup=f"<b>Route No {seq_num}: {row['party_name']}</b><br>{row['address']}",
          tooltip=f"{seq_num}. {row['party_name']}",
          icon=folium.Icon(color="blue", icon="info-sign")
      ).add_to(route_map)
      seq_num += 1

    if len(coordinates_list) > 1:
      folium.PolyLine(coordinates_list, color="#ff4b4b", weight=5, opacity=0.85, tooltip="Delivery Route (রুট)").add_to(route_map)

    st_folium(route_map, width=900, height=500, key="auto_route_map")
  else:
    st.info("No location saved on map. (ম্যাপে লোকেশন নেই।)")

# =========================================================
# 7. ATTENDANCE SYSTEM
# =========================================================
elif selected_menu == "📅 Attendance (উপস্থিতি)":
  st.write("### 📅 Attendance (উপস্থিতি)")

  att_tab1, att_tab2 = st.tabs([
      "📝 Today (আজকের উপস্থিতি)", 
      "📊 Monthly Summary (মাসিক সামারি)"
  ])

  with att_tab1:
    display_today_str = get_ist_time().strftime('%d-%m-%Y')
    st.write(f"#### Today's Date: `{display_today_str}`")
    
    current_user = st.session_state["username"]
    today_str = get_ist_time().strftime("%Y-%m-%d")
    
    c.execute("SELECT check_time FROM attendance WHERE username=? AND date=?", (current_user, today_str))
    already_checked = c.fetchone()

    if already_checked:
      st.success(f"Attendance recorded! (Time: `{already_checked[0]}`) (উপস্থিতি গ্রহণ করা হয়েছে।)")
    else:
      if st.button("🙋‍♂️ Give Attendance (উপস্থিতি দিন)", type="primary"):
        check_time_str = get_ist_time().strftime("%H:%M:%S")
        try:
          c.execute("INSERT INTO attendance (username, date, check_time, status) VALUES (?, ?, ?, ?)",
                    (current_user, today_str, check_time_str, "Present"))
          conn.commit()
          st.success("Attendance recorded! (সফল!)")
          st.rerun()
        except sqlite3.IntegrityError:
          st.error("Already attended. (ইতিমধ্যে দেওয়া হয়েছে।)")

    st.write("---")
    st.write("#### Today's Attendance List (আজকের তালিকা)")
    
    if st.session_state["user_role"] == "admin":
      full_att_today = pd.read_sql_query("SELECT username, check_time, status FROM attendance WHERE date=?", conn, params=(today_str,))
      if not full_att_today.empty:
        html_att_today = generate_html_report(f"Attendance Report - {today_str}", full_att_today)
        st.download_button(
            label="📥 Download Today's Attendance Report (PDF/HTML)",
            data=html_att_today,
            file_name=f"mediseller_attendance_{today_str}.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")

    today_att_df = pd.read_sql_query("SELECT username, check_time, status FROM attendance WHERE date=?", conn, params=(today_str,))
    if not today_att_df.empty:
      st.dataframe(today_att_df, use_container_width=True)
    else:
      st.info("No attendance today. (আজ কেউ দেয়নি।)")

  with att_tab2:
    st.write("#### 📊 Monthly Report (মাসিক রিপোর্ট)")
    
    current_month_str = get_ist_time().strftime("%Y-%m")
    current_user = st.session_state["username"]
    user_role = st.session_state["user_role"]

    if user_role == "admin":
      st.write(f"Current Month: **{current_month_str}** (Admin View)")
      summary_df = pd.read_sql_query("""
          SELECT username, COUNT(*) as total_present 
          FROM attendance 
          WHERE strftime('%Y-%m', date) = ? 
          GROUP BY username
      """, conn, params=(current_month_str,))
      
      full_monthly_att = pd.read_sql_query("""
          SELECT * FROM attendance 
          WHERE strftime('%Y-%m', date) = ? 
          ORDER BY date DESC, check_time DESC
      """, conn, params=(current_month_str,))
      
      if not full_monthly_att.empty:
        html_monthly_att = generate_html_report(f"Monthly Attendance - {current_month_str}", full_monthly_att)
        st.download_button(
            label="📥 Download Monthly Attendance Report (PDF/HTML)",
            data=html_monthly_att,
            file_name=f"mediseller_monthly_attendance_{current_month_str}.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")
    else:
      st.write(f"Current Month: **{current_month_str}**")
      summary_df = pd.read_sql_query("""
          SELECT username, COUNT(*) as total_present 
          FROM attendance 
          WHERE strftime('%Y-%m', date) = ? AND username = ?
          GROUP BY username
      """, conn, params=(current_month_str, current_user))

    if not summary_df.empty:
      st.dataframe(summary_df, use_container_width=True)
    else:
      st.info("No records for this month. (এই মাসের রেকর্ড নেই।)")

    st.write("---")
    if user_role == "admin":
      st.write("#### 📋 Detailed Records (বিস্তারিত রেকর্ড)")
      all_att_df = pd.read_sql_query("SELECT * FROM attendance ORDER BY date DESC, check_time DESC", conn)
      if not all_att_df.empty:
        html_all_att_records = generate_html_report("All Attendance Detailed Records", all_att_df)
        st.download_button(
            label="📥 Download Detailed Attendance History Report (PDF/HTML)",
            data=html_all_att_records,
            file_name=f"mediseller_all_attendance_records.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")
    else:
      st.write("#### 📋 Attendance History (ইতিহাস)")
      all_att_df = pd.read_sql_query("SELECT * FROM attendance WHERE username=? ORDER BY date DESC, check_time DESC", conn, params=(current_user,))
    
    if not all_att_df.empty:
      for idx, row in all_att_df.iterrows():
        try:
          formatted_row_date = datetime.strptime(row['date'], "%Y-%m-%d").strftime("%d-%m-%Y")
        except:
          formatted_row_date = row['date']

        cols = st.columns([2, 2, 2, 1.5, 1.5])
        cols[0].write(f"User: **{row['username']}**")
        cols[1].write(f"Date: {formatted_row_date}")
        cols[2].write(f"Time: {row['check_time']}")
        cols[3].write(f"Status: {row['status']}")

        if user_role == "admin":
          if cols[4].button("🗑️ Delete (ডিলিট)", key=f"del_att_{row['id']}"):
            c.execute("DELETE FROM attendance WHERE id=?", (row['id'],))
            conn.commit()
            st.success("Deleted! (মুছে ফেলা হয়েছে!)")
            st.rerun()
        else:
          cols[4].write("🔒 Locked (লকড)")
    else:
      st.info("No records. (রেকর্ড নেই।)")

# =========================================================
# 8. ADVANCED ADMIN LIVE TRACKING
# =========================================================
elif selected_menu == "📊 Live Tracking (লাইভ ট্র্যাকিং)":
  if st.session_state["user_role"] != "admin":
    st.error("Admin only page. (শুধুমাত্র অ্যাডমিনের জন্য।)")
  else:
    st.title("📍 Live Agent Tracking (লাইভ ট্র্যাকিং)")
    st.markdown("ℹ️ Updates every 30 seconds.")

    st.markdown("""
    <meta http-equiv="refresh" content="30">
    """, unsafe_allow_html=True)

    c.execute("SELECT username, role, fullname, phone FROM users")
    all_system_users = c.fetchall()

    if all_system_users:
      live_tracking_data = []
      for u_name, u_role, f_name, u_phone in all_system_users:
        c.execute("SELECT lat, lon, last_updated, completed_deliveries, completed_dues FROM agent_live_locations WHERE username=?", (u_name,))
        agent_data = c.fetchone()
        disp_agent_name = f_name if f_name else u_name
        if agent_data and agent_data[0] is not None:
          lat, lon, last_updated, comp_del, comp_due = agent_data
          live_tracking_data.append({
              "Username": u_name,
              "Full Name": disp_agent_name,
              "Role": u_role,
              "Latitude": lat,
              "Longitude": lon,
              "Last Updated": last_updated,
              "Completed Deliveries": comp_del,
              "Completed Dues": comp_due,
              "Phone": u_phone if u_phone else "None"
          })

      if live_tracking_data:
        live_df = pd.DataFrame(live_tracking_data)
        html_live_report = generate_html_report("Agent Live Tracking & Stats Report", live_df)
        st.download_button(
            label="📥 Download Live Tracking Report (PDF/HTML)",
            data=html_live_report,
            file_name="mediseller_live_tracking_report.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")

      for u_name, u_role, f_name, u_phone in all_system_users:
        c.execute("SELECT lat, lon, last_updated, completed_deliveries, completed_dues FROM agent_live_locations WHERE username=?", (u_name,))
        agent_data = c.fetchone()

        disp_agent_name = f_name if f_name else u_name
        
        IST = ZoneInfo("Asia/Kolkata")
        current_time_str = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

        if agent_data and agent_data[0] is not None:
          lat, lon, last_updated, comp_del, comp_due = agent_data
          display_last_update = last_updated if last_updated else current_time_str
          
          with st.container():
            st.markdown(
                f"""
                <div class="agent-card">
                    <h3>👤 Agent: {disp_agent_name} ({u_name}) - Role: {u_role}</h3>
                    <span class="status-active">🟢 Live Active (সক্রিয়)</span>
                    <p style="margin-top: 15px;"><b>📍 Location:</b> <code>{lat:.5f}, {lon:.5f}</code></p>
                    <p><b>🕒 Last Update:</b> <code>{display_last_update}</code></p>
                    <p><b>📞 Phone:</b> <code>{u_phone if u_phone else 'None (নেই)'}</code></p>
                    <div style="background: #0d1117; padding: 10px; border-radius: 6px; margin-top: 10px;">
                        <p>📊 <b>Stats (পরিসংখ্যান):</b></p>
                        <p>✅ Completed Deliveries: <b>{comp_del}</b></p>
                        <p>💰 Due Clearances: <b>{comp_due}</b></p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            st.markdown(
                f"""
                <a href="{maps_url}" target="_blank">
                    <button style="background-color: #1f6feb; color: white; border: none; padding: 10px 20px; border-radius: 5px; font-weight: bold; cursor: pointer;">
                        🧭 View on Google Maps (ম্যাপে দেখুন)
                    </button>
                </a>
                """,
                unsafe_allow_html=True,
            )
        else:
          with st.container():
            st.markdown(
                f"""
                <div class="agent-card">
                    <h3>👤 Agent: {disp_agent_name} ({u_name}) - Role: {u_role}</h3>
                    <p style="color: #f85149;">🔴 Offline or No GPS. (অফলাইন বা জিপিএস নেই।)</p>
                    <p><b>📞 Phone:</b> <code>{u_phone if u_phone else 'None (নেই)'}</code></p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
      st.info("No users found. (ইউজার নেই।)")

# =========================================================
# 9. SETTINGS, ADMIN PASSWORD & AGENT MANAGEMENT
# =========================================================
elif selected_menu == "⚙️ Settings & Agents (সেটিংস)":
  if st.session_state["user_role"] != "admin":
    st.error("Admin only page. (শুধুমাত্র অ্যাডমিনের জন্য।)")
  else:
    st.write("### 🔑 Change Password (পাসওয়ার্ড পরিবর্তন)")
    with st.form("admin_password_change_form"):
      old_pass = st.text_input("Old Password (পুরাতন পাসওয়ার্ড)", type="password")
      new_pass = st.text_input("New Password (নতুন পাসওয়ার্ড)", type="password")
      confirm_pass = st.text_input("Confirm Password (পুনরায় পাসওয়ার্ড)", type="password")
      change_pass_btn = st.form_submit_button("🔒 Update Password (আপডেট)", type="primary")

      if change_pass_btn:
        c.execute("SELECT password FROM users WHERE username='admin'")
        adm_db_row = c.fetchone()
        if adm_db_row and adm_db_row[0] == old_pass:
          if new_pass == confirm_pass and new_pass.strip() != "":
            c.execute("UPDATE users SET password=? WHERE username='admin'", (new_pass,))
            conn.commit()
            st.success("Password changed successfully! (পরিবর্তন করা হয়েছে!)")
          else:
            st.error("Passwords do not match or empty. (মিলছে না বা খালি।)")
        else:
          st.error("Incorrect Old Password! (পুরাতন পাসওয়ার্ড ভুল!)")

    st.write("---")
    st.write("### 👥 Agent Management (এজেন্ট ম্যানেজমেন্ট)")
    
    c.execute("SELECT username, role, fullname, phone, created_at, is_active FROM users")
    agents = c.fetchall()
    st.write(f"Total Users: **{len(agents)}** (মোট ইউজার)")

    users_report_df = pd.read_sql_query("SELECT username, role, fullname, phone, created_at FROM users", conn)
    if not users_report_df.empty:
      html_users_report = generate_html_report("System Users & Agents Directory", users_report_df)
      st.download_button(
          label="📥 Download Users & Agents Report (PDF/HTML)",
          data=html_users_report,
          file_name="mediseller_users_report.html",
          mime="text/html",
          type="primary"
      )
      st.write("---")

    for ag in agents:
      u_name, u_role, f_name, u_phone, c_date, is_act = ag
      display_name = f_name if f_name else "No name (নাম নেই)"
      
      try:
        join_date = datetime.strptime(c_date, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y %H:%M:%S") if c_date else "Unknown (অজানা)"
      except:
        join_date = c_date if c_date else "Unknown (অজানা)"

      phone_disp = u_phone if u_phone else "No number (নম্বর নেই)"
      
      with st.expander(f"👤 {display_name} ({u_name})"):
        st.write(f"📞 Phone: `{phone_disp}`")
        st.write(f"📅 Join Date: `{join_date}`")
        
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
          with st.form(f"edit_form_{u_name}"):
            new_name = st.text_input("Agent Name (নাম)", value=display_name, key=f"fname_{u_name}")
            new_phone = st.text_input("Phone Number (ফোন নম্বর)", value=phone_disp if phone_disp != "No number (নম্বর নেই)" else "", key=f"fphone_{u_name}")
            update_btn = st.form_submit_button("Save (সংরক্ষণ)")
            
            if update_btn:
              c.execute("UPDATE users SET fullname=?, phone=? WHERE username=?", (new_name, new_phone, u_name))
              conn.commit()
              st.success("Updated! (আপডেট হয়েছে!)")
              st.rerun()

        with col_ed2:
          if u_name != "admin":
            if st.button("🗑️ Delete Agent (এজেন্ট ডিলিট)", key=f"del_ag_{u_name}", type="secondary"):
              c.execute("DELETE FROM users WHERE username=?", (u_name,))
              c.execute("DELETE FROM agent_live_locations WHERE username=?", (u_name,))
              conn.commit()
              st.success("Agent deleted! (ডিলিট হয়েছে!)")
              st.rerun()

    st.write("---")
    st.write("### ➕ Add New Agent (নতুন এজেন্ট যোগ)")
    with st.form("new_agent_form"):
      n_fullname = st.text_input("Agent Name (এজেন্টের নাম)")
      n_user = st.text_input("Username (ইউজারনেম)")
      n_role = st.selectbox("Role (রোল)", ["staff", "admin"])
      add_agent_btn = st.form_submit_button("Add Agent (এজেন্ট যুক্ত করুন)")

      if add_agent_btn:
        if n_fullname and n_user:
          try:
            c.execute("INSERT INTO users (username, password, role, fullname, phone, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                      (n_user, "direct_login", n_role, n_fullname, "", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1))
            conn.commit()
            st.session_state["last_created_agent_user"] = n_user
            st.session_state["last_created_agent_name"] = n_fullname
            st.success("Agent added successfully! (যোগ করা হয়েছে!)")
            st.rerun()
          except sqlite3.IntegrityError:
            st.error("Username already exists. (ইউজারনেমটি রয়েছে।)")
        else:
          st.error("Fill name and username. (নাম ও ইউজারনেম দিন।)")

    if st.session_state.get("last_created_agent_user"):
      created_u = st.session_state["last_created_agent_user"]
      created_n = st.session_state["last_created_agent_name"]
      
      st.markdown("---")
      st.write(f"#### 🔗 Direct Link (ডাইরেক্ট লিংক)")
      
      direct_msg = f"Hello {created_n}, your account has been created in P.S Mediseller. Click below to login:\n"
      
      copy_html = f"""
      <div style="background: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #475569; margin-top: 10px;">
        <p style="color: #fff; margin-bottom: 8px; font-weight: 600;">Generated Direct Link (লিংক):</p> &nbsp;
        <input type="text" id="generated_link" readonly style="width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #64748b; background: #0f172a; color: #fff; font-size: 14px; margin-bottom: 10px; box-sizing: border-box;">
        <button onclick="copyLink()" id="copy_btn" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 10px 20px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer;">📋 Copy Link (কপি)</button>
        <span id="copy_status" style="color: #34d399; margin-left: 10px; font-weight: bold; display: none;">✓ Copied! (✓ কপি হয়েছে!)</span>
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
      if st.button("✖️ Close Window (বন্ধ করুন)"):
        st.session_state.pop("last_created_agent_user", None)
        st.session_state.pop("last_created_agent_name", None)
        st.rerun()

    st.write("---")
    st.write("### 💾 Database Backup (ডাটাবেস ব্যাকআপ)")
    
    if os.path.exists("mediseller_delivery.db"):
        with open("mediseller_delivery.db", "rb") as f:
            st.download_button(
                label="📥 Download DB (ডাউনলোড)",
                data=f,
                file_name="mediseller_delivery.db",
                mime="application/octet-stream",
                type="primary"
            )
    else:
        st.warning("No database file found. (নেই।)")

    st.write("---")
    st.write("### 📤 Restore DB (ডাটাবেস রিস্টোর)")
    uploaded_db = st.file_uploader("Upload .db file (.db ফাইল আপলোড)", type=["db"])

    if uploaded_db is not None:
        if st.button("⚠️ Confirm & Restore (রিস্টোর নিশ্চিত)", type="primary"):
            with open("mediseller_delivery.db", "wb") as f:
                f.write(uploaded_db.getbuffer())
            st.success("Database restored! Please refresh. (রিস্টোর হয়েছে!)")
            st.rerun()
