from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import urllib.parse
import base64
import os
import time
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
<script>
function checkAndRequestLocation() {
    if (!navigator.geolocation) {
        console.warn("Geolocation is not supported by your browser.");
        return;
    }
    navigator.geolocation.getCurrentPosition(
        function(position) {
            localStorage.setItem('ps_user_lat', position.coords.latitude);
            localStorage.setItem('ps_user_lon', position.coords.longitude);
        },
        function(error) {
            console.warn("Location error:", error.code, error.message);
        },
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

# FIXED CSS: Removed 'div' from color override to prevent white-screen error text issues
st.markdown("""
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
          .print-btn {{ display: block; width: 220px; margin: 20px auto; padding: 12px; background: #2563eb; color: white; border: none;
border-radius: 8px; font-size: 15px; font-weight: bold; cursor: pointer; text-align: center; box-shadow: 0 4px 10px rgba(37,99,235,0.3); }}
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
          <p>Generated on: {get_ist_time().strftime('%d.%m.%y %H:%M:%S')} IST</p>
      </div>
      <button class="print-btn" onclick="window.print()">Print / Save as PDF (প্রিন্ট / পিডিএফ)</button>
      {df.to_html(index=False, classes='table', border=0)}
  </body>
  </html>
  """
  return html.encode('utf-8')

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
if "login_processed" not in st.session_state:
  st.session_state["login_processed"] = False

# =========================================================
# SECURE AUTO-LOGIN FIX (NO MORE WHITE SCREENS)
# =========================================================
query_params = st.query_params
login_user = query_params.get("login", None)
target_login = None

if login_user:
    target_login = login_user
    # Store directly in JS without waiting for eval
    st.components.v1.html(f"<script>localStorage.setItem('ps_mediseller_user', '{login_user}');</script>", height=0)
    # Safely clear query params to prevent URL loop
    if "login" in st.query_params:
        del st.query_params["login"]
else:
    # Only evaluate localStorage if there is no direct login link, preventing WhatsApp browser locks
    if st.session_state.get("username") == "delivery":
        try:
            saved_user_js = streamlit_js_eval(js_expressions="localStorage.getItem('ps_mediseller_user')", key="get_saved_user_storage")
            if saved_user_js and saved_user_js != "null":
                target_login = saved_user_js
        except Exception as e:
            pass

if target_login:
    c.execute("SELECT fullname, role FROM users WHERE username=?", (target_login,))
    user_row = c.fetchone()
    if user_row:
        f_name, r_role = user_row        
        st.session_state["username"] = target_login
        st.session_state["user_role"] = r_role
        
        # If logging in directly from URL link, show success and wait slightly before rerun to allow JS storage to complete
        if login_user:
            st.success(f"Welcome, {f_name}! Logged in successfully. (স্বাগতম, {f_name}!)")
            time.sleep(0.5)
            st.rerun()
        # If logging in from local storage, only rerun once to establish session properly
        elif target_login and not st.session_state["login_processed"]:
            st.session_state["login_processed"] = True
            st.rerun()
    else:
        # Invalid user, clear storage
        st.components.v1.html("<script>localStorage.removeItem('ps_mediseller_user');</script>", height=0)

col_ht1, col_ht2 = st.columns([3, 1])
with col_ht1:
  st.markdown(f"""
  <div style="display: flex; align-items: center; gap: 12px;">
      <img src="data:image/jpeg;base64,{logo_b64}" style="width: 52px; height: 52px; border-radius: 10px; object-fit: cover; border: 1px
solid rgba(255,255,255,0.2); box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
      <div>
          <h1 style="margin: 0; font-family: 'Poppins', sans-serif; font-size: 19px !important; background: linear-gradient(90deg, #38bdf8,
#818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; line-height: 1.2;">P. S
MEDISELLER</h1>
          <p style="margin: 2px 0 0 0; color: #cbd5e1 !important; font-size: 11px; font-weight: 500;">Allopathy & Ayurvedic Wholesaler | Ph:
8918740325</p>
      </div>
  </div>
  """, unsafe_allow_html=True)

with col_ht2:
  if st.session_state["user_role"] == "admin":
    if st.button("🚪 Logout (লগআউট)", key="logout_btn_top"):
      st.session_state["username"] = "delivery"
      st.session_state["user_role"] = "staff"
      st.session_state["login_processed"] = False
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

c.execute("SELECT fullname FROM users WHERE username=?", (st.session_state['username'],))
curr_user_row = c.fetchone()
current_fullname = curr_user_row[0] if curr_user_row and curr_user_row[0] else st.session_state['username']
col_u1, _ = st.columns([3, 1])
with col_u1:
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
elif not loc:
  st.warning("⚠️ Location fetching pending or blocked. Please allow location access. (লোকেশন পারমিশন দিন)")

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
      [
          "🏠 With Map Party (ম্যাপ সহ পার্টি)",
          "🩺 Without Map Party (ম্যাপ ছাড়া পার্টি)"
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
  st.write("🔍 **Search & Select Party (পার্টি সার্চ ও সিলেক্ট করুন):**")
  order_search_text = st.text_input("Search Party", placeholder="Type name, address or keyword...", key="order_party_search_text_input", label_visibility="collapsed")
  if order_search_text.strip():
    q_term = f"%{order_search_text.strip()}%"
    c.execute("SELECT party_name FROM locations WHERE party_name LIKE ? OR address LIKE ? OR party_phone LIKE ? ORDER BY party_name ASC", (q_term, q_term, q_term))
    filtered_parties_list = [r[0] for r in c.fetchall()]
  else:
    c.execute("SELECT party_name FROM locations ORDER BY party_name ASC")
    filtered_parties_list = [r[0] for r in c.fetchall()]  
  if order_search_text.strip() and filtered_parties_list:
    st.markdown(f"<p style='color: #60a5fa; font-size: 12px; margin: 2px 0;'>💡 Suggestions ({len(filtered_parties_list)} found): Select below</p>", unsafe_allow_html=True)
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
      st.warning("No matching party found! (কোনো পার্টি পাওয়া যায়নি!)")
      selected_order_party_native = ""
  with st.form("order_visit_entry_form"):
    ord_details = st.text_area("Order Details (অর্ডার বিবরণ)")
   
    col_ob1, col_ob2 = st.columns(2)
    with col_ob1:
      submitted_order = st.form_submit_button("🛒 Submit Order (অর্ডার জমা)", type="primary")
    with col_ob2:
      submitted_visit = st.form_submit_button("📍 Save Visit (ভিজিট সেভ)")
    if submitted_order:
      if not selected_order_party_native.strip():
        st.error("Please select a party. (পার্টি সিলেক্ট করুন।)")
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
        st.error("Please select a party. (পার্টি সিলেক্ট করুন।)")
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
  st.write("#### 📋 Recent Orders & Visits (সামপ্রতিক রিপোর্ট)")
  report_df = pd.read_sql_query("SELECT party_name AS 'Party Name', activity_type AS 'Activity Type', work_date AS 'Work Date' FROM daily_work ORDER BY work_date DESC, id DESC LIMIT 20", conn)
  if not report_df.empty:
    if st.session_state["user_role"] == "admin":
      full_report_df = pd.read_sql_query("SELECT party_name AS 'Party Name', activity_type AS 'Activity Type', work_date AS 'Work Date' FROM daily_work ORDER BY work_date DESC, id DESC", conn)
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
      cols[0].write(f"Party: **{r_row['Party Name']}**")
      cols[1].write(f"Activity: `{r_row['Activity Type']}`")
      cols[2].write(f"Date: `{format_date_display(r_row['Work Date'])}`")
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
          st.success("GPS taken! (নেওয়া হয়েছে!)")          
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
    html_locs_df = generate_html_report("Locations & Parties Directory", df[["party_name", "address", "party_phone"]].rename(columns={"party_name": "Party Name", "address": "Address", "party_phone": "Phone"}))
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
  with st.expander(f"🩺 Non-Map List ({len(doc_df)} Entries) (ম্যাপবিহীন তালিকা)", expanded=True):    
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
          if cols[4].button("️ Delete (ডিলিট)", key=f"del_doc_search_{row['id']}"):
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
        if cols[4].button("️ Delete (ডিলিট)", key=f"del_loc_search_{row['id']}"):
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
      all_ord_df = pd.read_sql_query("SELECT party_name AS 'Party Name', order_details AS 'Order Details', order_date AS 'Order Date' FROM orders WHERE status='Pending' ORDER BY order_date DESC", conn)
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
      completed_ord_df = pd.read_sql_query("SELECT party_name AS 'Party Name', order_details AS 'Order Details', order_date AS 'Order Date' FROM orders WHERE status='Completed' ORDER BY order_date DESC", conn)
      if not completed_ord_df.empty:
        if st.session_state["user_role"] == "admin":
          html_comp_ord = generate_html_report("Completed Orders History", completed_ord_df)
          col_dc1, col_dc2 = st.columns(2)
          with col_dc1:
            st.download_button(
                label="📥 Download Completed Orders Report",
                data=html_comp_ord,                
                file_name="mediseller_completed_orders_history.html",
                mime="text/html",
                type="primary"
            )
          with col_dc2:
            if st.button("️ Clear All Completed Orders History (সব ডিলিট)", type="secondary"):              
              c.execute("DELETE FROM orders WHERE status='Completed'")
              conn.commit()
              st.success("All completed orders history deleted! (মুছে ফেলা হয়েছে!)")
              st.rerun()
          st.write("---")
        for idx, row in completed_ord_df.iterrows():
          if st.session_state["user_role"] == "admin":
            cols = st.columns([2, 4, 2, 1.5])
          else:
            cols = st.columns([2, 4, 2])
          cols[0].write(f"**{row['Party Name']}**")
          cols[1].write(row['Order Details'])
          cols[2].write("✅ Completed (সম্পন্ন)")
          if st.session_state["user_role"] == "admin":
            if cols[3].button("️ Delete", key=f"del_comp_ord_{row.get('id', idx)}"):
              c.execute("DELETE FROM orders WHERE id=?", (row.get('id', idx),))
              conn.commit()
              st.success("Deleted!")
              st.rerun()
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
      full_dw_df = pd.read_sql_query("SELECT party_name AS 'Party Name', activity_type AS 'Activity Type', work_date AS 'Work Date' FROM daily_work ORDER BY work_date DESC, id DESC", conn)
      if not full_dw_df.empty:
        html_dw_report = generate_html_report("Daily Work Report", full_dw_df)
        col_dw1, col_dw2 = st.columns(2)
        with col_dw1:
          st.download_button(
              label="📥 Download Daily Work Report (PDF/HTML)",
              data=html_dw_report,
              file_name="mediseller_daily_work_report.html",
              mime="text/html",
              type="primary"
          )
        with col_dw2:
          if st.button("️ Clear All Daily Work Records (সব কাজ মুছুন)", type="secondary"):
            c.execute("DELETE FROM daily_work")
            conn.commit()
            st.success("All daily work records deleted successfully! (সব মুছে ফেলা হয়েছে!)")
            st.rerun()
        st.write("---")
    work_df = pd.read_sql_query("SELECT * FROM daily_work ORDER BY work_date DESC, id DESC", conn)
    if not work_df.empty:
      unique_dates = work_df['work_date'].unique()
      for d_str in unique_dates:
        date_records = work_df[work_df['work_date'] == d_str]
        count_parties = len(date_records)
        formatted_d = format_date_display(d_str)
        with st.expander(f"📅 Date: {formatted_d} (Total: {count_parties})", expanded=False):
          if st.session_state["user_role"] == "admin":
            if st.button(f"️ Delete Date Data ({formatted_d}) (সব ডিলিট)", key=f"del_date_{d_str}", type="secondary"):
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
              if cols[2].button("️ Delete (ডিলিট)", key=f"del_dw_{w_row['id']}"):
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
   
    st.write("⚙️ **Select Year & Month (বছর ও মাস সিলেক্ট করুন):**")
    col_yr, col_mo = st.columns(2)
    with col_yr:
      selected_year = st.selectbox("Select Year (বছর)", [2026, 2025, 2024], index=0)
    with col_mo:
      months_dict = {
          "01": "January (জানুয়ারি)", "02": "February (ফেব্রুয়ারি)", "03": "March (মার্চ)",
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
          col_ms1, col_ms2 = st.columns(2)
          with col_ms1:
            st.download_button(
                label="📥 Download Monthly Summary Report",
                data=html_summary,
                file_name=f"mediseller_monthly_summary_{selected_month}.html",
                mime="text/html",
                type="primary"
            )
          with col_ms2:
            if st.button(f"️ Delete All Work Records for Month: {selected_month}", type="secondary"):
              c.execute("DELETE FROM daily_work WHERE work_date LIKE ?", (f"{selected_month}%",))
              conn.commit()
              st.success(f"All records for {selected_month} deleted successfully! (মুছে ফেলা হয়েছে!)")
              st.rerun()
          st.write("---")
        else:
          st.markdown("<p style='color: #60a5fa; font-size: 13px;'><i>Note: Monthly report downloads and management are restricted to admins only. Agents can only view their summary above.</i></p>", unsafe_allow_html=True)
        st.dataframe(report_summary_df, use_container_width=True)
        zero_activity_df = report_summary_df[(report_summary_df["Total Visits"] == 0) & (report_summary_df["Total Orders"] == 0)]
       
        st.write(f"⚠️ **Doctors/Parties with ZERO Visits & ZERO Orders ({len(zero_activity_df)}):**")
        if not zero_activity_df.empty:
          st.dataframe(zero_activity_df, use_container_width=True)
        else:
          st.success("All parties/doctors had at least one visit or order this month! (সব ডাক্তারের ভিজিট বা অর্ডার হয়েছে!)")
      else:
        st.info("No parties/doctors found in database. (কোনো পার্টি নেই।)")

# =========================================================
# 5. DUE CLEAR, DELIVERY PLAN & AGENT GROUPED CARDS VIEW
# =========================================================
elif selected_menu == "📋 Due & Delivery (বকেয়া ও ডেলিভারি)":
  st.markdown('<div class="main-title">Delivery & Due Plan (ডেলিভারি ও ডিউ প্ল্যান)</div>', unsafe_allow_html=True)
  
  c.execute("SELECT username, fullname FROM users")
  users_data = c.fetchall()
  all_agents = [r[0] for r in users_data]
  agent_name_map = {r[0]: (r[1] if r[1] else r[0]) for r in users_data}
  c.execute("SELECT party_name, lat, lon FROM locations ORDER BY party_name ASC")
  loc_data = c.fetchall()
  party_coords = {r[0]: (r[1], r[2]) for r in loc_data}
  all_parties = [r[0] for r in loc_data]
  task_tab1, task_tab2, task_tab3 = st.tabs([
      "Active Tasks (চলমান কাজ)",
      "Agent Date-wise Summary (এজেন্ট ও তারিখ অনুযায়ী সামারি)",
      "Completed Tasks History (সম্পন্ন কাজ)"
  ])
  with task_tab1:
    if st.session_state["user_role"] == "admin":      
      full_tasks_df = pd.read_sql_query("""
          SELECT t.id, u.fullname as agent_fullname, t.agent_name, t.party_name, t.task_type, t.due_amount, t.sale_amount, t.payment_collected_actual, t.status, t.created_at, l.address
          FROM task_assignments t
          LEFT JOIN users u ON t.agent_name = u.username
          LEFT JOIN locations l ON t.party_name = l.party_name
          WHERE t.status='Pending'
          ORDER BY t.id DESC
      """, conn)
      if not full_tasks_df.empty:
        export_tasks_df = full_tasks_df.copy()
        export_tasks_df['Agent Name'] = export_tasks_df.apply(lambda r: r['agent_fullname'] if pd.notna(r['agent_fullname']) and r['agent_fullname'] else r['agent_name'], axis=1)        
        export_tasks_df['Party Name'] = export_tasks_df['party_name']
        export_tasks_df['Task Type'] = export_tasks_df['task_type']
        export_tasks_df['Sale Amount (₹)'] = export_tasks_df['sale_amount']
        export_tasks_df['Collection Amount (₹)'] = export_tasks_df['payment_collected_actual']
        export_tasks_df['Due Amount (₹)'] = export_tasks_df['due_amount']
        export_tasks_df['Assigned Date'] = export_tasks_df['created_at'].apply(lambda x: format_date_display(x))
        export_tasks_df['Address'] = export_tasks_df['address']
        
        export_tasks_df_final = export_tasks_df[['Agent Name', 'Party Name', 'Task Type', 'Sale Amount (₹)', 'Collection Amount (₹)', 'Due Amount (₹)', 'Assigned Date', 'Address']]
       
        html_tasks_report = generate_html_report("Active Tasks & Deliveries Report", export_tasks_df_final)
        st.download_button(
            label="📥 Download Tasks Report (PDF/HTML)",
            data=html_tasks_report,
            file_name="mediseller_due_delivery_report.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")
    st.write("🔍 **Search & Select Party (পার্টি সার্চ ও সিলেক্ট করুন):**")
    task_search_text = st.text_input("Search Party for Task", placeholder="Type name, address or keyword...", key="task_party_search_text_input", label_visibility="collapsed")
   
    if task_search_text.strip():
      q_term = f"%{task_search_text.strip()}%"
      c.execute("SELECT party_name FROM locations WHERE party_name LIKE ? OR address LIKE ? OR party_phone LIKE ? ORDER BY party_name ASC", (q_term, q_term, q_term))
      filtered_task_parties = [r[0] for r in c.fetchall()]
    else:
      filtered_task_parties = all_parties

    if task_search_text.strip() and filtered_task_parties:
      st.markdown(f"<p style='color: #60a5fa; font-size: 12px; margin: 2px 0;'>💡 Suggestions ({len(filtered_task_parties)} found): Select below</p>", unsafe_allow_html=True)
      selected_task_party = st.radio(
          "Matching Task Parties",
          filtered_task_parties[:10],
          key="task_floating_suggestions_radio",
          label_visibility="collapsed"
      )
    else:
      if filtered_task_parties:
        selected_task_party = st.selectbox("Select Party for Task", filtered_task_parties, label_visibility="collapsed", key="task_select_party_box")
      else:
        st.warning("No matching party found! (কোনো পার্টি পাওয়া যায়নি!)")
        selected_task_party = ""

    with st.form("assign_task_form"):
      st.write("#### ➕ Assign New Task to Agent (এজেন্টকে নতুন কাজ দিন)")
      col_as1, col_as2 = st.columns(2)
      with col_as1:
        assigned_agent = st.selectbox("Select Agent (এজেন্ট সিলেক্ট করুন)", all_agents, format_func=lambda x: agent_name_map.get(x, x))
      with col_as2:
        task_type_sel = st.selectbox("Task Type (কাজের ধরণ)", ["Delivery & Due Collection (ডেলিভারি ও বকেয়া কালেকশন)", "Only Delivery (শুধু ডেলিভারি)", "Only Due Collection (শুধু বকেয়া কালেকশন)", "Payment Collection (পেমেন্ট কালেকশন)"])
      
      col_as3, col_as4, col_as5 = st.columns(3)
      with col_as3:
        sale_amt_input = st.text_input("Sale Amount (₹) (সেল অ্যামাউন্ট)", "0")
      with col_as4:
        due_amt_input = st.text_input("Due Amount (₹) (বকেয়া অ্যামাউন্ট)", "0")
      with col_as5:
        col_dummy = st.columns(1)[0]
        col_dummy.write("")

      submitted_task = st.form_submit_button("🚀 Assign Task (টাস্ক অ্যাসাইন করুন)", type="primary")
      if submitted_task:
        if not selected_task_party.strip():
          st.error("Please select a party. (পার্টি সিলেক্ট করুন।)")
        else:
          current_date_str = get_ist_time().strftime("%Y-%m-%d %H:%M:%S")
          c.execute("""
              INSERT INTO task_assignments (agent_name, party_name, task_type, due_amount, sale_amount, status, created_at)
              VALUES (?, ?, ?, ?, ?, 'Pending', ?)
          """, (assigned_agent, selected_task_party.strip(), task_type_sel, due_amt_input, sale_amt_input, current_date_str))
          conn.commit()
          st.success("Task assigned successfully! (টাস্ক অ্যাসাইন করা হয়েছে!)")
          st.rerun()

    st.write("---")
    st.write("#### 📋 Active Tasks List (চলমান টাস্কসমূহ)")
    
    if st.session_state["user_role"] == "admin":
      tasks_query = "SELECT * FROM task_assignments WHERE status='Pending' ORDER BY id DESC"
      tasks_df = pd.read_sql_query(tasks_query, conn)
    else:
      tasks_query = "SELECT * FROM task_assignments WHERE agent_name=? AND status='Pending' ORDER BY id DESC"
      tasks_df = pd.read_sql_query(tasks_query, conn, params=(st.session_state["username"],))

    if not tasks_df.empty:
      for idx, t_row in tasks_df.iterrows():
        a_fullname = agent_name_map.get(t_row['agent_name'], t_row['agent_name'])
        p_name = t_row['party_name']
        t_type = t_row['task_type']
        s_amt = t_row['sale_amount']
        d_amt = t_row['due_amount']
        
        st.markdown(f"""
        <div class="card">
            <div class="party-title">📍 {p_name}</div>
            <div class="card-text"><b>Assigned To:</b> {a_fullname} (`{t_row['agent_name']}`)</div>
            <div class="card-text"><b>Task Type:</b> {t_type}</div>
            <div class="card-text"><b>Sale Amount:</b> ₹{s_amt} | <b>Due Amount:</b> ₹{d_amt}</div>
            <div class="card-text"><b>Assigned Date:</b> {format_date_display(t_row['created_at'])}</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form(key=f"complete_task_form_{t_row['id']}"):
          col_cf1, col_cf2 = st.columns(2)
          with col_cf1:
            collected_input = st.text_input("Payment Collected (₹) (টাকা আদায়)", "0", key=f"coll_{t_row['id']}")
          with col_cf2:
            st.write("")
            st.write("")
            submit_complete = st.form_submit_button("✔️ Complete Task (টাস্ক সম্পন্ন করুন)", type="primary")
          
          if submit_complete:
            c.execute("""
                UPDATE task_assignments 
                SET status='Completed', payment_collected_actual=? 
                WHERE id=?
            """, (collected_input, t_row['id']))
            conn.commit()
            
            c.execute("UPDATE agent_live_locations SET completed_dues = completed_dues + 1 WHERE username=?", (t_row['agent_name'],))
            conn.commit()
            
            st.success("Task marked as completed successfully! (টাস্কটি সফলভাবে সম্পন্ন হয়েছে!)")
            st.rerun()
        st.write("---")
    else:
      st.info("No active pending tasks found. (কোনো চলমান টাস্ক নেই।)")

  with task_tab2:
    st.write("#### 📊 Agent & Date-wise Summary (এজেন্ট ও তারিখ অনুযায়ী সামারি)")
    summary_df = pd.read_sql_query("""
        SELECT agent_name AS 'Agent', party_name AS 'Party', task_type AS 'Task Type', 
               sale_amount AS 'Sale (₹)', due_amount AS 'Due (₹)', 
               payment_collected_actual AS 'Collected (₹)', status AS 'Status', created_at AS 'Date'
        FROM task_assignments
        ORDER BY created_at DESC
    """, conn)
    if not summary_df.empty:
      st.dataframe(summary_df, use_container_width=True)
    else:
      st.info("No summary data available. (কোনো ডেটা নেই।)")

  with task_tab3:
    st.write("#### 📜 Completed Tasks History (সম্পন্ন কাজের ইতিহাস)")
    comp_tasks_df = pd.read_sql_query("""
        SELECT t.id, u.fullname as agent_fullname, t.agent_name, t.party_name, t.task_type, 
               t.due_amount, t.sale_amount, t.payment_collected_actual, t.created_at
        FROM task_assignments t
        LEFT JOIN users u ON t.agent_name = u.username
        WHERE t.status='Completed'
        ORDER BY t.id DESC
    """, conn)
    if not comp_tasks_df.empty:
      for idx, ct_row in comp_tasks_df.iterrows():
        a_fullname = agent_name_map.get(ct_row['agent_name'], ct_row['agent_name'])
        st.markdown(f"""
        <div class="card">
            <div class="party-title">✅ {ct_row['party_name']}</div>
            <div class="card-text"><b>Agent:</b> {a_fullname}</div>
            <div class="card-text"><b>Task Type:</b> {ct_row['task_type']}</div>
            <div class="card-text"><b>Sale:</b> ₹{ct_row['sale_amount']} | <b>Collected:</b> ₹{ct_row['payment_collected_actual']}</div>
            <div class="card-text"><b>Date:</b> {format_date_display(ct_row['created_at'])}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state["user_role"] == "admin":
          if st.button("️ Delete Completed Task", key=f"del_comp_task_{ct_row['id']}"):
            c.execute("DELETE FROM task_assignments WHERE id=?", (ct_row['id'],))
            conn.commit()
            st.success("Deleted successfully! (ডিলিট হয়েছে!)")
            st.rerun()
        st.write("---")
    else:
      st.info("No completed tasks found. (কোনো সম্পন্ন কাজ নেই।)")

# =========================================================
# 6. ATTENDANCE VIEW
# =========================================================
elif selected_menu == "📅 Attendance (উপস্থিতি)":
  st.write("### 📅 Daily Attendance (দৈনিক উপস্থিতি)")
  current_date_str = get_ist_time().strftime("%Y-%m-%d")
  
  with st.form("attendance_form"):
    st.write(f"Mark attendance for today: **{format_date_display(current_date_str)}**")
    submit_att = st.form_submit_button("✋ Check-In / Mark Present (উপস্থিতি দিন)", type="primary")
    if submit_att:
      check_time_str = get_ist_time().strftime("%H:%M:%S")
      try:
        c.execute("""
            INSERT INTO attendance (username, date, check_time, status)
            VALUES (?, ?, ?, 'Present')
        """, (st.session_state["username"], current_date_str, check_time_str))
        conn.commit()
        st.success("Attendance marked successfully! (উপস্থিতি সফলভাবে রেকর্ড করা হয়েছে!)")
      except sqlite3.IntegrityError:
        st.warning("Attendance already marked for today! (আজকের উপস্থিতি ইতিমধ্যে নেওয়া হয়েছে!)")

  st.write("---")
  st.write("#### 📋 Attendance Records (উপস্থিতির তালিকা)")
  att_df = pd.read_sql_query("SELECT username AS 'Username', date AS 'Date', check_time AS 'Check-In Time', status AS 'Status' FROM attendance ORDER BY date DESC, check_time DESC", conn)
  if not att_df.empty:
    st.dataframe(att_df, use_container_width=True)
  else:
    st.info("No attendance records found. (কোনো উপস্থিতি রেকর্ড নেই।)")

# =========================================================
# 7. ADMIN SETTINGS & LIVE TRACKING
# =========================================================
elif selected_menu == "📊 Live Tracking (লাইভ ট্র্যাকিং)" and st.session_state["user_role"] == "admin":
  st.write("### 📊 Agent Live Tracking & Status (লাইভ ট্র্যাকিং)")
  tracking_df = pd.read_sql_query("""
      SELECT l.username AS 'Username', u.fullname AS 'Full Name', l.lat AS 'Latitude', l.lon AS 'Longitude', 
             l.last_updated AS 'Last Updated', l.completed_deliveries AS 'Deliveries Done', l.completed_dues AS 'Dues Collected'
      FROM agent_live_locations l
      LEFT JOIN users u ON l.username = u.username
  """, conn)
  if not tracking_df.empty:
    st.dataframe(tracking_df, use_container_width=True)
    
    track_map = folium.Map(location=[st.session_state["selected_lat"], st.session_state["selected_lon"]], zoom_start=13, tiles=None)
    folium.TileLayer(tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps", name="Street").add_to(track_map)
    
    for idx, t_row in tracking_df.iterrows():
      if pd.notna(t_row['Latitude']) and pd.notna(t_row['Longitude']):
        folium.Marker(
            [t_row['Latitude'], t_row['Longitude']],
            popup=f"<b>Agent: {t_row['Full Name']}</b><br>Updated: {t_row['Last Updated']}",
            tooltip=t_row['Full Name'],
            icon=folium.Icon(color="green", icon="truck", prefix="fa")
        ).add_to(track_map)
    folium.LayerControl().add_to(track_map)
    st_folium(track_map, width="100%", height=450, key="agent_live_tracking_map")
  else:
    st.info("No agent live location data available. (কোনো লাইভ লোকেশন পাওয়া যায়নি।)")

elif selected_menu == "⚙️ Settings & Agents (সেটিংস)" and st.session_state["user_role"] == "admin":
  st.write("### ⚙️ System Settings & Agent Management (সেটিংস ও ইউজার)")
  
  # Detect current base URL using JS
  current_origin = streamlit_js_eval(js_expressions="window.location.origin + window.location.pathname", key="get_current_url_origin")
  if not current_origin:
    current_origin = "https://your-app-url.streamlit.app"

  with st.form("create_agent_form"):
    st.write("#### ➕ Create Agent & Generate WhatsApp Login Link (এজেন্ট তৈরি ও লিংক জেনারেট)")
    st.markdown("<p style='color: #cbd5e1; font-size: 13px;'>এজেন্টের পুরো নাম ও ফোন নম্বর দিন। জেনারেট হওয়া লিংকটি কপি করে সরাসরি হোয়াটসঅ্যাপে শেয়ার করতে পারবেন।</p>", unsafe_allow_html=True)
    
    agent_full_name_input = st.text_input("Agent Full Name (এজেন্টের পুরো নাম, যেমন: Rahul Mondal)")
    agent_phone_input = st.text_input("Agent Phone Number (ফোন নম্বর, যেমন: 9876543210)")
    agent_password_input = st.text_input("Password (পাসওয়ার্ড)", value="1234", type="password")
    
    submit_new_user = st.form_submit_button("🚀 Create & Generate Link (তৈরি করুন ও লিংক পান)", type="primary")
    
    if submit_new_user:
      if agent_full_name_input.strip() and agent_phone_input.strip():
        # Clean phone or generate clean username
        clean_phone = "".join(filter(str.isdigit, agent_phone_input.strip()))
        generated_username = f"agent_{clean_phone}"
        
        c.execute("SELECT username FROM users WHERE username=? OR phone=?", (generated_username, agent_phone_input.strip()))
        existing_u = c.fetchone()
        
        if existing_u:
          st.error("This agent or phone number already exists in the system! (এই ফোন নম্বর বা এজেন্ট ইতিমধ্যে রেজিস্টার্ড আছে!)")
        else:
          try:
            c.execute("""
                INSERT INTO users (username, password, role, fullname, phone, created_at, is_active)
                VALUES (?, ?, 'staff', ?, ?, ?, 1)
            """, (generated_username, agent_password_input.strip(), agent_full_name_input.strip(), agent_phone_input.strip(), get_ist_time().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            
            # Store in session state to display shareable link immediately
            st.session_state["last_generated_agent_name"] = agent_full_name_input.strip()
            st.session_state["last_generated_link"] = f"{current_origin}?login={generated_username}"
            st.success(f"Agent '{agent_full_name_input}' created successfully! (সফলভাবে তৈরি হয়েছে!)")
          except Exception as e:
            st.error(f"Error creating agent: {e}")
      else:
        st.error("Please provide both Full Name and Phone Number. (পুরো নাম ও ফোন নম্বর আবশ্যক।)")

  # Display Generated Shareable Link if available in session state
  if st.session_state.get("last_generated_link"):
    st.write("---")
    st.markdown(f"#### 🔗 WhatsApp Shareable Link for **{st.session_state.get('last_generated_agent_name')}**")
    st.info("নিচের লিংকটি কপি করে এজেন্টের হোয়াটসঅ্যাপে পাঠিয়ে দিন। এজেন্ট লিংকে ক্লিক করলেই সরাসরি অ্যাপে লগইন হয়ে যাবে এবং হোম স্ক্রিনে সেভ (Add to Home Screen) করতে পারবে।")
    
    share_url = st.session_state["last_generated_link"]
    st.code(share_url, language="text")
    
    whatsapp_msg = urllib.parse.quote(f"নমস্কার {st.session_state.get('last_generated_agent_name')}! P.S Mediseller অ্যাপে কাজ করার জন্য আপনার সরাসরি লগইন লিংক:\n\n{share_url}\n\nএই লিংকে টাচ করে ব্রাউজার থেকে ওপেন করুন এবং 'Add to Home Screen' করে অ্যাপ হিসেবে ব্যবহার করুন।")
    whatsapp_url = f"https://api.whatsapp.com/send?text={whatsapp_msg}"
    
    st.markdown(f'''
    <a href="{whatsapp_url}" target="_blank">
        <button style="background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: white; border: none; padding: 12px 20px; border-radius: 10px; font-weight: bold; cursor: pointer; font-size: 15px; box-shadow: 0 4px 15px rgba(34, 197, 94, 0.4);">
            🟢 Share via WhatsApp (হোয়াটসঅ্যাপে পাঠান)
        </button>
    </a>
    ''', unsafe_allow_html=True)

  st.write("---")
  st.write("#### 👥 Registered Users / Agents (নিবন্ধিত ইউজারগণ)")
  users_list_df = pd.read_sql_query("SELECT username AS 'Username', role AS 'Role', fullname AS 'Full Name', phone AS 'Phone', created_at AS 'Created Date' FROM users", conn)
  if not users_list_df.empty:
    st.dataframe(users_list_df, use_container_width=True)
  else:
    st.info("No users found.")

