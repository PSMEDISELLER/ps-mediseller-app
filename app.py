import os
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
from datetime import datetime, timedelta, timezone

# === 1GB FILE UPLOAD LIMIT CONFIGURATION ===
os.makedirs(".streamlit", exist_ok=True)
config_path = ".streamlit/config.toml"
if not os.path.exists(config_path):
    with open(config_path, "w") as f:
        f.write("[server]\nmaxUploadSize = 1024\n")

# === PAGE CONFIGURATION ===
st.set_page_config(
    page_title="P. S MEDISELLER Allopathy & Ayurvedic Wholesaler",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
div[data-testid="stImage"] img {
    height: 180px !important;
    object-fit: cover !important;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

if os.path.exists("banner.jpg"):
    st.image("banner.jpg", use_container_width=True)

# === IST TIME & DATE FORMAT HELPERS ===
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
    except Exception:
        return date_str

# === CACHED ASSETS LOADING FOR SPEED ===
@st.cache_data
def load_logo_b64():
    for logo_name in ["1000135057_2.jpg", "1000204449.jpg", "1000135057.jpg"]:
        if os.path.exists(logo_name):
            with open(logo_name, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return ""

logo_b64 = load_logo_b64()

# === ADVANCED CUSTOM STYLING & PWA STANDALONE MANIFEST INJECTION ===
pwa_manifest_html = f"""
<script>
try {{
    const base_url = window.location.href.split('?')[0];
    const urlParams = new URLSearchParams(window.location.search);
    let current_user = urlParams.get('login');
    if (current_user) {{
        localStorage.setItem('ps_mediseller_user', current_user);
    }}
    let saved_user = localStorage.getItem('ps_mediseller_user');
    if (saved_user && saved_user !== "null" && saved_user !== "None") {{
        current_user = saved_user;
    }}
    const start_url_path = current_user ? base_url + "?login=" + current_user : base_url;
    const manifest = {{
        "name": "P.S MEDISELLER",
        "short_name": "Mediseller",
        "start_url": start_url_path,
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
    
    if ('serviceWorker' in navigator) {{
        navigator.serviceWorker.register('sw.js').catch(err => console.log('SW error:', err));
    }}
}} catch(e) {{
    console.log("PWA injection error:", e);
}}
</script>
"""
st.components.v1.html(pwa_manifest_html, height=0)

# === MANDATORY LOCATION PERMISSION ENFORCEMENT COMPONENT ===
mandatory_location_html = """
<div id="loc-overlay" style="display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(15, 23, 42, 0.98); z-index: 999999; justify-content: center; align-items: center; padding: 20px; box-sizing: border-box; font-family: 'Poppins', sans-serif;">
    <div style="background: #1e293b; border: 2px solid #ef4444; border-radius: 16px; padding: 30px; max-width: 450px; width: 100%; text-align: center; box-shadow: 0 20px 25px 5px rgba(0, 0, 0, 0.5);">
        <div style="font-size: 48px; margin-bottom: 15px;">📍</div>
        <h2 style="color: #f87171; margin-top: 0; font-size: 22px;">Location Permission Required<br> (লোকেশন পারমিশন আবশ্যক)</h2>
        <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin-bottom: 25px;">
            P.S Mediseller app requires your live GPS location to function properly. Please enable Location/GPS on your device and grant permission.<br><br>
            <b>(অ্যাপটি ব্যবহারের জন্য আপনার ফোনের জিপিএস লোকেশন অন করুন এবং পারমিশন দিন। লোকেশন বন্ধ রাখলে অ্যাপ ব্যবহার করা যাবে না।)</b>
        </p>
        <button onclick="requestLocation()" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border: none; padding: 14px 28px; border-radius: 10px; font-weight: bold; font-size: 16px; cursor: pointer; width: 100%; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);">
            Grant Permission / Retry (অনুমতি দিন / রিফ্রেশ)
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
        status.innerText = "Requesting location permission... (অনুমতি নেওয়া হচ্ছে...)";
    }
    checkAndRequestLocation();
}
window.addEventListener('load', function() {
    setTimeout(checkAndRequestLocation, 500);
    setInterval(checkAndRequestLocation, 300000);
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
.stButton>button, div.stButton > button, button[kind="secondary"],
button[kind="primary"], [data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
    color: #ffffff !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.2rem !important;
    font-weight: 600 !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important;
    transition: all 0.3s ease !important;
}
.stButton>button:hover, div.stButton > button:hover,
button[kind="secondary"]:hover, button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] > button:hover {
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

# === DATABASE SETUP & ACTIVE CONNECTION ===
DB_FILE = "mediseller_delivery.db"

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

# Global connection and cursor keep script fully active for line 810+
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
    allowed_menus TEXT DEFAULT 'Add Location (লোকেশন যোগ), Search & Details (অনুসন্ধান ও বিবরণ), Pending Orders (বাকি অর্ডার), Daily & Monthly Work (দৈনিক ও মাসিক কাজ), Due & Delivery (বকেয়া ও ডেলিভারি), Route Map (রুট ম্যাপ), Attendance (উপস্থিতি)'
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    date TEXT NOT NULL,
    check_time TEXT NOT NULL,
    status TEXT DEFAULT 'Present',
    UNIQUE (username, date)
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

# Database Column Checks
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
    c.execute("ALTER TABLE users ADD COLUMN allowed_menus TEXT DEFAULT 'Add Location (লোকেশন যোগ), Search & Details (অনুসন্ধান ও বিবরণ), Pending Orders (বাকি অর্ডার), Daily & Monthly Work (দৈনিক ও মাসিক কাজ), Due & Delivery (বকেয়া ও ডেলিভারি), Route Map (রুট ম্যাপ), Attendance (উপস্থিতি)'")

c.execute("PRAGMA table_info(task_assignments)")
existing_cols_task = [row[1] for row in c.fetchall()]
if "sale_amount" not in existing_cols_task:
    c.execute("ALTER TABLE task_assignments ADD COLUMN sale_amount TEXT DEFAULT '0'")
if "payment_collected_actual" not in existing_cols_task:
    c.execute("ALTER TABLE task_assignments ADD COLUMN payment_collected_actual TEXT DEFAULT '0'")
if "remaining_due" not in existing_cols_task:
    c.execute("ALTER TABLE task_assignments ADD COLUMN remaining_due TEXT DEFAULT '0'")

conn.commit()

# Default Users Creation
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
    c.execute(
        "INSERT INTO users (username, password, role, fullname, phone, created_at, is_active, allow_resubmit) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("admin", "admin123", "admin", "Admin", "8918740325", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1, 1)
    )
    c.execute(
        "INSERT INTO users (username, password, role, fullname, phone, created_at, is_active, allow_resubmit) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("staff", "user123", "staff", "Staff Agent", "8918740325", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1, 0)
    )
    conn.commit()

c.execute("SELECT username FROM users WHERE username='staff'")
if not c.fetchone():
    c.execute(
        "INSERT INTO users (username, password, role, fullname, phone, created_at, is_active, allow_resubmit) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("staff", "user123", "staff", "Staff Agent", "8918740325", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1, 0)
    )
    conn.commit()

# === UNIFIED & BULLETPROOF USER SESSION & REFRESH PERSISTENCE ===
url_user = st.query_params.get("login")
if isinstance(url_user, list):
    url_user = url_user[0] if url_user else None

saved_user_js = streamlit_js_eval(
    js_expressions="localStorage.getItem('ps_mediseller_user')",
    key="get_saved_user_storage_unique"
)

target_login = None
if url_user:
    target_login = str(url_user).strip()
elif saved_user_js and saved_user_js not in ["null", "None", "undefined"]:
    target_login = str(saved_user_js).strip()
elif "username" in st.session_state and st.session_state["username"] not in ["staff", "delivery"]:
    target_login = st.session_state["username"]

if not target_login:
    target_login = "staff"

c.execute("SELECT fullname, role, is_active FROM users WHERE username=?", (target_login,))
user_row = c.fetchone()

if user_row:
    f_name, r_role, is_active = user_row[0], user_row[1], user_row[2]
    if is_active == 0:
        st.warning("আপনার একাউন্টটি ব্লক করা হয়েছে। অনুগ্রহ করে অ্যাডমিনের সাথে যোগাযোগ করুন।")
        st.markdown("<script>localStorage.removeItem('ps_mediseller_user');</script>", unsafe_allow_html=True)
        st.query_params.clear()
        st.stop()
    else:
        st.session_state["username"] = target_login
        st.session_state["user_role"] = r_role
        st.query_params["login"] = target_login
        st.markdown(f"<script>localStorage.setItem('ps_mediseller_user', '{target_login}');</script>", unsafe_allow_html=True)
else:
    st.session_state["username"] = "staff"
    st.session_state["user_role"] = "staff"
    st.query_params["login"] = "staff"

def move_to_recycle_bin(item_type, item_title, item_data_dict):
    data_json = json.dumps(item_data_dict)
    deleted_at = get_ist_time().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "INSERT INTO recycle_bin (item_type, item_title, item_data, deleted_at) VALUES (?, ?, ?, ?)",
        (item_type, item_title, data_json, deleted_at)
    )
    conn.commit()

# === AUTOMATIC CLEANUP LOGIC ===
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

def generate_html_report(title, dataframe):
    import datetime
    safe_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    time_str = safe_now.strftime('%d.%m.%y %H:%M:%S')
    table_html = dataframe.to_html(index=False, border=0)
    html_content = f"""
<html>
<head>
<title>{title}</title>
<meta charset="UTF-8">
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; color: #333; background: #f9f9f9; }}
.header {{ text-align: center; margin-bottom: 20px; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; }}
h2 {{ color: #1e40af; margin: 0; }}
p {{ color: #555; font-size: 14px; margin: 5px 0; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 15px; background: white; }}
th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
th {{ background-color: #3b82f6; color: white; }}
.footer {{ margin-top: 20px; font-size: 12px; color: #777; text-align: center; }}
</style>
</head>
<body>
<div class="header">
<h2>{title}</h2>
<p>P. S MEDISELLER Report</p>
</div>
{table_html}
<p class="footer">Generated on: {time_str} IST</p>
</body>
</html>
"""
    return html_content

if "selected_lat" not in st.session_state:
    st.session_state["selected_lat"] = 22.8620
if "selected_lon" not in st.session_state:
    st.session_state["selected_lon"] = 87.3320

current_logged_username = st.session_state["username"]
if current_logged_username != "admin":
    c.execute("SELECT is_active FROM users WHERE username=?", (current_logged_username,))
    res_act = c.fetchone()
    if res_act and res_act[0] == 0:
        st.error("আপনার একাউন্টটি অ্যাডমিন কর্তৃক ব্লক (Block) করা হয়েছে। আপনি এই অ্যাপটি ব্যবহার করতে পারবেন না।")
        st.stop()

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
        if st.button("Logout (লগআউট)", key="logout_btn_top"):
            st.session_state["username"] = "staff"
            st.session_state["user_role"] = "staff"
            st.query_params.clear()
            st.markdown("<script>localStorage.removeItem('ps_mediseller_user');</script>", unsafe_allow_html=True)
            st.rerun()
    else:
        if st.button("Admin Login (অ্যাডমিন)", key="login_btn_top"):
            st.session_state["show_admin_login"] = True
            st.rerun()

c.execute("SELECT fullname FROM users WHERE username=?", (st.session_state['username'],))
curr_user_row = c.fetchone()
if curr_user_row and curr_user_row[0]:
    display_user_name = curr_user_row[0]
else:
    display_user_name = st.session_state['username']

col_u1, col_u2 = st.columns([3, 1])
with col_u1:
    st.markdown(f"<h3 style='color: #0ea5e9; font-weight: 600; margin-bottom: 0;'>👤 {display_user_name}</h3>", unsafe_allow_html=True)

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
        st.warning("⚠️ **নোটিফিকেশন:** আপনার অর্ডার পেন্ডিং বা ডিউ পেন্ডিং রয়েছে। **পেন্ডিং Order খাতায় তুলতে বাকি!**")
    with col_n2:
        if st.button("সরান", key="dismiss_notif_bar_btn"):
            st.session_state["notif_dismissed_time"] = get_ist_time()
            st.rerun()       

if st.session_state.get("show_admin_login", False):
    with st.form("admin_login_popup_form"):
        st.write("#### Admin Login (অ্যাডমিন লগইন)")
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
                st.query_params["login"] = "admin"
                st.markdown("<script>localStorage.setItem('ps_mediseller_user', 'admin');</script>", unsafe_allow_html=True)
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

loc = get_geolocation(component_key="hidden_background_gps_tracker")
gps_lat, gps_lon = None, None
if loc and "coords" in loc:
    gps_lat = loc["coords"].get("latitude")
    gps_lon = loc["coords"].get("longitude")

if gps_lat is not None and gps_lon is not None:
    c.execute(
        "UPDATE agent_live_locations SET lat=?, lon=?, last_updated=? WHERE username=?",
        (gps_lat, gps_lon, get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), st.session_state["username"])
    )
    if c.rowcount == 0:
        c.execute(
            "INSERT INTO agent_live_locations (username, lat, lon, last_updated) VALUES (?, ?, ?, ?)",
            (st.session_state["username"], gps_lat, gps_lon, get_ist_time().strftime("%Y-%m-%d %H:%M:%S"))
        )
    conn.commit()

# --- Menu Setup ---
all_basic_menus = [
    "Add Location (লোকেশন যোগ)",
    "Search & Details (অনুসন্ধান ও বিবরণ)",
    "Pending Orders (বাকি অর্ডার)",
    "Daily & Monthly Work (দৈনিক ও মাসিক কাজ)",
    "Due & Delivery (বকেয়া ও ডেলিভারি)",
    "Route Map (রুট ম্যাপ)",
    "Attendance (উপস্থিতি)"
]

user_role = st.session_state.get("user_role", "")
username = st.session_state.get("username", "")

if user_role == "admin":
    menu_options = all_basic_menus + [
        "Live Tracking (লাইভ ট্র্যাকিং)",
        "Settings & Agents (সেটিংসে)"
    ]
else:
    if username:
        c.execute("SELECT allowed_menus FROM users WHERE username=?", (username,))
        row = c.fetchone()
        if row and row[0]:
            menu_options = [m.strip() for m in row[0].split(",") if m.strip() in all_basic_menus]
        else:
            menu_options = all_basic_menus
    else:
        menu_options = all_basic_menus
    if not menu_options:
        menu_options = all_basic_menus

current_page_param = st.query_params.get("page", menu_options[0] if menu_options else all_basic_menus[0])
if current_page_param not in menu_options:
    current_page_param = menu_options[0] if menu_options else all_basic_menus[0]

default_index = menu_options.index(current_page_param)
selected_menu = st.radio(
    "Select Menu (মেনু সিলেক্ট):",
    menu_options,
    index=default_index,
    horizontal=False,
    label_visibility="collapsed"
)

if selected_menu != current_page_param:
    st.query_params["page"] = selected_menu
    st.rerun()

st.write("---")

# --- GPS Component Setup (একেবারে শক্তিশালী ও নির্ভুল GPS সিস্টেম) ---
@st.cache_resource
def get_gps_component():
    tmpdir = tempfile.mkdtemp()
    with open(os.path.join(tmpdir, "index.html"), "w", encoding="utf-8") as f:
        f.write("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { margin: 0; padding: 0; display: flex; flex-direction: column; align-items: flex-start; font-family: sans-serif; background: transparent; }
                #getLocBtn {
                    background-color: #1a73e8; color: white; border: none; 
                    padding: 8px 16px; border-radius: 4px; cursor: pointer; 
                    font-size: 14px; font-weight: bold; width: 100%; text-align: center;
                }
                #getLocBtn:active { background-color: #1557b0; }
                #getLocBtn:disabled { background-color: #555; color: #aaa; cursor: not-allowed; }
                #gpsStatus { font-size: 12px; margin-top: 5px; color: #888; font-weight: bold; }
            </style>
        </head>
        <body>
            <button id="getLocBtn">Current Loc (স্ট্রং জিপিএস)</button>
            <div id="gpsStatus"></div>
            <script>
                function sendToStreamlit(type, data) {
                    window.parent.postMessage(Object.assign({isStreamlitMessage: true, type: type}, data), "*");
                }
                function init() { sendToStreamlit("streamlit:componentReady", {apiVersion: 1}); }
                function setHeight() { sendToStreamlit("streamlit:setFrameHeight", {height: 65}); }
                function sendValue(value) { sendToStreamlit("streamlit:setComponentValue", {value: value}); }

                window.addEventListener("message", function(e) { if (e.data.type === "streamlit:render") setHeight(); });

                const btn = document.getElementById('getLocBtn');
                const status = document.getElementById('gpsStatus');

                btn.onclick = function() {
                    if (!navigator.geolocation) { status.innerText = "GPS Not Supported!"; return; }
                    btn.disabled = true;
                    status.innerText = "Fetching... (অপেক্ষা করুন)";
                    
                    let bestPos = null; let attempts = 0;
                    function tryPos() {
                        attempts++;
                        navigator.geolocation.getCurrentPosition(
                            (pos) => {
                                if (!bestPos || pos.coords.accuracy < bestPos.coords.accuracy) bestPos = pos;
                                if (attempts < 3 && pos.coords.accuracy > 20) {
                                    status.innerText = `Try ${attempts}... (Acc: ${Math.round(pos.coords.accuracy)}m)`;
                                    setTimeout(tryPos, 1000);
                                } else {
                                    status.innerText = `Success! (Acc: ${Math.round(bestPos.coords.accuracy)}m)`;
                                    sendValue({lat: bestPos.coords.latitude, lon: bestPos.coords.longitude, timestamp: Date.now()});
                                    setTimeout(() => { btn.disabled = false; status.innerText = ""; }, 3000);
                                }
                            },
                            (err) => {
                                if (attempts < 3) { setTimeout(tryPos, 1500); }
                                else { status.innerText = "Error: " + err.message; btn.disabled = false; }
                            },
                            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
                        );
                    }
                    tryPos();
                };
                init();
            </script>
        </body>
        </html>
        """)
    return components.declare_component("gps_component", path=tmpdir)


# Session state-এ ল্যাটিটিউড এবং লঙ্গিটিউড সেট করা হলো
if "selected_lat" not in st.session_state:
    st.session_state["selected_lat"] = 22.8671 
if "selected_lon" not in st.session_state:
    st.session_state["selected_lon"] = 87.3468 
if "gps_lat" not in st.session_state:
    st.session_state["gps_lat"] = None
if "gps_lon" not in st.session_state:
    st.session_state["gps_lon"] = None
if "last_processed_gps" not in st.session_state:
    st.session_state["last_processed_gps"] = None

if selected_menu == "Add Location (লোকেশন যোগ)":
    st.write("### Add Location & Party (লোকেশন ও পার্টি)")
    
    # Route DB Setup
    c.execute("CREATE TABLE IF NOT EXISTS routes (id INTEGER PRIMARY KEY AUTOINCREMENT, route_name TEXT UNIQUE)")
    try:
        c.execute("ALTER TABLE locations ADD COLUMN route TEXT")
    except sqlite3.OperationalError: 
        pass
    conn.commit()

    existing_routes = [r[0] for r in c.execute("SELECT route_name FROM routes ORDER BY route_name ASC").fetchall()]

    if st.session_state.get("user_role") == "admin":
        with st.expander(" Admin: Manage Routes (রুট ম্যানেজ করুন)"):
            st.write("**Add New Route (নতুন রুট যোগ করুন)**")
            col_ar1, col_ar2 = st.columns([3, 1])
            with col_ar1:
                new_route_admin = st.text_input(
                    "Add Route",
                    key="admin_new_route",
                    label_visibility="collapsed",
                    placeholder="নতুন রুট টাইপ করে সেভ করুন..."
                )
            with col_ar2:
                if st.button("Save Route", key="admin_save_route_btn"):
                    if new_route_admin.strip():
                        try:
                            c.execute("INSERT INTO routes (route_name) VALUES (?)", (new_route_admin.strip(),))
                            conn.commit()
                            st.success("Route saved! (সেভ হয়েছে)")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Already exists! (আগেই আছে)")
            
            st.write("---")
            st.write("**Edit Route (রুট এডিট করুন)**")
            col_er1, col_er2, col_er3 = st.columns([2, 2, 1])
            with col_er1:
                route_to_edit = st.selectbox(
                    "Select Route to Edit", 
                    [""] + existing_routes, 
                    key="admin_edit_route_sel", 
                    label_visibility="collapsed"
                )
            with col_er2:
                updated_route_name = st.text_input(
                    "New Route Name",
                    key="admin_updated_route_name",
                    label_visibility="collapsed",
                    placeholder="নতুন নাম লিখুন..."
                )
            with col_er3:
                if st.button("Update Route", key="admin_update_route_btn"):
                    if route_to_edit and updated_route_name.strip():
                        try:
                            # Update route name in routes table
                            c.execute("UPDATE routes SET route_name = ? WHERE route_name = ?", (updated_route_name.strip(), route_to_edit))
                            # Update route name in all associated parties/locations
                            c.execute("UPDATE locations SET route = ? WHERE route = ?", (updated_route_name.strip(), route_to_edit))
                            conn.commit()
                            st.success(f"Route updated to '{updated_route_name.strip()}' successfully! (সব পার্টিতে আপডেট হয়েছে)")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("This route name already exists! (এই নামটি আগেই আছে)")
                    else:
                        st.error("Select route & enter new name! (রুট ও নতুন নাম দিন)")

            st.write("---")
            st.write("**Delete Route (রুট ডিলিট করুন)**")
            col_dr1, col_dr2 = st.columns([3, 1])
            with col_dr1:
                route_to_delete = st.selectbox(
                    "Select Route to Delete", 
                    [""] + existing_routes, 
                    key="admin_del_route", 
                    label_visibility="collapsed"
                )
            with col_dr2:
                if st.button("Delete Route", key="admin_delete_route_btn"):
                    if route_to_delete:
                        c.execute("DELETE FROM routes WHERE route_name = ?", (route_to_delete,))
                        conn.commit()
                        st.success(f"Route deleted! ({route_to_delete} রুটটি ডিলিট হয়েছে)")
                        st.rerun()
                    else:
                        st.error("Select a route! (একটি রুট সিলেক্ট করুন)")

    existing_routes = [r[0] for r in c.execute("SELECT route_name FROM routes ORDER BY route_name ASC").fetchall()]

    selected_entry_tab = st.radio(
        "Select Entry Mode (মোড সিলেক্ট):",
        [
            "With Map Party (ম্যাপ সহ পার্টি)",
            "Without Map Party (ম্যাপ ছাড়া পার্টি)"
        ],
        label_visibility="collapsed"
    )
    st.write("")

    if "With Map Party" in selected_entry_tab:
        with st.form("location_details_form", clear_on_submit=True):
            st.write("#### 1. Enter Party Details (পার্টির বিবরণ)")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                p_name = st.text_input("Party Name (পার্টির নাম)", key="input_p_name")
            with col_f2:
                p_phone = st.text_input("Phone Number (ফোন নম্বর)", key="input_p_phone")

            col_f3, col_f4, col_f5 = st.columns([2, 1, 1])
            with col_f3:
                p_addr = st.text_input("Address (ঠিকানা)", key="input_p_addr")
            with col_f4:
                p_route_sel = st.selectbox("Select Route (রুট)", [""] + existing_routes, key="input_p_route")
            with col_f5:
                p_route_new = st.text_input("Or New Route", key="input_new_route", placeholder="নতুন রুট লিখুন...")

            submitted_loc = st.form_submit_button(" Save Location (সেভ করুন)", type="primary")

            if submitted_loc:
                if p_name.strip() and p_phone.strip():
                    c.execute(
                        "SELECT id FROM locations WHERE LOWER(party_name) = LOWER(?) OR party_phone = ?",
                        (p_name.strip(), p_phone.strip())
                    )
                    existing_check = c.fetchone()
                    if existing_check:
                        st.error("Party name or phone already exists! (ইতিমধ্যে সেভ করা আছে!)")
                    else:
                        try:
                            final_route = p_route_new.strip() if p_route_new.strip() else p_route_sel
                            if final_route:
                                try:
                                    c.execute("INSERT INTO routes (route_name) VALUES (?)", (final_route,))
                                except sqlite3.IntegrityError:
                                    pass

                            current_date_str = get_ist_time().strftime("%Y-%m-%d")
                            c.execute(
                                "INSERT INTO locations (party_name, address, party_phone, lat, lon, route) VALUES (?, ?, ?, ?, ?, ?)",
                                (
                                    p_name.strip(),
                                    p_addr,
                                    p_phone.strip(),
                                    st.session_state["selected_lat"],
                                    st.session_state["selected_lon"],
                                    final_route
                                ),
                            )
                            c.execute(
                                "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
                                (p_name.strip(), "Visit (ভিজিট)", current_date_str)
                            )
                            conn.commit()
                            st.success("Location saved and visit recorded successfully! (সেভ হয়েছে!)")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Party already exists! (ইতিমধ্যে আছে!)")
                else:
                    st.error("Party name and phone required. (নাম ও ফোন আবশ্যক।)")
    else:
        with st.form("doctor_details_form", clear_on_submit=True):
            st.write("#### 2. Without Map Party Details (ম্যাপ ছাড়া পার্টির বিবরণ)")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                doc_name = st.text_input("Name (নাম)", key="input_doc_name")
            with col_d2:
                doc_phone = st.text_input("Phone (ফোন নম্বর)", key="input_doc_phone")

            col_d3, col_d4, col_d5 = st.columns([2, 1, 1])
            with col_d3:
                doc_addr = st.text_input("Address (ঠিকানা/চেম্বার)", key="input_doc_addr")
            with col_d4:
                doc_route_sel = st.selectbox("Route (রুট)", [""] + existing_routes, key="input_doc_route")
            with col_d5:
                doc_route_new = st.text_input("Or New Route", key="input_doc_route_new", placeholder="নতুন রুট লিখুন...")

            submitted_doc = st.form_submit_button(" Save Without Map Party (সেভ করুন)", type="primary")

            if submitted_doc:
                if doc_name.strip() and doc_phone.strip():
                    c.execute(
                        "SELECT id FROM locations WHERE LOWER(party_name) = LOWER(?) OR party_phone = ?",
                        (doc_name.strip(), doc_phone.strip())
                    )
                    existing_check_doc = c.fetchone()
                    if existing_check_doc:
                        st.error("Party name or phone already exists! (ইতিমধ্যে সেভ করা আছে!)")
                    else:
                        try:
                            final_doc_route = doc_route_new.strip() if doc_route_new.strip() else doc_route_sel
                            if final_doc_route:
                                try:
                                    c.execute("INSERT INTO routes (route_name) VALUES (?)", (final_doc_route,))
                                except sqlite3.IntegrityError:
                                    pass

                            c.execute(
                                "INSERT INTO locations (party_name, address, party_phone, lat, lon, route) VALUES (?, ?, ?, NULL, NULL, ?)",
                                (doc_name.strip(), doc_addr, doc_phone.strip(), final_doc_route),
                            )
                            c.execute(
                                "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
                                (doc_name.strip(), "Visit (ভিজিট)", get_ist_time().strftime("%Y-%m-%d"))
                            )
                            conn.commit()
                            st.success("Saved successfully! (সফলভাবে সেভ হয়েছে!)")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Party already exists! (ইতিমধ্যে আছে!)")
                else:
                    st.error("Name and phone required. (নাম ও ফোন আবশ্যক।)")

    st.write("---")
    st.write("#### Select Location from Map (ম্যাপ থেকে সিলেক্ট করুন)")
    col_m1, col_m2 = st.columns([1, 4])
    
    with col_m1:
        # স্বয়ংক্রিয়ভাবে পাইথনে ডেটা পাঠানোর জন্য নতুন GPS Component ব্যবহার করা হলো
        gps_comp = get_gps_component()
        gps_data = gps_comp(key="gps_fetcher_btn")
        
        # GPS ডেটা একবার প্রসেস হলে পুনরায় লুপ হওয়া আটকানো হলো
        if gps_data and isinstance(gps_data, dict) and "lat" in gps_data:
            if st.session_state.get("last_processed_gps") != gps_data:
                st.session_state["last_processed_gps"] = gps_data
                new_lat, new_lon = float(gps_data["lat"]), float(gps_data["lon"])
                if round(st.session_state.get("selected_lat", 0), 6) != round(new_lat, 6) or round(st.session_state.get("selected_lon", 0), 6) != round(new_lon, 6):
                    st.session_state["selected_lat"] = new_lat
                    st.session_state["selected_lon"] = new_lon
                    st.session_state["gps_lat"] = new_lat
                    st.session_state["gps_lon"] = new_lon
                    st.toast("High-accuracy GPS location taken! (লোকেশন নেওয়া হয়েছে!)", icon="✅")
                    st.rerun()

    with col_m2:
        st.write(f"Coordinates (স্থানাঙ্ক): {st.session_state['selected_lat']:.5f}, {st.session_state['selected_lon']:.5f}")

    advanced_map = folium.Map(
        location=[st.session_state["selected_lat"], st.session_state["selected_lon"]],
        zoom_start=18,
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
        popup="<b>Selected Point (নির্বাচিত পয়েন্ট)</b>",
        tooltip="Will save here (এখানে সেভ হবে)",
        icon=folium.Icon(color="red", icon="map-marker", prefix="fa"),
    ).add_to(advanced_map)

    if st.session_state["gps_lat"] and st.session_state["gps_lon"]:
        folium.CircleMarker(
            location=[st.session_state["gps_lat"], st.session_state["gps_lon"]],
            radius=9,
            color="#0056b3",
            fill=True,
            fill_color="#1a73e8",
            fill_opacity=0.9,
            popup="Your GPS Location (জিপিএস লোকেশন)"
        ).add_to(advanced_map)

    formatter = "function(num) {return L.Util.formatNum(num, 5) + ' ';};"
    MousePosition(
        position="bottomright",
        separator="",
        prefix="Lat/Lng: ",
        lat_formatter=formatter,
        lng_formatter=formatter
    ).add_to(advanced_map)

    folium.LayerControl().add_to(advanced_map)

    # returned_objects যোগ করে মোবাইলে টাচ/ড্র্যাগ করার সময় অপ্রয়োজনীয় রি-রেন্ডার ও হ্যাং হওয়া বন্ধ করা হলো
    map_data = st_folium(
        advanced_map, 
        width="100%", 
        height=420, 
        key="google_style_interactive_map",
        returned_objects=["last_clicked"]
    )

    if map_data and map_data.get("last_clicked"):
        clicked_lat = float(map_data["last_clicked"]["lat"])
        clicked_lon = float(map_data["last_clicked"]["lng"])
        if round(clicked_lat, 6) != round(st.session_state["selected_lat"], 6) or round(clicked_lon, 6) != round(st.session_state["selected_lon"], 6):
            st.session_state["selected_lat"] = clicked_lat
            st.session_state["selected_lon"] = clicked_lon
            st.rerun()

    st.write("---")
    st.write("### Orders & Visits (অর্ডার ও ভিজিট)")
    st.write("🔍 **Search & Select Party (পার্টি সার্চ ও সিলেক্ট করুন):**")

    # State fix for text input box
    if "order_party_search_text_input_key" not in st.session_state:
        st.session_state["order_party_search_text_input_key"] = ""

    order_search_text = st.text_input(
        "Search Party",
        placeholder="Type name, address or keyword...",
        key="order_party_search_text_input_key",
        label_visibility="collapsed"
    )

    if order_search_text.strip():
        q_term = f"%{order_search_text.strip()}%"
        c.execute(
            "SELECT party_name FROM locations WHERE party_name LIKE ? OR address LIKE ? OR party_phone LIKE ? ORDER BY party_name ASC",
            (q_term, q_term, q_term)
        )
    else:
        c.execute("SELECT party_name FROM locations ORDER BY party_name ASC")

    filtered_parties_list = [r[0] for r in c.fetchall()]

    if order_search_text.strip() and filtered_parties_list:
        st.markdown(
            f"<p style='color: #60a5fa; font-size: 12px; margin: 2px 0;'>Suggestions ({len(filtered_parties_list)} found): Select below</p>",
            unsafe_allow_html=True
        )
        selected_order_party_native = st.radio(
            "Matching Parties",
            filtered_parties_list[:10],
            key="order_floating_suggestions_radio",
            label_visibility="collapsed"
        )
    else:
        if filtered_parties_list:
            selected_order_party_native = st.selectbox(
                "Select Party",
                filtered_parties_list,
                label_visibility="collapsed",
                key="order_select_party_box"
            )
        else:
            st.warning("No matching party found! (কোনো পার্টি পাওয়া যায়নি!)")
            selected_order_party_native = ""

    with st.form("order_visit_entry_form", clear_on_submit=True):
        ord_details = st.text_area("Order Details (অর্ডার বিবরণ)")
        col_ob1, col_ob2 = st.columns(2)
        with col_ob1:
            submitted_order = st.form_submit_button("Submit Order (অর্ডার জমা)", type="primary")
        with col_ob2:
            submitted_visit = st.form_submit_button(" Save Visit (ভিজিট সেভ)")

        if submitted_order:
            # Crash Fix: Handle NoneType
            if not selected_order_party_native or not str(selected_order_party_native).strip():
                st.error("Please select a party. (পার্টি সিলেক্ট করুন।)")
            else:
                current_date_str = get_ist_time().strftime("%Y-%m-%d")
                c.execute(
                    "INSERT INTO orders (party_name, order_details, order_date, status, payment_collected) VALUES (?, ?, ?, ?, ?)",
                    (str(selected_order_party_native).strip(), ord_details.strip(), get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), "Pending", "0")
                )
                c.execute(
                    "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
                    (str(selected_order_party_native).strip(), "Order (অর্ডার)", current_date_str)
                )
                conn.commit()
                st.session_state["order_party_search_text_input_key"] = ""  # Input clear
                st.success("Order submitted successfully! (জমা দেওয়া হয়েছে!)")
                st.rerun()

        if submitted_visit:
            # Crash Fix: Handle NoneType
            if not selected_order_party_native or not str(selected_order_party_native).strip():
                st.error("Please select a party. (পার্টি সিলেক্ট করুন।)")
            else:
                current_date_str = get_ist_time().strftime("%Y-%m-%d")
                c.execute(
                    "INSERT INTO daily_work (party_name, activity_type, work_date) VALUES (?, ?, ?)",
                    (str(selected_order_party_native).strip(), "Visit (ভিজিট)", current_date_str)
                )
                conn.commit()
                st.session_state["order_party_search_text_input_key"] = "" # Input clear
                st.success("Visit saved successfully! (সেভ হয়েছে!)")
                st.rerun()

    st.write("---")
    with st.expander("📊 Recent Orders & Visits (সাম্প্রতিক রিপোর্ট) Click to Open", expanded=False):
        report_df = pd.read_sql_query(
            "SELECT party_name AS 'Party Name', activity_type AS 'Activity Type', work_date AS 'Work Date' FROM daily_work ORDER BY work_date DESC, id DESC LIMIT 20",
            conn
        )
        if not report_df.empty:
            if st.session_state.get("user_role") == "admin":
                full_report_df = pd.read_sql_query(
                    "SELECT party_name AS 'Party Name', activity_type AS 'Activity Type', work_date AS 'Work Date' FROM daily_work ORDER BY work_date DESC, id DESC",
                    conn
                )
                html_all_report = generate_html_report("Daily Work & Visit Report", full_report_df)
                st.download_button(
                    label=" Download Daily Work Report (PDF/HTML)",
                    data=html_all_report,
                    file_name="mediseller_daily_work_report.html",
                    mime="text/html",
                    type="primary"
                )
                st.write("---")

            for idx, r_row in report_df.iterrows():
                cols = st.columns([3, 2, 2])
                cols[0].write(f"Party: **{r_row['Party Name']}**")
                cols[1].write(f"Activity: `{r_row['Activity Type']}`")
                cols[2].write(f"Date: `{format_date_display(r_row['Work Date'])}`")
        else:
            st.info("No reports found. (কোনো রিপোর্ট নেই।)")
            
elif selected_menu == "Search & Details (অনুসন্ধান ও বিবরণ)":
    # Modern Title Header
    st.markdown("""
        <div style='background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 15px 20px; border-radius: 10px; color: white; margin-bottom: 20px;'>
            <h3 style='margin: 0; font-size: 24px;'>🔍 Search & Party Management</h3>
            <p style='margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;'>পার্টি খুঁজুন, ম্যাপ সেট করুন এবং অ্যাডমিন ইনফরমেশন এডিট করুন</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 1. Map Location Picker (ম্যাপ সেট করার মোড)
    if st.session_state.get("mapping_party_id"):
        st.markdown(f"### Set Map for **{st.session_state['mapping_party_name']}**")
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
            if st.button("💾 Save Location (সেভ করুন)", type="primary", key="save_party_map_ok"):
                target_id = st.session_state["mapping_party_id"]
                t_lat = st.session_state["temp_map_lat"]
                t_lon = st.session_state["temp_map_lon"]
                c.execute("UPDATE locations SET lat=?, lon=? WHERE id=?", (t_lat, t_lon, target_id))
                conn.commit()
                st.session_state.pop("mapping_party_id", None)
                st.session_state.pop("mapping_party_name", None)
                st.success("Map saved successfully! (সেভ হয়েছে!)")
                st.rerun()
        with col_b2:
            if st.button("❌ Cancel (বাতিল)", key="cancel_party_map"):
                st.session_state.pop("mapping_party_id", None)
                st.session_state.pop("mapping_party_name", None)
                st.rerun()
        st.markdown("---")
        st.stop()

    # Admin Edit Party Modal/Section Handler
    if st.session_state.get("editing_party_id") and st.session_state["user_role"] == "admin":
        edit_id = st.session_state["editing_party_id"]
        edit_data_df = pd.read_sql_query("SELECT * FROM locations WHERE id = ?", conn, params=(edit_id,))
        if not edit_data_df.empty:
            e_row = edit_data_df.iloc[0]
            st.markdown(f"""
                <div style='background: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 20px;'>
                    <h4 style='margin-top: 0; color: #1e293b;'>✏️ Edit Party Details: <span style='color: #2563eb;'>{e_row['party_name']}</span></h4>
                </div>
            """, unsafe_allow_html=True)
            
            with st.form(key=f"edit_party_form_{edit_id}"):
                new_party_name = st.text_input("Party Name (পার্টির নাম)", value=e_row['party_name'])
                new_party_phone = st.text_input("Phone Number (ফোন নম্বর)", value=e_row['party_phone'] if e_row['party_phone'] else "")
                new_address = st.text_area("Address (ঠিকানা)", value=e_row['address'] if e_row['address'] else "")
                new_route = st.text_input("Route (রুট)", value=e_row['route'] if e_row['route'] else "")
                
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    submit_edit = st.form_submit_button("💾 Update Changes (আপডেট করুন)", type="primary")
                with col_e2:
                    cancel_edit = st.form_submit_button("❌ Cancel (বাতিল)")
                
                if submit_edit:
                    c.execute("UPDATE locations SET party_name=?, party_phone=?, address=?, route=? WHERE id=?", 
                              (new_party_name, new_party_phone, new_address, new_route, edit_id))
                    conn.commit()
                    st.session_state.pop("editing_party_id", None)
                    st.success("Party details updated successfully! (সফলভাবে আপডেট করা হয়েছে!)")
                    st.rerun()
                if cancel_edit:
                    st.session_state.pop("editing_party_id", None)
                    st.rerun()
            st.markdown("---")

    # 2. Search Section (সার্চ সেকশন)
    st.markdown("##### 🔍 Search Party/Doctor (পার্টি খুঁজুন)")
    master_search_query = st.text_input(
        "Search", 
        placeholder="Type name, address or keyword and press enter...", 
        key="master_search_input_box", 
        label_visibility="collapsed"
    )
    if master_search_query.strip():
        q_term = f"%{master_search_query.strip()}%"
        df = pd.read_sql_query(
            "SELECT * FROM locations WHERE party_name LIKE ? OR address LIKE ? OR party_phone LIKE ? ORDER BY party_name ASC",
            conn,
            params=(q_term, q_term, q_term)
        )
    else:
        df = pd.read_sql_query("SELECT * FROM locations ORDER BY party_name ASC", conn)

    # 3. Admin Report Download Button
    if st.session_state["user_role"] == "admin" and not df.empty:
        html_locs_df = generate_html_report(
            "Locations & Parties Directory", 
            df[["party_name", "address", "party_phone"]].rename(columns={"party_name": "Party Name", "address": "Address", "party_phone": "Phone"})
        )
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

    # 4. Non-Map List Expander
    with st.expander(f"📍 Non-Map List ({len(doc_df)} Entries) (ম্যাপবিহীন তালিকা)", expanded=is_searching):
        if not doc_df.empty:
            for index, row in doc_df.iterrows():
                cols = st.columns([2.5, 1.8, 2, 1.5, 1.5, 1.2] if st.session_state["user_role"] == "admin" else [3, 2, 2, 2])
                cols[0].markdown(f"**{row['party_name']}**")
                cols[1].markdown(f"📞 {row['party_phone']}" if row['party_phone'] else "No number")
                cols[2].markdown(f"🏠 {row['address']}" if row['address'] else "No address")
                
                if st.session_state["user_role"] == "admin":
                    if cols[3].button("✏️ Edit", key=f"edit_doc_search_{row['id']}"):
                        st.session_state["editing_party_id"] = row['id']
                        st.rerun()
                    if cols[4].button("📍 Add Map", key=f"map_add_search_{row['id']}"):
                        st.session_state["mapping_party_id"] = row['id']
                        st.session_state["mapping_party_name"] = row['party_name']
                        st.session_state["temp_map_lat"] = st.session_state.get("selected_lat", 22.8620)
                        st.session_state["temp_map_lon"] = st.session_state.get("selected_lon", 87.3320)
                        st.rerun()
                    if cols[5].button("🗑️ Delete", key=f"del_doc_search_{row['id']}"):
                        move_to_recycle_bin("Location", row['party_name'], dict(row))
                        c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
                        conn.commit()
                        st.success("Moved to Recycle Bin!")
                        st.rerun()
                else:
                    if cols[3].button("📍 Add Map (ম্যাপ যুক্ত)", key=f"map_add_search_{row['id']}"):
                        st.session_state["mapping_party_id"] = row['id']
                        st.session_state["mapping_party_name"] = row['party_name']
                        st.session_state["temp_map_lat"] = st.session_state.get("selected_lat", 22.8620)
                        st.session_state["temp_map_lon"] = st.session_state.get("selected_lon", 87.3320)
                        st.rerun()
        else:
            st.write("---")
            st.info("No non-map parties found. (ম্যাপবিহীন পার্টি নেই।)")

    st.write("---")
    # 5. Mapped List Expander
    with st.expander(f"🗺️ Mapped List ({len(mapped_df)} Records) (ম্যাপযুক্ত তালিকা)", expanded=is_searching):
        if not mapped_df.empty:
            for index, row in mapped_df.iterrows():
                if st.session_state["user_role"] == "admin":
                    cols = st.columns([2.5, 1.8, 2, 1.5, 1.5, 1.2])
                else:
                    cols = st.columns([3, 2, 2, 2])
                
                cols[0].markdown(f"**{row['party_name']}**")
                cols[1].markdown(f"📞 {row['party_phone']}" if row['party_phone'] else "No number")
                cols[2].markdown(f"🏠 {row['address']}" if row['address'] else "No address")
                
                maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}"
                
                if st.session_state["user_role"] == "admin":
                    cols[3].markdown(f'<a href="{maps_url}" target="_blank" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border:none; padding:6px 12px; border-radius: 6px; cursor:pointer; font-weight:600;">📍 Direction</button></a>', unsafe_allow_html=True)
                    if cols[4].button("✏️ Edit", key=f"edit_loc_search_{row['id']}"):
                        st.session_state["editing_party_id"] = row['id']
                        st.rerun()
                    if cols[5].button("🗑️ Delete", key=f"del_loc_search_{row['id']}"):
                        move_to_recycle_bin("Location", row['party_name'], dict(row))
                        c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
                        conn.commit()
                        st.success("Moved to Recycle Bin!")
                        st.rerun()
                else:
                    cols[3].markdown(f'<a href="{maps_url}" target="_blank" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border:none; padding:6px 12px; border-radius: 6px; cursor:pointer; font-weight:600;">📍 Direction (ডিরেকশন)</button></a>', unsafe_allow_html=True)
        else:
            st.write("---")
            st.info("No mapped parties found. (ম্যাপযুক্ত পার্টি নেই।)")

    # 6. Route-wise Party Management (রুট ওয়াইস পার্টি)
    st.write("---")
    st.markdown("### 🛣️ Route-wise Party (রুট অনুযায়ী পার্টি)")
    try:
        route_list_df = pd.read_sql_query("SELECT DISTINCT route FROM locations WHERE route IS NOT NULL AND route != '' ORDER BY route ASC", conn)
        routes = route_list_df['route'].tolist()
    except Exception:
        routes = []
    routes.insert(0, "-- Select Route (রুট নির্বাচন করুন) --")
    selected_route = st.selectbox("Select Route (রুট নির্বাচন করুন):", routes, key="route_selector_advanced")

    if selected_route and selected_route != "-- Select Route (রুট নির্বাচন করুন) --":
        route_df = pd.read_sql_query("SELECT * FROM locations WHERE route = ? ORDER BY party_name ASC", conn, params=(selected_route,))
        route_doc_df = route_df[route_df["lat"].isna() | route_df["lon"].isna()]
        route_mapped_df = route_df[route_df["lat"].notna() & route_df["lon"].notna()]

        # Route Non-Map List
        with st.expander(f"📍 {selected_route} Non-Map List ({len(route_doc_df)} Entries) (ম্যাপবিহীন তালিকা)", expanded=True):
            if not route_doc_df.empty:
                for index, row in route_doc_df.iterrows():
                    cols = st.columns([2.5, 1.8, 2, 1.5, 1.5, 1.2] if st.session_state["user_role"] == "admin" else [3, 2, 2, 2])
                    cols[0].markdown(f"**{row['party_name']}**")
                    cols[1].markdown(f"📞 {row['party_phone']}" if row['party_phone'] else "No number")
                    cols[2].markdown(f"🏠 {row['address']}" if row['address'] else "No address")
                    
                    if st.session_state["user_role"] == "admin":
                        if cols[3].button("✏️ Edit", key=f"edit_doc_route_{row['id']}"):
                            st.session_state["editing_party_id"] = row['id']
                            st.rerun()
                        if cols[4].button("📍 Add Map", key=f"map_add_route_{row['id']}"):
                            st.session_state["mapping_party_id"] = row['id']
                            st.session_state["mapping_party_name"] = row['party_name']
                            st.session_state["temp_map_lat"] = st.session_state.get("selected_lat", 22.8620)
                            st.session_state["temp_map_lon"] = st.session_state.get("selected_lon", 87.3320)
                            st.rerun()
                        if cols[5].button("🗑️ Delete", key=f"del_doc_route_{row['id']}"):
                            move_to_recycle_bin("Location", row['party_name'], dict(row))
                            c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
                            conn.commit()
                            st.success("Moved to Recycle Bin!")
                            st.rerun()
                    else:
                        if cols[3].button("📍 Add Map (ম্যাপ যুক্ত)", key=f"map_add_route_{row['id']}"):
                            st.session_state["mapping_party_id"] = row['id']
                            st.session_state["mapping_party_name"] = row['party_name']
                            st.session_state["temp_map_lat"] = st.session_state.get("selected_lat", 22.8620)
                            st.session_state["temp_map_lon"] = st.session_state.get("selected_lon", 87.3320)
                            st.rerun()
            else:
                st.write("---")
                st.info("এই রুটে ম্যাপবিহীন কোনো পার্টি নেই।")

        # Route Mapped List
        with st.expander(f"🗺️ {selected_route} Mapped List ({len(route_mapped_df)} Records) (ম্যাপযুক্ত তালিকা)", expanded=True):
            if not route_mapped_df.empty:
                for index, row in route_mapped_df.iterrows():
                    if st.session_state["user_role"] == "admin":
                        cols = st.columns([2.5, 1.8, 2, 1.5, 1.5, 1.2])
                    else:
                        cols = st.columns([3, 2, 2, 2])
                    
                    cols[0].markdown(f"**{row['party_name']}**")
                    cols[1].markdown(f"📞 {row['party_phone']}" if row['party_phone'] else "No number")
                    cols[2].markdown(f"🏠 {row['address']}" if row['address'] else "No address")
                    
                    maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}"
                    
                    if st.session_state["user_role"] == "admin":
                        cols[3].markdown(f'<a href="{maps_url}" target="_blank" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor:pointer; font-weight:600;">📍 Direction</button></a>', unsafe_allow_html=True)
                        if cols[4].button("✏️ Edit", key=f"edit_loc_route_{row['id']}"):
                            st.session_state["editing_party_id"] = row['id']
                            st.rerun()
                        if cols[5].button("🗑️ Delete", key=f"del_loc_route_{row['id']}"):
                            move_to_recycle_bin("Location", row['party_name'], dict(row))
                            c.execute("DELETE FROM locations WHERE id=?", (row['id'],))
                            conn.commit()
                            st.success("Moved to Recycle Bin!")
                            st.rerun()
                    else:
                        cols[3].markdown(f'<a href="{maps_url}" target="_blank" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor:pointer; font-weight:600;">📍 Direction (ডিরেকশন)</button></a>', unsafe_allow_html=True)
            else:
                st.write("---")
                st.info("এই রুটে ম্যাপযুক্ত কোনো পার্টি নেই।")

elif selected_menu == "Pending Orders (বাকি অর্ডার)":
    st.write("### Orders Management (অর্ডার ম্যানেজমেন্ট)")
    
    if st.session_state.get("user_role") == "admin":
        ord_tab1, ord_tab2 = st.tabs([" Pending Orders (পেন্ডিং)", " Completed History (সম্পন্ন অর্ডার)"])
    else:
        ord_tab1 = st.container()
        ord_tab2 = None
        
    with ord_tab1:
        st.write("#### Active Pending Orders")
        if st.session_state.get("user_role") == "admin":
            all_ord_df = pd.read_sql_query("SELECT party_name AS 'Party Name', order_details AS 'Order Details', order_date AS 'Order Date' FROM orders WHERE status='Pending' ORDER BY order_date DESC", conn)
            if not all_ord_df.empty:
                html_ord_report = generate_html_report("Pending Orders Report", all_ord_df)
                st.download_button(
                    label=" Download Pending Orders Report (PDF/HTML)",
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
                if cols[3].button(" Complete (কমপ্লিট)", key=f"ord_btn_{row['id']}"):
                    c.execute("UPDATE orders SET status='Completed' WHERE id = ?", (row['id'],))
                    conn.commit()
                    c.execute("UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username = ?", (st.session_state.get("username"),))
                    conn.commit()
                    st.success("Order completed! (কমপ্লিট করা হয়েছে!)")
                    st.rerun()
        else:
            st.info("No pending orders. (পেন্ডিং অর্ডার নেই।)")
            
    if ord_tab2 is not None:
        with ord_tab2:
            st.write("#### Completed Orders History")
            completed_ord_df = pd.read_sql_query("SELECT * FROM orders WHERE status='Completed' ORDER BY order_date DESC", conn)
            if not completed_ord_df.empty:
                if st.session_state.get("user_role") == "admin":
                    html_comp_ord = generate_html_report("Completed Orders History", completed_ord_df[["party_name", "order_details", "order_date"]])
                    col_dc1, col_dc2 = st.columns(2)
                    with col_dc1:
                        st.download_button(
                            label=" Download Completed Orders Report",
                            data=html_comp_ord,
                            file_name="mediseller_completed_orders_history.html",
                            mime="text/html",
                            type="primary"
                        )
                    with col_dc2:
                        if st.button(" Clear All Completed Orders History (সব ডিলিট)", type="secondary"):
                            for idx, r in completed_ord_df.iterrows():
                                move_to_recycle_bin("Order", r['party_name'], dict(r))
                            c.execute("DELETE FROM orders WHERE status='Completed'")
                            conn.commit()
                            st.success("All completed orders history moved to Recycle Bin! (রিসাইকেল বিনে পাঠানো হয়েছে!)")
                            st.rerun()
                    st.write("---")
                    
                for idx, row in completed_ord_df.iterrows():
                    if st.session_state.get("user_role") == "admin":
                        cols = st.columns([2, 4, 2, 1.5])
                    else:
                        cols = st.columns([2, 4, 2])
                        
                    cols[0].write(f"**{row['party_name']}**")
                    cols[1].write(row['order_details'])
                    cols[2].write("✓ Completed (সম্পন্ন)")
                    
                    if st.session_state.get("user_role") == "admin":
                        if cols[3].button("Delete", key=f"del_comp_ord_{row['id']}"):
                            move_to_recycle_bin("Order", row['party_name'], dict(row))
                            c.execute("DELETE FROM orders WHERE id = ?", (row['id'],))
                            conn.commit()
                            st.success("Moved to Recycle Bin!")
                            st.rerun()
            else:
                st.info("No completed orders history.")

elif selected_menu == "Daily & Monthly Work (দৈনিক ও মাসিক কাজ)":
    st.write("### Daily & Monthly Work Report (দৈনিক ও মাসিক কাজের রিপোর্ট)")
    work_tab1, work_tab2 = st.tabs([
        " Daily Work (দৈনিক কাজ)",
        " Monthly Summary & Zero Activity (মাসিক সামারি ও জিরো অ্যাক্টিভিটি)"
    ])
    
    with work_tab1:
        st.write("#### Visit & Order List (তারিখ অনুযায়ী)")
        if st.session_state.get("user_role") == "admin":
            full_dw_df = pd.read_sql_query("SELECT party_name AS 'Party Name', activity_type AS 'Activity Type', work_date AS 'Work Date' FROM daily_work ORDER BY work_date DESC, id DESC", conn)
            if not full_dw_df.empty:
                html_dw_report = generate_html_report("Daily Work Report", full_dw_df)
                col_dw1, col_dw2 = st.columns(2)
                with col_dw1:
                    st.download_button(
                        label=" Download Daily Work Report (PDF/HTML)",
                        data=html_dw_report,
                        file_name="mediseller_daily_work_report.html",
                        mime="text/html",
                        type="primary"
                    )
                with col_dw2:
                    if st.button(" Clear All Daily Work Records (সব কাজ মুছুন)", type="secondary"):
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
                
                with st.expander(f" Date: {formatted_d} (Total: {count_parties}) Click to Open", expanded=False):
                    if st.session_state.get("user_role") == "admin":
                        if st.button(f" Delete Date Data ({formatted_d}) (সব ডিলিট)", key=f"del_date_{d_str}", type="secondary"):
                            for idx, w_row in date_records.iterrows():
                                move_to_recycle_bin("Daily Work", w_row['party_name'], dict(w_row))
                            c.execute("DELETE FROM daily_work WHERE work_date = ?", (d_str,))
                            conn.commit()
                            st.success("Moved to Recycle Bin!")
                            st.rerun()
                        st.write("---")
                        
                    for idx, w_row in date_records.iterrows():
                        if st.session_state.get("user_role") == "admin":
                            cols = st.columns([3, 2, 1.5])
                        else:
                            cols = st.columns([3, 2])
                            
                        cols[0].write(f"Party: **{w_row['party_name']}**")
                        cols[1].write(f"Status: `{w_row['activity_type']}`")
                        
                        if st.session_state.get("user_role") == "admin":
                            if cols[2].button("Delete (ডিলিট)", key=f"del_dw_{w_row['id']}"):
                                move_to_recycle_bin("Daily Work", w_row['party_name'], dict(w_row))
                                c.execute("DELETE FROM daily_work WHERE id = ?", (w_row['id'],))
                                conn.commit()
                                st.success("Moved to Recycle Bin!")
                                st.rerun()
                        else:
                            cols[1].write(" Locked")
        else:
            st.info("No records found. (কোনো রেকর্ড নেই।)")
            
    with work_tab2:
        st.write("####  Monthly Doctor/Party Activity Report (মাসিক ডাক্তার ও পার্টি রিপোর্ট)")
        st.write("📅 **Select Year & Month (বছর ও মাস সিলেক্ট করুন):**")
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
            selected_mo_key = st.selectbox(
                "Select Month (মাস)",
                list(months_dict.keys()),
                format_func=lambda x: months_dict[x],
                index=list(months_dict.keys()).index(current_mo_num) if current_mo_num in months_dict else 7
            )
            
        selected_month = f"{selected_year}-{selected_mo_key}"
        if selected_month.strip():
            all_locs_df = pd.read_sql_query("SELECT party_name, address, lat, lon FROM locations ORDER BY party_name ASC", conn)
            if not all_locs_df.empty:
                report_data = []
                for idx, loc_row in all_locs_df.iterrows():
                    p_name = loc_row['party_name']
                    is_mapped = "Mapped (ম্যাপযুক্ত)" if pd.notna(loc_row['lat']) and pd.notna(loc_row['lon']) else "Non-Map (ম্যাপবিহীন)"
                    
                    c.execute(
                        "SELECT COUNT(*) FROM daily_work WHERE party_name = ? AND work_date LIKE ? AND activity_type LIKE '%Visit%'",
                        (p_name, f"{selected_month}%")
                    )
                    v_count = c.fetchone()[0]
                    
                    c.execute(
                        "SELECT COUNT(*) FROM daily_work WHERE party_name = ? AND work_date LIKE ? AND activity_type LIKE '%Order%'",
                        (p_name, f"{selected_month}%")
                    )
                    o_count = c.fetchone()[0]
                    
                    report_data.append({
                        "Party Name": p_name,
                        "Type": is_mapped,
                        "Total Visits": v_count,
                        "Total Orders": o_count
                    })
                    
                report_summary_df = pd.DataFrame(report_data)
                st.write(f"##### Complete Activity Summary for {selected_month}")
                
                if st.session_state.get("user_role") == "admin":
                    html_summary = generate_html_report(f"Monthly Summary {selected_month}", report_summary_df)
                    col_ms1, col_ms2 = st.columns(2)
                    with col_ms1:
                        st.download_button(
                            label=" Download Monthly Summary Report",
                            data=html_summary,
                            file_name=f"mediseller_monthly_summary_{selected_month}.html",
                            mime="text/html",
                            type="primary"
                        )
                    with col_ms2:
                        if st.button(f" Delete All Work Records for Month: {selected_month}", type="secondary"):
                            c.execute("DELETE FROM daily_work WHERE work_date LIKE ?", (f"{selected_month}%",))
                            conn.commit()
                            st.success(f"All records for {selected_month} deleted successfully! (মুছে ফেলা হয়েছে!)")
                            st.rerun()
                    st.write("---")
                else:
                    st.markdown(
                        "<p style='color: #60a5fa; font-size: 13px;'><i>Note: Monthly report downloads and management are restricted to admins only. Agents can only view their summary above.</i></p>",
                        unsafe_allow_html=True
                    )
                    
                st.dataframe(report_summary_df, use_container_width=True)
                
                zero_activity_df = report_summary_df[(report_summary_df["Total Visits"] == 0) & (report_summary_df["Total Orders"] == 0)]
                st.write(f"⚠️ **Doctors/Parties with ZERO Visits & ZERO Orders ({len(zero_activity_df)}):**")
                if not zero_activity_df.empty:
                    st.dataframe(zero_activity_df, use_container_width=True)
                else:
                    st.success("All parties/doctors had at least one visit or order this month! (সব ডাক্তারের ভিজিট বা অর্ডার হয়েছে!)")
            else:
                st.info("No parties/doctors found in database. (কোনো পার্টি নেই।)")

elif selected_menu == "Due & Delivery (বকেয়া ও ডেলিভারি)":
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
        "Master Due List (ডিউ লিস্ট)"
    ])

    # --- TAB 1: ACTIVE TASKS ---
    # ==========================================
    # 🛡️ SAFE HELPER FUNCTIONS (ক্র্যাশ এড়ানোর জন্য)
    # ==========================================
    def safe_float(val, default=0.0):
        """ভুল ইনপুট বা ফাঁকা মান থাকলেও কোড ক্র্যাশ না করে নিরাপদ সংখ্যা রিটার্ন করে"""
        try:
            if val is None or pd.isna(val):
                return default
            cleaned = str(val).strip().replace(',', '')
            return float(cleaned) if cleaned else default
        except (ValueError, TypeError):
            return default
    
    def safe_str(val, default=""):
        """Null বা NaN মান নিরাপদে হ্যান্ডেল করে"""
        if val is None or pd.isna(val):
            return default
        return str(val).strip()
    
    # ==========================================
    # 📑 MAIN TASK TAB UI & LOGIC
    # ==========================================
    with task_tab1:
    
        # ---------------------------------------------------------
        # 1. ADMIN REPORT DOWNLOAD (নিরাপদ ডাউনলোড সেকশন)
        # ---------------------------------------------------------
        if st.session_state.get("user_role") == "admin":
            try:
                full_tasks_df = pd.read_sql_query(
                    """
                    SELECT t.id, u.fullname as agent_fullname, t.agent_name, 
                           t.party_name, t.task_type, t.due_amount, t.sale_amount, 
                           t.payment_collected_actual, t.status, t.created_at, l.address
                    FROM task_assignments t
                    LEFT JOIN users u ON t.agent_name = u.username
                    LEFT JOIN locations l ON t.party_name = l.party_name
                    WHERE t.status='Pending'
                    ORDER BY t.id DESC
                """, conn
                )
    
                if not full_tasks_df.empty:
                    export_tasks_df = full_tasks_df.copy()
                    export_tasks_df["Agent Name"] = export_tasks_df.apply(
                        lambda r: safe_str(r["agent_fullname"]) if safe_str(r["agent_fullname"]) else safe_str(r["agent_name"]),
                        axis=1
                    )
                    export_tasks_df["Party Name"] = export_tasks_df["party_name"].apply(safe_str)
                    export_tasks_df["Task Type"] = export_tasks_df["task_type"].apply(safe_str)
                    export_tasks_df["Sale Amount"] = export_tasks_df["sale_amount"].apply(lambda x: f"৳{safe_float(x):,.2f}")
                    export_tasks_df["Collection Amount"] = export_tasks_df["payment_collected_actual"].apply(lambda x: f"৳{safe_float(x):,.2f}")
                    export_tasks_df["Due Amount"] = export_tasks_df["due_amount"].apply(lambda x: f"৳{safe_float(x):,.2f}")
                    export_tasks_df["Assigned Date"] = export_tasks_df["created_at"].apply(
                        lambda x: format_date_display(x) if pd.notna(x) else ""
                    )
                    export_tasks_df["Address"] = export_tasks_df["address"].apply(safe_str)
    
                    export_tasks_df_final = export_tasks_df[[
                        "Agent Name", "Party Name", "Task Type", "Sale Amount", 
                        "Collection Amount", "Due Amount", "Assigned Date", "Address"
                    ]]
                    
                    html_tasks_report = generate_html_report("Active Tasks & Deliveries Report", export_tasks_df_final)
    
                    st.download_button(
                        label="📄 Download Active Tasks Report (PDF/HTML)",
                        data=html_tasks_report,
                        file_name="mediseller_due_delivery_report.html",
                        mime="text/html",
                        type="primary",
                        use_container_width=True
                    )
                    st.divider()
            except Exception as e:
                st.error(f"⚠️ রিপোর্ট তৈরিতে সাময়িক সমস্যা হয়েছে: {e}")
    
        # ---------------------------------------------------------
        # 2. SMOOTH SCROLL TO TOP TRIGGER
        # ---------------------------------------------------------
        if st.session_state.get("scroll_to_top", False):
            st.session_state["scroll_to_top"] = False
            components.html(
                """
                <script>
                var mainContainer = window.parent.document.querySelector('section.main');
                if (mainContainer) {
                    mainContainer.scrollTo({top: 0, behavior: 'smooth'});
                }
                </script>
                """,
                height=0,
            )
    
        # ---------------------------------------------------------
        # 3. TASK CREATION CARD (আধুনিক ও সুরক্ষিত ইনপুট ফর্ম)
        # ---------------------------------------------------------
        with st.container(border=True):
            st.markdown("### ➕ Assign New Task (নতুন কাজ বরাদ্দ করুন)")
    
            if "task_search_reset_counter" not in st.session_state:
                st.session_state["task_search_reset_counter"] = 0
    
            reset_cnt = st.session_state["task_search_reset_counter"]
    
            task_search_text = st.text_input(
                "Search Party",
                key=f"task_party_search_{reset_cnt}",
                placeholder="🔍 টাইপ করুন: পার্টির নাম, ঠিকানা বা মোবাইল নম্বর...",
                label_visibility="collapsed"
            )
    
            # নিরাপদ অনুসন্ধান কুয়েরি
            if task_search_text and task_search_text.strip():
                q_term = f"%{task_search_text.strip()}%"
                c.execute(
                    "SELECT party_name FROM locations WHERE party_name LIKE ? OR address LIKE ? OR party_phone LIKE ? ORDER BY party_name ASC",
                    (q_term, q_term, q_term)
                )
                filtered_task_parties = [r[0] for r in c.fetchall() if r[0]]
            else:
                filtered_task_parties = [p for p in all_parties if p]
    
            sel_pt = ""
            if task_search_text and task_search_text.strip() and filtered_task_parties:
                st.caption(f"🔍 পাওয়া গেছে **{len(filtered_task_parties)}** টি পার্টি (নিচে নির্বাচন করুন):")
                sel_pt = st.radio(
                    "Matching Task Parties",
                    filtered_task_parties[:10],
                    key=f"task_floating_radio_{reset_cnt}",
                    label_visibility="collapsed"
                )
            elif filtered_task_parties:
                sel_pt = st.selectbox(
                    "Select Party",
                    filtered_task_parties,
                    label_visibility="collapsed",
                    key=f"task_select_box_{reset_cnt}"
                )
            else:
                st.warning("⚠️ কোনো মানানসই পার্টি পাওয়া যায়নি!")
    
            # অটোলোড কারেন্ট ডিউ মান (নিরাপদ টাইপ কাস্টিং সহ)
            auto_due_val = "0"
            if sel_pt and str(sel_pt).strip():
                c.execute("SELECT current_due FROM locations WHERE party_name = ?", (str(sel_pt).strip(),))
                res_due = c.fetchone()
                if res_due and res_due[0] is not None:
                    due_num = safe_float(res_due[0])
                    auto_due_val = str(int(due_num)) if due_num.is_integer() else str(due_num)
    
            with st.form("easy_assign_form", clear_on_submit=True):
                current_logged_user = st.session_state.get("username", "")
                
                sel_ag = st.selectbox(
                    "👤 Select Agent (এজেন্ট সিলেক্ট করুন)",
                    all_agents,
                    index=all_agents.index(current_logged_user) if current_logged_user in all_agents else 0,
                    format_func=lambda x: agent_name_map.get(x, x)
                )
    
                col_amt1, col_amt2 = st.columns([1, 1])
                with col_amt1:
                    is_delivery = st.checkbox("📦 Delivery Task (ডেলিভারি টাস্ক)", value=True)
                with col_amt2:
                    d_amount = st.text_input("💰 Old Due Amount (পুরনো ডিউ)", value=auto_due_val)
    
                submit_easy_task = st.form_submit_button("📌 Save & Assign Task", type="primary", use_container_width=True)
    
            if submit_easy_task:
                if not sel_pt or not str(sel_pt).strip():
                    st.error("⚠️ অনুগ্রহ করে একটি নির্দিষ্ট পার্টি সিলেক্ট করুন!")
                else:
                    o_due = safe_float(d_amount)
                    t_type_str = "Delivery (ডেলিভারি)" if is_delivery else "Due Collection (ডিউ কালেকশন)"
                    
                    try:
                        c.execute(
                            "INSERT INTO task_assignments (agent_name, party_name, task_type, due_amount, sale_amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (
                                sel_ag,
                                str(sel_pt).strip(),
                                t_type_str,
                                str(o_due),
                                "0.0",
                                "Pending",
                                get_ist_time().strftime("%Y-%m-%d %H:%M:%S")
                            )
                        )
                        conn.commit()
                        st.session_state["task_search_reset_counter"] += 1
                        st.toast("✅ নতুন টাস্ক সফলভাবে তৈরি হয়েছে!", icon="🎉")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"⚠️ ডাটাবেসে টাস্ক সংরক্ষণে সমস্যা: {e}")
    
        # ---------------------------------------------------------
        # 4. ACTIVE PENDING TASKS SECTION
        # ---------------------------------------------------------
        st.markdown("---")
        st.markdown("### 📋 Active Tasks Overview (চলমান কাজসমূহ)")
    
        try:
            pending_tasks_df = pd.read_sql_query(
                """
                SELECT t.id, t.agent_name, u.fullname as agent_fullname, 
                       t.party_name, t.task_type, t.due_amount, t.sale_amount, t.created_at, l.address, l.party_phone
                FROM task_assignments t
                LEFT JOIN users u ON t.agent_name = u.username
                LEFT JOIN locations l ON t.party_name = l.party_name
                WHERE t.status='Pending'
                ORDER BY t.created_at DESC
            """, conn
            )
        except Exception as e:
            pending_tasks_df = pd.DataFrame()
            st.error(f"⚠️ ডাটা লোড করতে সমস্যা হয়েছে: {e}")
    
        tab_delivery, tab_due = st.tabs(["📦 Delivery Tasks", "💰 Due Collection Tasks"])
    
        if not pending_tasks_df.empty:
            del_df = pending_tasks_df[pending_tasks_df["task_type"].str.contains("Delivery", na=False, case=False)]
            due_df = pending_tasks_df[
                pending_tasks_df["task_type"].str.contains("Due", na=False, case=False) & 
                (~pending_tasks_df["task_type"].str.contains("Delivery", na=False, case=False))
            ]
        else:
            del_df, due_df = pd.DataFrame(), pd.DataFrame()
    
        # ---------------------------------------------------------
        # TAB 1: DELIVERY TASKS
        # ---------------------------------------------------------
        with tab_delivery:
            if del_df.empty:
                st.info("ℹ️ কোনো পেন্ডিং ডেলিভারি টাস্ক নেই।")
            else:
                for ag_username in del_df["agent_name"].unique():
                    ag_rows = del_df[del_df["agent_name"] == ag_username]
                    ag_disp_name = safe_str(ag_rows.iloc[0]["agent_fullname"]) or ag_username
    
                    with st.expander(f"👤 Agent: **{ag_disp_name}** ({len(ag_rows)}টি কাজ)", expanded=True):
                        for _, row in ag_rows.iterrows():
                            task_id = int(row["id"])
                            o_due = safe_float(row.get("due_amount", 0))
                            s_amt = safe_float(row.get("sale_amount", 0))
                            master_due = o_due + s_amt
    
                            with st.container(border=True):
                                c1, c2 = st.columns([2, 1])
                                with c1:
                                    st.markdown(f"#### 🏢 {safe_str(row['party_name'])}")
                                    addr = safe_str(row.get("address"))
                                    phone = safe_str(row.get("party_phone"))
                                    if addr:
                                        st.caption(f"📍 {addr}" + (f" | 📞 {phone}" if phone else ""))
                                with c2:
                                    st.metric(label="Master Due (ডিউ/বিল)", value=f"৳ {master_due:,.2f}")
    
                                with st.form(key=f"complete_task_form_del_{task_id}", clear_on_submit=True):
                                    col_f1, col_f2 = st.columns(2)
                                    with col_f1:
                                        sale_input = st.text_input(
                                            "New Sale Amount (নতুন বিল)*",
                                            value="" if s_amt == 0.0 else str(s_amt),
                                            key=f"sale_amt_del_{task_id}",
                                            placeholder="টাকা লিখুন"
                                        )
                                    with col_f2:
                                        payment_input = st.text_input(
                                            "Payment Collected (প্রাপ্ত পেমেন্ট)",
                                            value=str(master_due),
                                            key=f"pay_amt_del_{task_id}"
                                        )
    
                                    submit_complete = st.form_submit_button("✅ Complete Task", type="primary", use_container_width=True)
    
                                if submit_complete:
                                    if not sale_input.strip():
                                        st.error("⚠️ নতুন বিক্রয় (Sale Amount) ইনপুট দেওয়া বাধ্যতামূলক!")
                                    else:
                                        final_sale = safe_float(sale_input)
                                        p_amt = safe_float(payment_input)
    
                                        if final_sale <= 0:
                                            st.error("⚠️ বিক্রয়ের মান সঠিক সংখ্যায় (০-এর চেয়ে বড়) হতে হবে!")
                                        else:
                                            r_due = (o_due + final_sale) - p_amt
                                            try:
                                                c.execute(
                                                    "UPDATE task_assignments SET status='Completed', sale_amount=?, payment_collected_actual=?, remaining_due=? WHERE id=?",
                                                    (str(final_sale), str(p_amt), str(r_due), task_id)
                                                )
                                                c.execute(
                                                    "UPDATE locations SET current_due=? WHERE party_name=?",
                                                    (r_due, str(row["party_name"]))
                                                )
                                                c.execute(
                                                    "UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?",
                                                    (str(row["agent_name"]),)
                                                )
                                                conn.commit()
    
                                                st.session_state["task_search_reset_counter"] += 1
                                                st.session_state["scroll_to_top"] = True
                                                st.toast("🎉 টাস্ক সফলভাবে সম্পন্ন করা হয়েছে!", icon="✅")
                                                st.rerun()
                                            except Exception as e:
                                                conn.rollback()
                                                st.error(f"⚠️ আপডেট করতে সমস্যা হয়েছে: {e}")
    
                                if st.session_state.get("user_role") == "admin":
                                    if st.button("🗑️ Delete Task", key=f"del_task_del_btn_{task_id}"):
                                        try:
                                            move_to_recycle_bin("Task", row["party_name"], dict(row))
                                            c.execute("DELETE FROM task_assignments WHERE id=?", (task_id,))
                                            conn.commit()
                                            st.toast("🗑️ টাস্ক মুছে রিসাইকেল বিনে পাঠানো হয়েছে!", icon="ℹ️")
                                            st.rerun()
                                        except Exception as e:
                                            conn.rollback()
                                            st.error(f"⚠️ টাস্ক মুছতে ব্যর্থ: {e}")
    
        # ---------------------------------------------------------
        # TAB 2: DUE COLLECTION TASKS
        # ---------------------------------------------------------
        with tab_due:
            if due_df.empty:
                st.info("ℹ️ কোনো পেন্ডিং ডিউ কালেকশন টাস্ক নেই।")
            else:
                for ag_username in due_df["agent_name"].unique():
                    ag_rows = due_df[due_df["agent_name"] == ag_username]
                    ag_disp_name = safe_str(ag_rows.iloc[0]["agent_fullname"]) or ag_username
    
                    with st.expander(f"👤 Agent: **{ag_disp_name}** ({len(ag_rows)}টি কালেকশন)", expanded=True):
                        for _, row in ag_rows.iterrows():
                            task_id = int(row["id"])
                            o_due = safe_float(row.get("due_amount", 0))
    
                            with st.container(border=True):
                                c1, c2 = st.columns([2, 1])
                                with c1:
                                    st.markdown(f"#### 🏢 {safe_str(row['party_name'])}")
                                    addr = safe_str(row.get("address"))
                                    phone = safe_str(row.get("party_phone"))
                                    if addr:
                                        st.caption(f"📍 {addr}" + (f" | 📞 {phone}" if phone else ""))
                                with c2:
                                    st.metric(label="Total Due (মোট ডিউ)", value=f"৳ {o_due:,.2f}")
    
                                with st.form(key=f"complete_task_form_due_{task_id}", clear_on_submit=True):
                                    payment_input = st.text_input(
                                        "Payment Collected (প্রাপ্ত কালেকশন)",
                                        value=str(o_due),
                                        key=f"pay_amt_due_{task_id}"
                                    )
                                    submit_complete = st.form_submit_button("✅ Complete Task", type="primary", use_container_width=True)
    
                                if submit_complete:
                                    p_amt = safe_float(payment_input)
                                    r_due = o_due - p_amt
                                    try:
                                        c.execute(
                                            "UPDATE task_assignments SET status='Completed', sale_amount='0', payment_collected_actual=?, remaining_due=? WHERE id=?",
                                            (str(p_amt), str(r_due), task_id)
                                        )
                                        c.execute(
                                            "UPDATE locations SET current_due=? WHERE party_name=?",
                                            (r_due, str(row["party_name"]))
                                        )
                                        c.execute(
                                            "UPDATE agent_live_locations SET completed_deliveries = completed_deliveries + 1 WHERE username=?",
                                            (str(row["agent_name"]),)
                                        )
                                        conn.commit()
    
                                        st.session_state["task_search_reset_counter"] += 1
                                        st.session_state["scroll_to_top"] = True
                                        st.toast("🎉 কালেকশন সফলভাবে সম্পন্ন করা হয়েছে!", icon="✅")
                                        st.rerun()
                                    except Exception as e:
                                        conn.rollback()
                                        st.error(f"⚠️ আপডেট করতে সমস্যা হয়েছে: {e}")
    
                                if st.session_state.get("user_role") == "admin":
                                    if st.button("🗑️ Delete Task", key=f"del_task_due_btn_{task_id}"):
                                        try:
                                            move_to_recycle_bin("Task", row["party_name"], dict(row))
                                            c.execute("DELETE FROM task_assignments WHERE id=?", (task_id,))
                                            conn.commit()
                                            st.toast("🗑️ টাস্ক মুছে রিসাইকেল বিনে পাঠানো হয়েছে!", icon="ℹ️")
                                            st.rerun()
                                        except Exception as e:
                                            conn.rollback()
                                            st.error(f"⚠️ টাস্ক মুছতে ব্যর্থ: {e}")

    # --- TAB 2: AGENT SUMMARY ---
    with task_tab2:
        st.markdown("#### Agent Date-wise Summary (এজেন্ট ও তারিখ অনুযায়ী সামারি)")
        agent_sum_df = pd.read_sql_query("""
            SELECT t.agent_name, u.fullname as agent_fullname,
                   SUBSTR(t.created_at, 1, 10) as task_date,
                   COUNT(t.id) as total_tasks, 
                   SUM(CASE WHEN t.status='Completed' THEN 1 ELSE 0 END) as completed_tasks
            FROM task_assignments t
            LEFT JOIN users u ON LOWER(TRIM(t.agent_name)) = LOWER(TRIM(u.username))
            GROUP BY t.agent_name, task_date
            ORDER BY task_date DESC
        """, conn)

        if not agent_sum_df.empty:
            current_role = str(st.session_state.get("user_role", "")).strip().lower()
            is_admin = (current_role == "admin")

            if is_admin:
                export_sum_df = agent_sum_df.copy()
                export_sum_df['Agent Name'] = export_sum_df.apply(lambda r: r['agent_fullname'] if pd.notna(r['agent_fullname']) and r['agent_fullname'] else r['agent_name'], axis=1)
                export_sum_df['Date'] = export_sum_df['task_date'].apply(lambda x: format_date_display(x))
                export_sum_df['Total Tasks'] = export_sum_df['total_tasks']
                export_sum_df['Completed Tasks'] = export_sum_df['completed_tasks']
                export_sum_df_final = export_sum_df[['Agent Name', 'Date', 'Total Tasks', 'Completed Tasks']]
                
                html_agent_sum = generate_html_report("Agent Task Summary Report", export_sum_df_final)
                st.download_button(
                    label="Download Agent Summary Report",
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
                    <p style="margin: 0 0 6px 0; color: #38bdf8 !important; font-size: 16px;">Agent: {ag_disp}</p>
                    <p style="margin: 0 0 4px 0; color: #cbd5e1 !important; font-size: 13px;">Date: <b>{t_date}</b></p>
                    <p style="margin: 0 0 4px 0; color: #cbd5e1 !important; font-size: 13px;">Total Tasks: <b>{tot}</b> | Completed: <b style="color: #34d399;">{comp}</b></p>
                </div>
                """, unsafe_allow_html=True)

                agent_identifier = str(row['agent_name']).strip()
                c.execute("SELECT allow_resubmit FROM users WHERE LOWER(TRIM(username))=LOWER(?) OR LOWER(TRIM(fullname))=LOWER(?)", (agent_identifier, agent_identifier))
                resub_row = c.fetchone()
                agent_allowed = True if resub_row and str(resub_row[0]) in ['1', 'True', 'true'] else False

                if is_admin:
                    resub_toggle = st.checkbox(
                        f"Allow {ag_disp} to Re-submit completed tasks (রি-সাবমিশনের অনুমতি প্রদান করুন)",
                        value=agent_allowed,
                        key=f"resub_perm_{agent_identifier}_{row['task_date']}_{idx}"
                    )
                    if resub_toggle != agent_allowed:
                        c.execute("UPDATE users SET allow_resubmit=? WHERE LOWER(TRIM(username))=LOWER(?) OR LOWER(TRIM(fullname))=LOWER(?)", (1 if resub_toggle else 0, agent_identifier, agent_identifier))
                        conn.commit()
                        st.rerun()

                comp_tasks_df = pd.read_sql_query("""
                    SELECT id, party_name, task_type, due_amount, sale_amount, payment_collected_actual, remaining_due
                    FROM task_assignments
                    WHERE agent_name=? AND SUBSTR(created_at, 1, 10)=? AND status='Completed'
                """, conn, params=(row['agent_name'], row['task_date']))

                if not comp_tasks_df.empty:
                    with st.expander(f"Re-submission Option (ভুলবশত কমপ্লিট হওয়া কাজ পুনরায় একটিভ করুন {len(comp_tasks_df)})", expanded=False):
                        can_do_resubmit = is_admin or agent_allowed
                        if not can_do_resubmit:
                            st.warning("রি-সাবমিশন করার অনুমতি নেই। শুধুমাত্র অ্যাডমিন বা অ্যাডমিন অনুমতি দিলে এই এজেন্ট কাজ পুনরায় একটিভ করতে পারবে।")
                        else:
                            for ct_idx, ct_row in comp_tasks_df.iterrows(): # Fixed tuple unpacking bug
                                st.markdown(f"**Party:** `{ct_row['party_name']}` | **Type:** `{ct_row['task_type']}` | **Collected:** `{ct_row['payment_collected_actual']}`")
                                if st.button(f"Move to Active Tasks (পুনরায় একটিভ করুন)", key=f"btn_resub_ok_{ct_row['id']}_{idx}"):
                                    c.execute("UPDATE task_assignments SET status='Pending' WHERE id=?", (ct_row['id'],))
                                    c.execute("""
                                        UPDATE agent_live_locations
                                        SET completed_deliveries = CASE WHEN completed_deliveries > 0 THEN completed_deliveries - 1 ELSE 0 END
                                        WHERE LOWER(TRIM(username))=LOWER(?)
                                    """, (agent_identifier,))
                                    conn.commit()
                                    st.success("Task moved back to Active Tasks!")
                                    st.rerun()

                if is_admin:
                    if st.button(f"Delete Tasks ({ag_disp} {t_date})", key=f"del_agent_date_sum_{agent_identifier}_{row['task_date']}_{idx}"):
                        c.execute("DELETE FROM task_assignments WHERE agent_name=? AND SUBSTR(created_at, 1, 10)=?", (row['agent_name'], row['task_date']))
                        conn.commit()
                        st.success("Deleted successfully!")
                        st.rerun()
                st.write("---")
        else:
            st.info("No summary records found.")

    # --- TAB 3: COMPLETED TASKS HISTORY ---
    with task_tab3:
        from io import BytesIO
        import re
        
        st.markdown("#### Completed Tasks History (সম্পন্ন কাজ)")
        
        try:
            from xhtml2pdf import pisa
        except ImportError:
            st.error("xhtml2pdf লাইব্রেরি পাওয়া যায়নি! requirements.txt ফাইলে যুক্ত করুন।")
            pisa = None

        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS pdf_permissions (
                username TEXT PRIMARY KEY,
                can_download INTEGER DEFAULT 0
            )
        """)
        conn.commit()

        current_user = st.session_state.get("username", st.session_state.get("user", ""))
        current_user_role = st.session_state.get("user_role", "")
        is_admin = (current_user_role == "admin")

        if is_admin:
            with st.expander("Manage Agent PDF Download Permissions (এজেন্টদের ডাউনলোডের অনুমতি দিন)"):
                try:
                    users_df = pd.read_sql_query("SELECT username, COALESCE(fullname, username) as name FROM users WHERE role != 'admin'", conn)
                    all_agents_db = users_df['username'].tolist()
                    user_display_map = dict(zip(users_df['username'], users_df['name']))
                except Exception:
                    all_agents_db = []
                    user_display_map = {}

                permitted_agents_df = pd.read_sql_query("SELECT username FROM pdf_permissions WHERE can_download = 1", conn)
                allowed_list = permitted_agents_df['username'].tolist()

                selected_allowed_agents = st.multiselect(
                    "অনুমোদিত এজেন্ট বেছে নিন (যারা PDF ডাউনলোড করতে পারবে):",
                    options=all_agents_db,
                    default=[ag for ag in allowed_list if ag in all_agents_db],
                    format_func=lambda x: user_display_map.get(x, x)
                )

                if st.button("Save Permissions (পারমিশন সেভ করুন)", type="primary"):
                    c.execute("UPDATE pdf_permissions SET can_download = 0")
                    for ag in selected_allowed_agents:
                        c.execute("""
                            INSERT INTO pdf_permissions (username, can_download)
                            VALUES (?, 1)
                            ON CONFLICT(username) DO UPDATE SET can_download = 1
                        """, (ag,))
                    conn.commit()
                    st.success("পারমিশন সফলভাবে আপডেট করা হয়েছে!")
                    st.rerun()

        if is_admin:
            can_download = True
        else:
            perm_check = pd.read_sql_query("SELECT can_download FROM pdf_permissions WHERE LOWER(username) = LOWER(?)", conn, params=(current_user,))
            can_download = True if not perm_check.empty and perm_check.iloc[0]['can_download'] == 1 else False

        completed_tasks_df = pd.read_sql_query("""
            SELECT t.id, t.agent_name, u.fullname as agent_fullname,
                   t.party_name, t.task_type, t.due_amount, t.sale_amount,
                   t.payment_collected_actual, t.remaining_due, t.created_at,
                   l.address, l.current_due as master_due
            FROM task_assignments t
            LEFT JOIN users u ON LOWER(t.agent_name) = LOWER(u.username)
            LEFT JOIN locations l ON t.party_name = l.party_name
            WHERE t.status='Completed'
            ORDER BY t.created_at DESC
        """, conn)

        if not completed_tasks_df.empty:
            completed_tasks_df['created_datetime'] = pd.to_datetime(completed_tasks_df['created_at'], errors='coerce')
            completed_tasks_df['created_date'] = completed_tasks_df['created_datetime'].dt.date
            completed_tasks_df['month_year'] = completed_tasks_df['created_datetime'].dt.strftime('%B %Y')
            completed_tasks_df['display_agent'] = completed_tasks_df['agent_fullname'].fillna(completed_tasks_df['agent_name'])

            st.markdown("##### Filter Records (তারিখ ও এজেন্ট অনুযায়ী খুঁজুন)")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                min_date = completed_tasks_df['created_date'].min()
                max_date = completed_tasks_df['created_date'].max()
                selected_date = st.date_input("Select Date (তারিখ সিলেক্ট করুন)", value=max_date, min_value=min_date, max_value=max_date)
            
            with col_f2:
                all_agents_list = completed_tasks_df['display_agent'].dropna().unique().tolist()
                try:
                    users_df = pd.read_sql_query("SELECT DISTINCT COALESCE(fullname, username) as name FROM users", conn)
                    db_agents = users_df['name'].dropna().tolist()
                    all_agents_list = list(set(all_agents_list + db_agents))
                except Exception:
                    pass
                all_agents_list = sorted([str(ag) for ag in all_agents_list if ag])
                agent_list = ["All Agents (সব এজেন্ট)"] + all_agents_list
                selected_agent = st.selectbox("Select Agent (এজেন্ট সিলেক্ট করুন)", agent_list)

            filtered_df = completed_tasks_df[completed_tasks_df['created_date'] == selected_date]
            if selected_agent != "All Agents (সব এজেন্ট)":
                final_filtered_df = filtered_df[filtered_df['display_agent'] == selected_agent]
            else:
                final_filtered_df = filtered_df

            st.write("---")

            if final_filtered_df.empty:
                st.warning(f"{selected_date} তারিখে '{selected_agent}' এর কোনো সম্পন্ন হওয়া কাজ পাওয়া যায়নি।")
            else:
                if can_download:
                    def clean_text_for_pdf(text):
                        if not isinstance(text, str):
                            return str(text) if text is not None else ""
                        cleaned = re.sub(r'[\u0980-\u09FF]+', '', text)
                        cleaned = re.sub(r'\(\s*\)', '', cleaned).strip()
                        return cleaned if cleaned else text

                    export_comp_df = final_filtered_df.copy()
                    export_comp_df['Agent Name'] = export_comp_df['display_agent']
                    export_comp_df['Party Name'] = export_comp_df['party_name']
                    export_comp_df['Task Type'] = export_comp_df['task_type']
                    export_comp_df['Sale Amount (Rs.)'] = export_comp_df['sale_amount']
                    export_comp_df['Collection Amount (Rs.)'] = export_comp_df['payment_collected_actual']
                    export_comp_df['Task Remaining Due (Rs.)'] = export_comp_df['remaining_due']
                    export_comp_df['Master Total Due (Rs.)'] = export_comp_df['master_due']
                    export_comp_df['Completed Date'] = export_comp_df['created_at'].apply(lambda x: format_date_display(x))

                    export_comp_df_final = export_comp_df[['Agent Name', 'Party Name', 'Task Type', 'Sale Amount (Rs.)', 'Collection Amount (Rs.)', 'Task Remaining Due (Rs.)', 'Master Total Due (Rs.)', 'Completed Date']]
                    pdf_clean_df = export_comp_df_final.copy()
                    
                    for col in pdf_clean_df.columns:
                        pdf_clean_df[col] = pdf_clean_df[col].apply(clean_text_for_pdf)

                    clean_agent_title = clean_text_for_pdf(selected_agent)
                    report_title = f"Tasks Report {selected_date} ({clean_agent_title})"
                    html_comp_tasks = generate_html_report(report_title, pdf_clean_df)

                    col_tc1, col_tc2 = st.columns(2)
                    with col_tc1:
                        if pisa:
                            pdf_buffer = BytesIO()
                            pisa_status = pisa.CreatePDF(html_comp_tasks, dest=pdf_buffer)
                            if not pisa_status.err:
                                st.download_button(
                                    label=f"Download PDF ({selected_agent})",
                                    data=pdf_buffer.getvalue(),
                                    file_name=f"report_{selected_date}_{clean_agent_title.replace(' ', '_')}.pdf",
                                    mime="application/pdf",
                                    type="primary"
                                )
                            else:
                                st.error("PDF তৈরিতে সমস্যা হয়েছে।")
                    with col_tc2:
                        if is_admin:
                            if st.button("Clear Filtered Tasks History", type="secondary"):
                                task_ids = final_filtered_df['id'].tolist()
                                for r_idx, r in final_filtered_df.iterrows(): # Fixed typo loop bug
                                    move_to_recycle_bin("Task", r['party_name'], dict(r))
                                conn.executemany("DELETE FROM task_assignments WHERE id=?", [(tid,) for tid in task_ids])
                                conn.commit()
                                st.success("Filtered tasks moved to Recycle Bin!")
                                st.rerun()
                else:
                    st.info("আপনার PDF ডাউনলোড করার অনুমতি নেই। প্রয়োজনে অ্যাডমিনের সাথে যোগাযোগ করুন।")

                st.write("---")
                for idx, row in final_filtered_df.iterrows():
                    ag_c_name = row['display_agent']
                    st.markdown(f"**Agent:** `{ag_c_name}` | **Party:** `{row['party_name']}` | **Task:** `{row['task_type']}`")
                    master_due_text = f" | Master Due: `{row['master_due']}`" if pd.notna(row['master_due']) else ""
                    st.markdown(f"Sale: `{row['sale_amount']}` | Collected: `{row['payment_collected_actual']}` | Task Due: `{row['remaining_due']}`{master_due_text}")

                    if is_admin:
                        if st.button("Delete Task Record", key=f"del_comp_task_{row['id']}"):
                            move_to_recycle_bin("Task", row['party_name'], dict(row))
                            conn.execute("DELETE FROM task_assignments WHERE id=?", (row['id'],))
                            conn.commit()
                            st.success("Moved to Recycle Bin!")
                            st.rerun()
                    st.write("---")

                if is_admin:
                    with st.expander("Monthly Bulk Delete (মাসিক ভিত্তিতে ডেটা মুছুন)"):
                        st.warning("এখান থেকে কোনো মাসের ডেটা ডিলিট করলে সেটি সরাসরি রিসাইকেল বিনে চলে যাবে।")
                        unique_months = completed_tasks_df['month_year'].dropna().unique().tolist()
                        if unique_months:
                            selected_month_to_delete = st.selectbox("Select Month to Delete (যে মাসের ডেটা মুছতে চান):", unique_months)
                            if st.button(f"Delete All Data for {selected_month_to_delete}", type="primary"):
                                month_df_to_delete = completed_tasks_df[completed_tasks_df['month_year'] == selected_month_to_delete]
                                month_task_ids = month_df_to_delete['id'].tolist()
                                for r_idx, r in month_df_to_delete.iterrows():
                                    move_to_recycle_bin("Task", r['party_name'], dict(r))
                                conn.executemany("DELETE FROM task_assignments WHERE id=?", [(tid,) for tid in month_task_ids])
                                conn.commit()
                                st.success(f"{selected_month_to_delete} মাসের সমস্ত ডেটা সফলভাবে ডিলিট হয়ে রিসাইকেল বিনে চলে গেছে!")
                                st.rerun()
                        else:
                            st.info("ডিলিট করার মতো কোনো মাসের ডেটা পাওয়া যায়নি।")
        else:
            st.info("No completed tasks history found.")

    # --- TAB 4: MASTER DUE LIST ---
    with task_tab4:
        st.write("#### Master Due List & Management (পার্টি ডিউ ম্যানেজমেন্ট)")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            if "master_due_search_key" not in st.session_state:
                st.session_state["master_due_search_key"] = ""
            party_search_query = st.text_input("Search Party (পার্টি সার্চ করুন)", placeholder="Type party name...", key="master_due_search_input")
        
        with col_f2:
            import datetime
            current_year_month = datetime.datetime.now().strftime("%Y-%m")
            selected_month = st.selectbox("Select Month (মাস সিলেক্ট করুন)", [current_year_month, "All Months (সব মাস)"], key="master_due_month_select")

        st.write("---")
        st.write("##### Due Summary & Records (ডিউ তালিকা)")
        
        if selected_month != "All Months (সব মাস)":
            st.info(f"Showing records for: {selected_month}")
        else:
            st.info("Showing all time records.")

        if party_search_query.strip():
            c.execute("SELECT party_name, current_due FROM locations WHERE party_name LIKE ? ORDER BY party_name ASC", (f"%{party_search_query.strip()}%",))
        else:
            c.execute("SELECT party_name, current_due FROM locations ORDER BY party_name ASC LIMIT 10")
        
        parties_due_data = c.fetchall()
        if parties_due_data:
            df_due_show = pd.DataFrame(parties_due_data, columns=["Party Name", "Current Due"])
            st.dataframe(df_due_show, use_container_width=True, hide_index=True)
        else:
            st.warning("No data available.")

elif selected_menu == "Route Map (রুট ম্যাপ)":
    st.write("### Route Map & Locations (রুট ম্যাপ)")
    c.execute("""
        SELECT party_name, address, lat, lon, party_phone 
        FROM locations 
        WHERE lat IS NOT NULL AND lon IS NOT NULL 
        ORDER BY party_name ASC
    """)
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
            popup_html = f"<b>{p_n}</b><br>{p_a or 'No Address'}<br>{('Ph: ' + str(p_ph)) if p_ph else ''}"
            
            folium.Marker(
                [p_lat, p_lon],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{idx+1}. {p_n}",
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(r_map)

        gps_lat = st.session_state.get("user_lat")
        gps_lon = st.session_state.get("user_lon")
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

elif selected_menu == "Attendance (উপস্থিতি)":
    import datetime
    import calendar
    import pandas as pd

    def safe_ist_now():
        return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

    def format_date_display(date_str):
        try:
            parts = str(date_str).split('-')
            if len(parts) == 3:
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
        except Exception:
            pass
        return date_str

    now_dt = safe_ist_now()
    current_year = now_dt.year
    current_month = now_dt.month

    st.write("### 📅 Daily & Monthly Attendance (উপস্থিতি ব্যবস্থাপনা)")
    c.execute("SELECT username, fullname, role FROM users")
    att_users_data = c.fetchall()
    agent_name_map = {r[0]: (r[1] if r[1] else r[0]) for r in att_users_data}

    att_tab1, att_tab2 = st.tabs([
        "✔ Daily Attendance (আজকের উপস্থিতি ও চেক-ইন)",
        "📋 Monthly & Agent Attendance Report (মাসিক রিপোর্ট)"
    ])

    with att_tab1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%); padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h4 style="margin:0; color:white; font-size: 22px;">🌟 Daily Attendance & Check-in</h4>
            <p style="margin:5px 0 0 0; font-size: 15px; opacity: 0.9;">আপনার আজকের উপস্থিতি নিশ্চিত করতে নিচের বাটনে ক্লিক করুন।</p>
        </div>
        """, unsafe_allow_html=True)
        
        today_date_str = safe_ist_now().strftime("%Y-%m-%d")
        today_display_str = safe_ist_now().strftime("%d.%m.%Y")
        
        with st.form("attendance_form", clear_on_submit=True):
            agent_for_att = st.session_state.get("username", "staff")
            
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"📅 **আজকের তারিখ:**\n\n**{today_display_str}**")
            with c2:
                st.success(f"👤 **স্টাফের নাম:**\n\n**{agent_name_map.get(agent_for_att, agent_for_att)}**")
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit_att = st.form_submit_button("🚀 Give Attendance / Check-in (উপস্থিতি দিন)", type="primary", use_container_width=True)

        if submit_att:
            try:
                check_time_str = safe_ist_now().strftime("%H:%M:%S")
                c.execute(
                    "INSERT INTO attendance (username, date, check_time, status) VALUES (?, ?, ?, ?)",
                    (agent_for_att, today_date_str, check_time_str, "Present")
                )
                conn.commit()
                st.success("✨ Attendance recorded successfully! (উপস্থিতি সফলভাবে নথিভুক্ত হয়েছে!)")
                st.rerun()
            except sqlite3.IntegrityError:
                st.warning("⚠️ Attendance already given for today! (আজকে ইতিমধ্যে উপস্থিতি দেওয়া হয়েছে!)")

        st.markdown("---")
        st.markdown("#### 📊 Today's Attendance List (আজকের উপস্থিতি তালিকা)")
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
            st.info("ℹ️ No attendance recorded for today yet. (আজ কেউ উপস্থিতি দেননি।)")

    with att_tab2:
        current_role = st.session_state.get("user_role", "staff")
        current_user = st.session_state.get("username", "staff")

        if current_role == "admin":
            st.write("#### Agent-wise Monthly Attendance & Report Download")
            st.write("নিচে থেকে যেকোনো এজেন্টকে সিলেক্ট করে তার এই মাসের মোট কাজের দিন দেখতে পাবেন এবং তার ব্যক্তিগত রিপোর্ট ডাউনলোড করতে পারবেন:")
            
            c.execute("SELECT username, fullname FROM users WHERE role='staff'")
            staff_list = c.fetchall()

            if staff_list:
                selected_rep_agent = st.selectbox(
                    "Select Agent for Report & Summary:",
                    options=[s[0] for s in staff_list],
                    format_func=lambda x: agent_name_map.get(x, x),
                    key="agent_report_dropdown"
                )

                if selected_rep_agent:
                    total_days_in_month = calendar.monthrange(current_year, current_month)[1]
                    c.execute("""
                        SELECT COUNT(DISTINCT date) FROM attendance
                        WHERE username = ? AND SUBSTR(date, 1, 7) = ?
                    """, (selected_rep_agent, f"{current_year}-{current_month:02d}"))
                    days_worked_count = c.fetchone()[0]

                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        st.metric(label="Total Days in This Month", value=f"{total_days_in_month} Days")
                    with col_r2:
                        st.metric(label="Days Worked by Agent", value=f"{days_worked_count} Days")

                    agent_rep_df = pd.read_sql_query("""
                        SELECT date AS 'Date', check_time AS 'Check-in Time', status AS 'Status'
                        FROM attendance
                        WHERE username = ?
                        ORDER BY date DESC, check_time DESC
                    """, conn, params=(selected_rep_agent,))

                    if not agent_rep_df.empty:
                        agent_rep_df['Date'] = agent_rep_df['Date'].apply(lambda x: format_date_display(x))
                        st.dataframe(agent_rep_df, use_container_width=True)

                        agent_fullname_str = agent_name_map.get(selected_rep_agent, selected_rep_agent)
                        try:
                            html_agent_att = generate_html_report(f"Attendance Report {agent_fullname_str}", agent_rep_df)
                            st.download_button(
                                label=f"Download Report for {agent_fullname_str} ({selected_rep_agent})",
                                data=html_agent_att,
                                file_name=f"attendance_report_{selected_rep_agent}_{current_year}_{current_month:02d}.html",
                                mime="text/html",
                                type="primary",
                                key=f"dl_btn_{selected_rep_agent}"
                            )
                        except NameError:
                            csv_data = agent_rep_df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label=f"Download CSV Report for {agent_fullname_str}",
                                data=csv_data,
                                file_name=f"attendance_{selected_rep_agent}_{current_year}_{current_month:02d}.csv",
                                mime="text/csv",
                                type="primary"
                            )
                    else:
                        st.info(f"এই মাসের জন্য {agent_name_map.get(selected_rep_agent, selected_rep_agent)}-এর কোনো উপস্থিতির রেকর্ড পাওয়া যায়নি।")

            st.write("---")
            st.write("#### Delete Attendance Records (Admin Only)")
            
            del_mode = st.radio("Delete Option:", ["Delete Single Date", "Delete Full Month Data"], horizontal=True)

            if del_mode == "Delete Single Date":
                col_del1, col_del2 = st.columns(2)
                with col_del1:
                    del_agent = st.selectbox(
                        "Select Agent:",
                        options=[s[0] for s in staff_list] if staff_list else [],
                        format_func=lambda x: agent_name_map.get(x, x),
                        key="del_agent_select"
                    )
                with col_del2:
                    del_date = st.date_input("Select Date to Delete:", value=safe_ist_now().date(), key="del_date_select")

                if st.button("Delete Selected Attendance Record", type="primary", key="btn_del_att"):
                    if staff_list:
                        del_date_str = del_date.strftime("%Y-%m-%d")
                        c.execute("SELECT COUNT(*) FROM attendance WHERE username = ? AND date = ?", (del_agent, del_date_str))
                        record_exists = c.fetchone()[0]

                        if record_exists > 0:
                            c.execute("DELETE FROM attendance WHERE username = ? AND date = ?", (del_agent, del_date_str))
                            conn.commit()
                            st.success(f"Successfully deleted attendance record on {del_date.strftime('%d-%m-%Y')}!")
                            st.rerun()
                        else:
                            st.warning(f"No attendance record found on {del_date.strftime('%d-%m-%Y')}.")
            else:
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    target_year = st.number_input("Year (বছর):", min_value=2024, max_value=2035, value=current_year)
                with col_m2:
                    target_month = st.selectbox("Month (মাস):", options=list(range(1, 13)), format_func=lambda x: calendar.month_name[x], index=current_month-1)

                if st.button("⚠️ Delete All Attendance for This Month", type="primary", key="btn_del_full_month"):
                    month_str = f"{target_year}-{target_month:02d}"
                    c.execute("SELECT COUNT(*) FROM attendance WHERE SUBSTR(date, 1, 7) = ?", (month_str,))
                    month_count = c.fetchone()[0]
                    
                    if month_count > 0:
                        c.execute("DELETE FROM attendance WHERE SUBSTR(date, 1, 7) = ?", (month_str,))
                        conn.commit()
                        st.success(f"Successfully deleted all attendance records for {calendar.month_name[target_month]} {target_year}!")
                        st.rerun()
                    else:
                        st.warning(f"No attendance records found for {calendar.month_name[target_month]} {target_year}.")
        else:
            st.write("#### Your Monthly Attendance Report")
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

elif selected_menu == "Live Tracking (লাইভ ট্র্যাকিং)" and st.session_state.get("user_role") == "admin":
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h4 style="margin:0; color:white; font-size: 22px;">📍 Live Agent Tracking</h4>
        <p style="margin:5px 0 0 0; font-size: 15px; opacity: 0.9;">এজেন্টদের লাইভ লোকেশন এবং সর্বশেষ আপডেট এখানে দেখুন।</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        live_df = pd.read_sql_query("""
            SELECT a.username, u.fullname, u.phone, a.lat, a.lon, a.last_updated, a.completed_deliveries
            FROM agent_live_locations a 
            LEFT JOIN users u ON a.username = u.username
            ORDER BY a.last_updated DESC
        """, conn)
    except Exception as e:
        live_df = pd.DataFrame()
        st.error(f"Database query error: {e}")

    if not live_df.empty:
        agent_options = ["All Agents (সব এজেন্ট একসাথে)"]
        for idx, r in live_df.iterrows():
            d_name = f"{r['fullname']} ({r['username']})" if pd.notna(r.get('fullname')) and r['fullname'] else r['username']
            agent_options.append(d_name)

        selected_agent_box = st.selectbox("🔍 Select Agent to Track:", agent_options)
        st.write("---")

        filtered_df = live_df
        if selected_agent_box != "All Agents (সব এজেন্ট একসাথে)":
            sel_uname = selected_agent_box.split("(")[-1].strip(")")
            filtered_df = live_df[live_df['username'] == sel_uname]

        for idx, r in filtered_df.iterrows():
            name = r['fullname'] if pd.notna(r.get('fullname')) and r['fullname'] else r['username']
            username = r['username']
            phone = r.get('phone', 'N/A')
            lat = r.get('lat')
            lon = r.get('lon')
            last_up = r.get('last_updated')
            completed = r.get('completed_deliveries', 0)

            with st.expander(f"👤 Agent: {name} (ID: {username})", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.info(f"📞 **Phone Number:**\n\n{phone}")
                with c2:
                    st.success(f"✅ **Completed Tasks:**\n\n{completed}")
                with c3:
                    st.warning(f"🕒 **Last Updated:**\n\n{last_up if pd.notna(last_up) else 'No update'}")

                if pd.notna(lat) and pd.notna(lon):
                    g_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                    st.markdown("<br>", unsafe_allow_html=True)
                    # HTML বাটনের বদলে স্ট্রিমলিটের লেটেস্ট লিংক বাটন ব্যবহার করা হয়েছে, যা দেখতে অনেক সুন্দর
                    st.link_button("🗺️ Track on Google Maps", url=g_url, type="primary", use_container_width=True)
                else:
                    st.error("⚠️ GPS coordinates not available for this agent.")
    else:
        st.warning("⚠️ কোনো এজেন্টের লাইভ লোকেশন ডাটা পাওয়া যায়নি বা টেবিলটি খালি আছে।")
        st.info("💡 এজেন্ট অ্যাপ থেকে লোকেশন আপডেট হলে এখানে দেখতে পাবেন।")

elif selected_menu == "Settings & Agents (সেটিংসে)" and st.session_state.get("user_role") == "admin":
    st.write("### Settings & Agents Management (কর্মী, অজানা ইউজার ও ম্যানেজমেন্ট)")
    
    c.execute("SELECT COUNT(*) FROM users WHERE role='staff'")
    total_staff_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users")
    total_users_count = c.fetchone()[0]
    
    col_st1, col_st2 = st.columns(2)
    with col_st1:
        st.markdown(f"""
        <div style="background: #1e293b; padding: 15px; border-radius: 12px; border: 1px solid #3b82f6; text-align: center;">
            <h4 style="margin: 0; color: #60a5fa;">Registered Staff Agents</h4>
            <h2 style="margin: 5px 0 0 0; color: #34d399;">{total_staff_count}</h2>
        </div>
        """, unsafe_allow_html=True)
    with col_st2:
        st.markdown(f"""
        <div style="background: #1e293b; padding: 15px; border-radius: 12px; border: 1px solid #818cf8; text-align: center;">
            <h4 style="margin: 0; color: #a78bfa;">Total System Users</h4>
            <h2 style="margin: 5px 0 0 0; color: #38bdf8;">{total_users_count}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("")
    set_tab1, set_tab_perm, set_tab3, set_tab4, set_tab5, set_tab6 = st.tabs([
        "+ Add Agents & Links",
        "Menu Permissions",
        "Unknown & Blocked Agents",
        "Backup & Restore",
        "Recycle Bin",
        "Admin Password"
    ])

    # --- TAB 1: ADD AGENTS & LINKS ---
    with set_tab1:
        st.write("#### Add New Staff / Agent & Generate Auto-Login Link")
        st.info("এই সেকশন থেকে অ্যাডমিন নতুন এজেন্টের নাম, ইউজারনেম ও পাসওয়ার্ড দিয়ে একাউন্ট তৈরি করতে পারবেন। সাথে সাথে অটো-লগইন লিংক তৈরি হয়ে যাবে।")
        
        try:
            eval_parent_url = streamlit_js_eval(
                js_expressions="window.parent.location.origin + window.parent.location.pathname",
                key="get_parent_window_url_clean"
            )
            if eval_parent_url and "component" not in eval_parent_url:
                clean_base_url = eval_parent_url.rstrip("/")
            else:
                clean_base_url = "https://ps-mediseller-app-gcanjbehuut7h9rzk4xzfg.streamlit.app"
        except Exception:
            clean_base_url = "https://ps-mediseller-app-gcanjbehuut7h9rzk4xzfg.streamlit.app"

        with st.form("add_agent_form", clear_on_submit=True):
            new_uname = st.text_input("Username (ইউজারনেম, যেমন: rahul1)")
            new_pass = st.text_input("Password (পাসওয়ার্ড)")
            new_fname = st.text_input("Full Name (পুরো নাম)")
            new_phone = st.text_input("Phone Number (ফোন নম্বর)")
            submit_new_agent = st.form_submit_button("+ Add Agent (এজেন্ট যুক্ত করুন)", type="primary")

            if submit_new_agent:
                if new_uname.strip() and new_pass.strip() and new_fname.strip():
                    try:
                        c.execute(
                            "INSERT INTO users (username, password, role, fullname, phone, created_at, is_active, allow_resubmit) VALUES (?, ?, 'staff', ?, ?, ?, 1, 0)",
                            (new_uname.strip(), new_pass.strip(), new_fname.strip(), new_phone.strip(), get_ist_time().strftime("%Y-%m-%d %H:%M:%S"))
                        )
                        conn.commit()
                        st.success(f"New agent '{new_fname.strip()}' added successfully! (নতুন এজেন্ট যুক্ত হয়েছে!)")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Username already exists! (এই ইউজারনেম ইতিমধ্যে আছে!)")
                else:
                    st.error("Username, Password and Full Name are required! (সব তথ্য আবশ্যক!)")

        st.write("---")
        st.write("#### Existing Agents, Auto-Login Links & Edit")
        st.write("এজেন্টদের তথ্য পরিবর্তন করতে 'Edit Agent'-এ ক্লিক করুন।")
        
        c.execute("SELECT username, fullname, password, phone, is_active FROM users WHERE role='staff'")
        staff_data = c.fetchall()
        
        if staff_data:
            for s in staff_data:
                s_uname, s_fname, s_pass, s_ph, s_act = s
                status = "Active" if s_act == 1 else "Blocked"
                st.markdown(f"**Name:** {s_fname} | **User:** `{s_uname}` | **Pass:** `{s_pass}` | **Phone:** {s_ph} | **Status:** {status}")
                
                link = f"{clean_base_url}/?login={s_uname}"
                st.code(link, language="text")
                
                with st.expander(f"Edit Agent: {s_fname}"):
                    with st.form(f"edit_form_{s_uname}"):
                        edit_fname = st.text_input("Full Name (নতুন নাম)", value=s_fname)
                        edit_uname = st.text_input("Username / ID (নতুন আইডি)", value=s_uname)
                        edit_pass = st.text_input("Password (নতুন পাসওয়ার্ড)", value=s_pass)
                        edit_phone = st.text_input("Phone Number (নতুন ফোন নম্বর)", value=s_ph)
                        submit_edit = st.form_submit_button("Update Details (আপডেট করুন)", type="primary")

                        if submit_edit:
                            if edit_uname.strip() and edit_fname.strip():
                                try:
                                    if edit_uname.strip() != s_uname:
                                        c.execute("SELECT username FROM users WHERE username = ?", (edit_uname.strip(),))
                                        if c.fetchone():
                                            st.error("এই নতুন আইডিটি (Username) ইতিমধ্যে অন্য কারো আছে! অন্য নাম দিন।")
                                            st.stop()

                                    c.execute("""
                                        UPDATE users
                                        SET username=?, fullname=?, password=?, phone=?
                                        WHERE username=?
                                    """, (edit_uname.strip(), edit_fname.strip(), edit_pass.strip(), edit_phone.strip(), s_uname))

                                    if edit_uname.strip() != s_uname:
                                        c.execute("UPDATE attendance SET username=? WHERE username=?", (edit_uname.strip(), s_uname))
                                        c.execute("UPDATE agent_live_locations SET username=? WHERE username=?", (edit_uname.strip(), s_uname))
                                        c.execute("UPDATE task_assignments SET agent_name=? WHERE agent_name=?", (edit_uname.strip(), s_uname))
                                    
                                    conn.commit()
                                    st.success("এজেন্টের তথ্য সফলভাবে আপডেট হয়েছে!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating agent: {e}")
                            else:
                                st.error("নাম এবং আইডি (Username) ফাঁকা রাখা যাবে না!")
                st.write("---")
        else:
            st.warning("এখনো কোনো স্টাফ/এজেন্ট যুক্ত করা হয়নি।")

    # --- TAB 2: MENU PERMISSIONS ---
    with set_tab_perm:
        import time
        st.write("### Menu Permissions (মেনু পারমিশন)")
        st.divider()

        try:
            c.execute("SELECT username, fullname FROM users WHERE role='staff'")
            staff_data = c.fetchall()
            
            if not staff_data:
                st.info("কোনো স্টাফ একাউন্ট পাওয়া যায়নি।")
            else:
                for s in staff_data:
                    s_uname, s_fname = s
                    with st.expander(f"Permission Settings: {s_fname} ({s_uname})"):
                        c.execute("SELECT allowed_menus FROM users WHERE username=?", (s_uname,))
                        am_row = c.fetchone()
                        
                        curr_menus = am_row[0].split(",") if am_row and am_row[0] else all_basic_menus
                        valid_defaults = [menu.strip() for menu in curr_menus if menu.strip() in all_basic_menus]

                        sel_menus = st.multiselect(
                            "যে মেনুগুলোর এক্সেস দিতে চান তা নির্বাচন করুন:",
                            all_basic_menus,
                            default=valid_defaults,
                            key=f"perm_{s_uname}"
                        )

                        if st.button("Save Permissions", key=f"btn_perm_{s_uname}", use_container_width=True):
                            try:
                                updated_menus_str = ",".join(sel_menus)
                                c.execute("UPDATE users SET allowed_menus=? WHERE username=?", (updated_menus_str, s_uname))
                                conn.commit()
                                st.success(f"{s_fname}-এর পারমিশন সফলভাবে আপডেট হয়েছে!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"ডাটাবেজ আপডেট করতে সমস্যা হয়েছে: {e}")
        except Exception as e:
            st.error(f"স্টাফদের তথ্য আনতে সমস্যা হয়েছে: {e}")

    # --- TAB 3: UNKNOWN & BLOCKED AGENTS ---
    with set_tab3:
        st.write("### 🛡️ Unknown & Blocked Agents Management")
        st.caption("লিংক দিয়ে প্রবেশ করা নতুন ইউজার এবং ব্লকড এজেন্টদের তালিকা ও পরিচালনা সেকশন।")
    
        # ডাটাবেজ থেকে স্টাফ ও অজানা (Unknown) ইউজারদের ডাটা ফেচ করা
        c.execute("SELECT username, fullname, role, is_active, created_at FROM users WHERE role != 'admin'")
        all_users_data = c.fetchall()
    
        if "delete_msg" in st.session_state:
            st.success(st.session_state["delete_msg"])
            del st.session_state["delete_msg"]
    
        if not all_users_data:
            st.info("বর্তমানে কোনো Unknown বা Blocked এজেন্ট পাওয়া যায়নি।")
        else:
            # ১. ড্রপডাউন ফিল্টারিং
            user_options = [row[0] for row in all_users_data]
            user_dict = {row[0]: f"{row[1]} (@{row[0]}) - [{row[2].upper()}]" for row in all_users_data}
    
            st.markdown("##### 🔍 সিলেক্ট করুন যাকে ম্যানেজ করতে চান")
            selected_uname = st.selectbox(
                "ইউজারনেম বা আইডি নির্বাচন করুন:",
                options=user_options,
                format_func=lambda x: user_dict.get(x, x)
            )
    
            if selected_uname:
                c.execute("SELECT username, fullname, role, is_active, phone FROM users WHERE username=?", (selected_uname,))
                u_row = c.fetchone()
                
                if u_row:
                    s_uname, s_fname, s_role, s_act, s_phone = u_row
                    status_label = "🟢 Active" if s_act == 1 else "🔴 Blocked"
                    role_label = "⚠️ Unknown (Link Access)" if s_role == "unknown" else f"👤 {s_role.capitalize()}"
                    
                    # 📌 কার্ডের মতো সুন্দর ডিটেইলস ডিসপ্লে
                    st.info(f"""
                    **নাম:** {s_fname}  
                    **ইউজারনেম:** `{s_uname}` | **ফোন:** {s_phone}  
                    **টাইপ:** {role_label} | **স্ট্যাটাস:** {status_label}
                    """)
    
                    col1, col2, col3 = st.columns([1, 1, 1])
    
                    # কলাম ১: ব্লক / আনব্লক অ্যাকশন
                    with col1:
                        if s_act == 1:
                            if st.button("🔒 Block User", key=f"blk_{s_uname}", use_container_width=True):
                                c.execute("UPDATE users SET is_active=0 WHERE username=?", (s_uname,))
                                conn.commit()
                                st.success(f"'{s_uname}' কে ব্লক করা হয়েছে।")
                                st.rerun()
                        else:
                            if st.button("🔓 Unblock User", key=f"unblk_{s_uname}", use_container_width=True):
                                c.execute("UPDATE users SET is_active=1 WHERE username=?", (s_uname,))
                                conn.commit()
                                st.success(f"'{s_uname}' কে আনব্লক করা হয়েছে।")
                                st.rerun()
    
                    # কলাম ২: স্টাফ হিসেবে অ্যাপ্রুভ করা (Unknown ইউজারদের জন্য)
                    with col2:
                        if s_role == "unknown":
                            if st.button("✅ Approve as Staff", key=f"appr_{s_uname}", use_container_width=True):
                                c.execute("UPDATE users SET role='staff' WHERE username=?", (s_uname,))
                                conn.commit()
                                st.success(f"'{s_uname}' এখন রেজিস্টার্ড Staff!")
                                st.rerun()
    
                    # কলাম ৩: ডিলিট অ্যাকশন
                    with col3:
                        if st.button("🗑️ Delete User", key=f"del_{s_uname}", type="primary", use_container_width=True):
                            c.execute("DELETE FROM users WHERE username=?", (s_uname,))
                            conn.commit()
                            st.session_state["delete_msg"] = f"User '{s_uname}' সফলভাবে মুছে ফেলা হয়েছে!"
                            st.rerun()
    
            st.divider()
    
            # ২. সামারি টেবিল ও লিস্ট
            st.markdown("##### 📋 সকল এজেন্ট ও অটো-লগইন ইউজারদের সামারি")
            
            summary_list = []
            for u in all_users_data:
                uname, fname, role, is_act, created = u
                st_text = "🟢 Active" if is_act == 1 else "🔴 Blocked"
                type_text = "🔗 Link User (Unknown)" if role == "unknown" else "👤 Staff"
                summary_list.append({
                    "Username": uname,
                    "Full Name": fname,
                    "Type": type_text,
                    "Status": st_text,
                    "Joined": created
                })
                
            st.dataframe(summary_list, use_container_width=True)
   
    # ==========================================
    # ১. হেলপার ফাংশন (নিরাপদ ব্যাকআপ ও রিস্টোর code start)
    # ==========================================
    def generate_safe_backup(db_path):
        """SQLite-এর নেটিভ ব্যাকআপ ইঞ্জিন ব্যবহার করে নিরাপদ ব্যাকআপ বাইট রিটার্ন করে"""
        if not os.path.exists(db_path):
            return None
        try:
            # WAL ফ্লাশ করা
            with sqlite3.connect(db_path) as src_conn:
                src_conn.execute("PRAGMA wal_checkpoint(FULL);")
    
                # মেমোরিতে ব্যাকআপ স্ন্যাপশট নেওয়া (ফাইল লক এড়াতে)
                mem_db = sqlite3.connect(":memory:")
                src_conn.backup(mem_db)
    
                # বাইনারি ডেটা এক্সপোর্ট
                raw_bytes = mem_db.serialize()
                mem_db.close()
                return raw_bytes
        except Exception as e:
            st.error(f"⚠️ Backup creation failed: {e}")
            return None
    
    
    def validate_and_restore_db(uploaded_file, target_db_path):
        """আপলোড করা ফাইলটি আসল ও নিখুঁত SQLite ডাটাবেস কিনা তা পরীক্ষা করে রিস্টোর করে"""
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, "temp_restore.db")
    
        try:
            # ১. অস্থায়ী ফাইলে আপলোড করা ফাইল সেভ করা
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
    
            # ২. ডাটাবেসের সঠিনতা পরীক্ষা (Integrity Check)
            test_conn = sqlite3.connect(temp_file_path)
            cursor = test_conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            check_result = cursor.fetchone()[0]
    
            # ৩. ডাটাবেসে টেবিল আছে কিনা ভ্যালিডেশন
            cursor.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table';"
            )
            table_count = cursor.fetchone()[0]
            test_conn.close()
    
            if check_result != "ok" or table_count == 0:
                st.error(
                    "❌ ফাইলটি একটি ভ্যালিড ডাটাবেস নয় অথবা ডাটাবেসটি কারাপ্ট/খালি!"
                )
                return False
    
            # ৪. সেফ রিস্টোর: নেটিভ SQLite Backup API দিয়ে আসল ডাটাবেসে রিস্টোর
            with (
                sqlite3.connect(temp_file_path) as src_conn,
                sqlite3.connect(target_db_path) as dst_conn,
            ):
                src_conn.backup(dst_conn)
    
            # টিডি ক্লিনআপ
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
            return True
    
        except Exception as e:
            st.error(f"❌ Restore Failed: {e}")
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return False
    
    
    # ==========================================
    # ২. Tab 4 - Modern Backup & Restore UI
    # ==========================================
    with set_tab4:
        st.markdown("### 💾 Database Management & Security")
        st.caption("আপনার সিস্টেমের সম্পূর্ণ ডাটাবেস ব্যাকআপ নিন বা আগের ব্যাকআপ রিস্টোর করুন।")
        st.divider()
    
        col_backup, col_restore = st.columns(2, gap="large")
    
        # ----- 📦 ডাটাবেস ব্যাকআপ সেকশন -----
        with col_backup:
            st.markdown("#### 📥 Database Backup")
            st.info(
                "সব সাম্প্রতিক তথ্য সহ একটি ডুপ্লিকেট `.db` ফাইল ব্যাকআপ নিন।"
            )
    
            # ডাটাবেসের আকার প্রদর্শন
            if os.path.exists(DB_FILE):
                db_size_kb = round(os.path.getsize(DB_FILE) / 1024, 2)
                st.metric(label="Current Database Size", value=f"{db_size_kb} KB")
    
            # বর্তমান তারিখ ও সময় দিয়ে ইউনিক ফাইলের নাম
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"mediseller_backup_{timestamp}.db"
    
            # ব্যাকআপ বাইট জেনারেট
            db_bytes = generate_safe_backup(DB_FILE)
    
            if db_bytes:
                st.download_button(
                    label="⬇️ Download Fresh Backup (.db)",
                    data=db_bytes,
                    file_name=backup_filename,
                    mime="application/x-sqlite3",
                    type="primary",
                    use_container_width=True,
                )
            else:
                st.error("ডাটাবেস ব্যাকআপ তৈরি করতে সমস্যা হয়েছে!")
    
        # ----- 🔄 ডাটাবেস রিস্টোর সেকশন -----
        with col_restore:
            st.markdown("#### 📤 Database Restore")
            st.warning(
                "⚠️ **সতর্কতা:** রিস্টোর করলে বর্তমান ডাটাবেস ওভাররাইট হয়ে যাবে।"
            )
    
            uploaded_file = st.file_uploader(
                "রিস্টোর করার জন্য `.db` ফাইল সিলেক্ট করুন",
                type=["db"],
                key="db_restore_uploader",
            )
    
            if uploaded_file is not None:
                # আপলোড করা ফাইলের সাইজ
                file_size_kb = round(uploaded_file.size / 1024, 2)
                st.caption(
                    f"📄 Selected File: `{uploaded_file.name}` ({file_size_kb} KB)"
                )
    
                if st.button(
                    "🔄 Confirm & Restore Database",
                    type="primary",
                    use_container_width=True,
                ):
                    with st.spinner("রিস্টোর করা হচ্ছে এবং ডাটাবেস যাচাই করা হচ্ছে..."):
                        success = validate_and_restore_db(uploaded_file, DB_FILE)
    
                    if success:
                        # স্ট্রিমলিট ক্যাশ ক্লিয়ার করা যাতে নতুন ডাটা লোড হয়
                        st.cache_resource.clear()
                        st.cache_data.clear()
    
                        st.success("✅ Database restored successfully!")
                        st.balloons()
                        st.rerun()
        
    # --- TAB 5: RECYCLE BIN ---
    with set_tab5:
        st.subheader("Recycle Bin (রিসাইকেল বিন)")
        try:
            recycle_rows = c.execute("SELECT id, item_type, item_title, item_data, deleted_at FROM recycle_bin").fetchall()
            
            if recycle_rows:
                display_data = []
                options = {}
                for row in recycle_rows:
                    r_id, item_type, item_title, item_data, deleted_at = row
                    display_data.append({
                        "ID": r_id,
                        "Item Type": item_type,
                        "Name / Title": item_title,
                        "Deleted At": deleted_at
                    })
                    label = f"ID: {r_id} | [{item_type}] {item_title}"
                    options[label] = row

                df_recycle = pd.DataFrame(display_data)
                st.dataframe(df_recycle, use_container_width=True, hide_index=True)
                st.markdown("---")

                st.subheader("Restore Item")
                selected_label = st.selectbox("Select Item to Restore:", list(options.keys()))
                
                if st.button("Restore Selected Item", type="primary"):
                    selected_row = options[selected_label]
                    selected_id = selected_row[0]
                    item_type = selected_row[1]
                    raw_data = selected_row[3]
                    data = {}

                    if isinstance(raw_data, dict):
                        data = raw_data
                    elif isinstance(raw_data, str) and raw_data.strip():
                        try:
                            import ast
                            data = ast.literal_eval(raw_data)
                        except Exception:
                            try:
                                import json
                                data = json.loads(raw_data)
                            except Exception:
                                data = {}

                    if not data:
                        st.error("Error: Failed to parse item data for restoration!")
                        st.stop()

                    if item_type == "Location":
                        c.execute("""
                            INSERT OR IGNORE INTO locations (party_name, address, party_phone, lat, lon, route_order, current_due)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (data.get('party_name'), data.get('address'), data.get('party_phone'), data.get('lat'), data.get('lon'), data.get('route_order'), data.get('current_due')))
                    
                    elif item_type == "Orders":
                        c.execute("""
                            INSERT INTO orders (party_name, order_details, order_date, status, payment_collected)
                            VALUES (?, ?, ?, ?, ?)
                        """, (data.get('party_name'), data.get('order_details'), data.get('order_date'), data.get('status', 'Pending'), data.get('payment_collected', '0')))

                    elif item_type == "Daily Work":
                        c.execute("""
                            INSERT INTO daily_work (party_name, activity_type, work_date)
                            VALUES (?, ?, ?)
                        """, (data.get('party_name', 'N/A'), data.get('activity_type', 'N/A'), data.get('work_date', '')))

                    elif item_type == "Task":
                        c.execute("""
                            INSERT INTO task_assignments (agent_name, party_name, task_type, due_amount, sale_amount, payment_collected_actual, remaining_due, status, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (data.get('agent_name'), data.get('party_name'), data.get('task_type'), data.get('due_amount', '0'), data.get('sale_amount', '0'), data.get('payment_collected_actual', '0'), data.get('remaining_due', '0'), data.get('status', 'Pending'), data.get('created_at')))

                    c.execute("DELETE FROM recycle_bin WHERE id=?", (selected_id,))
                    conn.commit()
                    st.success(f"Successfully restored '{selected_row[2]}'!")
                    st.rerun()

                if st.button("Clear Recycle Bin"):
                    c.execute("DELETE FROM recycle_bin")
                    conn.commit()
                    st.success("Recycle Bin cleared!")
                    st.rerun()
            else:
                st.info("Recycle Bin is empty. (রিসাইকেল বিন ফাঁকা)")
        except Exception as e:
            st.error(f"Error loading Recycle Bin: {e}. ডেটাবেসে recycle_bin টেবিলটি আছে কিনা চেক করুন।")

    # --- TAB 6: ADMIN PASSWORD ---
    with set_tab6:
        st.write("#### Admin Password Update (পাসওয়ার্ড পরিবর্তন)")
        with st.form("update_admin_pass"):
            new_pass = st.text_input("New Admin Password", type="password")
            if st.form_submit_button("Update Password", type="primary"):
                if new_pass.strip():
                    c.execute("UPDATE users SET password=? WHERE username='admin'", (new_pass.strip(),))
                    conn.commit()
                    st.success("Admin Password Updated Successfully!")
                else:
                    st.error("Please enter a valid password.")
