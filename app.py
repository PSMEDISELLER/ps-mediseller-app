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
    page_icon="??",
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
        <div style="font-size: 48px; margin-bottom: 15px;">??</div>
        <h2 style="color: #f87171; margin-top: 0; font-size: 22px;">Location Permission Required<br>(?????? ??????? ??????)</h2>
        <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin-bottom: 25px;">
            P.S Mediseller app requires your live GPS location to function properly. Please enable Location/GPS on your device and grant permission.<br><br>
            <b>(??????? ????????? ???? ????? ????? ?????? ?????? ?? ???? ??? ??????? ???? ?????? ???? ????? ????? ??????? ??? ???? ???)</b>
        </p>
        <button onclick="requestLocation()" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border: none; padding: 14px 28px; border-radius: 10px; font-weight: bold; font-size: 16px; cursor: pointer; width: 100%; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);">
            ?? Grant Permission / Retry (?????? ??? / ???????)
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
                    status.innerText = "?? Location permission denied! Please enable it in browser & phone settings. (?????? ??????? ???)";
                } else if (error.code === error.POSITION_UNAVAILABLE) {
                    status.innerText = "?? GPS signal unavailable. Please turn on phone GPS/Location. (?????? ?? ????)";
                } else {
                    status.innerText = "?? Please enable location to continue. (?????? ?? ????)";
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
        status.innerText = "? Requesting location permission... (?????? ????? ?????...)";
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

.main-title {
    font-size: 24px;
    font-weight: bold;
    color: #ffffff;
    text-align: center;
    margin-bottom: 20px;
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

c.execute("SELECT id, order_date, status FROM orders")
for row_ord in c.fetchall():
  try:
    o_time = datetime.strptime(row_ord[1], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    if (current_dt_str - o_time) > timedelta(days=7):
      c.execute("DELETE FROM orders WHERE id=?", (row_ord[0],))
  except:
    pass

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
      <button class="print-btn" onclick="window.print()">??? Print / Save as PDF (??????? / ??????)</button>
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
            st.success(f"Welcome, {f_name}! Logged in. (???????, {f_name}!)")
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
    if st.button("?? Logout (?????)", key="logout_btn_top"):
      st.session_state["username"] = "delivery"
      st.session_state["user_role"] = "staff"
      st.markdown("""
      <script>
          localStorage.removeItem('ps_mediseller_user');
      </script>
      """, unsafe_allow_html=True)
      st.rerun()
  else:
    if st.button("?? Admin Login (????????)", key="login_btn_top"):
      st.session_state["show_admin_login"] = True
      st.rerun()

c.execute("SELECT fullname FROM users WHERE username=?", (st.session_state['username'],))
curr_user_row = c.fetchone()
current_fullname = curr_user_row[0] if curr_user_row and curr_user_row[0] else st.session_state['username']

col_u1, _ = st.columns([3, 1])
with col_u1:
  st.write(f"?? User: **{current_fullname}** (`{st.session_state['user_role']}`)")

if st.session_state.get("show_admin_login", False):
  with st.form("admin_login_popup_form"):
    st.write("#### ?? Admin Login (???????? ????)")
    admin_pass_input = st.text_input("Enter Admin Password (?????????? ???)", type="password")
    col_al1, col_al2 = st.columns(2)
    with col_al1:
      submit_admin = st.form_submit_button("Login (????)", type="primary")
    with col_al2:
      cancel_admin = st.form_submit_button("Cancel (?????)")

    if submit_admin:
      c.execute("SELECT password, role FROM users WHERE username='admin'")
      adm_row = c.fetchone()
      if adm_row and adm_row[0] == admin_pass_input:
        st.session_state["username"] = "admin"
        st.session_state["user_role"] = "admin"
        st.session_state["show_admin_login"] = False
        st.success("Admin login successful! (???!)")
        st.rerun()
      else:
        st.error("Incorrect Password! (??? ??????????!)")
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
    "?? Add Location (?????? ???)",
    "?? Search & Details (????????? ? ?????)",
    "?? Pending Orders (???? ??????)",
    "?? Daily & Monthly Work (????? ? ????? ???)",
    "?? Due & Delivery (????? ? ????????)",
    "??? Route Map (??? ?????)",
    "?? Attendance (????????)",
]
if st.session_state["user_role"] == "admin":
  menu_options.extend([
      "?? Live Tracking (???? ?????????)", 
      "?? Settings & Agents (??????)"
  ])

current_page_param = query_params.get("page", menu_options[0])
if current_page_param not in menu_options:
  current_page_param = menu_options[0]

default_index = menu_options.index(current_page_param)

selected_menu = st.radio("Select Menu (???? ???????):", menu_options, index=default_index, horizontal=False, label_visibility="collapsed")

if selected_menu != current_page_param:
  st.query_params["page"] = selected_menu
  st.rerun()

st.write("---")

# =========================================================
# 1. ADD NEW LOCATION & ORDER / VISIT ENTRY
# =========================================================
if selected_menu == "?? Add Location (?????? ???)":
  st.write("### ?? Add Location & Party (?????? ? ??????)")
  
  selected_entry_tab = st.radio(
      "Select Entry Mode (??? ???????):",
      [
          "?? With Map Party (????? ?? ??????)",
          "????? Without Map Party (????? ???? ??????)"
      ],
      label_visibility="collapsed"
  )
  
  st.write("")

  if "With Map Party" in selected_entry_tab:
    with st.form("location_details_form", clear_on_submit=True):
      st.write("#### 1. Enter Party Details (??????? ?????)")
      col_f1, col_f2, col_f3 = st.columns(3)
      with col_f1:
        p_name = st.text_input("Party Name (??????? ???)", key="input_p_name")
      with col_f2:
        p_addr = st.text_input("Address (??????)", key="input_p_addr")
      with col_f3:
        p_phone = st.text_input("Phone Number (??? ?????)", key="input_p_phone")
      
      submitted_loc = st.form_submit_button("?? Save Location (??? ????)", type="primary")

    if submitted_loc:
      if p_name.strip() and p_phone.strip():
        c.execute("SELECT id FROM locations WHERE LOWER(party_name) = LOWER(?) OR party_phone = ?", (p_name.strip(), p_phone.strip()))
        existing_check = c.fetchone()
        
        if existing_check:
          st.error("Party name or phone already exists! (???????? ??? ??? ???!)")
        else:
          try:
            current_date_str = get_ist_time().strftime("%Y-%m-%d")
            c.execute(
                "INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, ?, ?)",
                (p_name.strip(), p_addr, p_phone.strip(), st.session_state["selected_lat"], st.session_state["selected_lon"]),
            )
            c.execute(
                "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
                (p_name.strip(), "Visit (?????)", current_date_str)
            )
            conn.commit()
            st.success("Location saved and visit recorded successfully! (??? ?????!)")
            st.rerun()
          except sqlite3.IntegrityError:
            st.error("Party already exists! (???????? ???!)")
      else:
        st.error("Party name and phone required. (??? ? ??? ???????)")

  else:
    with st.form("doctor_details_form", clear_on_submit=True):
      st.write("#### 2. Without Map Party Details (????? ???? ??????? ?????)")
      col_d1, col_d2, col_d3 = st.columns(3)
      with col_d1:
        doc_name = st.text_input("Name (???)", key="input_doc_name")
      with col_d2:
        doc_addr = st.text_input("Address (??????/???????)", key="input_doc_addr")
      with col_d3:
        doc_phone = st.text_input("Phone (??? ?????)", key="input_doc_phone")
      
      submitted_doc = st.form_submit_button("?? Save Without Map Party (??? ????)", type="primary")

    if submitted_doc:
      if doc_name.strip() and doc_phone.strip():
        c.execute("SELECT id FROM locations WHERE LOWER(party_name) = LOWER(?) OR party_phone = ?", (doc_name.strip(), doc_phone.strip()))
        existing_check_doc = c.fetchone()

        if existing_check_doc:
          st.error("Party name or phone already exists! (???????? ??? ??? ???!)")
        else:
          try:
            c.execute(
                "INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, NULL, NULL)",
                (doc_name.strip(), doc_addr, doc_phone.strip()),
            )
            c.execute(
                "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
                (doc_name.strip(), "Visit (?????)", get_ist_time().strftime("%Y-%m-%d"))
            )
            conn.commit()
            st.success("Saved successfully! (??????? ??? ?????!)")
            st.rerun()
          except sqlite3.IntegrityError:
            st.error("Party already exists! (???????? ???!)")
      else:
        st.error("Name and phone required. (??? ? ??? ???????)")

  st.write("---")
  st.write("#### Select Location from Map (????? ???? ??????? ????)")
  
  col_m1, col_m2 = st.columns([1, 4])
  with col_m1:
    if st.button("?? Current Loc (??????? ??????)"):
      if gps_lat and gps_lon:
        st.session_state["selected_lat"] = gps_lat
        st.session_state["selected_lon"] = gps_lon
        st.success("GPS location taken! (????? ?????!)")
        st.rerun()
      else:
        st.warning("GPS not found! (???!)")
  with col_m2:
    st.write(f"Coordinates (?????????): `{st.session_state['selected_lat']:.5f}, {st.session_state['selected_lon']:.5f}`")

  advanced_map = folium.Map(
      location=[st.session_state["selected_lat"], st.session_state["selected_lon"]],
      zoom_start=17,
      tiles=None
  )

  street_layer = folium.TileLayer(
      tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
      attr="Google Maps Street",
      name="Street View (??????? ???)",
      overlay=False,
      control=True,
      show=True
  )
  street_layer.add_to(advanced_map)

  satellite_layer = folium.TileLayer(
      tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
      attr="Google Maps Satellite",
      name="Satellite View (?????????? ???)",
      overlay=False,
      control=True,
      show=False
  )
  satellite_layer.add_to(advanced_map)

  folium.Marker(
      [st.session_state["selected_lat"], st.session_state["selected_lon"]],
      popup="<b>Selected Point (????????? ??????)</b>",
      tooltip="Will save here (????? ??? ???)",
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
        popup="Your GPS Location (?????? ??????)"
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
  st.write("### ?? Orders & Visits (?????? ? ?????)")

  st.write("?? **Search & Select Party (?????? ????? ? ??????? ????):**")
  order_search_text = st.text_input("Search Party", placeholder="Type name, address or keyword...", key="order_party_search_text_input", label_visibility="collapsed")
  
  if order_search_text.strip():
    q_term = f"%{order_search_text.strip()}%"
    c.execute("SELECT party_name FROM locations WHERE party_name LIKE ? OR address LIKE ? OR party_phone LIKE ? ORDER BY party_name ASC", (q_term, q_term, q_term))
    filtered_parties_list = [r[0] for r in c.fetchall()]
  else:
    c.execute("SELECT party_name FROM locations ORDER BY party_name ASC")
    filtered_parties_list = [r[0] for r in c.fetchall()]

  if order_search_text.strip() and filtered_parties_list:
    st.markdown(f"<p style='color: #60a5fa; font-size: 12px; margin: 2px 0;'>?? Suggestions ({len(filtered_parties_list)} found): Select below</p>", unsafe_allow_html=True)
    selected_order_party_native = st.radio(
        "Matching Parties",
        filtered_parties_list[:10],
        key="order_floating_suggestions_radio",
        label_visibility="collapsed"
    )
  else:
    if filtered_parties_list:
      selected_order_party_native = st.selectbox("Select Party", filtered_parties_list, label_visibility="collapsed", key="order_select_party_box")
    else:
      st.warning("No matching party found! (???? ?????? ????? ?????!)")
      selected_order_party_native = ""

  with st.form("order_visit_entry_form"):
    ord_details = st.text_area("Order Details (?????? ?????)")
    
    col_ob1, col_ob2 = st.columns(2)
    with col_ob1:
      submitted_order = st.form_submit_button("?? Submit Order (?????? ???)", type="primary")
    with col_ob2:
      submitted_visit = st.form_submit_button("?? Save Visit (????? ???)")

    if submitted_order:
      if not selected_order_party_native.strip():
        st.error("Please select a party. (?????? ??????? ?????)")
      else:
        current_date_str = get_ist_time().strftime("%Y-%m-%d")
        c.execute(
            "INSERT INTO orders (party_name, order_details, order_date, status, payment_collected) VALUES (?, ?, ?, ?, ?)",
            (selected_order_party_native.strip(), ord_details.strip(), get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), "Pending", "0")
        )
        c.execute(
            "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
            (selected_order_party_native.strip(), "Order (??????)", current_date_str)
        )
        conn.commit()
        st.success("Order submitted successfully! (??? ????? ?????!)")
        st.rerun()

    if submitted_visit:
      if not selected_order_party_native.strip():
        st.error("Please select a party. (?????? ??????? ?????)")
      else:
        current_date_str = get_ist_time().strftime("%Y-%m-%d")
        c.execute(
            "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
            (selected_order_party_native.strip(), "Visit (?????)", current_date_str)
        )
        conn.commit()
        st.success("Visit saved successfully! (??? ?????!)")
        st.rerun()

  st.write("---")
  st.write("#### ?? Recent Orders & Visits (?????????? ???????)")
  report_df = pd.read_sql_query("SELECT * FROM daily_work ORDER BY work_date DESC, id DESC LIMIT 20", conn)
  if not report_df.empty:
    if st.session_state["user_role"] == "admin":
      full_report_df = pd.read_sql_query("SELECT * FROM daily_work ORDER BY work_date DESC, id DESC", conn)
      html_all_report = generate_html_report("Daily Work & Visit Report", full_report_df)
      st.download_button(
          label="?? Download Daily Work Report (PDF/HTML)",
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
    st.info("No reports found. (???? ??????? ????)")

# =========================================================
# 2. SEARCH PARTY DETAILS & ADMIN DELETE OPTION
# =========================================================
elif selected_menu == "?? Search & Details (????????? ? ?????)":
  st.write("### ?? Search & Party Management (????? ? ????????????)")

  if st.session_state.get("mapping_party_id"):
    st.markdown(f"### ?? Set Map for **{st.session_state['mapping_party_name']}**")
    st.write("Click correct location on map and click **'Save Location'** below.")
    
    if "temp_map_lat" not in st.session_state:
      st.session_state["temp_map_lat"] = 22.8620
    if "temp_map_lon" not in st.session_state:
      st.session_state["temp_map_lon"] = 87.3320

    col_tm1, col_tm2 = st.columns([1, 4])
    with col_tm1:
      if st.button("?? Current GPS (??????? ??????)", key="btn_curr_gps_temp"):
        if gps_lat and gps_lon:
          st.session_state["temp_map_lat"] = gps_lat
          st.session_state["temp_map_lon"] = gps_lon
          st.success("GPS taken! (????? ?????!)")
          st.rerun()
        else:
          st.warning("GPS not found! (???!)")
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
        name="Street View (??????? ???)",
        show=True
    ).add_to(pick_map)
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google Maps Satellite",
        name="Satellite View (?????????? ???)",
        show=False
    ).add_to(pick_map)

    folium.Marker(
        [st.session_state["temp_map_lat"], st.session_state["temp_map_lon"]],
        popup="<b>Set Here (????? ???)</b>",
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
          popup="Your Location (????? ??????)"
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
      if st.button("? Save Location (??? ????)", type="primary", key="save_party_map_ok"):
        target_id = st.session_state["mapping_party_id"]
        t_lat = st.session_state["temp_map_lat"]
        t_lon = st.session_state["temp_map_lon"]
        c.execute("UPDATE locations SET lat=?, lon=? WHERE id=?", (t_lat, t_lon, target_id))
        conn.commit()
        st.session_state.pop("mapping_party_id", None)
        st.session_state.pop("mapping_party_name", None)
        st.success(f"Map saved successfully! (??? ?????!)")
        st.rerun()
    with col_b2:
      if st.button("? Cancel (?????)", key="cancel_party_map"):
        st.session_state.pop("mapping_party_id", None)
        st.session_state.pop("mapping_party_name", None)
        st.rerun()

    st.markdown("---")
    st.stop()

  st.write("?? **Search Party/Doctor (?????? ??????):**")
  master_search_query = st.text_input("Search", placeholder="Type name, address or keyword and press enter...", key="master_search_input_box", label_visibility="collapsed")

  if master_search_query.strip():
    q_term = f"%{master_search_query.strip()}%"
    df = pd.read_sql_query(
        "SELECT * FROM locations WHERE party_name LIKE ? OR address LIKE ? OR party_phone LIKE ? ORDER BY party_name ASC",
        conn,
        params=(q_term, q_term, q_term)
    )
  else:
    df = pd.read_sql_query("SELECT * FROM locations ORDER BY party_name ASC", conn)

  if st.session_state["user_role"] == "admin" and not df.empty:
    html_locs_df = generate_html_report("Locations & Parties Directory", df)
    st.download_button(
        label="?? Download Locations Report (PDF/HTML)",
        data=html_locs_df,
        file_name="mediseller_locations_report.html",
        mime="text/html",
        type="primary"
    )
    st.write("---")

  doc_df = df[df["lat"].isna() | df["lon"].isna()]
  mapped_df = df[df["lat"].notna() & df["lon"].notna()]

  with st.expander(f"????? Non-Map List ({len(doc_df)} Entries) (?????????? ??????)", expanded=True):
    if not doc_df.empty:
      for index, row in doc_df.iterrows():
        cols = st.columns([3, 2, 2, 2, 1.5])
        cols[0].write(f"**{row['party_name']}**")
        cols[1].write(row['party_phone'] if row['party_phone'] else "No number (????? ???)")
        cols[2].write(row['address'] if row['address'] else "No address (?????? ???)")
        
        if cols[3].button("?? Add Map (????? ?????)", key=f"map_add_search_{row['id']}"):
          st.session_state["mapping_party_id"] = row['id']
          st.session_state["mapping_party_name"] = row['party_name']
          st.session_state["temp_map_lat"] = st.session_state.get("selected_lat", 22.8620)
          st.session_state["temp_map_lon"] = st.session_state.get("selected_lon", 87.3320)
          st.rerun()

        if st.session_state["user_role"] == "admin":
          if cols[4].button("??? Delete (?????)", key=f"del_doc_search_{row['id']}"):
            c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
            conn.commit()
            st.success("Deleted! (????? ?????!)")
            st.rerun()
        st.write("---")
    else:
      st.info("No non-map parties found. (?????????? ?????? ????)")

  st.write("---")
  st.write(f"#### ?? Mapped List ({len(mapped_df)} Records) (?????????? ??????)")
  if not mapped_df.empty:
    for index, row in mapped_df.iterrows():
      if st.session_state["user_role"] == "admin":
        cols = st.columns([3, 2, 2, 2, 1.5])
      else:
        cols = st.columns([3, 2, 2, 2])

      cols[0].write(f"**{row['party_name']}**")
      cols[1].write(row['party_phone'] if row['party_phone'] else "No number (????? ???)")
      cols[2].write(row['address'] if row['address'] else "No address (?????? ???)")
      
      maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}"
      cols[3].markdown(f'<a href="{maps_url}" target="_blank" style="text-decoration:none;"><button style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color:white; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; font-weight:600;">?? Direction (???????)</button></a>', unsafe_allow_html=True)

      if st.session_state["user_role"] == "admin":
        if cols[4].button("??? Delete (?????)", key=f"del_loc_search_{row['id']}"):
          c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
          conn.commit()
          st.success("Deleted! (????? ?????!)")
          st.rerun()

      st.write("---")
  else:
    st.info("No mapped parties found. (?????????? ?????? ????)")

# =========================================================
# 3. PENDING ORDERS & COMPLETED ORDERS HISTORY
# =========================================================
elif selected_menu == "?? Pending Orders (???? ??????)":
  st.write("### ?? Orders Management (?????? ????????????)")
  
  if st.session_state["user_role"] == "admin":
    ord_tab1, ord_tab2 = st.tabs(["? Pending Orders (???????)", "?? Completed History (??????? ??????)"])
  else:
    ord_tab1 = st.container()
    ord_tab2 = None

  with ord_tab1:
    st.write("#### ? Active Pending Orders")
    if st.session_state["user_role"] == "admin":
      all_ord_df = pd.read_sql_query("SELECT * FROM orders WHERE status='Pending' ORDER BY order_date DESC", conn)
      if not all_ord_df.empty:
        html_ord_report = generate_html_report("Pending Orders Report", all_ord_df)
        st.download_button(
            label="?? Download Pending Orders Report (PDF/HTML)",
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
        cols[2].write("? Pending (???????)")

        if cols[3].button("?? Complete (???????)", key=f"ord_btn_{row['id']}"):
          c.execute("UPDATE orders SET status='Completed' WHERE id=?", (row['id'],))
          conn.commit()
          c.execute("UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?", (st.session_state["username"],))
          conn.commit()
          st.success("Order completed! (??????? ??? ?????!)")
          st.rerun()
        st.write("---")
    else:
      st.info("No pending orders. (??????? ?????? ????)")

  if ord_tab2 is not None:
    with ord_tab2:
      st.write("#### ?? Completed Orders History")
      completed_ord_df = pd.read_sql_query("SELECT * FROM orders WHERE status='Completed' ORDER BY order_date DESC", conn)
      if not completed_ord_df.empty:
        html_comp_ord = generate_html_report("Completed Orders History", completed_ord_df)
        st.download_button(
            label="?? Download Completed Orders Report (PDF/HTML)",
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
          cols[2].write("? Completed (???????)")
          st.write("---")
      else:
        st.info("No completed orders history.")

# =========================================================
# 4. DAILY & MONTHLY WORK
# =========================================================
elif selected_menu == "?? Daily & Monthly Work (????? ? ????? ???)":
  st.write("### ?? Daily & Monthly Work Report (????? ? ????? ????? ???????)")

  work_tab1, work_tab2 = st.tabs([
      "?? Daily Work (????? ???)", 
      "?? Monthly Summary & Zero Activity (????? ?????? ? ???? ????????????)"
  ])

  with work_tab1:
    st.write("#### ?? Visit & Order List (????? ???????)")

    if st.session_state["user_role"] == "admin":
      full_dw_df = pd.read_sql_query("SELECT * FROM daily_work ORDER BY work_date DESC, id DESC", conn)
      if not full_dw_df.empty:
        html_dw_report = generate_html_report("Daily Work Report", full_dw_df)
        st.download_button(
            label="?? Download Daily Work Report (PDF/HTML)",
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

        with st.expander(f"?? Date: {formatted_d} (Total: {count_parties})", expanded=False):
          if st.session_state["user_role"] == "admin":
            if st.button(f"??? Delete Date Data ({formatted_d}) (?? ?????)", key=f"del_date_{d_str}", type="secondary"):
              c.execute("DELETE FROM daily_work WHERE work_date=?", (d_str,))
              conn.commit()
              st.success("Deleted! (???? ???? ?????!)")
              st.rerun()
            st.write("---")

          for idx, w_row in date_records.iterrows():
            cols = st.columns([3, 2, 1.5])
            cols[0].write(f"Party: **{w_row['party_name']}**")
            cols[1].write(f"Status: `{w_row['activity_type']}`")
            
            if st.session_state["user_role"] == "admin":
              if cols[2].button("??? Delete (?????)", key=f"del_dw_{w_row['id']}"):
                c.execute("DELETE FROM daily_work WHERE id=?", (w_row['id'],))
                conn.commit()
                st.success("Deleted! (????? ?????!)")
                st.rerun()
            else:
              cols[2].write("?? Locked (???)")
            st.write("---")
    else:
      st.info("No records found. (???? ?????? ????)")

  with work_tab2:
    st.write("#### ?? Monthly Doctor/Party Activity Report (????? ??????? ? ?????? ???????)")
    
    st.write("??? **Select Year & Month (??? ? ??? ??????? ????):**")
    col_yr, col_mo = st.columns(2)
    with col_yr:
      selected_year = st.selectbox("Select Year (???)", [2026, 2025, 2024], index=0)
    with col_mo:
      months_dict = {
          "01": "January (?????????)", "02": "February (???????????)", "03": "March (?????)", 
          "04": "April (??????)", "05": "May (??)", "06": "June (???)", 
          "07": "July (?????)", "08": "August (?????)", "09": "September (??????????)", 
          "10": "October (???????)", "11": "November (???????)", "12": "December (????????)"
      }
      current_mo_num = get_ist_time().strftime("%m")
      selected_mo_key = st.selectbox("Select Month (???)", list(months_dict.keys()), format_func=lambda x: months_dict[x], index=list(months_dict.keys()).index(current_mo_num) if current_mo_num in months_dict else 7)
    
    selected_month = f"{selected_year}-{selected_mo_key}"

    if selected_month.strip():
      all_locs_df = pd.read_sql_query("SELECT party_name, address, lat, lon FROM locations ORDER BY party_name ASC", conn)
      
      if not all_locs_df.empty:
        report_data = []
        
        for idx, loc_row in all_locs_df.iterrows():
          p_name = loc_row['party_name']
          is_mapped = "Mapped (??????????)" if pd.notna(loc_row['lat']) and pd.notna(loc_row['lon']) else "Non-Map (??????????)"
          
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

        st.write(f"##### ?? Complete Activity Summary for `{selected_month}`")
        
        if st.session_state["user_role"] == "admin":
          html_summary = generate_html_report(f"Monthly Summary - {selected_month}", report_summary_df)
          st.download_button(
              label="?? Download Monthly Summary Report (PDF/HTML)",
              data=html_summary,
              file_name=f"mediseller_monthly_summary_{selected_month}.html",
              mime="text/html",
              type="primary"
          )
          st.write("---")

        st.dataframe(report_summary_df, use_container_width=True)

        zero_activity_df = report_summary_df[(report_summary_df["Total Visits"] == 0) & (report_summary_df["Total Orders"] == 0)]
        
        st.write(f"?? **Doctors/Parties with ZERO Visits & ZERO Orders ({len(zero_activity_df)}):**")
        if not zero_activity_df.empty:
          st.dataframe(zero_activity_df, use_container_width=True)
        else:
          st.success("All parties/doctors had at least one visit or order this month! (?? ????????? ????? ?? ?????? ?????!)")

        if st.session_state["user_role"] == "admin":
          st.write("---")
          st.write("#### ?? Admin Actions for this Month")
          if st.button(f"??? Delete All Work Records for Month: {selected_month} (?? ????? ?? ???? ?????)", type="secondary"):
            c.execute("DELETE FROM daily_work WHERE work_date LIKE ?", (f"{selected_month}%",))
            conn.commit()
            st.success(f"All records for {selected_month} deleted successfully! (???? ???? ?????!)")
            st.rerun()
      else:
        st.info("No parties/doctors found in database. (???? ?????? ????)")

# =========================================================
# 5. DUE CLEAR, DELIVERY PLAN & CARD-BASED UI (GROUPED BY AGENT FULLNAME)
# =========================================================
elif selected_menu == "?? Due & Delivery (????? ? ????????)":
  st.markdown('<div class="main-title">?? ???????? ? ??? ??????? (????? ????? ???)</div>', unsafe_allow_html=True)
  
  c.execute("SELECT username, fullname FROM users")
  users_data = c.fetchall()
  all_agents = [r[0] for r in users_data]
  agent_name_map = {r[0]: (r[1] if r[1] else r[0]) for r in users_data}

  c.execute("SELECT party_name, lat, lon FROM locations ORDER BY party_name ASC")
  loc_data = c.fetchall()
  party_coords = {r[0]: (r[1], r[2]) for r in loc_data}
  all_parties = [r[0] for r in loc_data]

  task_tab1, task_tab2, task_tab3 = st.tabs([
      "?? Active Tasks (????? ???)", 
      "?? Agent Date-wise Summary (?????? ? ????? ??????? ??????)",
      "?? Completed Tasks History (??????? ???)"
  ])

  with task_tab1:
    if st.session_state["user_role"] == "admin":
      full_tasks_df = pd.read_sql_query("""
          SELECT t.id, u.fullname as agent_fullname, t.agent_name, t.party_name, t.task_type, t.due_amount, t.status, t.created_at, l.address 
          FROM task_assignments t 
          LEFT JOIN users u ON t.agent_name = u.username 
          LEFT JOIN locations l ON t.party_name = l.party_name 
          WHERE t.status='Pending' 
          ORDER BY t.id DESC
      """, conn)
      if not full_tasks_df.empty:
        export_tasks_df = full_tasks_df.copy()
        export_tasks_df['agent_name'] = export_tasks_df.apply(lambda r: r['agent_fullname'] if pd.notna(r['agent_fullname']) and r['agent_fullname'] else r['agent_name'], axis=1)
        export_tasks_df = export_tasks_df[['agent_name', 'party_name', 'task_type', 'due_amount', 'created_at', 'address']]
        
        html_tasks_report = generate_html_report("Active Tasks & Deliveries Report", export_tasks_df)
        st.download_button(
            label="?? Download Tasks Report (PDF/HTML)",
            data=html_tasks_report,
            file_name="mediseller_due_delivery_report.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")

    st.write("?? **Search & Select Party (?????? ????? ? ??????? ????):**")
    task_search_text = st.text_input("Search Party for Task", placeholder="Type name, address or keyword...", key="task_party_search_text_input", label_visibility="collapsed")
    
    if task_search_text.strip():
      q_term = f"%{task_search_text.strip()}%"
      c.execute("SELECT party_name FROM locations WHERE party_name LIKE ? OR address LIKE ? OR party_phone LIKE ? ORDER BY party_name ASC", (q_term, q_term, q_term))
      filtered_task_parties = [r[0] for r in c.fetchall()]
    else:
      filtered_task_parties = all_parties

    if task_search_text.strip() and filtered_task_parties:
      st.markdown(f"<p style='color: #60a5fa; font-size: 12px; margin: 2px 0;'>?? Suggestions ({len(filtered_task_parties)} found): Select below</p>", unsafe_allow_html=True)
      sel_pt = st.radio(
          "Matching Task Parties",
          filtered_task_parties[:10],
          key="task_floating_suggestions_radio",
          label_visibility="collapsed"
      )
    else:
      if filtered_task_parties:
        sel_pt = st.selectbox("Select Party", filtered_task_parties, label_visibility="collapsed", key="task_select_party_box")
      else:
        st.warning("No matching party found! (???? ?????? ????? ?????!)")
        sel_pt = ""

    with st.form("easy_assign_form"):
      sel_ag = st.selectbox("Select Agent (?????? ???????)", all_agents, format_func=lambda x: agent_name_map.get(x, x))

      st.write("**Work Type (????? ???):**")
      col_chk1, col_chk2 = st.columns(2)
      with col_chk1:
        chk_delivery = st.checkbox("?? Delivery (????????)")
      with col_chk2:
        chk_due = st.checkbox("?? Due Collection (??? ???????)")

      d_amount = st.text_input("Due Amount (??? ????)", "0")

      submit_easy_task = st.form_submit_button("?? Add Task (??? ???)", type="primary")

      if submit_easy_task:
        if not sel_pt.strip():
          st.error("Please select a party. (?????? ??????? ?????)")
        else:
          selected_tasks = []
          if chk_delivery:
            selected_tasks.append("Delivery (????????)")
          if chk_due:
            selected_tasks.append("Due Collection (??? ???????)")

          if selected_tasks:
            t_type_str = " & ".join(selected_tasks)
            current_date_str = get_ist_time().strftime("%Y-%m-%d")
            c.execute(
                "INSERT INTO task_assignments (agent_name, party_name, task_type, due_amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (sel_ag, sel_pt.strip(), t_type_str, d_amount, "Pending", get_ist_time().strftime("%Y-%m-%d %H:%M:%S")),
            )
            c.execute(
                "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
                (sel_pt.strip(), "Visit (?????)", current_date_str)
            )
            conn.commit()
            st.success("Task assigned! (??? ???????? ??? ?????!)")
            st.rerun()
          else:
            st.warning("Select at least one work type. (????? ??? ??????? ?????)")

    st.write("---")
    st.markdown("### ?? Current Tasks Grouped by Worker (????? ??????? ??????? ???)")

    if st.session_state["user_role"] == "admin":
      tasks_all_df = pd.read_sql_query("""
          SELECT t.*, l.address, u.fullname as agent_fullname 
          FROM task_assignments t 
          LEFT JOIN locations l ON t.party_name = l.party_name 
          LEFT JOIN users u ON t.agent_name = u.username
          WHERE t.status='Pending' 
          ORDER BY t.id DESC
      """, conn)
      if not tasks_all_df.empty:
        grouped_by_worker = {}
        for _, row in tasks_all_df.iterrows():
          ag_uname = row['agent_name']
          ag_fname = row['agent_fullname'] if pd.notna(row['agent_fullname']) and row['agent_fullname'] else ag_uname
          if ag_fname not in grouped_by_worker:
            grouped_by_worker[ag_fname] = []
          grouped_by_worker[ag_fname].append({
              "id": row['id'],
              "agent_name": ag_uname,
              "agent_display": ag_fname,
              "party_name": row['party_name'],
              "type": row['task_type'],
              "due_amount": row['due_amount'],
              "created_at": row['created_at'],
              "address": row['address'] if pd.notna(row['address']) else ""
          })

        for worker_display_name, worker_tasks in grouped_by_worker.items():
          total_tasks = len(worker_tasks)
          delivery_count = sum(1 for t in worker_tasks if "Delivery" in str(t.get("type", "")))
          due_count = sum(1 for t in worker_tasks if "Due" in str(t.get("type", "")))
          total_due_amount = sum(float(t.get("due_amount", 0) or 0) for t in worker_tasks)

          expander_title = (
              f"?? {worker_display_name} | ????????: {delivery_count} | ?????: {due_count}"
              f" | ??? ???: ???? {total_due_amount}"
          )

          with st.expander(expander_title, expanded=True):
            deliveries = [t for t in worker_tasks if "Delivery" in str(t.get("type", ""))]
            due_collections = [t for t in worker_tasks if "Due" in str(t.get("type", ""))]

            if deliveries:
              st.markdown("##### ?? ???????? ??????")
              for t in deliveries:
                party_name = t.get("party_name", "????? ??????")
                address = t.get("address", "")
                details = t.get("type", "")

                map_url = (
                    f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(address)}"
                    if address
                    else "#"
                )

                col1, col2 = st.columns([5, 1])
                with col1:
                  st.markdown(f"- **{party_name}** — {details}")
                with col2:
                  st.markdown(f"[?? ???????]({map_url})")

                auto_completed = False
                if gps_lat and gps_lon and party_name in party_coords:
                  p_coords = party_coords[party_name]
                  if p_coords[0] is not None and p_coords[1] is not None:
                    p_lat, p_lon = p_coords
                    import math
                    dist = math.sqrt((gps_lat - p_lat)**2 + (gps_lon - p_lon)**2) * 111000
                    if dist <= 30:
                      auto_completed = True

                c_col1, c_col2 = st.columns(2)
                with c_col1:
                  if st.button(f"? ??? ??????? ({party_name})", key=f"done_{t['id']}", use_container_width=True) or auto_completed:
                    c.execute("UPDATE task_assignments SET status='Completed' WHERE id=?", (t['id'],))
                    if "Delivery" in str(t['type']):
                      c.execute("UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?", (t['agent_name'],))
                    if "Due" in str(t['type']):
                      c.execute("UPDATE agent_live_locations SET completed_dues = completed_dues + 1 WHERE username=?", (t['agent_name'],))
                    conn.commit()
                    st.success(f"'{party_name}' ?? ????? ??????? ??????? ?????? ??? ??? ?????!")
                    st.rerun()
                with c_col2:
                  if st.button(f"??? Delete ({party_name})", key=f"del_task_admin_{t['id']}", use_container_width=True):
                    c.execute("DELETE FROM task_assignments WHERE id=?", (t['id'],))
                    conn.commit()
                    st.success("Deleted by admin! (????? ?????!)")
                    st.rerun()
                st.markdown("---")

            if due_collections:
              st.markdown("##### ?? ??? ??????? ??????")
              for t in due_collections:
                party_name = t.get("party_name", "????? ??????")
                due_amount = t.get("due_amount", 0)
                address = t.get("address", "")

                map_url = (
                    f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(address)}"
                    if address
                    else "#"
                )

                col1, col2 = st.columns([5, 1])
                with col1:
                  st.markdown(f"- **{party_name}** — ?????: ???? {due_amount}")
                with col2:
                  st.markdown(f"[?? ???????]({map_url})")

                c_col1, c_col2 = st.columns(2)
                with c_col1:
                  if st.button(f"? ??? ??????? ??????? ({party_name})", key=f"done_due_{t['id']}", use_container_width=True):
                    c.execute("UPDATE task_assignments SET status='Completed' WHERE id=?", (t['id'],))
                    c.execute("UPDATE agent_live_locations SET completed_dues = completed_dues + 1 WHERE username=?", (t['agent_name'],))
                    conn.commit()
                    st.success(f"'{party_name}' ?? ??? ??????? ??????? ?????!")
                    st.rerun()
                with c_col2:
                  if st.button(f"??? Delete ({party_name})", key=f"del_task_due_admin_{t['id']}", use_container_width=True):
                    c.execute("DELETE FROM task_assignments WHERE id=?", (t['id'],))
                    conn.commit()
                    st.success("Deleted by admin! (????? ?????!)")
                    st.rerun()
                st.markdown("---")

            if not deliveries and not due_collections:
              st.info("?? ???????? ???? ????? ????")
      else:
        st.info("No pending tasks assigned. (???? ??? ????)")
    else:
      tasks_staff_df = pd.read_sql_query("""
          SELECT t.*, l.address, u.fullname as agent_fullname 
          FROM task_assignments t 
          LEFT JOIN locations l ON t.party_name = l.party_name 
          LEFT JOIN users u ON t.agent_name = u.username
          WHERE t.agent_name=? AND t.status='Pending' 
          ORDER BY t.id DESC
      """, conn, params=(st.session_state["username"],))
      if not tasks_staff_df.empty:
        worker_tasks = []
        for _, row in tasks_staff_df.iterrows():
          worker_tasks.append({
              "id": row['id'],
              "agent_name": row['agent_name'],
              "agent_display": row['agent_fullname'] if pd.notna(row['agent_fullname']) and row['agent_fullname'] else row['agent_name'],
              "party_name": row['party_name'],
              "type": row['task_type'],
              "due_amount": row['due_amount'],
              "created_at": row['created_at'],
              "address": row['address'] if pd.notna(row['address']) else ""
          })
        
        worker_display_name = worker_tasks[0]['agent_display'] if worker_tasks else st.session_state["username"]
        total_tasks = len(worker_tasks)
        delivery_count = sum(1 for t in worker_tasks if "Delivery" in str(t.get("type", "")))
        due_count = sum(1 for t in worker_tasks if "Due" in str(t.get("type", "")))
        total_due_amount = sum(float(t.get("due_amount", 0) or 0) for t in worker_tasks)

        expander_title = (
            f"?? {worker_display_name} | ????????: {delivery_count} | ?????: {due_count}"
            f" | ??? ???: ???? {total_due_amount}"
        )

        with st.expander(expander_title, expanded=True):
          deliveries = [t for t in worker_tasks if "Delivery" in str(t.get("type", ""))]
          due_collections = [t for t in worker_tasks if "Due" in str(t.get("type", ""))]

          if deliveries:
            st.markdown("##### ?? ???????? ??????")
            for t in deliveries:
              party_name = t.get("party_name", "????? ??????")
              address = t.get("address", "")
              details = t.get("type", "")

              map_url = (
                  f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(address)}"
                  if address
                  else "#"
              )

              col1, col2 = st.columns([5, 1])
              with col1:
                st.markdown(f"- **{party_name}** — {details}")
              with col2:
                st.markdown(f"[?? ???????]({map_url})")

              if st.button(f"? ??? ??????? ({party_name})", key=f"done_staff_{t['id']}", use_container_width=True):
                c.execute("UPDATE task_assignments SET status='Completed' WHERE id=?", (t['id'],))
                if "Delivery" in str(t['type']):
                  c.execute("UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?", (t['agent_name'],))
                if "Due" in str(t['type']):
                  c.execute("UPDATE agent_live_locations SET completed_dues = completed_dues + 1 WHERE username=?", (t['agent_name'],))
                conn.commit()
                st.success("??? ??????? ??? ?????!")
                st.rerun()
              st.markdown("---")

          if due_collections:
            st.markdown("##### ?? ??? ??????? ??????")
            for t in due_collections:
              party_name = t.get("party_name", "????? ??????")
              due_amount = t.get("due_amount", 0)
              address = t.get("address", "")

              map_url = (
                  f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(address)}"
                  if address
                  else "#"
              )

              col1, col2 = st.columns([5, 1])
              with col1:
                st.markdown(f"- **{party_name}** — ?????: ???? {due_amount}")
              with col2:
                st.markdown(f"[?? ???????]({map_url})")

              if st.button(f"? ??? ??????? ??????? ({party_name})", key=f"done_staff_due_{t['id']}", use_container_width=True):
                c.execute("UPDATE task_assignments SET status='Completed' WHERE id=?", (t['id'],))
                c.execute("UPDATE agent_live_locations SET completed_dues = completed_dues + 1 WHERE username=?", (t['agent_name'],))
                conn.commit()
                st.success("??? ??????? ??????? ??? ?????!")
                st.rerun()
              st.markdown("---")
      else:
        st.info("No pending tasks. (???? ??????? ??? ????)")

  with task_tab2:
    st.write("#### ?? Agent Date-wise & Party Summary (?????? ? ????? ??????? ????? ?????)")
    
    agent_summary_df = pd.read_sql_query("""
        SELECT u.fullname as agent_name, substr(t.created_at, 1, 10) as task_date, t.task_type, COUNT(DISTINCT t.party_name) as party_count, SUM(CAST(t.due_amount AS REAL)) as total_due
        FROM task_assignments t
        LEFT JOIN users u ON t.agent_name = u.username
        GROUP BY t.agent_name, task_date, t.task_type
        ORDER BY task_date DESC, agent_name ASC
    """, conn)

    if not agent_summary_df.empty:
      st.dataframe(agent_summary_df, use_container_width=True)
      
      if st.session_state["user_role"] == "admin":
        html_agent_sum = generate_html_report("Agent Date-wise Task Summary", agent_summary_df)
        st.download_button(
            label="?? Download Agent Summary Report (PDF/HTML)",
            data=html_agent_sum,
            file_name="mediseller_agent_datewise_summary.html",
            mime="text/html",
            type="primary"
        )
    else:
      st.info("No summary data available yet.")

  if task_tab3 is not None:
    with task_tab3:
      st.write("#### ?? Completed Tasks History (Auto expires after 48 hours)")
      completed_tasks_df = pd.read_sql_query("""
          SELECT t.*, u.fullname as agent_fullname 
          FROM task_assignments t 
          LEFT JOIN users u ON t.agent_name = u.username 
          WHERE t.status='Completed' 
          ORDER BY t.id DESC
      """, conn)
      if not completed_tasks_df.empty:
        export_comp_tasks = completed_tasks_df.copy()
        export_comp_tasks['agent_name'] = export_comp_tasks.apply(lambda r: r['agent_fullname'] if pd.notna(r['agent_fullname']) and r['agent_fullname'] else r['agent_name'], axis=1)
        export_comp_tasks = export_comp_tasks[['agent_name', 'party_name', 'task_type', 'due_amount', 'created_at', 'status']]
        
        html_comp_tasks = generate_html_report("Completed Tasks History", export_comp_tasks)
        st.download_button(
            label="?? Download Completed Tasks Report (PDF/HTML)",
            data=html_comp_tasks,
            file_name="mediseller_completed_tasks_history.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")
        for idx, row in completed_tasks_df.iterrows():
          disp_ag_name = row['agent_fullname'] if pd.notna(row['agent_fullname']) and row['agent_fullname'] else row['agent_name']
          cols = st.columns([2, 2, 2, 1.5])
          cols[0].write(f"Agent: **{disp_ag_name}**\n\nParty: **{row['party_name']}**")
          cols[1].write(f"Work: {row['task_type']}\n\nDue: {row['due_amount']} INR")
          cols[2].write("? Completed (???????)")
          
          if st.session_state["user_role"] == "admin":
            if cols[3].button("??? Delete (?????)", key=f"del_comp_task_{row['id']}"):
              c.execute("DELETE FROM task_assignments WHERE id=?", (row['id'],))
              conn.commit()
              st.success("Deleted! (????? ?????!)")
              st.rerun()
          else:
            cols[3].write("?? Locked")
          st.write("---")
      else:
        st.info("No completed tasks history.")

# =========================================================
# 6. HOME-TO-HOME AUTO ROUTE & MAP
# =========================================================
elif selected_menu == "??? Route Map (??? ?????)":
  st.write("### ??? Route Planning (??? ?????????)")

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
        name="Google Maps (???? ?????)"
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
      folium.PolyLine(coordinates_list, color="#ff4b4b", weight=5, opacity=0.85, tooltip="Delivery Route (???)").add_to(route_map)

    st_folium(route_map, width=900, height=500, key="auto_route_map")
  else:
    st.info("No location saved on map. (?????? ?????? ????)")

# =========================================================
# 7. ATTENDANCE SYSTEM
# =========================================================
elif selected_menu == "?? Attendance (????????)":
  st.write("### ?? Attendance (????????)")

  att_tab1, att_tab2 = st.tabs([
      "?? Today (????? ????????)", 
      "?? Monthly Summary (????? ??????)"
  ])

  with att_tab1:
    display_today_str = get_ist_time().strftime('%d-%m-%Y')
    st.write(f"#### Today's Date: `{display_today_str}`")
    
    current_user = st.session_state["username"]
    today_str = get_ist_time().strftime("%Y-%m-%d")
    
    c.execute("SELECT check_time FROM attendance WHERE username=? AND date=?", (current_user, today_str))
    already_checked = c.fetchone()

    if already_checked:
      st.success(f"Attendance recorded! (Time: `{already_checked[0]}`) (???????? ????? ??? ??????)")
    else:
      if st.button("????? Give Attendance (???????? ???)", type="primary"):
        check_time_str = get_ist_time().strftime("%H:%M:%S")
        try:
          c.execute("INSERT INTO attendance (username, date, check_time, status) VALUES (?, ?, ?, ?)",
                    (current_user, today_str, check_time_str, "Present"))
          conn.commit()
          st.success("Attendance recorded! (???!)")
          st.rerun()
        except sqlite3.IntegrityError:
          st.error("Already attended. (???????? ????? ??????)")

    st.write("---")
    st.write("#### Today's Attendance List (????? ??????)")
    
    if st.session_state["user_role"] == "admin":
      full_att_today = pd.read_sql_query("""
          SELECT u.fullname as employee_name, a.check_time, a.status 
          FROM attendance a 
          LEFT JOIN users u ON a.username = u.username 
          WHERE a.date=?
      """, conn, params=(today_str,))
      if not full_att_today.empty:
        html_att_today = generate_html_report(f"Attendance Report - {today_str}", full_att_today)
        st.download_button(
            label="?? Download Today's Attendance Report (PDF/HTML)",
            data=html_att_today,
            file_name=f"mediseller_attendance_{today_str}.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")

    today_att_df = pd.read_sql_query("""
        SELECT u.fullname as employee_name, a.check_time, a.status 
        FROM attendance a 
        LEFT JOIN users u ON a.username = u.username 
        WHERE a.date=?
    """, conn, params=(today_str,))
    if not today_att_df.empty:
      st.dataframe(today_att_df, use_container_width=True)
    else:
      st.info("No attendance today. (?? ??? ??????)")

  with att_tab2:
    st.write("#### ?? Monthly Report (????? ???????)")
    
    current_month_str = get_ist_time().strftime("%Y-%m")
    current_user = st.session_state["username"]
    user_role = st.session_state["user_role"]

    if user_role == "admin":
      st.write(f"Current Month: **{current_month_str}** (Admin View)")
      summary_df = pd.read_sql_query("""
          SELECT u.fullname as employee_name, COUNT(*) as total_present 
          FROM attendance a 
          LEFT JOIN users u ON a.username = u.username
          WHERE strftime('%Y-%m', a.date) = ? 
          GROUP BY a.username
      """, conn, params=(current_month_str,))
      
      full_monthly_att = pd.read_sql_query("""
          SELECT u.fullname as employee_name, a.date, a.check_time, a.status 
          FROM attendance a 
          LEFT JOIN users u ON a.username = u.username
          WHERE strftime('%Y-%m', a.date) = ? 
          ORDER BY a.date DESC, a.check_time DESC
      """, conn, params=(current_month_str,))
      
      if not full_monthly_att.empty:
        html_monthly_att = generate_html_report(f"Monthly Attendance - {current_month_str}", full_monthly_att)
        st.download_button(
            label="?? Download Monthly Attendance Report (PDF/HTML)",
            data=html_monthly_att,
            file_name=f"mediseller_monthly_attendance_{current_month_str}.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")
    else:
      st.write(f"Current Month: **{current_month_str}**")
      summary_df = pd.read_sql_query("""
          SELECT u.fullname as employee_name, COUNT(*) as total_present 
          FROM attendance a 
          LEFT JOIN users u ON a.username = u.username
          WHERE strftime('%Y-%m', a.date) = ? AND a.username = ?
          GROUP BY a.username
      """, conn, params=(current_month_str, current_user))

    if not summary_df.empty:
      st.dataframe(summary_df, use_container_width=True)
    else:
      st.info("No records for this month. (?? ????? ?????? ????)")

    st.write("---")
    if user_role == "admin":
      st.write("#### ?? Detailed Records (????????? ??????)")
      all_att_df = pd.read_sql_query("""
          SELECT a.id, a.username, u.fullname, a.date, a.check_time, a.status 
          FROM attendance a 
          LEFT JOIN users u ON a.username = u.username 
          ORDER BY a.date DESC, a.check_time DESC
      """, conn)
      if not all_att_df.empty:
        export_all_att = all_att_df.copy()
        export_all_att['username'] = export_all_att.apply(lambda r: r['fullname'] if pd.notna(r['fullname']) and r['fullname'] else r['username'], axis=1)
        export_all_att = export_all_att[['username', 'date', 'check_time', 'status']]
        
        html_all_att_records = generate_html_report("All Attendance Detailed Records", export_all_att)
        st.download_button(
            label="?? Download Detailed Attendance History Report (PDF/HTML)",
            data=html_all_att_records,
            file_name=f"mediseller_all_attendance_records.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")
    else:
      st.write("#### ?? Attendance History (??????)")
      all_att_df = pd.read_sql_query("""
          SELECT a.id, a.username, u.fullname, a.date, a.check_time, a.status 
          FROM attendance a 
          LEFT JOIN users u ON a.username = u.username 
          WHERE a.username=? 
          ORDER BY a.date DESC, a.check_time DESC
      """, conn, params=(current_user,))
    
    if not all_att_df.empty:
      for idx, row in all_att_df.iterrows():
        try:
          formatted_row_date = datetime.strptime(row['date'], "%Y-%m-%d").strftime("%d-%m-%Y")
        except:
          formatted_row_date = row['date']

        disp_uname = row['fullname'] if pd.notna(row['fullname']) and row['fullname'] else row['username']

        cols = st.columns([2, 2, 2, 1.5, 1.5])
        cols[0].write(f"Name: **{disp_uname}**")
        cols[1].write(f"Date: {formatted_row_date}")
        cols[2].write(f"Time: {row['check_time']}")
        cols[3].write(f"Status: {row['status']}")

        if user_role == "admin":
          if cols[4].button("??? Delete (?????)", key=f"del_att_{row['id']}"):
            c.execute("DELETE FROM attendance WHERE id=?", (row['id'],))
            conn.commit()
            st.success("Deleted! (???? ???? ?????!)")
            st.rerun()
        else:
          cols[4].write("?? Locked (???)")
    else:
      st.info("No records. (?????? ????)")

# =========================================================
# 8. ADVANCED ADMIN LIVE TRACKING
# =========================================================
elif selected_menu == "?? Live Tracking (???? ?????????)":
  if st.session_state["user_role"] != "admin":
    st.error("Admin only page. (????????? ?????????? ?????)")
  else:
    st.title("?? Live Agent Tracking (???? ?????????)")
    st.markdown("?? Updates every 30 seconds.")

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
            label="?? Download Live Tracking Report (PDF/HTML)",
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
                    <h3>?? Agent: {disp_agent_name} ({u_name}) - Role: {u_role}</h3>
                    <span class="status-active">?? Live Active (???????)</span>
                    <p style="margin-top: 15px;"><b>?? Location:</b> <code>{lat:.5f}, {lon:.5f}</code></p>
                    <p><b>?? Last Update:</b> <code>{display_last_update}</code></p>
                    <p><b>?? Phone:</b> <code>{u_phone if u_phone else 'None (???)'}</code></p>
                    <div style="background: #0d1117; padding: 10px; border-radius: 6px; margin-top: 10px;">
                        <p>?? <b>Stats (??????????):</b></p>
                        <p>? Completed Deliveries: <b>{comp_del}</b></p>
                        <p>?? Due Clearances: <b>{comp_due}</b></p>
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
                        ?? View on Google Maps (?????? ?????)
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
                    <h3>?? Agent: {disp_agent_name} ({u_name}) - Role: {u_role}</h3>
                    <p style="color: #f85149;">?? Offline or No GPS. (?????? ?? ?????? ????)</p>
                    <p><b>?? Phone:</b> <code>{u_phone if u_phone else 'None (???)'}</code></p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
      st.info("No users found. (????? ????)")

# =========================================================
# 9. SETTINGS, ADMIN PASSWORD & AGENT MANAGEMENT
# =========================================================
elif selected_menu == "?? Settings & Agents (??????)":
  if st.session_state["user_role"] != "admin":
    st.error("Admin only page. (????????? ?????????? ?????)")
  else:
    st.write("### ?? Change Password (?????????? ????????)")
    with st.form("admin_password_change_form"):
      old_pass = st.text_input("Old Password (?????? ??????????)", type="password")
      new_pass = st.text_input("New Password (???? ??????????)", type="password")
      confirm_pass = st.text_input("Confirm Password (?????? ??????????)", type="password")
      change_pass_btn = st.form_submit_button("?? Update Password (?????)", type="primary")

      if change_pass_btn:
        c.execute("SELECT password FROM users WHERE username='admin'")
        adm_db_row = c.fetchone()
        if adm_db_row and adm_db_row[0] == old_pass:
          if new_pass == confirm_pass and new_pass.strip() != "":
            c.execute("UPDATE users SET password=? WHERE username='admin'", (new_pass,))
            conn.commit()
            st.success("Password changed successfully! (???????? ??? ?????!)")
          else:
            st.error("Passwords do not match or empty. (????? ?? ?? ?????)")
        else:
          st.error("Incorrect Old Password! (?????? ?????????? ???!)")

    st.write("---")
    st.write("### ?? Agent Management (?????? ????????????)")
    
    c.execute("SELECT username, role, fullname, phone, created_at, is_active FROM users")
    agents = c.fetchall()
    st.write(f"Total Users: **{len(agents)}** (??? ?????)")

    users_report_df = pd.read_sql_query("SELECT username, role, fullname, phone, created_at FROM users", conn)
    if not users_report_df.empty:
      html_users_report = generate_html_report("System Users & Agents Directory", users_report_df)
      st.download_button(
          label="?? Download Users & Agents Report (PDF/HTML)",
          data=html_users_report,
          file_name="mediseller_users_report.html",
          mime="text/html",
          type="primary"
      )
      st.write("---")

    for ag in agents:
      u_name, u_role, f_name, u_phone, c_date, is_act = ag
      display_name = f_name if f_name else "No name (??? ???)"
      
      try:
        join_date = datetime.strptime(c_date, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y %H:%M:%S") if c_date else "Unknown (?????)"
      except:
        join_date = c_date if c_date else "Unknown (?????)"

      phone_disp = u_phone if u_phone else "No number (????? ???)"
      
      with st.expander(f"?? {display_name} ({u_name})"):
        st.write(f"?? Phone: `{phone_disp}`")
        st.write(f"?? Join Date: `{join_date}`")
        
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
          with st.form(f"edit_form_{u_name}"):
            new_name = st.text_input("Agent Name (???)", value=display_name, key=f"fname_{u_name}")
            new_phone = st.text_input("Phone Number (??? ?????)", value=phone_disp if phone_disp != "No number (????? ???)" else "", key=f"fphone_{u_name}")
            update_btn = st.form_submit_button("Save (???????)")
            
            if update_btn:
              c.execute("UPDATE users SET fullname=?, phone=? WHERE username=?", (new_name, new_phone, u_name))
              conn.commit()
              st.success("Updated! (????? ?????!)")
              st.rerun()

        with col_ed2:
          if u_name != "admin":
            if st.button("??? Delete Agent (?????? ?????)", key=f"del_ag_{u_name}", type="secondary"):
              c.execute("DELETE FROM users WHERE username=?", (u_name,))
              c.execute("DELETE FROM agent_live_locations WHERE username=?", (u_name,))
              conn.commit()
              st.success("Agent deleted! (????? ?????!)")
              st.rerun()

    st.write("---")
    st.write("### ? Add New Agent (???? ?????? ???)")
    with st.form("new_agent_form"):
      n_fullname = st.text_input("Agent Name (???????? ???)")
      n_user = st.text_input("Username (????????)")
      n_role = st.selectbox("Role (???)", ["staff", "admin"])
      add_agent_btn = st.form_submit_button("Add Agent (?????? ????? ????)")

      if add_agent_btn:
        if n_fullname and n_user:
          try:
            c.execute("INSERT INTO users (username, password, role, fullname, phone, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                      (n_user, "direct_login", n_role, n_fullname, "", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1))
            conn.commit()
            st.session_state["last_created_agent_user"] = n_user
            st.session_state["last_created_agent_name"] = n_fullname
            st.success("Agent added successfully! (??? ??? ?????!)")
            st.rerun()
          except sqlite3.IntegrityError:
            st.error("Username already exists. (?????????? ??????)")
        else:
          st.error("Fill name and username. (??? ? ???????? ????)")

    if st.session_state.get("last_created_agent_user"):
      created_u = st.session_state["last_created_agent_user"]
      created_n = st.session_state["last_created_agent_name"]
      
      st.markdown("---")
      st.write(f"#### ?? Direct Link (???????? ????)")
      
      direct_msg = f"Hello {created_n}, your account has been created in P.S Mediseller. Click below to login:\n"
      
      copy_html = f"""
      <div style="background: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #475569; margin-top: 10px;">
        <p style="color: #fff; margin-bottom: 8px; font-weight: 600;">Generated Direct Link (????):</p> &nbsp;
        <input type="text" id="generated_link" readonly style="width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #64748b; background: #0f172a; color: #fff; font-size: 14px; margin-bottom: 10px; box-sizing: border-box;">
        <button onclick="copyLink()" id="copy_btn" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 10px 20px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer;">?? Copy Link (???)</button>
        <span id="copy_status" style="color: #34d399; margin-left: 10px; font-weight: bold; display: none;">? Copied! (? ??? ?????!)</span>
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
        
        const fullLink = currentUrl + '?login=' + encodeURIComponent('{created_u}');
        document.getElementById('generated_link').value = fullLink;
        
        function copyLink() {{
          const copyText = document.getElementById('generated_link');
          copyText.select();
          copyText.setSelectionRange(0, 99999);
          navigator.clipboard.writeText(copyText.value);
          
          const status = document.getElementById('copy_status');
          status.style.display = 'inline';
          setTimeout(() => {{ status.style.display = 'none'; }}, 2000);
        }}
      </script>
      """
      st.components.v1.html(copy_html, height=140)
      
      whatsapp_msg = urllib.parse.quote(direct_msg + "\n" + f"{{fullLink}}")
      st.markdown(f'<a href="https://wa.me/?text={whatsapp_msg}" target="_blank"><button style="background: #25d366; color: white; padding: 10px 20px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer;">?? Share via WhatsApp (????? ????)</button></a>', unsafe_allow_html=True)

