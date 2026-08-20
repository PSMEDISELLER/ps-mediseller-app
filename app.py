import os

# =========================================================
# 1GB FILE UPLOAD LIMIT CONFIGURATION
# =========================================================
os.makedirs(".streamlit", exist_ok=True)
with open(".streamlit/config.toml", "w") as f:
    f.write("[server]\nmaxUploadSize = 1024\n")

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import urllib.parse
import base64
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
  const base_url = window.location.href.split('?')[0];
  const manifest = {{
    "name": "P.S MEDISELLER",
    "short_name": "Mediseller",
    "start_url": base_url,
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
  
  if ('serviceWorker' in navigator) {{
    navigator.serviceWorker.register('sw.js').catch(err => console.log('SW error:', err));
  }}
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
            <b>(অ্যাপটি ব্যবহারের জন্য আপনার ফোনের জিপিএস লোকেশন অন করুন এবং পারমিশন দিন। লোকেশন বন্ধ রাখলে অ্যাপ ব্যবহার করা যাবে কাশী করা যাবে না।)</b>
        </p>
        <button onclick="requestLocation()" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border:
none; padding: 14px 28px; border-radius: 10px; font-weight: bold; font-size: 16px; cursor: pointer; width: 100%; box-shadow: 0 4px 15px
rgba(59, 130, 246, 0.4);">
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
setInterval(checkAndRequestLocation, 300000);
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
# DATABASE SETUP
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
    is_active INTEGER DEFAULT 1,
    allow_resubmit INTEGER DEFAULT 0,
    allowed_menus TEXT DEFAULT '📍 Add Location (লোকেশন যোগ),🔍 Search & Details (অনুসন্ধান ও বিবরণ),📦 Pending Orders (বাকি অর্ডার),📋 Daily & Monthly Work (দৈনিক ও মাসিক কাজ),📋 Due & Delivery (বকেয়া ও ডেলিভারি),🗺️ Route Map (রুট ম্যাপ),📅 Attendance (উপস্থিতি)'
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
    route_order INTEGER DEFAULT 0,
    current_due REAL DEFAULT 0
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
    remaining_due TEXT DEFAULT '0',
    status TEXT DEFAULT 'Pending',
    created_at TEXT NOT NULL
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL,
    date TEXT NOT NULL,
    check_time TEXT NOT NULL,
    status TEXT DEFAULT 'Present',
    UNIQUE(username, date)
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS recycle_bin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type TEXT NOT NULL,
    item_title TEXT NOT NULL,
    item_data TEXT NOT NULL,
    deleted_at TEXT NOT NULL
)
""")

c.execute("PRAGMA table_info(locations)")
existing_cols_loc = [row[1] for row in c.fetchall()]
if "party_phone" not in existing_cols_loc:
  c.execute("ALTER TABLE locations ADD COLUMN party_phone TEXT")
if "current_due" not in existing_cols_loc:
  c.execute("ALTER TABLE locations ADD COLUMN current_due REAL DEFAULT 0")

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
if "allow_resubmit" not in existing_user_cols:
  c.execute("ALTER TABLE users ADD COLUMN allow_resubmit INTEGER DEFAULT 0")
if "allowed_menus" not in existing_user_cols:
  c.execute("ALTER TABLE users ADD COLUMN allowed_menus TEXT DEFAULT '📍 Add Location (লোকেশন যোগ),🔍 Search & Details (অনুসন্ধান ও বিবরণ),📦 Pending Orders (বাকি অর্ডার),📋 Daily & Monthly Work (দৈনিক ও মাসিক কাজ),📋 Due & Delivery (বকেয়া ও ডেলিভারি),🗺️ Route Map (রুট ম্যাপ),📅 Attendance (উপস্থিতি)'")

c.execute("PRAGMA table_info(task_assignments)")
existing_cols_task = [row[1] for row in c.fetchall()]
if "sale_amount" not in existing_cols_task:
  c.execute("ALTER TABLE task_assignments ADD COLUMN sale_amount TEXT DEFAULT '0'")
if "payment_collected_actual" not in existing_cols_task:
  c.execute("ALTER TABLE task_assignments ADD COLUMN payment_collected_actual TEXT DEFAULT '0'")
if "remaining_due" not in existing_cols_task:
  c.execute("ALTER TABLE task_assignments ADD COLUMN remaining_due TEXT DEFAULT '0'")
conn.commit()

c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
  c.execute("INSERT INTO users (username, password, role, fullname, phone, created_at, is_active, allow_resubmit) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("admin", "admin123", "admin", "Admin", "8918740325", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1, 1))
  c.execute("INSERT INTO users (username, password, role, fullname, phone, created_at, is_active, allow_resubmit) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("delivery", "user123", "staff", "Delivery Agent", "8918740325", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1, 0))
  conn.commit()

def move_to_recycle_bin(item_type, item_title, item_data_dict):
    data_json = json.dumps(item_data_dict)
    deleted_at = get_ist_time().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO recycle_bin (item_type, item_title, item_data, deleted_at) VALUES (?, ?, ?, ?)",
              (item_type, item_title, data_json, deleted_at))
    conn.commit()

current_dt_str = get_ist_time()

c.execute("SELECT id, order_date FROM orders")
for row_ord in c.fetchall():
  try:
    cleaned_date = str(row_ord[1]).strip()
    if " " in cleaned_date:
        o_time = datetime.strptime(cleaned_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    else:
        o_time = datetime.strptime(cleaned_date, "%Y-%m-%d").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    if (current_dt_str - o_time) > timedelta(days=7):
      c.execute("DELETE FROM orders WHERE id=?", (row_ord[0],))
  except Exception:
    pass

c.execute("SELECT id, created_at, status FROM task_assignments")
for row_task in c.fetchall():
  try:
    t_status = str(row_task[2]).strip().lower() if row_task[2] else ""
    if t_status == "completed":
      cleaned_task_date = str(row_task[1]).strip()
      if " " in cleaned_task_date:
          t_time = datetime.strptime(cleaned_task_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
      else:
          t_time = datetime.strptime(cleaned_task_date, "%Y-%m-%d").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
      if (current_dt_str - t_time) > timedelta(hours=48):
        c.execute("DELETE FROM task_assignments WHERE id=?", (row_task[0],))
  except Exception:
    pass

conn.commit()

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

query_params = st.query_params
saved_user_js = streamlit_js_eval(js_expressions="localStorage.getItem('ps_mediseller_user')", key="get_saved_user_storage")
target_login = None

if query_params.get("login"):
    target_login = query_params.get("login")
    st.markdown(f"<script>localStorage.setItem('ps_mediseller_user', '{target_login}');</script>", unsafe_allow_html=True)
    st.session_state["username"] = target_login
elif saved_user_js and saved_user_js != "null" and saved_user_js != "None":
    target_login = saved_user_js
    st.session_state["username"] = target_login

if "username" not in st.session_state:
    st.session_state["username"] = target_login if target_login else "delivery"
if "user_role" not in st.session_state:
    st.session_state["user_role"] = "staff"

if target_login:
    c.execute("SELECT fullname, role, is_active FROM users WHERE username=?", (target_login,))
    user_row = c.fetchone()
    if user_row:
        f_name, r_role, is_active = user_row
        if is_active == 0:
            st.warning("⚠️ আপনার একাউন্টটি ব্লক করা হয়েছে। অনুগ্রহ করে অ্যাডমিনের সাথে যোগাযোগ করুন।")
            st.markdown("<script>localStorage.removeItem('ps_mediseller_user');</script>", unsafe_allow_html=True)
            st.stop()
        else:
            st.session_state["username"] = target_login
            st.session_state["user_role"] = r_role
            if query_params.get("login"):
                st.query_params.clear()
                st.rerun()
    else:
        st.markdown("<script>localStorage.removeItem('ps_mediseller_user');</script>", unsafe_allow_html=True)

current_logged_username = st.session_state["username"]
if current_logged_username != "admin":
    c.execute("SELECT is_active FROM users WHERE username=?", (current_logged_username,))
    res_act = c.fetchone()
    if res_act and res_act[0] == 0:
        st.error("🚫 আপনার একাউন্টটি অ্যাডমিন কর্তৃক ব্লক (Block) করা হয়েছে। আপনি এই অ্যাপটি ব্যবহার করতে পারবেন না।")
        st.stop()

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
if curr_user_row and curr_user_row[0]:
    display_user_name = curr_user_row[0]
else:
    display_user_name = st.session_state['username']

col_u1, _ = st.columns([3, 1])
with col_u1:
  # ফ্রন্ট পেজে ইউজারের নাম সঠিকভাবে শো করানো হচ্ছে
  st.write(f"👤 User: **{display_user_name}** (`{st.session_state['user_role']}`)")

c.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'")
pending_ord_count = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM task_assignments WHERE status='Pending'")
pending_task_count = c.fetchone()[0]

total_pending_items = pending_ord_count + pending_task_count

show_notif = True
if "notif_dismissed_time" in st.session_state:
    time_diff = (get_ist_time() - st.session_state["notif_dismissed_time"]).total_seconds()
    if time_diff < 3600:
        show_notif = False

if show_notif and total_pending_items > 0:
    col_n1, col_n2 = st.columns([5, 1])
    with col_n1:
        st.warning("🔔 **নোটিফিকেশন:** আপনার অর্ডার পেন্ডিং বা ডিউ পেন্ডিং রয়েছে। **পেন্ডিং Order খাতায় তুলতে বাকি!**")
    with col_n2:
        if st.button("❌ সরান", key="dismiss_notif_bar_btn"):
            st.session_state["notif_dismissed_time"] = get_ist_time()
            st.rerun()

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
  with st.expander("পাসওয়ার্ড ভুলে গেছেন? (Forgot Password)"):
    st.info("অ্যাডমিন পাসওয়ার্ড রিসেট করতে মাস্টার কোড ব্যবহার করুন। (Master Code: PSMEDISELLER)")
    master_code = st.text_input("Master Code (মাস্টার কোড)", type="password")
    new_admin_pass = st.text_input("New Admin Password", type="password")
    if st.button("Reset Admin Password (রিসেট করুন)"):
        if master_code == "PSMEDISELLER" and new_admin_pass.strip():
            c.execute("UPDATE users SET password=? WHERE username='admin'", (new_admin_pass.strip(),))
            conn.commit()
            st.success("পাসওয়ার্ড সফলভাবে রিসেট হয়েছে! (Password Reset Successful!)")
        else:
            st.error("ভুল কোড বা পাসওয়ার্ড! (Invalid Code or Password!)")

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
# DYNAMIC MENU PERMISSIONS 
# =========================================================
all_basic_menus = [
    "📍 Add Location (লোকেশন যোগ)",
    "🔍 Search & Details (অনুসন্ধান ও বিবরণ)",
    "📦 Pending Orders (বাকি অর্ডার)",
    "📋 Daily & Monthly Work (দৈনিক ও মাসিক কাজ)",
    "📋 Due & Delivery (বকেয়া ও ডেলিভারি)",
    "🗺️ Route Map (রুট ম্যাপ)",
    "📅 Attendance (উপস্থিতি)"
]

menu_options = []
if st.session_state["user_role"] == "admin":
  menu_options = all_basic_menus + [
      "📊 Live Tracking (লাইভ ট্র্যাকিং)",
      "⚙️ Settings & Agents (সেটিংসে)"
  ]
else:
  c.execute("SELECT allowed_menus FROM users WHERE username=?", (st.session_state["username"],))
  row = c.fetchone()
  if row and row[0]:
    menu_options = [m.strip() for m in row[0].split(",") if m.strip() in all_basic_menus]
  if not menu_options:
    menu_options = all_basic_menus

current_page_param = query_params.get("page", menu_options[0] if menu_options else all_basic_menus[0])
if current_page_param not in menu_options:
  current_page_param = menu_options[0] if menu_options else all_basic_menus[0]

default_index = menu_options.index(current_page_param)
selected_menu = st.radio("Select Menu (মেনু সিলেক্ট):", menu_options, index=default_index, horizontal=False, label_visibility="collapsed")

if selected_menu != current_page_param:
  st.query_params["page"] = selected_menu
  st.rerun()

st.write("---")

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
        st.success("GPS location taken! (নেওয়া হয়েছে!)")
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

  with st.form("order_visit_entry_form", clear_on_submit=True):
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
        st.session_state["order_party_search_text_input"] = "" # Search clear update
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
        st.session_state["order_party_search_text_input"] = "" # Search clear update
        st.success("Visit saved successfully! (সেভ হয়েছে!)")
        st.rerun()

  st.write("---")
  with st.expander("📋 Recent Orders & Visits (সামপ্রতিক রিপোর্ট) - Click to Open", expanded=False):
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
  
  is_searching = bool(master_search_query.strip())
  
  with st.expander(f"🩺 Non-Map List ({len(doc_df)} Entries) (ম্যাপবিহীন তালিকা)", expanded=is_searching):    
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
            move_to_recycle_bin("Location", row['party_name'], dict(row))
            c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
            conn.commit()
            st.success("Moved to Recycle Bin! (রিসাইকেল বিনে পাঠানো হয়েছে!)")
            st.rerun()
        st.write("---")
    else:
      st.info("No non-map parties found. (ম্যাপবিহীন পার্টি নেই।)")

  st.write("---")
  with st.expander(f"📍 Mapped List ({len(mapped_df)} Records) (ম্যাপযুক্ত তালিকা)", expanded=is_searching):
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
            move_to_recycle_bin("Location", row['party_name'], dict(row))
            c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
            conn.commit()
            st.success("Moved to Recycle Bin! (রিসাইকেল বিনে পাঠানো হয়েছে!)")
            st.rerun()
        st.write("---")
    else:
      st.info("No mapped parties found. (ম্যাপযুক্ত পার্টি নেই।)")

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
          c.execute("UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?",
          (st.session_state["username"],))
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
        if st.session_state["user_role"] == "admin":
          html_comp_ord = generate_html_report("Completed Orders History", completed_ord_df[["party_name", "order_details", "order_date"]])
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
            if st.button("🗑️ Clear All Completed Orders History (সব ডিলিট)", type="secondary"):
              for _, r in completed_ord_df.iterrows():
                  move_to_recycle_bin("Order", r['party_name'], dict(r))
              c.execute("DELETE FROM orders WHERE status='Completed'")
              conn.commit()
              st.success("All completed orders history moved to Recycle Bin! (রিসাইকেল বিনে পাঠানো হয়েছে!)")
              st.rerun()
          st.write("---")
        for idx, row in completed_ord_df.iterrows():
          if st.session_state["user_role"] == "admin":
            cols = st.columns([2, 4, 2, 1.5])
          else:
            cols = st.columns([2, 4, 2])
          cols[0].write(f"**{row['party_name']}**")
          cols[1].write(row['order_details'])
          cols[2].write("✅ Completed (সম্পন্ন)")
          if st.session_state["user_role"] == "admin":
            if cols[3].button("🗑️ Delete", key=f"del_comp_ord_{row['id']}"):
              move_to_recycle_bin("Order", row['party_name'], dict(row))
              c.execute("DELETE FROM orders WHERE id=?", (row['id'],))
              conn.commit()
              st.success("Moved to Recycle Bin!")
              st.rerun()
          st.write("---")
      else:
        st.info("No completed orders history.")

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
          if st.button("🗑️ Clear All Daily Work Records (সব কাজ মুছুন)", type="secondary"):
            c.execute("SELECT * FROM daily_work")
            all_dw = c.fetchall()
            for dw in all_dw:
                move_to_recycle_bin("Daily Work", dw[1], {"id": dw[0], "party_name": dw[1], "activity_type": dw[2], "work_date": dw[3]})
            c.execute("DELETE FROM daily_work")
            conn.commit()
            st.success("All daily work records moved to Recycle Bin! (রিসাইকেল বিনে পাঠানো হয়েছে!)")
            st.rerun()
        st.write("---")
    work_df = pd.read_sql_query("SELECT * FROM daily_work ORDER BY work_date DESC, id DESC", conn)
    if not work_df.empty:
      unique_dates = work_df['work_date'].unique()
      for d_str in unique_dates:
        date_records = work_df[work_df['work_date'] == d_str]
        count_parties = len(date_records)
        formatted_d = format_date_display(d_str)

        with st.expander(f"📅 Date: {formatted_d} (Total: {count_parties}) - Click to Open", expanded=False):
          if st.session_state["user_role"] == "admin":
            if st.button(f"🗑️ Delete Date Data ({formatted_d}) (সব ডিলিট)", key=f"del_date_{d_str}", type="secondary"):
              for _, w_row in date_records.iterrows():
                  move_to_recycle_bin("Daily Work", w_row['party_name'], dict(w_row))
              c.execute("DELETE FROM daily_work WHERE work_date=?", (d_str,))
              conn.commit()
              st.success("Moved to Recycle Bin!")
              st.rerun()
            st.write("---")
          for idx, w_row in date_records.iterrows():
            cols = st.columns([3, 2, 1.5])
            cols[0].write(f"Party: **{w_row['party_name']}**")
            cols[1].write(f"Status: `{w_row['activity_type']}`")
           
            if st.session_state["user_role"] == "admin":
              if cols[2].button("🗑️ Delete (ডিলিট)", key=f"del_dw_{w_row['id']}"):
                move_to_recycle_bin("Daily Work", w_row['party_name'], dict(w_row))
                c.execute("DELETE FROM daily_work WHERE id=?", (w_row['id'],))
                conn.commit()
                st.success("Moved to Recycle Bin!")
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
      selected_mo_key = st.selectbox("Select Month (মাস)", list(months_dict.keys()), format_func=lambda x: months_dict[x],
      index=list(months_dict.keys()).index(current_mo_num) if current_mo_num in months_dict else 7)      
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
            if st.button(f"🗑️ Delete All Work Records for Month: {selected_month}", type="secondary"):
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

  task_tab1, task_tab2, task_tab3, task_tab4 = st.tabs([
      "Active Tasks (চলমান কাজ)",
      "Agent Date-wise Summary (এজেন্ট ও তারিখ অনুযায়ী সামারি)",
      "Completed Tasks History (সম্পন্ন কাজ)",
      "💰 Master Due List (ডিউ লিস্ট)"
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
        st.warning("No matching party found! (কোনো পার্টি পাওয়া যায়নি!)")
        sel_pt = ""

    auto_due_val = "0"
    if sel_pt and sel_pt.strip():
      c.execute("SELECT current_due FROM locations WHERE party_name=?", (sel_pt.strip(),))
      res_due = c.fetchone()
      if res_due and res_due[0] is not None:
        auto_due_val = str(int(res_due[0]) if float(res_due[0]).is_integer() else res_due[0])

    with st.form("easy_assign_form", clear_on_submit=True):
      st.write("#### ➕ Assign New Task (নতুন টাস্ক দিন)")
      
      current_logged_user = st.session_state["username"]
      sel_ag = st.selectbox(
          "Select Agent (এজেন্ট সিলেক্ট করুন)", 
          all_agents, 
          index=all_agents.index(current_logged_user) if current_logged_user in all_agents else 0,
          format_func=lambda x: agent_name_map.get(x, x)
      )

      st.write("**Work Type (কাজের ধরণ):**")
      col_chk1, col_chk2 = st.columns(2)
      with col_chk1:
        chk_delivery = st.checkbox("🚚 Delivery (ডেলিভারি)")
      with col_chk2:
        chk_due = st.checkbox("💰 Due Collection (ডিউ কালেকশন)")

      d_amount = st.text_input("Due Amount (ডিউ টাকা)", auto_due_val)
      submit_easy_task = st.form_submit_button("🎯 Add Task (কাজ যোগ)", type="primary")

      if submit_easy_task:
        if not sel_pt.strip():          
          st.error("Please select a party. (পার্টি সিলেক্ট করুন।)")
        else:
          selected_tasks = []
          if chk_delivery:
            selected_tasks.append("Delivery (ডেলিভারি)")
          if chk_due:
            selected_tasks.append("Due Collection (ডিউ কালেকশন)")
          if selected_tasks:
            t_type_str = " & ".join(selected_tasks)
            c.execute(
                "INSERT INTO task_assignments (agent_name, party_name, task_type, due_amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (sel_ag, sel_pt.strip(), t_type_str, d_amount, "Pending", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            st.session_state["task_party_search_text_input"] = "" # Search clear update
            st.success("Task assigned successfully! (কাজ দেওয়া হয়েছে!)")
            st.rerun()
          else:
            st.error("Please select at least one task type (Delivery or Due Collection).")

    st.write("---")
    st.write("#### 📋 Active Pending Tasks (কর্মচারী অনুযায়ী কাজ)")
   
    pending_tasks_df = pd.read_sql_query("""
        SELECT t.id, t.agent_name, u.fullname as agent_fullname, t.party_name, t.task_type, t.due_amount, t.created_at, l.address, l.party_phone
        FROM task_assignments t
        LEFT JOIN users u ON t.agent_name = u.username
        LEFT JOIN locations l ON t.party_name = l.party_name
        WHERE t.status='Pending'
        ORDER BY t.created_at DESC
    """, conn)
    if not pending_tasks_df.empty:
      unique_agents_in_tasks = pending_tasks_df['agent_name'].unique()
      for ag_username in unique_agents_in_tasks:
        ag_rows = pending_tasks_df[pending_tasks_df['agent_name'] == ag_username]
        ag_disp_name = ag_rows.iloc[0]['agent_fullname'] if pd.notna(ag_rows.iloc[0]['agent_fullname']) else ag_username
       
        with st.expander(f"👤 Agent: {ag_disp_name} ({len(ag_rows)} Pending Tasks) - Click to Open", expanded=False):
          for idx, row in ag_rows.iterrows():
            st.markdown(f"**Party:** `{row['party_name']}` | **Task:** `{row['task_type']}` | **Assigned Due:** ₹`{row['due_amount']}`")
            if pd.notna(row['address']) and row['address']:
              st.markdown(f"📍 Address: {row['address']} {(' | Ph: ' + str(row['party_phone'])) if pd.notna(row['party_phone']) else ''}")
           
            with st.form(key=f"complete_task_form_{row['id']}", clear_on_submit=True):
              col_f1, col_f2 = st.columns(2)
              with col_f1:
                sale_input = st.text_input("Total Sale Amount (কত টাকা সেল ছিল)", value="0", key=f"sale_amt_{row['id']}")
              with col_f2:
                payment_input = st.text_input("Payment Collected (কত টাকা পেমেন্ট দিয়েছে)", value=str(row['due_amount']), key=f"pay_amt_{row['id']}")
             
              submit_complete = st.form_submit_button("✔️ Complete Task (সম্পন্ন বলে ক্লিক করুন)", type="primary")
              if submit_complete:
                try:
                  t_due = float(row['due_amount']) if str(row['due_amount']).strip() else 0.0
                  s_amt = float(sale_input) if sale_input.strip() else 0.0
                  p_amt = float(payment_input) if payment_input.strip() else 0.0
                  r_due = t_due + s_amt - p_amt
                except ValueError:
                  r_due = 0.0

                c.execute(
                    "UPDATE task_assignments SET status='Completed', sale_amount=?, payment_collected_actual=?, remaining_due=? WHERE id=?",
                    (sale_input, payment_input, str(r_due), row['id'])
                )
                c.execute("UPDATE locations SET current_due=? WHERE party_name=?", (r_due, row['party_name']))
                c.execute(
                    "UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?",
                    (row['agent_name'],)
                )
                conn.commit()
                st.success("Task marked as completed successfully! (সম্পন্ন হয়েছে!)")
                st.rerun()
            
            if st.session_state["user_role"] == "admin":
              if st.button("🗑️ Delete Task (টাস্ক ডিলিট)", key=f"del_pend_task_{row['id']}"):
                move_to_recycle_bin("Task", row['party_name'], dict(row))
                c.execute("DELETE FROM task_assignments WHERE id=?", (row['id'],))
                conn.commit()
                st.success("Task moved to Recycle Bin!")
                st.rerun()

            st.write("---")
    else:      
      st.info("No active pending tasks. (কোনো পেন্ডিং টাস্ক নেই।)")

  with task_tab2:
    st.markdown("#### Agent Date-wise Summary (এজেন্ট ও তারিখ অনুযায়ী সামারি)")
    agent_sum_df = pd.read_sql_query("""
        SELECT t.agent_name, u.fullname as agent_fullname, SUBSTR(t.created_at, 1, 10) as task_date,
               COUNT(t.id) as total_tasks, SUM(CASE WHEN t.status='Completed' THEN 1 ELSE 0 END) as completed_tasks
        FROM task_assignments t
        LEFT JOIN users u ON t.agent_name = u.username
        GROUP BY t.agent_name, task_date
        ORDER BY task_date DESC
    """, conn)
    if not agent_sum_df.empty:
      if st.session_state["user_role"] == "admin":
        export_sum_df = agent_sum_df.copy()
        export_sum_df['Agent Name'] = export_sum_df.apply(lambda r: r['agent_fullname'] if pd.notna(r['agent_fullname']) and r['agent_fullname'] else r['agent_name'], axis=1)
        export_sum_df['Date'] = export_sum_df['task_date'].apply(lambda x: format_date_display(x))
        export_sum_df['Total Tasks'] = export_sum_df['total_tasks']
        export_sum_df['Completed Tasks'] = export_sum_df['completed_tasks']
        
        export_sum_df_final = export_sum_df[['Agent Name', 'Date', 'Total Tasks', 'Completed Tasks']]
        html_agent_sum = generate_html_report("Agent Task Summary Report", export_sum_df_final)
        st.download_button(
            label="📥 Download Agent Summary Report",
            data=html_agent_sum,
            file_name="mediseller_agent_summary_report.html",
            mime="text/html",
            type="primary"
        )
        st.write("---")

      for idx, row in agent_sum_df.iterrows():
        ag_disp = row['agent_fullname'] if pd.notna(row['agent_fullname']) and row['agent_fullname'] else row['agent_name']
        t_date = format_date_display(row['task_date'])
        tot = row['total_tasks']
        comp = row['completed_tasks']

        st.markdown(f"""
        <div style="background: #1e293b; border: 1px solid rgba(148, 163, 184, 0.35); border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
            <p style="margin: 0 0 6px 0; color: #38bdf8 !important; font-weight: 700; font-size: 16px;">👤 Agent: {ag_disp}</p>
            <p style="margin: 0 0 4px 0; color: #cbd5e1 !important; font-size: 13px;">📅 Date: <b>{t_date}</b></p>
            <p style="margin: 0 0 4px 0; color: #cbd5e1 !important; font-size: 13px;">📋 Total Tasks: <b>{tot}</b> | ✅ Completed: <b style="color: #34d399;">{comp}</b></p>
        </div>
        """, unsafe_allow_html=True)

        # Admin permission toggle for agent re-submission
        c.execute("SELECT allow_resubmit FROM users WHERE username=?", (row['agent_name'],))
        resub_row = c.fetchone()
        agent_allowed = bool(resub_row[0]) if resub_row and resub_row[0] is not None else False

        if st.session_state["user_role"] == "admin":
          resub_toggle = st.checkbox(
              f"🔓 Allow {ag_disp} to Re-submit completed tasks (রি-সাবমিশনের অনুমতি প্রদান করুন)", 
              value=agent_allowed, 
              key=f"resub_perm_{row['agent_name']}_{row['task_date']}"
          )
          if resub_toggle != agent_allowed:
            c.execute("UPDATE users SET allow_resubmit=? WHERE username=?", (1 if resub_toggle else 0, row['agent_name']))
            conn.commit()
            st.rerun()

        comp_tasks_df = pd.read_sql_query("""
            SELECT id, party_name, task_type, due_amount, sale_amount, payment_collected_actual, remaining_due
            FROM task_assignments
            WHERE agent_name=? AND SUBSTR(created_at, 1, 10)=? AND status='Completed'
        """, conn, params=(row['agent_name'], row['task_date']))

        if not comp_tasks_df.empty:
          with st.expander(f"🔄 Re-submission Option (ভুলবশত কমপ্লিট হওয়া কাজ পুনরায় একটিভ করুন - {len(comp_tasks_df)})", expanded=False):
            can_do_resubmit = (st.session_state["user_role"] == "admin") or (st.session_state["username"] == row['agent_name'] and agent_allowed)
            if not can_do_resubmit:
              st.warning("🔒 রি-সাবমিশন করার অনুমতি নেই। শুধুমাত্র অ্যাডমিন বা অ্যাডমিন অনুমতি দিলে এই এজেন্ট কাজ পুনরায় একটিভ করতে পারবে।")
            
            for _, ct_row in comp_tasks_df.iterrows():
              st.markdown(f"• **Party:** `{ct_row['party_name']}` | **Type:** `{ct_row['task_type']}` | **Collected:** ₹`{ct_row['payment_collected_actual']}`")
              if can_do_resubmit:
                if st.button(f"🔄 Move to Active Tasks (পুনরায় একটিভ করুন)", key=f"btn_resubmit_{ct_row['id']}"):
                  c.execute("UPDATE task_assignments SET status='Pending' WHERE id=?", (ct_row['id'],))
                  c.execute("UPDATE agent_live_locations SET completed_deliveries = CASE WHEN completed_deliveries > 0 THEN completed_deliveries - 1 ELSE 0 END WHERE username=?", (row['agent_name'],))
                  conn.commit()
                  st.success("Task moved back to Active Tasks! (কাজটি সফলভাবে পুনরায় একটিভ টাস্কে পাঠানো হয়েছে!)")
                  st.rerun()
              st.write("---")

        if st.session_state["user_role"] == "admin":
          if st.button(f"🗑️ Delete Tasks ({ag_disp} - {t_date})", key=f"del_agent_date_sum_{row['agent_name']}_{row['task_date']}"):
            c.execute("DELETE FROM task_assignments WHERE agent_name=? AND SUBSTR(created_at, 1, 10)=?", (row['agent_name'], row['task_date']))
            conn.commit()
            st.success("Deleted successfully! (ডিলিট হয়েছে!)")
            st.rerun()
        st.write("---")
    else:
      st.info("No summary records found.")

  with task_tab3:
    st.markdown("#### Completed Tasks History (সম্পন্ন কাজ)")
    completed_tasks_df = pd.read_sql_query("""
        SELECT t.id, t.agent_name, u.fullname as agent_fullname, t.party_name, t.task_type, t.due_amount, t.sale_amount, t.payment_collected_actual, t.remaining_due, t.created_at, l.address
        FROM task_assignments t
        LEFT JOIN users u ON t.agent_name = u.username
        LEFT JOIN locations l ON t.party_name = l.party_name
        WHERE t.status='Completed'
        ORDER BY t.created_at DESC
    """, conn)
    if not completed_tasks_df.empty:
      if st.session_state["user_role"] == "admin":
        export_comp_df = completed_tasks_df.copy()
        export_comp_df['Agent Name'] = export_comp_df.apply(lambda r: r['agent_fullname'] if pd.notna(r['agent_fullname']) and r['agent_fullname'] else r['agent_name'], axis=1)
        export_comp_df['Party Name'] = export_comp_df['party_name']
        export_comp_df['Task Type'] = export_comp_df['task_type']
        export_comp_df['Due Amount (₹)'] = export_comp_df['due_amount']
        export_comp_df['Sale Amount (₹)'] = export_comp_df['sale_amount']
        export_comp_df['Collection Amount (₹)'] = export_comp_df['payment_collected_actual']
        export_comp_df['Remaining Due (₹)'] = export_comp_df['remaining_due']
        export_comp_df['Completed Date'] = export_comp_df['created_at'].apply(lambda x: format_date_display(x))
        
        export_comp_df_final = export_comp_df[['Agent Name', 'Party Name', 'Task Type', 'Sale Amount (₹)', 'Collection Amount (₹)', 'Remaining Due (₹)', 'Completed Date']]
        
        html_comp_tasks = generate_html_report("Completed Tasks History", export_comp_df_final)
        col_tc1, col_tc2 = st.columns(2)
        with col_tc1:
          st.download_button(
              label="📥 Download Completed Tasks Report",
              data=html_comp_tasks,
              file_name="mediseller_completed_tasks_report.html",
              mime="text/html",
              type="primary"
          )
        with col_tc2:
          if st.button("🗑️ Clear All Completed Tasks History", type="secondary"):
            for _, r in completed_tasks_df.iterrows():
                move_to_recycle_bin("Task", r['party_name'], dict(r))
            c.execute("DELETE FROM task_assignments WHERE status='Completed'")
            conn.commit()
            st.success("All completed tasks moved to Recycle Bin!")
            st.rerun()
        st.write("---")
      for idx, row in completed_tasks_df.iterrows():
        ag_c_name = row['agent_fullname'] if pd.notna(row['agent_fullname']) and row['agent_fullname'] else row['agent_name']
        st.markdown(f"**Agent:** `{ag_c_name}` | **Party:** `{row['party_name']}` | **Task:** `{row['task_type']}`")
        st.markdown(f"📦 Sale: ₹`{row['sale_amount']}` | 💰 Collected: ₹`{row['payment_collected_actual']}` | ⏳ Remaining Due: ₹`{row['remaining_due']}`")
        if st.session_state["user_role"] == "admin":
          if st.button("🗑️ Delete Task Record", key=f"del_comp_task_{row['id']}"):
            move_to_recycle_bin("Task", row['party_name'], dict(row))
            c.execute("DELETE FROM task_assignments WHERE id=?", (row['id'],))
            conn.commit()
            st.success("Moved to Recycle Bin!")
            st.rerun()
        st.write("---")
    else:
      st.info("No completed tasks history found.")

  with task_tab4:
    st.write("#### 💰 Master Due List & Management (পার্টি ডিউ ম্যানেজমেন্ট)")
    
    col_md1, col_md2 = st.columns([1, 2])
    with col_md1:
      st.write("##### ✏️ Update Due (ডিউ আপডেট)")
      due_parties = [p for p in all_parties]
      if due_parties:
        selected_due_party = st.selectbox("Select Party:", due_parties, key="admin_due_update_party")
        c.execute("SELECT current_due FROM locations WHERE party_name=?", (selected_due_party,))
        curr_d = c.fetchone()
        curr_d_val = curr_d[0] if (curr_d and curr_d[0] is not None) else 0.0
        
        with st.form("update_due_form"):
          new_due_val = st.text_input("Current Due Amount (বর্তমান ডিউ)", str(curr_d_val))
          if st.form_submit_button("💾 Update Due", type="primary"):
            try:
              nd_val = float(new_due_val)
            except ValueError:
              nd_val = 0.0
            c.execute("UPDATE locations SET current_due=? WHERE party_name=?", (nd_val, selected_due_party))
            conn.commit()
            st.success("Due updated successfully! (ডিউ আপডেট হয়েছে!)")
            st.rerun()
      else:
        st.info("No parties available.")

    with col_md2:
      st.write("##### 📋 Parties with Pending Due (বাকি ডিউ তালিকা)")
      due_df = pd.read_sql_query("SELECT party_name AS 'Party Name', current_due AS 'Due Amount (₹)', party_phone AS 'Phone' FROM locations WHERE current_due > 0 ORDER BY current_due DESC", conn)
      if not due_df.empty:
        st.dataframe(due_df, use_container_width=True)
      else:
        st.success("No parties have any pending dues! (কারো ডিউ বাকি নেই!)")

elif selected_menu == "🗺️ Route Map (রুট ম্যাপ)":
  st.write("### 🗺️ Route Map & Locations (রুট ম্যাপ)")
  c.execute("SELECT party_name, address, lat, lon, party_phone FROM locations WHERE lat IS NOT NULL AND lon IS NOT NULL ORDER BY party_name ASC")
  route_data = c.fetchall()
  if route_data:
    avg_lat = sum([r[2] for r in route_data]) / len(route_data)
    avg_lon = sum([r[3] for r in route_data]) / len(route_data)
    r_map = folium.Map(location=[avg_lat, avg_lon], zoom_start=13, tiles=None)
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google Maps Street",
        name="Street View (স্ট্রিট ভিউ)",
        show=True
    ).add_to(r_map)
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google Maps Satellite",
        name="Satellite View (স্যাটেলাইট ভিউ)",
        show=False
    ).add_to(r_map)

    for idx, r in enumerate(route_data):
      p_n, p_a, p_lat, p_lon, p_ph = r[0], r[1], r[2], r[3], r[4]
      popup_html = f"<b>{p_n}</b><br>{p_a or ''}<br>{('Ph: ' + str(p_ph)) if p_ph else ''}"
      folium.Marker(
          [p_lat, p_lon],
          popup=folium.Popup(popup_html, max_width=250),
          tooltip=f"{idx+1}. {p_n}",
          icon=folium.Icon(color="blue", icon="info-sign")
      ).add_to(r_map)

    if gps_lat and gps_lon:
      folium.Marker(
          [gps_lat, gps_lon],
          popup="<b>Your Live Location (আপনার লাইভ লোকেশন)</b>",
          tooltip="You are here",
          icon=folium.Icon(color="red", icon="user", prefix="fa")
      ).add_to(r_map)

    folium.LayerControl().add_to(r_map)
    st_folium(r_map, width="100%", height=500, key="route_map_view")
  else:
    st.info("No mapped locations available to show on route map. (ম্যাপযুক্ত কোনো লোকেশন নেই।)")

elif selected_menu == "📅 Attendance (উপস্থিতি)":
  st.write("### 📅 Daily & Monthly Attendance (উপস্থিতি ব্যবস্থাপনা)")
  
  c.execute("SELECT username, fullname, role FROM users")
  att_users_data = c.fetchall()
  agent_name_map = {r[0]: (r[1] if r[1] else r[0]) for r in att_users_data}

  att_tab1, att_tab2 = st.tabs([
      "📅 Daily Attendance (আজকের উপস্থিতি ও চেক-ইন)",
      "📊 Monthly & Agent Attendance Report (মাসিক ও কর্মী উপস্থিতি রিপোর্ট)"
  ])

  with att_tab1:
    st.write("#### 📝 Today's Check-in")
    today_date_str = get_ist_time().strftime("%Y-%m-%d")
    today_display_str = get_ist_time().strftime("%d.%m.%y")
    with st.form("attendance_form", clear_on_submit=True):
      st.write(f"Today Date: **{today_display_str}**")
      agent_for_att = st.session_state["username"]
      st.write(f"Agent: **{agent_name_map.get(agent_for_att, agent_for_att)}**")
      submit_att = st.form_submit_button("✅ Give Attendance / Check-in (উপস্থিতি দিন)", type="primary")
      if submit_att:
        try:
          check_time_str = get_ist_time().strftime("%H:%M:%S")
          c.execute(
              "INSERT INTO attendance (username, date, check_time, status) VALUES (?, ?, ?, ?)",
              (agent_for_att, today_date_str, check_time_str, "Present")
          )
          conn.commit()
          st.success("Attendance recorded successfully! (উপস্থিতি নথিভুক্ত হয়েছে!)")
          st.rerun()
        except sqlite3.IntegrityError:
          st.warning("Attendance already given for today! (আজকে ইতিমধ্যে উপস্থিতি দেওয়া হয়েছে!)")

    st.write("---")
    st.write("#### 📋 Today's Attendance List (আজকের উপস্থিতি তালিকা - সবাই দেখবে)")
    today_att_df = pd.read_sql_query("""
        SELECT a.date AS 'Date', u.fullname AS 'Agent Name', a.check_time AS 'Check-in Time', a.status AS 'Status'
        FROM attendance a
        LEFT JOIN users u ON a.username = u.username
        WHERE a.date = ?
        ORDER BY a.check_time DESC
    """, conn, params=(today_date_str,))
    if not today_att_df.empty:
      today_att_df['Date'] = today_att_df['Date'].apply(lambda x: format_date_display(x))
      st.dataframe(today_att_df, use_container_width=True)
    else:
      st.info("No attendance recorded for today yet. (আজ কেউ উপস্থিতি দেননি।)")

  with att_tab2:
    current_role = st.session_state["user_role"]
    current_user = st.session_state["username"]

    if current_role == "admin":
      st.write("#### 📊 Agent Attendance Summary & Date-wise Details")
      st.write("নিচে সব এজেন্টের নামের তালিকা দেওয়া হলো। যেকোনো এজেন্টে ক্লিক বা সিলেক্ট করলে তার পুরো মাসের তারিখ অনুযায়ী উপস্থিতি দেখতে পাবেন:")

      c.execute("SELECT username, fullname FROM users WHERE role='staff'")
      staff_list = c.fetchall()

      if staff_list:
        for s_user, s_fname in staff_list:
          display_name = s_fname if s_fname else s_user
          
          c.execute("SELECT COUNT(*) FROM attendance WHERE username=?", (s_user,))
          total_att_count = c.fetchone()[0]

          with st.expander(f"👤 Agent: {display_name} (`{s_user}`) — Total Attendance: {total_att_count} - Click to Open", expanded=False):
            agent_att_df = pd.read_sql_query("""
                SELECT date AS 'Date', check_time AS 'Check-in Time', status AS 'Status'
                FROM attendance
                WHERE username = ?
                ORDER BY date DESC, check_time DESC
            """, conn, params=(s_user,))

            if not agent_att_df.empty:
              agent_att_df['Date'] = agent_att_df['Date'].apply(lambda x: format_date_display(x))
              st.dataframe(agent_att_df, use_container_width=True)
            else:
              st.info(f"No attendance records found for {display_name}.")
      else:
        st.info("No delivery staff agents found.")

      st.write("---")
      all_att_report_df = pd.read_sql_query("""
          SELECT a.date AS 'Date', u.fullname AS 'Agent Name', a.check_time AS 'Check-in Time', a.status AS 'Status'
          FROM attendance a
          LEFT JOIN users u ON a.username = u.username
          ORDER BY a.date DESC, a.check_time DESC
      """, conn)
      if not all_att_report_df.empty:
        all_att_report_df['Date'] = all_att_report_df['Date'].apply(lambda x: format_date_display(x))
        html_all_att = generate_html_report("Complete Attendance Report", all_att_report_df)
        st.download_button(
            label="📥 Download Complete Attendance Report (PDF/HTML)",
            data=html_all_att,
            file_name="mediseller_complete_attendance_report.html",
            mime="text/html",
            type="primary"
        )
    else:
      st.write("#### 📊 Your Monthly Attendance Report")
      staff_att_df = pd.read_sql_query("""
          SELECT date AS 'Date', check_time AS 'Check-in Time', status AS 'Status'
          FROM attendance
          WHERE username = ?
          ORDER BY date DESC, check_time DESC
      """, conn, params=(current_user,))

      if not staff_att_df.empty:
        staff_att_df['Date'] = staff_att_df['Date'].apply(lambda x: format_date_display(x))
        st.dataframe(staff_att_df, use_container_width=True)
      else:
        st.info("You have no attendance records yet.")
      st.markdown("<p style='color: #60a5fa; font-size: 13px; margin-top: 10px;'><i>Note: Agents can only view their own attendance records. Report downloads are restricted to admins only.</i></p>", unsafe_allow_html=True)

elif selected_menu == "📊 Live Tracking (লাইভ ট্র্যাকিং)" and st.session_state["user_role"] == "admin":
  st.write("### 📊 Live Agent Tracking & Last Saved Locations (লাইভ ও লাস্ট লোকেশন ট্র্যাকিং)")
  st.markdown("<p style='color: #38bdf8; font-size: 13px;'><i>💡 Note: This page automatically refreshes every 10 seconds. Click on any agent marker on the map to see their last saved location or live location!</i></p>", unsafe_allow_html=True)

  live_df = pd.read_sql_query("""
      SELECT a.username, u.fullname, u.phone, a.lat, a.lon, a.last_updated, a.completed_deliveries
      FROM agent_live_locations a
      LEFT JOIN users u ON a.username = u.username
  """, conn)

  if not live_df.empty:
    for idx, r in live_df.iterrows():
      name = r['fullname'] if pd.notna(r['fullname']) and r['fullname'] else r['username']
      username = r['username']
      phone = r['phone'] if pd.notna(r['phone']) else "N/A"
      lat = r['lat']
      lon = r['lon']
      last_up = r['last_updated']
      completed = r['completed_deliveries']

      time_ago_str = "Never"
      if pd.notna(last_up):
        try:
          up_dt = datetime.strptime(str(last_up), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
          diff_sec = (get_ist_time() - up_dt).total_seconds()
          if diff_sec < 60:
            time_ago_str = f"{int(diff_sec)} seconds ago"
          elif diff_sec < 3600:
            time_ago_str = f"{int(diff_sec // 60)} minutes ago"
          else:
            time_ago_str = f"{int(diff_sec // 3600)} hours ago"
        except:
          time_ago_str = str(last_up)

      with st.expander(f"👤 Agent: {name} (`{username}`) — Last Active: {time_ago_str} - Click to Open", expanded=False):
        st.markdown(f"""
        - **Full Name:** {name}
        - **Username:** `{username}`
        - **Phone:** {phone}
        - **Completed Tasks:** <b style="color: #34d399;">{completed}</b>
        - **Last Updated Time:** `{last_up if pd.notna(last_up) else 'No update yet'}` ({time_ago_str})
        - **Last Known Coordinates:** `{lat}, {lon}`
        """, unsafe_allow_html=True)

        if pd.notna(lat) and pd.notna(lon):
          google_maps_track_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
          st.markdown(f'<a href="{google_maps_track_url}" target="_blank" style="text-decoration:none;"><button style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color:white; border:none; padding:10px 20px; border-radius:8px; cursor:pointer; font-weight:600; font-size:15px; margin-top:10px; box-shadow: 0 4px 12px rgba(16,185,129,0.4);">🗺️ Track Agent on Google Maps (গুগল ম্যাপে ট্র্যাক করুন)</button></a>', unsafe_allow_html=True)
        else:
          st.warning("GPS coordinates not yet available for this agent.")
        st.write("---")
  else:
    st.info("No live agent location data available yet.")

elif selected_menu == "⚙️ Settings & Agents (সেটিংসে)" and st.session_state["user_role"] == "admin":
  st.write("### ⚙️ Settings & Agents Management (কর্মী, অজানা ইউজার ও ম্যানেজমেন্ট)")
  
  c.execute("SELECT COUNT(*) FROM users WHERE role='staff'")
  total_staff_count = c.fetchone()[0]
  c.execute("SELECT COUNT(*) FROM users")
  total_users_count = c.fetchone()[0]

  col_st1, col_st2 = st.columns(2)
  with col_st1:
      st.markdown(f"""
      <div style="background: #1e293b; padding: 15px; border-radius: 12px; border: 1px solid #3b82f6; text-align: center;">
          <h4 style="margin: 0; color: #60a5fa;">👥 Registered Staff Agents</h4>
          <h2 style="margin: 5px 0 0 0; color: #34d399;">{total_staff_count}</h2>
      </div>
      """, unsafe_allow_html=True)
  with col_st2:
      st.markdown(f"""
      <div style="background: #1e293b; padding: 15px; border-radius: 12px; border: 1px solid #818cf8; text-align: center;">
          <h4 style="margin: 0; color: #a78bfa;">👤 Total System Users</h4>
          <h2 style="margin: 5px 0 0 0; color: #38bdf8;">{total_users_count}</h2>
      </div>
      """, unsafe_allow_html=True)
  st.write("")

  set_tab1, set_tab_perm, set_tab3, set_tab4, set_tab5, set_tab6 = st.tabs([
      "👥 Add Agents & Links",
      "🛡️ Menu Permissions",
      "🚨 Unknown & Blocked Agents", 
      "📂 Backup & Restore",
      "🗑️ Recycle Bin",
      "🔑 Admin Password"
  ])

  with set_tab1:
    st.write("#### ➕ Add New Staff / Agent & Generate Auto-Login Link")
    st.info("💡 এই সেকশন থেকে অ্যাডমিন নতুন এজেন্টের নাম, ইউজারনেম ও পাসওয়ার্ড দিয়ে একাউন্ট তৈরি করতে পারবেন। সাথে সাথে প্রতিটি এজেন্টের জন্য একটি **Auto-Login Link** তৈরি হয়ে যাবে, যা কপি করে এজেন্টকে দিলে সে বিনা বাধায় সরাসরি অ্যাপে প্রবেশ করতে পারবে।")

    eval_parent_url = streamlit_js_eval(js_expressions="window.parent.location.origin + window.parent.location.pathname", key="get_parent_window_url_clean")
    if eval_parent_url and "component" not in eval_parent_url:
        clean_base_url = eval_parent_url.rstrip("/")
    else:
        clean_base_url = "https://ps-mediseller-app-gcanjbehuut7h9rzk4xzfg.streamlit.app"

    with st.form("add_agent_form", clear_on_submit=True):
      new_uname = st.text_input("Username (ইউজারনেম, যেমন: rahul1)")
      new_pass = st.text_input("Password (পাসওয়ার্ড)")
      new_fname = st.text_input("Full Name (পুরো নাম)")
      new_phone = st.text_input("Phone Number (ফোন নম্বর)")
      submit_new_agent = st.form_submit_button("✅ Add Agent (এজেন্ট যুক্ত করুন)", type="primary")
      if submit_new_agent:
          if new_uname.strip() and new_pass.strip() and new_fname.strip():
              try:
                  c.execute("INSERT INTO users (username, password, role, fullname, phone, created_at, is_active, allow_resubmit) VALUES (?, ?, 'staff', ?, ?, ?, 1, 0)",
                            (new_uname.strip(), new_pass.strip(), new_fname.strip(), new_phone.strip(), get_ist_time().strftime("%Y-%m-%d %H:%M:%S")))
                  conn.commit()
                  st.success("New agent added successfully! (নতুন এজেন্ট যুক্ত হয়েছে!)")
                  st.rerun()
              except sqlite3.IntegrityError:
                  st.error("Username already exists! (এই ইউজারনেম ইতিমধ্যে আছে!)")
          else:
              st.error("Username, Password and Full Name are required! (সব তথ্য আবশ্যক!)")
              
    st.write("#### 📋 Existing Agents & Login Links")
    c.execute("SELECT username, fullname, password, phone, is_active FROM users WHERE role='staff'")
    staff_data = c.fetchall()
    for s in staff_data:
        s_uname, s_fname, s_pass, s_ph, s_act = s
        st.markdown(f"**Name:** {s_fname} | **User:** `{s_uname}` | **Pass:** `{s_pass}` | **Phone:** {s_ph}")
        link = f"{clean_base_url}/?login={s_uname}"
        st.code(link, language="text")
        st.write("---")

  with set_tab_perm:
    st.write("#### 🛡️ Menu Permissions (মেনু পারমিশন)")
    for s in staff_data:
        s_uname = s[0]
        c.execute("SELECT allowed_menus FROM users WHERE username=?", (s_uname,))
        am_row = c.fetchone()
        curr_menus = am_row[0].split(",") if am_row and am_row[0] else all_basic_menus
        sel_menus = st.multiselect(f"Permissions for {s_uname}", all_basic_menus, default=curr_menus, key=f"perm_{s_uname}")
        if st.button(f"Save Permissions for {s_uname}", key=f"btn_perm_{s_uname}"):
            c.execute("UPDATE users SET allowed_menus=? WHERE username=?", (",".join(sel_menus), s_uname))
            conn.commit()
            st.success("Permissions updated successfully!")

  with set_tab3:
    st.write("#### 🚨 Block/Unblock Agents (এজেন্ট ব্লক/আনব্লক)")
    for s in staff_data:
        s_uname, s_fname, _, _, s_act = s
        status = "Active" if s_act else "Blocked"
        st.write(f"**Agent:** {s_fname} (`{s_uname}`) - Status: `{status}`")
        if s_act:
            if st.button(f"🚫 Block {s_uname}", key=f"blk_{s_uname}"):
                c.execute("UPDATE users SET is_active=0 WHERE username=?", (s_uname,))
                conn.commit()
                st.rerun()
        else:
            if st.button(f"✅ Unblock {s_uname}", key=f"unblk_{s_uname}"):
                c.execute("UPDATE users SET is_active=1 WHERE username=?", (s_uname,))
                conn.commit()
                st.rerun()
        st.write("---")

  with set_tab4:
    st.write("#### 📂 Database Backup (ডাটাবেস ব্যাকআপ)")
    with open(DB_FILE, "rb") as f:
        st.download_button("📥 Download Database Backup (.db)", f, file_name="mediseller_backup.db")

  with set_tab5:
    st.write("#### 🗑️ Recycle Bin (রিসাইকেল বিন)")
    recycle_df = pd.read_sql_query("SELECT * FROM recycle_bin ORDER BY id DESC", conn)
    st.dataframe(recycle_df, use_container_width=True)
    if st.button("Clear Recycle Bin"):
        c.execute("DELETE FROM recycle_bin")
        conn.commit()
        st.success("Recycle Bin Cleared!")
        st.rerun()

  with set_tab6:
    st.write("#### 🔑 Admin Password Update (পাসওয়ার্ড পরিবর্তন)")
    with st.form("update_admin_pass"):
        new_pass = st.text_input("New Admin Password", type="password")
        if st.form_submit_button("Update Password", type="primary"):
            if new_pass.strip():
                c.execute("UPDATE users SET password=? WHERE username='admin'", (new_pass.strip(),))
                conn.commit()
                st.success("Admin Password Updated Successfully!")
            else:
                st.error("Please enter a valid password.")
