
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
            <b>(অ্যাপটি ব্যবহারের জন্য আপনার ফোনের জিপিএস লোকেশন অন করুন এবং পারমিশন দিন।)</b>
        </p>
        <button onclick="requestLocation()" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border:
none; padding: 14px 28px; border-radius: 10px; font-weight: bold; font-size: 16px; cursor: pointer; width: 100%;">
            🔄 Grant Permission / Retry (অনুমতি দিন / রিফ্রেশ)
        </button>
        <p id="loc-status" style="color: #fbbf24; font-size: 13px; margin-top: 15px; display: none;"></p>
    </div>
</div>
<script>
function checkAndRequestLocation() {
    if (!navigator.geolocation) return;
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
html, body, [class*="css"], p, span, label, div { font-family: 'Poppins', sans-serif; color: #ffffff !important; }
.stApp { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%); color: #ffffff !important; }
div.stExpander, div[data-testid="stForm"] { background: #1e293b !important; border: 1px solid rgba(148, 163, 184, 0.35) !important; border-radius: 14px !important; padding: 20px !important; }
.stButton>button, div.stButton > button { background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important; color: #ffffff !important; border-radius: 10px !important; font-weight: 600 !important; }
input, textarea, select { background-color: #0f172a !important; color: #ffffff !important; border: 1px solid #3b82f6 !important; border-radius: 8px !important; }
.main-title { font-size: 24px; font-weight: bold; color: #ffffff; text-align: center; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE SETUP
# =========================================================
DB_FILE = "mediseller_delivery.db"
def get_db_connection(): return sqlite3.connect(DB_FILE, check_same_thread=False)
conn = get_db_connection()
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT NOT NULL, fullname TEXT, phone TEXT, created_at TIMESTAMP, is_active INTEGER DEFAULT 1)")
c.execute("CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY AUTOINCREMENT, party_name TEXT NOT NULL UNIQUE, address TEXT, party_phone TEXT UNIQUE, lat REAL, lon REAL, route_order INTEGER DEFAULT 0)")
c.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, party_name TEXT NOT NULL, order_details TEXT, order_date TEXT NOT NULL, status TEXT DEFAULT 'Pending', payment_collected TEXT DEFAULT '0')")
c.execute("CREATE TABLE IF NOT EXISTS daily_work (id INTEGER PRIMARY KEY AUTOINCREMENT, party_name TEXT NOT NULL, activity_type TEXT NOT NULL, work_date TEXT NOT NULL)")
c.execute("CREATE TABLE IF NOT EXISTS agent_live_locations (username TEXT PRIMARY KEY, lat REAL, lon REAL, last_updated TEXT, completed_deliveries INTEGER DEFAULT 0, completed_dues INTEGER DEFAULT 0)")
c.execute("CREATE TABLE IF NOT EXISTS task_assignments (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_name TEXT NOT NULL, party_name TEXT NOT NULL, task_type TEXT NOT NULL, due_amount TEXT DEFAULT '0', sale_amount TEXT DEFAULT '0', payment_collected_actual TEXT DEFAULT '0', status TEXT DEFAULT 'Pending', created_at TEXT NOT NULL)")
c.execute("CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, date TEXT NOT NULL, check_time TEXT NOT NULL, status TEXT DEFAULT 'Present', UNIQUE(username, date))")
c.execute("CREATE TABLE IF NOT EXISTS recycle_bin (id INTEGER PRIMARY KEY AUTOINCREMENT, item_type TEXT NOT NULL, item_title TEXT NOTLink, item_data TEXT NOT NULL, deleted_at TEXT NOT NULL)")

# COLUMN CHECKS
c.execute("PRAGMA table_info(locations)")
if "party_phone" not in [r[1] for r in c.fetchall()]: c.execute("ALTER TABLE locations ADD COLUMN party_phone TEXT")
c.execute("PRAGMA table_info(orders)")
ord_cols = [r[1] for r in c.fetchall()]
if "payment_collected" not in ord_cols: c.execute("ALTER TABLE orders ADD COLUMN payment_collected TEXT DEFAULT '0'")
if "status" not in ord_cols: c.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'Pending'")
c.execute("PRAGMA table_info(users)")
usr_cols = [r[1] for r in c.fetchall()]
if "fullname" not in usr_cols: c.execute("ALTER TABLE users ADD COLUMN fullname TEXT")
if "phone" not in usr_cols: c.execute("ALTER TABLE users ADD COLUMN phone TEXT")
c.execute("PRAGMA table_info(task_assignments)")
task_cols = [r[1] for r in c.fetchall()]
if "sale_amount" not in task_cols: c.execute("ALTER TABLE task_assignments ADD COLUMN sale_amount TEXT DEFAULT '0'")
if "payment_collected_actual" not in task_cols: c.execute("ALTER TABLE task_assignments ADD COLUMN payment_collected_actual TEXT DEFAULT '0'")
conn.commit()

c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
  c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", ("admin", "admin123", "admin", "Admin", "8918740325", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1))
  c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", ("delivery", "user123", "staff", "Delivery Agent", "8918740325", get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1))
  conn.commit()

def move_to_recycle_bin(item_type, item_title, item_data_dict):
    c.execute("INSERT INTO recycle_bin (item_type, item_title, item_data, deleted_at) VALUES (?, ?, ?, ?)",
              (item_type, item_title, json.dumps(item_data_dict), get_ist_time().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

# =========================================================
# PERSISTENT SESSION HANDLING (ROBUST LOGIN PERSISTENCE)
# =========================================================
query_params = st.query_params

if "username" not in st.session_state:
    st.session_state["username"] = "delivery"
    st.session_state["user_role"] = "staff"

# Check localStorage via JS to persist user session across reloads
saved_user_js = streamlit_js_eval(js_expressions="localStorage.getItem('ps_mediseller_user')", key="get_saved_user_storage")
login_user_param = query_params.get("login", None)

target_user = login_user_param if login_user_param else saved_user_js

if target_user:
    c.execute("SELECT fullname, role FROM users WHERE username=?", (target_user,))
    user_row = c.fetchone()
    if user_row:
        st.session_state["username"] = target_user
        st.session_state["user_role"] = user_row[1]
        st.markdown(f"<script>localStorage.setItem('ps_mediseller_user', '{target_user}');</script>", unsafe_allow_html=True)

# JOIN LINK PAGE
if query_params.get("join") == "true":
    st.markdown("## 🤝 Join P. S MEDISELLER Team (এজেন্ট নতুন একাউন্ট)")
    with st.form("agent_public_join_form", clear_on_submit=True):
        j_fname = st.text_input("Full Name (আপনার নাম)")
        j_uname = st.text_input("Username (ইউজারনেম)")
        j_phone = st.text_input("Phone Number (ফোন নম্বর)")
        j_pass = st.text_input("Create Password (পাসওয়ার্ড)", type="password")
        if st.form_submit_button("✅ Submit & Join Team", type="primary"):
            if j_fname.strip() and j_uname.strip() and j_pass.strip():
                try:
                    c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", (j_uname.strip(), j_pass.strip(), "staff", j_fname.strip(), j_phone.strip(), get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1))
                    conn.commit()
                    st.success("Registration successful! You can now use the app.")
                    st.query_params.clear()
                    st.stop()
                except:
                    st.error("Username already exists!")
    st.stop()

# HEADER & TOP CONTROLS
col_ht1, col_ht2 = st.columns([3, 1])
with col_ht1:
  st.markdown(f"""
  <div style="display: flex; align-items: center; gap: 12px;">
      <img src="data:image/jpeg;base64,{logo_b64}" style="width: 52px; height: 52px; border-radius: 10px; object-fit: cover;">
      <div>
          <h1 style="margin: 0; font-size: 19px; color: #38bdf8; font-weight: 700;">P. S MEDISELLER</h1>
          <p style="margin: 2px 0 0 0; color: #cbd5e1; font-size: 11px;">Allopathy & Ayurvedic Wholesaler | Ph: 8918740325</p>
      </div>
  </div>
  """, unsafe_allow_html=True)

with col_ht2:
  if st.session_state["user_role"] == "admin":
    if st.button("🚪 Logout", key="logout_btn"):
      st.session_state["username"] = "delivery"
      st.session_state["user_role"] = "staff"
      st.markdown("<script>localStorage.removeItem('ps_mediseller_user'); window.location.href='./';</script>", unsafe_allow_html=True)
      st.rerun()
  else:
    if st.button("🔐 Admin Login", key="login_btn"):
      st.session_state["show_admin_login"] = True
      st.rerun()

if st.session_state.get("show_admin_login", False):
  with st.form("admin_login_popup_form"):
    st.write("#### 🔑 Admin Login")
    admin_pass = st.text_input("Password", type="password")
    if st.form_submit_button("Login", type="primary"):
      c.execute("SELECT password FROM users WHERE username='admin'")
      adm = c.fetchone()
      if adm and adm[0] == admin_pass:
        st.session_state["username"] = "admin"
        st.session_state["user_role"] = "admin"
        st.session_state["show_admin_login"] = False
        st.markdown("<script>localStorage.setItem('ps_mediseller_user', 'admin');</script>", unsafe_allow_html=True)
        st.rerun()
      else:
        st.error("Incorrect Password!")

st.write("---")

# GPS TRACKER
loc = get_geolocation(component_key="gps_tracker_component")
gps_lat, gps_lon = None, None
if loc and "coords" in loc:
  gps_lat, gps_lon = loc["coords"]["latitude"], loc["coords"]["longitude"]
  c.execute("INSERT OR REPLACE INTO agent_live_locations VALUES (?, ?, ?, ?, COALESCE((SELECT completed_deliveries FROM agent_live_locations WHERE username=?), 0), 0)",
            (st.session_state["username"], gps_lat, gps_lon, get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), st.session_state["username"]))
  conn.commit()

# NAVIGATION MENU
menu_options = [
    "📍 Add Location (লোকেশন যোগ)",
    "🔍 Search & Details (অনুসন্ধান ও বিবরণ)",
    "📦 Pending Orders (বাকি অর্ডার)",
    "📋 Daily & Monthly Work (দৈনিক ও মাসিক কাজ)",
    "📋 Due & Delivery (বকেয়া ও ডেলিভারি)",
    "🗺️ Route Map (রুট ম্যাপ)",
    "📅 Attendance (উপস্থিতি)",
]
if st.session_state["user_role"] == "admin":
  menu_options.extend(["📊 Live Tracking (লাইভ ট্র্যাকিং)", "⚙️ Settings & Agents (সেটিংসে)"])

current_page = query_params.get("page", menu_options[0])
if current_page not in menu_options: current_page = menu_options[0]

selected_menu = st.radio("Menu", menu_options, index=menu_options.index(current_page), horizontal=False, label_visibility="collapsed")
if selected_menu != current_page:
  st.query_params["page"] = selected_menu
  st.rerun()

st.write("---")

# =========================================================
# 1. ADD LOCATION & ORDER
# =========================================================
if selected_menu == "📍 Add Location (লোকেশন যোগ)":
  st.write("### 📍 Add Location & Party")
  with st.form("location_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    p_name = col1.text_input("Party Name")
    p_addr = col2.text_input("Address")
    p_phone = col3.text_input("Phone Number")
    if st.form_submit_button("💾 Save Location", type="primary"):
      if p_name.strip() and p_phone.strip():
        try:
          c.execute("INSERT INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, ?, ?)",
                    (p_name.strip(), p_addr, p_phone.strip(), gps_lat or 22.8620, gps_lon or 87.3320))
          conn.commit()
          st.success("Location saved successfully!")
          st.rerun()
        except:
          st.error("Party already exists!")
      else:
        st.error("Name & Phone required.")

# =========================================================
# 2. SEARCH & DETAILS
# =========================================================
elif selected_menu == "🔍 Search & Details (অনুসন্ধান ও বিবরণ)":
  st.write("### 🔍 Search Party")
  q = st.text_input("Search", label_visibility="collapsed", placeholder="Search parties...")
  df = pd.read_sql_query("SELECT * FROM locations WHERE party_name LIKE ? OR party_phone LIKE ? ORDER BY party_name", conn, params=(f"%{q}%", f"%{q}%"))
  st.dataframe(df, use_container_width=True)

# =========================================================
# 3. PENDING ORDERS
# =========================================================
elif selected_menu == "📦 Pending Orders (বাকি অর্ডার)":
  st.write("### 📦 Active Pending Orders")
  df = pd.read_sql_query("SELECT * FROM orders WHERE status='Pending'", conn)
  if not df.empty:
    for _, row in df.iterrows():
      cols = st.columns([3, 4, 2])
      cols[0].write(f"**{row['party_name']}**")
      cols[1].write(row['order_details'])
      if cols[2].button("✔️ Complete", key=f"ord_{row['id']}"):
        c.execute("UPDATE orders SET status='Completed' WHERE id=?", (row['id'],))
        conn.commit()
        st.success("Completed!")
        st.rerun()
      st.write("---")
  else:
    st.info("No pending orders.")

# =========================================================
# 4. DAILY & MONTHLY WORK
# =========================================================
elif selected_menu == "📋 Daily & Monthly Work (দৈনিক ও মাসিক কাজ)":
  st.write("### 📋 Daily & Monthly Work Report")
  df = pd.read_sql_query("SELECT * FROM daily_work ORDER BY work_date DESC", conn)
  st.dataframe(df, use_container_width=True)

# =========================================================
# 5. DUE & DELIVERY
# =========================================================
elif selected_menu == "📋 Due & Delivery (বকেয়া ও ডেলিভারি)":
  st.markdown('<div class="main-title">Delivery & Due Plan</div>', unsafe_allow_html=True)
  
  c.execute("SELECT username, fullname FROM users")
  all_agents = {r[0]: (r[1] or r[0]) for r in c.fetchall()}
  all_parties = [r[0] for r in c.execute("SELECT party_name FROM locations").fetchall()]

  with st.form("assign_task_form", clear_on_submit=True):
    sel_ag = st.selectbox("Select Agent", list(all_agents.keys()), format_func=lambda x: all_agents[x])
    sel_pt = st.selectbox("Select Party", all_parties if all_parties else ["No Party"])
    col1, col2 = st.columns(2)
    chk_del = col1.checkbox("Delivery")
    chk_due = col2.checkbox("Due Collection")
    d_amt = st.text_input("Due Amount", "0")
    if st.form_submit_button("🎯 Assign Task", type="primary"):
      t_type = " & ".join([t for t, c in [("Delivery", chk_del), ("Due Collection", chk_due)] if c])
      if sel_pt != "No Party" and t_type:
        c.execute("INSERT INTO task_assignments (agent_name, party_name, task_type, due_amount, status, created_at) VALUES (?, ?, ?, ?, 'Pending', ?)",
                  (sel_ag, sel_pt, t_type, d_amt, get_ist_time().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        st.success("Task Assigned!")
        st.rerun()

  st.write("#### Active Tasks")
  tasks = pd.read_sql_query("SELECT * FROM task_assignments WHERE status='Pending'", conn)
  if not tasks.empty:
    for _, row in tasks.iterrows():
      st.write(f"**Party:** {row['party_name']} | **Task:** {row['task_type']} | **Due:** ₹{row['due_amount']}")
      with st.form(f"complete_task_{row['id']}"):
        sale_inp = st.text_input("Total Sale Amount", "0", key=f"sale_{row['id']}")
        pay_inp = st.text_input("Payment Collected", row['due_amount'], key=f"pay_{row['id']}")
        if st.form_submit_button("✔️ Complete Task", type="primary"):
          c.execute("UPDATE task_assignments SET status='Completed', sale_amount=?, payment_collected_actual=? WHERE id=?",
                    (sale_inp, pay_inp, row['id']))
          conn.commit()
          st.success("Completed successfully!")
          st.rerun()

# =========================================================
# 6. ROUTE MAP
# =========================================================
elif selected_menu == "🗺️ Route Map (রুট ম্যাপ)":
  st.write("### 🗺️ Route Map")
  m = folium.Map(location=[gps_lat or 22.8620, gps_lon or 87.3320], zoom_start=13)
  st_folium(m, width="100%", height=450)

# =========================================================
# 7. ATTENDANCE
# =========================================================
elif selected_menu == "📅 Attendance (উপস্থিতি)":
  st.write("### 📅 Attendance")
  if st.button("✅ Check-in Today", type="primary"):
    try:
      c.execute("INSERT INTO attendance VALUES (NULL, ?, ?, ?, 'Present')",
                (st.session_state["username"], get_ist_time().strftime("%Y-%m-%d"), get_ist_time().strftime("%H:%M:%S")))
      conn.commit()
      st.success("Attendance marked!")
    except:
      st.warning("Already checked in today!")

# =========================================================
# 8. LIVE TRACKING
# =========================================================
elif selected_menu == "📊 Live Tracking (লাইভ ট্র্যাকিং)" and st.session_state["user_role"] == "admin":
  st.write("### 📊 Live Agent Tracking")
  st.dataframe(pd.read_sql_query("SELECT * FROM agent_live_locations", conn), use_container_width=True)

# =========================================================
# 9. SETTINGS & AGENTS
# =========================================================
elif selected_menu == "⚙️ Settings & Agents (সেটিংসে)" and st.session_state["user_role"] == "admin":
  st.write("### ⚙️ Settings & Agents")
  st.code(f"https://ps-mediseller-app-gcanjbehuut7h9rzk4xzfg.streamlit.app/?join=true", language="text")
  st.info("Share this link with agents to join easily.")
