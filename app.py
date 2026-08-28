import os
import json
import urllib.parse
import base64
import folium
import pandas as pd
import streamlit as st
from folium.plugins import MousePosition
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation, streamlit_js_eval
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client

# ==========================================
# 1. SERVER CONFIGURATION & PAGE SETUP
# ==========================================
os.makedirs(".streamlit", exist_ok=True)
with open(".streamlit/config.toml", "w") as f:
    f.write("[server]\nmaxUploadSize = 1024\n")

st.set_page_config(
    page_title="P. S MEDISELLER Allopathy & Ayurvedic Wholesaler",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def get_ist_time():
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist_offset)

def format_date_display(date_str):
    if not date_str:
        return
    try:
        cleaned = str(date_str).strip()
        if " " in cleaned:
            dt = datetime.strptime(cleaned.split(" ")[0], "%Y-%m-%d")
        else:
            dt = datetime.strptime(cleaned, "%Y-%m-%d")
        return dt.strftime("%d.%m.%y")
    except Exception:
        return date_str

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

# ==========================================
# 3. DATABASE SETUP & INITIALIZATION (SUPABASE)
# ==========================================
# Streamlit Secrets থেকে Supabase URL ও Key নিরাপদে রিড করা
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_URL.startswith("https://"):
        st.error("⚠️ Invalid or missing SUPABASE_URL in Streamlit Secrets! Please check Secrets settings.")
        st.stop()
    if not SUPABASE_KEY:
        st.error("⚠️ Missing SUPABASE_KEY in Streamlit Secrets! Please check Secrets settings.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# Initial Default Users Check in Supabase
try:
    res = supabase.table("users").select("username").eq("username", "admin").execute()
    if not res.data:
        supabase.table("users").insert({
            "username": "admin",
            "password": "admin123",
            "role": "admin",
            "fullname": "Admin",
            "phone": "8918740325",
            "created_at": get_ist_time().strftime("%Y-%m-%d %H:%M:%S"),
            "is_active": 1,
            "allow_resubmit": 1
        }).execute()
        
    res_staff = supabase.table("users").select("username").eq("username", "staff").execute()
    if not res_staff.data:
        supabase.table("users").insert({
            "username": "staff",
            "password": "user123",
            "role": "staff",
            "fullname": "Staff Agent",
            "phone": "8918740325",
            "created_at": get_ist_time().strftime("%Y-%m-%d %H:%M:%S"),
            "is_active": 1,
            "allow_resubmit": 0
        }).execute()
except Exception as e:
    pass

def move_to_recycle_bin(item_type, item_title, item_data_dict):
    data_json = json.dumps(item_data_dict)
    deleted_at = get_ist_time().strftime("%Y-%m-%d %H:%M:%S")
    supabase.table("recycle_bin").insert({
        "item_type": item_type,
        "item_title": item_title,
        "item_data": data_json,
        "deleted_at": deleted_at
    }).execute()

# Automatic Cleanup Logic (Supabase integration)
try:
    current_dt_str = get_ist_time()
    orders_data = supabase.table("orders").select("id, order_date").execute().data
    for row_ord in orders_data:
        try:
            cleaned_date = str(row_ord.get("order_date")).strip()
            if " " in cleaned_date:
                o_time = datetime.strptime(cleaned_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
            else:
                o_time = datetime.strptime(cleaned_date, "%Y-%m-%d").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
            if (current_dt_str - o_time) > timedelta(days=7):
                supabase.table("orders").delete().eq("id", row_ord["id"]).execute()
        except Exception:
            pass

    tasks_data = supabase.table("task_assignments").select("id, created_at, status").execute().data
    for row_task in tasks_data:
        try:
            t_status = str(row_task.get("status")).strip().lower() if row_task.get("status") else ""
            if t_status == "completed":
                cleaned_task_date = str(row_task.get("created_at")).strip()
                if " " in cleaned_task_date:
                    t_time = datetime.strptime(cleaned_task_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
                else:
                    t_time = datetime.strptime(cleaned_task_date, "%Y-%m-%d").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
                if (current_dt_str - t_time) > timedelta(hours=48):
                    supabase.table("task_assignments").delete().eq("id", row_task["id"]).execute()
        except Exception:
            pass
except Exception as e:
    pass

# ==========================================
# 4. CUSTOM STYLING & PWA INJECTION
# ==========================================
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

mandatory_location_html = """
<div id="loc-overlay" style="display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(15, 23, 42, 0.98); z-index: 999999; justify-content: center; align-items: center; padding: 20px; box-sizing: border-box; font-family: 'Poppins', sans-serif;">
    <div style="background: #1e293b; border: 2px solid #ef4444; border-radius: 16px; padding: 30px; max-width: 450px; width: 100%; text-align: center; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
        <div style="font-size: 48px; margin-bottom: 15px;">📍</div>
        <h2 style="color: #f87171; margin-top: 0; font-size: 22px;">Location Permission Required<br> (লোকেশন পারমিশন আবশ্যক)</h2>
        <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin-bottom: 25px;">
            P.S Mediseller app requires your live GPS location to function properly. Please enable Location/GPS on your device and grant permission.<br><br>
            <b> (অ্যাপটি ব্যবহারের জন্য আপনার ফোনের জিপিএস লোকেশন অন করুন এবং পারমিশন দিন। লোকেশন বন্ধ রাখলে অ্যাপ ব্যবহার করা যাবে না।)</b>
        </p>
        <button onclick="requestLocation()" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border: none; padding: 14px 28px; border-radius: 10px; font-weight: bold; font-size: 16px; cursor: pointer; width: 100%; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);">
            Grant Permission / Retry (অনুমতি দিন/রিফ্রেশ)
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
        status.innerText = "Requesting location permission... (অনুমতি নেওয়া হচ্ছে...)";
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

# ==========================================
# 5. USER SESSION & AUTHENTICATION (SAFE FIX)
# ==========================================
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

user_row = None
try:
    user_res = supabase.table("users").select("fullname, role, is_active").eq("username", target_login).execute()
    if user_res.data:
        user_row = user_res.data[0]
except Exception as e:
    pass

if user_row:
    f_name = user_row.get("fullname")
    r_role = user_row.get("role")
    is_active = user_row.get("is_active", 1)
    if is_active == 0:
        st.warning("আপনার একাউন্টটি ব্লক করা হয়েছে। অনুগ্রহ করে অ্যাডমিনের সাথে যোগাযোগ করুন।")
        st.markdown("<script>localStorage.removeItem('ps_mediseller_user');</script>", unsafe_allow_html=True)
        st.query_params.clear()
        st.stop()
    else:
        st.session_state["username"] = target_login
        st.session_state["user_role"] = r_role if r_role else "staff"
        st.query_params["login"] = target_login
        st.markdown(f"<script>localStorage.setItem('ps_mediseller_user', '{target_login}');</script>", unsafe_allow_html=True)
else:
    st.session_state["username"] = target_login
    st.session_state["user_role"] = "admin" if target_login == "admin" else "staff"
    st.query_params["login"] = target_login

# Default state variables
if "selected_lat" not in st.session_state:
    st.session_state["selected_lat"] = 22.8620
if "selected_lon" not in st.session_state:
    st.session_state["selected_lon"] = 87.3320

# Active User Check
current_logged_username = st.session_state["username"]
if current_logged_username != "admin":
    res_act_data = supabase.table("users").select("is_active").eq("username", current_logged_username).execute().data
    if res_act_data and res_act_data[0].get("is_active") == 0:
        st.error("আপনার একাউন্টটি অ্যাডমিন কর্তৃক ব্লক (Block) করা হয়েছে। আপনি এই অ্যাপটি ব্যবহার করতে পারবেন না।")
        st.stop()

# ==========================================
# 6. MAIN APP UI / HEADER
# ==========================================
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

curr_user_data = supabase.table("users").select("fullname").eq("username", st.session_state['username']).execute().data
if curr_user_data and curr_user_data[0].get("fullname"):
    display_user_name = curr_user_data[0].get("fullname")
else:
    display_user_name = st.session_state['username']

col_u1, col_u2 = st.columns([3, 1])
with col_u1:
    st.markdown(f"<h3 style='color: #0ea5e9; font-weight: 600; margin-bottom: 0;'>{display_user_name}</h3>", unsafe_allow_html=True)

# Notifications
pending_ord_count = len(supabase.table("orders").select("id", count="exact").eq("status", "Pending").execute().data)
pending_task_count = len(supabase.table("task_assignments").select("id", count="exact").eq("status", "Pending").execute().data)
total_pending_items = pending_ord_count + pending_task_count

show_notif = True
if "notif_dismissed_time" in st.session_state:
    time_diff = (get_ist_time() - st.session_state["notif_dismissed_time"]).total_seconds()
    if time_diff < 3600:
        show_notif = False

if show_notif and total_pending_items > 0:
    col_n1, col_n2 = st.columns([5, 1])
    with col_n1:
        st.warning("⚠️ **নোটিফিকেশন:** আপনার অর্ডার পেন্ডিং বা ডিউ পেন্ডিং রয়েছে। **পেন্ডিং Order খাতায় তুলতে বাকি!**")
    with col_n2:
        if st.button("সরান", key="dismiss_notif_bar_btn"):
            st.session_state["notif_dismissed_time"] = get_ist_time()
            st.rerun()

# Admin Login Modal / Form
if st.session_state.get("show_admin_login", False):
    with st.form("admin_login_popup_form"):
        st.write("#### Admin Login (অ্যাডমিন লগইন)")
        admin_pass_input = st.text_input("Enter Admin Password (পাসওয়ার্ড দিন)", type="password")
        col_al1, col_al2 = st.columns(2)
        with col_al1:
            submit_admin = st.form_submit_button("Login (লগইন)", type="primary")
        with col_al2:
            cancel_admin = st.form_submit_button("Cancel (বাতিল)")
        
        if submit_admin:
            adm_res = supabase.table("users").select("password, role").eq("username", "admin").execute().data
            adm_row = adm_res[0] if adm_res else None
            if adm_row and adm_row.get("password") == admin_pass_input:
                st.session_state["username"] = "admin"
                st.session_state["user_role"] = "admin"
                st.session_state["show_admin_login"] = False
                st.query_params["login"] = "admin"
                st.markdown("<script>localStorage.setItem('ps_mediseller_user', 'admin');</script>", unsafe_allow_html=True)
                st.success("Admin login successful! (সফল!)")
                st.rerun()
            else:
                st.error("Incorrect Password! (ভুল পাসওয়ার্ড!)")
        
        if cancel_admin:
            st.session_state["show_admin_login"] = False
            st.rerun()

    with st.expander("পাসওয়ার্ড ভুলে গেছেন? (Forgot Password)"):
        st.info("অ্যাডমিন পাসওয়ার্ড রিসেট করতে মাস্টার কোড ব্যবহার করুন। (Master Code: PSMEDISELLER)")
        master_code = st.text_input("Master Code (মাস্টার কোড)", type="password")
        new_admin_pass = st.text_input("New Admin Password", type="password")
        if st.button("Reset Admin Password (রিসেট করুন)"):
            if master_code == "PSMEDISELLER" and new_admin_pass.strip():
                supabase.table("users").update({"password": new_admin_pass.strip()}).eq("username", "admin").execute()
                st.success("পাসওয়ার্ড সফলভাবে রিসেট হয়েছে! (Password Reset Successful!)")
            else:
                st.error("ভুল কোড বা পাসওয়ার্ড! (Invalid Code or Password!)")

# ==========================================
# 7. GPS LOCATION TRACKER (BACKGROUND)
# ==========================================
loc = get_geolocation(component_key="hidden_background_gps_tracker")
gps_lat, gps_lon = None, None
if loc and "coords" in loc:
    gps_lat = loc["coords"]["latitude"]
    gps_lon = loc["coords"]["longitude"]

if gps_lat and gps_lon:
    now_time = get_ist_time().strftime("%Y-%m-%d %H:%M:%S")
    update_res = supabase.table("agent_live_locations").update({
        "lat": gps_lat,
        "lon": gps_lon,
        "last_updated": now_time
    }).eq("username", st.session_state["username"]).execute()
    
    if not update_res.data:
        supabase.table("agent_live_locations").insert({
            "username": st.session_state["username"],
            "lat": gps_lat,
            "lon": gps_lon,
            "last_updated": now_time
        }).execute()

# ==========================================
# PAGE 2: MENU & LOCATION / PARTY MANAGEMENT
# ==========================================

# --- Menu Setup
all_basic_menus = [
    "Add Location (লোকেশন যোগ)",
    "Search & Details (অনুসন্ধান ও বিবরণ)",
    "Pending Orders (বাকি অর্ডার)",
    "Daily & Monthly Work (দৈনিক ও মাসিক কাজ)",
    "Due & Delivery (বকেয়া ও ডেলিভারি)",
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
        res = supabase.table("users").select("allowed_menus").eq("username", username).execute()
        row = res.data[0] if res.data else None
        if row and row.get("allowed_menus"):
            menu_options = [m.strip() for m in row["allowed_menus"].split(",") if m.strip() in all_basic_menus]
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

# GPS Component Setup (একেবারে শক্তিশালী ও নির্ভুল GPS সিস্টেম)
@st.cache_resource
def get_gps_component():
    import tempfile
    import streamlit.components.v1 as components
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
status.innerText = `Try ${attempts}... (Acc: ${Math.round(pos.coords.accuracy)}m)`;
if (attempts < 3 && pos.coords.accuracy > 20) {
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
{ enableHighAccuracy: true, timeout: 10000, maximumAge: 0}
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

# ==========================================
# PAGE LOGIC: ADD LOCATION
# ==========================================
if selected_menu == "Add Location (লোকেশন যোগ)":
    st.write("### Add Location & Party (লোকেশন ও পার্টি)")
    
    # Supabase implementation for fetching routes
    routes_res = supabase.table("routes").select("route_name").order("route_name", desc=False).execute()
    existing_routes = [r["route_name"] for r in routes_res.data] if routes_res.data else []

    if st.session_state.get("user_role") == "admin":
        with st.expander("🛠️ Admin: Manage Routes (রুট ম্যানেজ করুন)"):
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
                        chk = supabase.table("routes").select("route_name").eq("route_name", new_route_admin.strip()).execute()
                        if not chk.data:
                            supabase.table("routes").insert({"route_name": new_route_admin.strip()}).execute()
                            st.success("Route saved! (সেভ হয়েছে)")
                            st.rerun()
                        else:
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
                        chk = supabase.table("routes").select("route_name").eq("route_name", updated_route_name.strip()).execute()
                        if chk.data:
                            st.error("This route name already exists! (এই নামটি আগেই আছে)")
                        else:
                            supabase.table("routes").update({"route_name": updated_route_name.strip()}).eq("route_name", route_to_edit).execute()
                            supabase.table("locations").update({"route": updated_route_name.strip()}).eq("route", route_to_edit).execute()
                            st.success(f"Route updated to '{updated_route_name.strip()}' successfully! (সব পার্টিতে আপডেট হয়েছে)")
                            st.rerun()
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
                        supabase.table("routes").delete().eq("route_name", route_to_delete).execute()
                        st.success(f"Route deleted! ({route_to_delete} রুটটি ডিলিট হয়েছে)")
                        st.rerun()
                    else:
                        st.error("Select a route! (একটি রুট সিলেক্ট করুন)")

        # Re-fetch after updates
        routes_res = supabase.table("routes").select("route_name").order("route_name", desc=False).execute()
        existing_routes = [r["route_name"] for r in routes_res.data] if routes_res.data else []

    selected_entry_tab = st.radio(
        "Select Entry Mode (মোড সিলেক্ট):",
        [
            "With Map Party (ম্যাপ সহ পার্টি)",
            "Without Map Party (ম্যাপ ছাড়া পার্টি)"
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

            submitted_loc = st.form_submit_button("💾 Save Location (সেভ করুন)", type="primary")

            if submitted_loc:
                if p_name.strip() and p_phone.strip():
                    chk_p = supabase.table("locations").select("id").ilike("party_name", p_name.strip()).execute()
                    chk_ph = supabase.table("locations").select("id").eq("party_phone", p_phone.strip()).execute()
                    
                    if chk_p.data or chk_ph.data:
                        st.error("Party name or phone already exists! (ইতিমধ্যে সেভ করা আছে!)")
                    else:
                        final_route = p_route_new.strip() if p_route_new.strip() else p_route_sel
                        if final_route:
                            r_chk = supabase.table("routes").select("route_name").eq("route_name", final_route).execute()
                            if not r_chk.data:
                                supabase.table("routes").insert({"route_name": final_route}).execute()

                        current_date_str = get_ist_time().strftime("%Y-%m-%d")

                        supabase.table("locations").insert({
                            "party_name": p_name.strip(),
                            "address": p_addr,
                            "party_phone": p_phone.strip(),
                            "lat": st.session_state["selected_lat"],
                            "lon": st.session_state["selected_lon"],
                            "route": final_route
                        }).execute()

                        supabase.table("daily_work").insert({
                            "party_name": p_name.strip(),
                            "activity_type": "Visit (ভিজিট)",
                            "work_date": current_date_str
                        }).execute()

                        st.success("Location saved and visit recorded successfully! (সেভ হয়েছে!)")
                        st.rerun()
                else:
                    st.error("Party name and phone required. (নাম ও ফোন আবশ্যক।)")

    else:
        with st.form("doctor_details_form", clear_on_submit=True):
            st.write("#### 2. Without Map Party Details (ম্যাপ ছাড়া পার্টির বিবরণ)")
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

            submitted_doc = st.form_submit_button("💾 Save Without Map Party (সেভ করুন)", type="primary")

            if submitted_doc:
                if doc_name.strip() and doc_phone.strip():
                    chk_p = supabase.table("locations").select("id").ilike("party_name", doc_name.strip()).execute()
                    chk_ph = supabase.table("locations").select("id").eq("party_phone", doc_phone.strip()).execute()

                    if chk_p.data or chk_ph.data:
                        st.error("Party name or phone already exists! (ইতিমধ্যে সেভ করা আছে!)")
                    else:
                        final_doc_route = doc_route_new.strip() if doc_route_new.strip() else doc_route_sel
                        if final_doc_route:
                            r_chk = supabase.table("routes").select("route_name").eq("route_name", final_doc_route).execute()
                            if not r_chk.data:
                                supabase.table("routes").insert({"route_name": final_doc_route}).execute()

                        supabase.table("locations").insert({
                            "party_name": doc_name.strip(),
                            "address": doc_addr,
                            "party_phone": doc_phone.strip(),
                            "lat": None,
                            "lon": None,
                            "route": final_doc_route
                        }).execute()

                        supabase.table("daily_work").insert({
                            "party_name": doc_name.strip(),
                            "activity_type": "Visit (ভিজিট)",
                            "work_date": get_ist_time().strftime("%Y-%m-%d")
                        }).execute()

                        st.success("Saved successfully! (সফলভাবে সেভ হয়েছে!)")
                        st.rerun()
                else:
                    st.error("Name and phone required. (নাম ও ফোন আবশ্যক।)")

    st.write("---")
    st.write("#### Select Location from Map (ম্যাপ থেকে সিলেক্ট করুন)")
    col_m1, col_m2 = st.columns([1, 4])
    with col_m1:
        gps_comp = get_gps_component()
        gps_data = gps_comp(key="gps_fetcher_btn")

        if gps_data and isinstance(gps_data, dict) and "lat" in gps_data:
            if st.session_state.get("last_processed_gps") != gps_data:
                st.session_state["last_processed_gps"] = gps_data
                new_lat, new_lon = float(gps_data["lat"]), float(gps_data["lon"])
                if round(st.session_state.get("selected_lat", 0), 6) != round(new_lat, 6) or round(st.session_state.get("selected_lon", 0), 6) != round(new_lon, 6):
                    st.session_state["selected_lat"] = new_lat
                    st.session_state["selected_lon"] = new_lon
                    st.session_state["gps_lat"] = new_lat
                    st.session_state["gps_lon"] = new_lon
                    st.toast("High-accuracy GPS location taken! (লোকেশন নেওয়া হয়েছে!)", icon="📍")
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
        popup="<b>Selected Point (নির্বাচিত পয়েন্ট)</b>",
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
        separator=" | ",
        prefix="Lat/Lng: ",
        lat_formatter=formatter,
        lng_formatter=formatter
    ).add_to(advanced_map)

    folium.LayerControl().add_to(advanced_map)

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
        # Fetch matching parties using Supabase logic
        res_loc = supabase.table("locations").select("party_name").or_(
            f"party_name.ilike.{q_term},address.ilike.{q_term},party_phone.ilike.{q_term}"
        ).order("party_name", desc=False).execute()
    else:
        res_loc = supabase.table("locations").select("party_name").order("party_name", desc=False).execute()

    filtered_parties_list = [r["party_name"] for r in res_loc.data] if res_loc.data else []

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
            st.warning("No matching party found! (কোনো পার্টি পাওয়া যায়নি!)")
            selected_order_party_native = ""

    with st.form("order_visit_entry_form", clear_on_submit=True):
        ord_details = st.text_area("Order Details (অর্ডার বিবরণ)")
        col_ob1, col_ob2 = st.columns(2)
        with col_ob1:
            submitted_order = st.form_submit_button("Submit Order (অর্ডার জমা)", type="primary")
        with col_ob2:
            submitted_visit = st.form_submit_button("💾 Save Visit (ভিজিট সেভ)")

        if submitted_order:
            if not selected_order_party_native or not str(selected_order_party_native).strip():
                st.error("Please select a party. (পার্টি সিলেক্ট করুন।)")
            else:
                current_date_str = get_ist_time().strftime("%Y-%m-%d")
                supabase.table("orders").insert({
                    "party_name": str(selected_order_party_native).strip(),
                    "order_details": ord_details.strip(),
                    "order_date": get_ist_time().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "Pending",
                    "payment_collected": "0"
                }).execute()

                supabase.table("daily_work").insert({
                    "party_name": str(selected_order_party_native).strip(),
                    "activity_type": "Order (অর্ডার)",
                    "work_date": current_date_str
                }).execute()

                st.session_state["order_party_search_text_input_key"] = ""
                st.success("Order submitted successfully! (জমা দেওয়া হয়েছে!)")
                st.rerun()

        if submitted_visit:
            if not selected_order_party_native or not str(selected_order_party_native).strip():
                st.error("Please select a party. (পার্টি সিলেক্ট করুন।)")
            else:
                current_date_str = get_ist_time().strftime("%Y-%m-%d")
                supabase.table("daily_work").insert({
                    "party_name": str(selected_order_party_native).strip(),
                    "activity_type": "Visit (ভিজিট)",
                    "work_date": current_date_str
                }).execute()

                st.session_state["order_party_search_text_input_key"] = ""
                st.success("Visit saved successfully! (সেভ হয়েছে!)")
                st.rerun()

    st.write("---")
    with st.expander("📊 Recent Orders & Visits (সাম্প্রতিক রিপোর্ট) Click to Open", expanded=False):
        rep_res = supabase.table("daily_work").select("party_name, activity_type, work_date").order("work_date", desc=True).limit(20).execute()
        report_df = pd.DataFrame(rep_res.data) if rep_res.data else pd.DataFrame()

        if not report_df.empty:
            report_df.rename(columns={
                "party_name": "Party Name",
                "activity_type": "Activity Type",
                "work_date": "Work Date"
            }, inplace=True)

            if st.session_state.get("user_role") == "admin":
                full_rep = supabase.table("daily_work").select("party_name, activity_type, work_date").order("work_date", desc=True).execute()
                full_report_df = pd.DataFrame(full_rep.data) if full_rep.data else pd.DataFrame()
                if not full_report_df.empty:
                    full_report_df.rename(columns={
                        "party_name": "Party Name",
                        "activity_type": "Activity Type",
                        "work_date": "Work Date"
                    }, inplace=True)

                html_all_report = generate_html_report("Daily Work & Visit Report", full_report_df)
                st.download_button(
                    label="📥 Download Daily Work Report (PDF/HTML)",
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

# ==========================================
# PAGE LOGIC: SEARCH & DETAILS
# ==========================================
elif selected_menu == "Search & Details (অনুসন্ধান ও বিবরণ)":
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
            if st.button("💾 Save Location (সেভ করুন)", type="primary", key="save_party_map_ok"):
                target_id = st.session_state["mapping_party_id"]
                t_lat = st.session_state["temp_map_lat"]
                t_lon = st.session_state["temp_map_lon"]

                supabase.table("locations").update({
                    "lat": t_lat,
                    "lon": t_lon
                }).eq("id", target_id).execute()

                st.session_state.pop("mapping_party_id", None)
                st.session_state.pop("mapping_party_name", None)
                st.success("Map saved successfully! (সেভ হয়েছে!)")
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
        res_e = supabase.table("locations").select("*").eq("id", edit_id).execute()
        edit_data_df = pd.DataFrame(res_e.data) if res_e.data else pd.DataFrame()

        if not edit_data_df.empty:
            e_row = edit_data_df.iloc[0]
            st.markdown(f"""
            <div style='background: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 20px;'>
                <h4 style='margin-top: 0; color: #ffffff;'>Edit Party Details: <span style='color: #60a5fa;'>{e_row['party_name']}</span></h4>
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
                    supabase.table("locations").update({
                        "party_name": new_party_name,
                        "party_phone": new_party_phone,
                        "address": new_address,
                        "route": new_route
                    }).eq("id", edit_id).execute()

                    st.session_state.pop("editing_party_id", None)
                    st.success("Party details updated successfully! (সফলভাবে আপডেট করা হয়েছে!)")
                    st.rerun()

                if cancel_edit:
                    st.session_state.pop("editing_party_id", None)
                    st.rerun()

            st.markdown("---")

# ==========================================
# PAGE 3: SEARCH, ORDERS, WORK & DUE SYSTEM
# ==========================================

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
    res = supabase.table("locations").select("*").or_(
        f"party_name.ilike.{q_term},address.ilike.{q_term},party_phone.ilike.{q_term}"
    ).order("party_name", desc=False).execute()
else:
    res = supabase.table("locations").select("*").order("party_name", desc=False).execute()

df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

# 3. Admin Report Download Button
if st.session_state.get("user_role") == "admin" and not df.empty:
    report_data_df = df[["party_name", "address", "party_phone"]].rename(columns={
        "party_name": "Party Name",
        "address": "Address",
        "party_phone": "Phone"
    })
    html_locs_df = generate_html_report("Locations & Parties Directory", report_data_df)
    st.download_button(
        label="📥 Download Locations Report (PDF/HTML)",
        data=html_locs_df,
        file_name="mediseller_locations_report.html",
        mime="text/html",
        type="primary"
    )
    st.write("---")

if not df.empty:
    doc_df = df[df["lat"].isna() | df["lon"].isna()]
    mapped_df = df[df["lat"].notna() & df["lon"].notna()]
else:
    doc_df = pd.DataFrame()
    mapped_df = pd.DataFrame()

is_searching = bool(master_search_query.strip())

# 4. Non-Map List Expander
with st.expander(f"📍 Non-Map List ({len(doc_df)} Entries) (ম্যাপবিহীন তালিকা)", expanded=is_searching):
    if not doc_df.empty:
        for index, row in doc_df.iterrows():
            cols = st.columns([2.5, 1.8, 2, 1.5, 1.5, 1.2] if st.session_state.get("user_role") == "admin" else [3, 2, 2, 2])
            cols[0].markdown(f"**{row['party_name']}**")
            cols[1].markdown(f"📞 {row['party_phone']}" if row['party_phone'] else "No number")
            cols[2].markdown(f"🏠 {row['address']}" if row['address'] else "No address")

            if st.session_state.get("user_role") == "admin":
                if cols[3].button("Edit", key=f"edit_doc_search_{row['id']}"):
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
                    supabase.table("locations").delete().eq("id", row['id']).execute()
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
        st.info("No non-map parties found. (ম্যাপবিহীন পার্টি নেই।)")

st.write("---")

# 5. Mapped List Expander
with st.expander(f"🗺️ Mapped List ({len(mapped_df)} Records) (ম্যাপযুক্ত তালিকা)", expanded=is_searching):
    if not mapped_df.empty:
        for index, row in mapped_df.iterrows():
            if st.session_state.get("user_role") == "admin":
                cols = st.columns([2.5, 1.8, 2, 1.5, 1.5, 1.2])
            else:
                cols = st.columns([3, 2, 2, 2])

            cols[0].markdown(f"**{row['party_name']}**")
            cols[1].markdown(f"📞 {row['party_phone']}" if row['party_phone'] else "No number")
            cols[2].markdown(f"🏠 {row['address']}" if row['address'] else "No address")

            maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}"

            if st.session_state.get("user_role") == "admin":
                cols[3].markdown(f'<a href="{maps_url}" target="_blank" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border:none; padding:6px 12px; border-radius: 6px; cursor:pointer; font-weight:600;">Direction</button></a>', unsafe_allow_html=True)
                
                if cols[4].button("Edit", key=f"edit_loc_search_{row['id']}"):
                    st.session_state["editing_party_id"] = row['id']
                    st.rerun()

                if cols[5].button("Delete", key=f"del_loc_search_{row['id']}"):
                    move_to_recycle_bin("Location", row['party_name'], dict(row))
                    supabase.table("locations").delete().eq("id", row['id']).execute()
                    st.success("Moved to Recycle Bin!")
                    st.rerun()
            else:
                cols[3].markdown(f'<a href="{maps_url}" target="_blank" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border:none; padding:6px 12px; border-radius: 6px; cursor:pointer; font-weight: 600;">Direction (ডিরেকশন)</button></a>', unsafe_allow_html=True)
    else:
        st.info("No mapped parties found. (ম্যাপযুক্ত পার্টি নেই।)")

# 6. Route-wise Party Management (রুট ওয়াইস পার্টি)
st.write("---")
st.markdown("### 🛣️ Route-wise Party (রুট অনুযায়ী পার্টি)")

try:
    r_res = supabase.table("locations").select("route").not_.is_("route", "null").order("route", desc=False).execute()
    routes = sorted(list(set([r["route"] for r in r_res.data if r.get("route") and r["route"].strip() != ""])))
except Exception:
    routes = []

routes.insert(0, "-- Select Route (রুট নির্বাচন করুন) --")
selected_route = st.selectbox("Select Route (রুট নির্বাচন করুন):", routes, key="route_selector_advanced")

if selected_route and selected_route != "-- Select Route (রুট নির্বাচন করুন) --":
    res_r_parties = supabase.table("locations").select("*").eq("route", selected_route).order("party_name", desc=False).execute()
    route_df = pd.DataFrame(res_r_parties.data) if res_r_parties.data else pd.DataFrame()

    if not route_df.empty:
        route_doc_df = route_df[route_df["lat"].isna() | route_df["lon"].isna()]
        route_mapped_df = route_df[route_df["lat"].notna() & route_df["lon"].notna()]
    else:
        route_doc_df = pd.DataFrame()
        route_mapped_df = pd.DataFrame()

    # Route Non-Map List
    with st.expander(f"📍 {selected_route} Non-Map List ({len(route_doc_df)} Entries) (ম্যাপবিহীন তালিকা)", expanded=True):
        if not route_doc_df.empty:
            for index, row in route_doc_df.iterrows():
                cols = st.columns([2.5, 1.8, 2, 1.5, 1.5, 1.2] if st.session_state.get("user_role") == "admin" else [3, 2, 2, 2])
                cols[0].markdown(f"**{row['party_name']}**")
                cols[1].markdown(f"📞 {row['party_phone']}" if row['party_phone'] else "No number")
                cols[2].markdown(f"🏠 {row['address']}" if row['address'] else "No address")

                if st.session_state.get("user_role") == "admin":
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
                        supabase.table("locations").delete().eq("id", row['id']).execute()
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
            st.info("এই রুটে ম্যাপবিহীন কোনো পার্টি নেই।")

    # Route Mapped List
    with st.expander(f"🗺️ {selected_route} Mapped List ({len(route_mapped_df)} Records) (ম্যাপযুক্ত তালিকা)", expanded=True):
        if not route_mapped_df.empty:
            for index, row in route_mapped_df.iterrows():
                if st.session_state.get("user_role") == "admin":
                    cols = st.columns([2.5, 1.8, 2, 1.5, 1.5, 1.2])
                else:
                    cols = st.columns([3, 2, 2, 2])

                cols[0].markdown(f"**{row['party_name']}**")
                cols[1].markdown(f"📞 {row['party_phone']}" if row['party_phone'] else "No number")
                cols[2].markdown(f"🏠 {row['address']}" if row['address'] else "No address")

                maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}"

                if st.session_state.get("user_role") == "admin":
                    cols[3].markdown(f'<a href="{maps_url}" target="_blank" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor:pointer; font-weight: 600;">Direction</button></a>', unsafe_allow_html=True)
                    if cols[4].button("✏️ Edit", key=f"edit_loc_route_{row['id']}"):
                        st.session_state["editing_party_id"] = row['id']
                        st.rerun()
                    if cols[5].button("Delete", key=f"del_loc_route_{row['id']}"):
                        move_to_recycle_bin("Location", row['party_name'], dict(row))
                        supabase.table("locations").delete().eq("id", row['id']).execute()
                        st.success("Moved to Recycle Bin!")
                        st.rerun()
                else:
                    cols[3].markdown(f'<a href="{maps_url}" target="_blank" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor:pointer; font-weight:600;">Direction (ডিরেকশন)</button></a>', unsafe_allow_html=True)
        else:
            st.info("এই রুটে ম্যাপযুক্ত কোনো পার্টি নেই।")

# ==========================================
# PAGE LOGIC: PENDING ORDERS
# ==========================================
elif selected_menu == "Pending Orders (বাকি অর্ডার)":
    st.write("### Orders Management (অর্ডার ম্যানেজমেন্ট)")

    if st.session_state.get("user_role") == "admin":
        ord_tab1, ord_tab2 = st.tabs(["⏳ Pending Orders (পেন্ডিং)", "✅ Completed History (সম্পন্ন অর্ডার)"])
    else:
        ord_tab1 = st.container()
        ord_tab2 = None

    with ord_tab1:
        st.write("#### Active Pending Orders")
        if st.session_state.get("user_role") == "admin":
            res_p_ord = supabase.table("orders").select("party_name, order_details, order_date").eq("status", "Pending").order("order_date", desc=True).execute()
            all_ord_df = pd.DataFrame(res_p_ord.data) if res_p_ord.data else pd.DataFrame()
            if not all_ord_df.empty:
                all_ord_df.rename(columns={
                    "party_name": "Party Name",
                    "order_details": "Order Details",
                    "order_date": "Order Date"
                }, inplace=True)
                html_ord_report = generate_html_report("Pending Orders Report", all_ord_df)
                st.download_button(
                    label="📥 Download Pending Orders Report (PDF/HTML)",
                    data=html_ord_report,
                    file_name="mediseller_pending_orders_report.html",
                    mime="text/html",
                    type="primary"
                )
                st.write("---")

        res_orders = supabase.table("orders").select("*").eq("status", "Pending").order("order_date", desc=True).execute()
        orders_df = pd.DataFrame(res_orders.data) if res_orders.data else pd.DataFrame()

        if not orders_df.empty:
            for index, row in orders_df.iterrows():
                cols = st.columns([2, 4, 2, 2])
                cols[0].write(f"**{row['party_name']}**")
                cols[1].write(row['order_details'])
                cols[2].write("⏳ Pending (পেন্ডিং)")
                if cols[3].button("✅ Complete (কমপ্লিট)", key=f"ord_btn_{row['id']}"):
                    supabase.table("orders").update({"status": "Completed"}).eq("id", row['id']).execute()

                    # Increment completed delivery count logic
                    curr_user = st.session_state.get("username")
                    if curr_user:
                        a_res = supabase.table("agent_live_locations").select("completed_deliveries").eq("username", curr_user).execute()
                        if a_res.data:
                            curr_count = a_res.data[0].get("completed_deliveries", 0) or 0
                            supabase.table("agent_live_locations").update({"completed_deliveries": curr_count + 1}).eq("username", curr_user).execute()

                    st.success("Order completed! (কমপ্লিট করা হয়েছে!)")
                    st.rerun()
        else:
            st.info("No pending orders. (পেন্ডিং অর্ডার নেই।)")

    if ord_tab2 is not None:
        with ord_tab2:
            st.write("#### Completed Orders History")
            res_comp = supabase.table("orders").select("*").eq("status", "Completed").order("order_date", desc=True).execute()
            completed_ord_df = pd.DataFrame(res_comp.data) if res_comp.data else pd.DataFrame()

            if not completed_ord_df.empty:
                if st.session_state.get("user_role") == "admin":
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
                            for idx, r in completed_ord_df.iterrows():
                                move_to_recycle_bin("Order", r['party_name'], dict(r))
                            supabase.table("orders").delete().eq("status", "Completed").execute()
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
                            supabase.table("orders").delete().eq("id", row['id']).execute()
                            st.success("Moved to Recycle Bin!")
                            st.rerun()
            else:
                st.info("No completed orders history.")

# ==========================================
# PAGE LOGIC: DAILY & MONTHLY WORK
# ==========================================
elif selected_menu == "Daily & Monthly Work (দৈনিক ও মাসিক কাজ)":
    st.write("### Daily & Monthly Work Report (দৈনিক ও মাসিক কাজের রিপোর্ট)")

    work_tab1, work_tab2 = st.tabs([
        "📅 Daily Work (দৈনিক কাজ)",
        "📊 Monthly Summary & Zero Activity (মাসিক সামারি ও জিরো অ্যাক্টিভিটি)"
    ])

    with work_tab1:
        st.write("#### Visit & Order List (তারিখ অনুযায়ী)")
        if st.session_state.get("user_role") == "admin":
            dw_res = supabase.table("daily_work").select("party_name, activity_type, work_date").order("work_date", desc=True).order("id", desc=True).execute()
            full_dw_df = pd.DataFrame(dw_res.data) if dw_res.data else pd.DataFrame()

            if not full_dw_df.empty:
                full_dw_df.rename(columns={
                    "party_name": "Party Name",
                    "activity_type": "Activity Type",
                    "work_date": "Work Date"
                }, inplace=True)
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
                        all_dw_res = supabase.table("daily_work").select("*").execute()
                        if all_dw_res.data:
                            for dw in all_dw_res.data:
                                move_to_recycle_bin("Daily Work", dw['party_name'], dw)
                            supabase.table("daily_work").delete().neq("id", 0).execute()
                            st.success("All daily work records moved to Recycle Bin! (রিসাইকেল বিনে পাঠানো হয়েছে!)")
                            st.rerun()

                st.write("---")

        work_res = supabase.table("daily_work").select("*").order("work_date", desc=True).order("id", desc=True).execute()
        work_df = pd.DataFrame(work_res.data) if work_res.data else pd.DataFrame()

        if not work_df.empty:
            unique_dates = work_df['work_date'].unique()
            for d_str in unique_dates:
                date_records = work_df[work_df['work_date'] == d_str]
                count_parties = len(date_records)
                formatted_d = format_date_display(d_str)

                with st.expander(f"📅 Date: {formatted_d} (Total: {count_parties}) Click to Open", expanded=False):
                    if st.session_state.get("user_role") == "admin":
                        if st.button(f"🗑️ Delete Date Data ({formatted_d}) (সব ডিলিট)", key=f"del_date_{d_str}", type="secondary"):
                            for idx, w_row in date_records.iterrows():
                                move_to_recycle_bin("Daily Work", w_row['party_name'], dict(w_row))
                            supabase.table("daily_work").delete().eq("work_date", d_str).execute()
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
                                supabase.table("daily_work").delete().eq("id", w_row['id']).execute()
                                st.success("Moved to Recycle Bin!")
                                st.rerun()
        else:
            st.info("No records found. (কোনো রেকর্ড নেই।)")

    with work_tab2:
        st.write("#### Monthly Doctor/Party Activity Report (মাসিক ডাক্তার ও পার্টি রিপোর্ট)")
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
            all_locs_res = supabase.table("locations").select("party_name, address, lat, lon").order("party_name", desc=False).execute()
            all_locs_df = pd.DataFrame(all_locs_res.data) if all_locs_res.data else pd.DataFrame()

            if not all_locs_df.empty:
                report_data = []

                # Pre-fetch month's daily_work to optimize loop performance
                dw_m_res = supabase.table("daily_work").select("party_name, activity_type").ilike("work_date", f"{selected_month}%").execute()
                month_dw_data = dw_m_res.data if dw_m_res.data else []

                for idx, loc_row in all_locs_df.iterrows():
                    p_name = loc_row['party_name']
                    is_mapped = "Mapped (ম্যাপযুক্ত)" if pd.notna(loc_row['lat']) and pd.notna(loc_row['lon']) else "Non-Map (ম্যাপবিহীন)"

                    v_count = sum(1 for d in month_dw_data if d["party_name"] == p_name and "Visit" in str(d["activity_type"]))
                    o_count = sum(1 for d in month_dw_data if d["party_name"] == p_name and "Order" in str(d["activity_type"]))

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
                            label="📥 Download Monthly Summary Report",
                            data=html_summary,
                            file_name=f"mediseller_monthly_summary_{selected_month}.html",
                            mime="text/html",
                            type="primary"
                        )
                    with col_ms2:
                        if st.button(f"🗑️ Delete All Work Records for Month: {selected_month}", type="secondary"):
                            supabase.table("daily_work").delete().ilike("work_date", f"{selected_month}%").execute()
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

# ==========================================
# PAGE LOGIC: DUE & DELIVERY
# ==========================================
elif selected_menu == "Due & Delivery (বকেয়া ও ডেলিভারি)":
    st.markdown('<div class="main-title">Delivery & Due Plan (ডেলিভারি ও ডিউ প্ল্যান)</div>', unsafe_allow_html=True)

    users_res = supabase.table("users").select("username, fullname").execute()
    users_data = users_res.data if users_res.data else []
    all_agents = [r["username"] for r in users_data]
    agent_name_map = {r["username"]: (r["fullname"] if r.get("fullname") else r["username"]) for r in users_data}

    loc_res = supabase.table("locations").select("party_name, lat, lon").order("party_name", desc=False).execute()
    loc_data = loc_res.data if loc_res.data else []
    party_coords = {r["party_name"]: (r.get("lat"), r.get("lon")) for r in loc_data}
    all_parties = [r["party_name"] for r in loc_data]

# ==========================================
# PAGE 4: DUE & DELIVERY (TASKS, SUMMARY, HISTORY)
# ==========================================

task_tab1, task_tab2, task_tab3, task_tab4 = st.tabs([
    "📋 Active Tasks (চলমান কাজ)",
    "📊 Agent Date-wise Summary (এজেন্ট ও তারিখ অনুযায়ী সামারি)",
    "📜 Completed Tasks History (সম্পন্ন কাজ)",
    "💰 Master Due List (ডিউ লিস্ট)"
])

# ==========================================
# SAFE HELPER FUNCTIONS (ক্র্যাশ এড়ানোর জন্য)
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
# TAB 1: ACTIVE TASKS
# ==========================================
with task_tab1:
    # 1. ADMIN REPORT DOWNLOAD (নিরাপদ ডাউনলোড সেকশন)
    if st.session_state.get("user_role") == "admin":
        try:
            tasks_res = supabase.table("task_assignments").select("*").eq("status", "Pending").order("id", desc=True).execute()
            t_data = tasks_res.data if tasks_res.data else []
            
            if t_data:
                users_res = supabase.table("users").select("username, fullname").execute()
                users_map = {u["username"]: u.get("fullname") for u in (users_res.data or [])}
                
                locs_res = supabase.table("locations").select("party_name, address").execute()
                locs_map = {l["party_name"]: l.get("address") for l in (locs_res.data or [])}
                
                for t in t_data:
                    t["agent_fullname"] = users_map.get(t.get("agent_name"))
                    t["address"] = locs_map.get(t.get("party_name"))

            full_tasks_df = pd.DataFrame(t_data) if t_data else pd.DataFrame()

            if not full_tasks_df.empty:
                export_tasks_df = full_tasks_df.copy()
                export_tasks_df["Agent Name"] = export_tasks_df.apply(
                    lambda r: safe_str(r.get("agent_fullname")) if safe_str(r.get("agent_fullname")) else safe_str(r.get("agent_name")),
                    axis=1
                )
                export_tasks_df["Party Name"] = export_tasks_df["party_name"].apply(safe_str)
                export_tasks_df["Task Type"] = export_tasks_df["task_type"].apply(safe_str)
                export_tasks_df["Sale Amount"] = export_tasks_df["sale_amount"].apply(lambda x: f"৳ {safe_float(x):,.2f}")
                export_tasks_df["Collection Amount"] = export_tasks_df["payment_collected_actual"].apply(lambda x: f"৳ {safe_float(x):,.2f}")
                export_tasks_df["Due Amount"] = export_tasks_df["due_amount"].apply(lambda x: f"৳ {safe_float(x):,.2f}")
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
                    label="📥 Download Active Tasks Report (PDF/HTML)",
                    data=html_tasks_report,
                    file_name="mediseller_due_delivery_report.html",
                    mime="text/html",
                    type="primary",
                    use_container_width=True
                )
                st.divider()
        except Exception as e:
            st.error(f"⚠️ রিপোর্ট তৈরিতে সাময়িক সমস্যা হয়েছে: {e}")

    # 2. SMOOTH SCROLL TO TOP TRIGGER
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

    # 3. TASK CREATION CARD (আধুনিক ও সুরক্ষিত ইনপুট ফর্ম)
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

        if task_search_text and task_search_text.strip():
            q_term = f"%{task_search_text.strip()}%"
            s_loc_res = supabase.table("locations").select("party_name").or_(
                f"party_name.ilike.{q_term},address.ilike.{q_term},party_phone.ilike.{q_term}"
            ).order("party_name", desc=False).execute()
            filtered_task_parties = [r["party_name"] for r in (s_loc_res.data or []) if r.get("party_name")]
        else:
            filtered_task_parties = [p for p in all_parties if p]

        sel_pt = None
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
                key=f"task_select_box_{reset_cnt}",
                label_visibility="collapsed",
            )
        else:
            st.warning("⚠️ কোনো মানানসই পার্টি পাওয়া যায়নি!")

        # অটোলোড কারেন্ট ডিউ মান (নিরাপদ টাইপ কাস্টিং সহ)
        auto_due_val = "0"
        if sel_pt and str(sel_pt).strip():
            c_due_res = supabase.table("locations").select("current_due").eq("party_name", str(sel_pt).strip()).execute()
            if c_due_res.data and c_due_res.data[0].get("current_due") is not None:
                due_num = safe_float(c_due_res.data[0]["current_due"])
                auto_due_val = str(int(due_num)) if due_num.is_integer() else str(due_num)

        with st.form("easy_assign_form", clear_on_submit=True):
            current_logged_user = st.session_state.get("username", "")
            sel_ag = st.selectbox(
                "Select Agent (এজেন্ট সিলেক্ট করুন)",
                all_agents,
                index=all_agents.index(current_logged_user) if current_logged_user in all_agents else 0,
                format_func=lambda x: agent_name_map.get(x, x)
            )

            col_amt1, col_amt2 = st.columns([1, 1])
            with col_amt1:
                is_delivery = st.checkbox("Delivery Task (ডেলিভারি টাস্ক)", value=True)
            with col_amt2:
                d_amount = st.text_input("💳 Old Due Amount (পুরনো ডিউ)", value=auto_due_val)

            submit_easy_task = st.form_submit_button("🚀 Save & Assign Task", type="primary", use_container_width=True)

            if submit_easy_task:
                if not sel_pt or not str(sel_pt).strip():
                    st.error("⚠️ অনুগ্রহ করে একটি নির্দিষ্ট পার্টি সিলেক্ট করুন!")
                else:
                    o_due = safe_float(d_amount)
                    t_type_str = "Delivery (ডেলিভারি)" if is_delivery else "Due Collection (ডিউ কালেকশন)"

                    try:
                        task_payload = {
                            "agent_name": sel_ag,
                            "party_name": str(sel_pt).strip(),
                            "task_type": t_type_str,
                            "due_amount": str(o_due),
                            "sale_amount": "0.0",
                            "status": "Pending",
                            "created_at": get_ist_time().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        supabase.table("task_assignments").insert(task_payload).execute()
                        st.session_state["task_search_reset_counter"] += 1
                        st.toast("🎉 নতুন টাস্ক সফলভাবে তৈরি হয়েছে!", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ ডাটাবেসে টাস্ক সংরক্ষণে সমস্যা: {e}")

    # 4. ACTIVE PENDING TASKS SECTION
    st.markdown("---")
    st.markdown("### 📌 Active Tasks Overview (চলমান কাজসমূহ)")

    try:
        p_tasks_res = supabase.table("task_assignments").select("*").eq("status", "Pending").order("created_at", desc=True).execute()
        pt_data = p_tasks_res.data if p_tasks_res.data else []

        if pt_data:
            users_res = supabase.table("users").select("username, fullname").execute()
            users_map = {u["username"]: u.get("fullname") for u in (users_res.data or [])}

            locs_res = supabase.table("locations").select("party_name, address, party_phone").execute()
            locs_map = {l["party_name"]: l for l in (locs_res.data or [])}

            for t in pt_data:
                t["agent_fullname"] = users_map.get(t.get("agent_name"))
                loc_info = locs_map.get(t.get("party_name"), {})
                t["address"] = loc_info.get("address")
                t["party_phone"] = loc_info.get("party_phone")

        pending_tasks_df = pd.DataFrame(pt_data) if pt_data else pd.DataFrame()
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

    # TAB 1: DELIVERY TASKS
    with tab_delivery:
        if del_df.empty:
            st.info("ℹ️ কোনো পেন্ডিং ডেলিভারি টাস্ক নেই।")
        else:
            for ag_username in del_df["agent_name"].unique():
                ag_rows = del_df[del_df["agent_name"] == ag_username]
                ag_disp_name = safe_str(ag_rows.iloc[0]["agent_fullname"]) or ag_username

                with st.expander(f"👤 Agent: **{ag_disp_name}** ({len(ag_rows)}টি কাজ)", expanded=True):
                    for idx, row in ag_rows.iterrows():
                        task_id = int(row["id"])
                        o_due = safe_float(row.get("due_amount", 0))
                        s_amt = safe_float(row.get("sale_amount", 0))
                        master_due = o_due + s_amt

                        with st.container(border=True):
                            c1, c2 = st.columns([2, 1])
                            with c1:
                                st.markdown(f"#### 🏥 {safe_str(row['party_name'])}")
                                addr = safe_str(row.get("address"))
                                phone = safe_str(row.get("party_phone"))
                                if addr:
                                    st.caption(f"🏠 {addr}" + (f" | 📞 {phone}" if phone else ""))
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
                                                supabase.table("task_assignments").update({
                                                    "status": "Completed",
                                                    "sale_amount": str(final_sale),
                                                    "payment_collected_actual": str(p_amt),
                                                    "remaining_due": str(r_due)
                                                }).eq("id", task_id).execute()

                                                supabase.table("locations").update({
                                                    "current_due": str(r_due)
                                                }).eq("party_name", str(row["party_name"])).execute()

                                                # Increment agent delivery count
                                                ag_curr = str(row["agent_name"])
                                                a_res = supabase.table("agent_live_locations").select("completed_deliveries").eq("username", ag_curr).execute()
                                                if a_res.data:
                                                    c_del = a_res.data[0].get("completed_deliveries", 0) or 0
                                                    supabase.table("agent_live_locations").update({"completed_deliveries": c_del + 1}).eq("username", ag_curr).execute()

                                                st.session_state["task_search_reset_counter"] += 1
                                                st.session_state["scroll_to_top"] = True
                                                st.toast("🎉 টাস্ক সফলভাবে সম্পন্ন করা হয়েছে!", icon="✅")
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"⚠️ আপডেট করতে সমস্যা হয়েছে: {e}")

                        if st.session_state.get("user_role") == "admin":
                            if st.button("🗑️ Delete Task", key=f"del_task_del_btn_{task_id}"):
                                try:
                                    move_to_recycle_bin("Task", row["party_name"], dict(row))
                                    supabase.table("task_assignments").delete().eq("id", task_id).execute()
                                    st.toast("🗑️ টাস্ক মুছে রিসাইকেল বিনে পাঠানো হয়েছে!", icon="ℹ️")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"⚠️ টাস্ক মুছতে ব্যর্থ: {e}")

    # TAB 2: DUE COLLECTION TASKS
    with tab_due:
        if due_df.empty:
            st.info("ℹ️ কোনো পেন্ডিং ডিউ কালেকশন টাস্ক নেই।")
        else:
            for ag_username in due_df["agent_name"].unique():
                ag_rows = due_df[due_df["agent_name"] == ag_username]
                ag_disp_name = safe_str(ag_rows.iloc[0]["agent_fullname"]) or ag_username

                with st.expander(f"👤 Agent: **{ag_disp_name}** ({len(ag_rows)}টি কালেকশন)", expanded=True):
                    for idx, row in ag_rows.iterrows():
                        task_id = int(row["id"])
                        o_due = safe_float(row.get("due_amount", 0))

                        with st.container(border=True):
                            c1, c2 = st.columns([2, 1])
                            with c1:
                                st.markdown(f"#### 🏥 {safe_str(row['party_name'])}")
                                addr = safe_str(row.get("address"))
                                phone = safe_str(row.get("party_phone"))
                                if addr:
                                    st.caption(f"🏠 {addr}" + (f" | 📞 {phone}" if phone else ""))
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
                                        supabase.table("task_assignments").update({
                                            "status": "Completed",
                                            "sale_amount": "0",
                                            "payment_collected_actual": str(p_amt),
                                            "remaining_due": str(r_due)
                                        }).eq("id", task_id).execute()

                                        supabase.table("locations").update({
                                            "current_due": str(r_due)
                                        }).eq("party_name", str(row["party_name"])).execute()

                                        ag_curr = str(row["agent_name"])
                                        a_res = supabase.table("agent_live_locations").select("completed_deliveries").eq("username", ag_curr).execute()
                                        if a_res.data:
                                            c_del = a_res.data[0].get("completed_deliveries", 0) or 0
                                            supabase.table("agent_live_locations").update({"completed_deliveries": c_del + 1}).eq("username", ag_curr).execute()

                                        st.session_state["task_search_reset_counter"] += 1
                                        st.session_state["scroll_to_top"] = True
                                        st.toast("🎉 কালেকশন সফলভাবে সম্পন্ন করা হয়েছে!", icon="✅")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"⚠️ আপডেট করতে সমস্যা হয়েছে: {e}")

                        if st.session_state.get("user_role") == "admin":
                            if st.button("🗑️ Delete Task", key=f"del_task_due_btn_{task_id}"):
                                try:
                                    move_to_recycle_bin("Task", row["party_name"], dict(row))
                                    supabase.table("task_assignments").delete().eq("id", task_id).execute()
                                    st.toast("🗑️ টাস্ক মুছে রিসাইকেল বিনে পাঠানো হয়েছে!", icon="ℹ️")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"⚠️ টাস্ক মুছতে ব্যর্থ: {e}")

# ==========================================
# TAB 2: AGENT SUMMARY
# ==========================================
with task_tab2:
    st.markdown("#### Agent Date-wise Summary (এজেন্ট ও তারিখ অনুযায়ী সামারি)")

    # Supabase aggregate replacement logic
    all_tasks_res = supabase.table("task_assignments").select("id, agent_name, status, created_at").execute()
    t_list = all_tasks_res.data if all_tasks_res.data else []

    if t_list:
        users_res = supabase.table("users").select("username, fullname, allow_resubmit").execute()
        users_map = {u["username"].strip().lower(): u for u in (users_res.data or [])}

        summary_dict = {}
        for t in t_list:
            ag = t.get("agent_name", "")
            c_at = str(t.get("created_at", ""))[:10]
            key = (ag, c_at)

            if key not in summary_dict:
                summary_dict[key] = {"total_tasks": 0, "completed_tasks": 0}

            summary_dict[key]["total_tasks"] += 1
            if t.get("status") == "Completed":
                summary_dict[key]["completed_tasks"] += 1

        summary_rows = []
        for (ag, t_date), counts in summary_dict.items():
            ag_lower = ag.strip().lower()
            u_info = users_map.get(ag_lower, {})
            summary_rows.append({
                "agent_name": ag,
                "agent_fullname": u_info.get("fullname"),
                "allow_resubmit": u_info.get("allow_resubmit"),
                "task_date": t_date,
                "total_tasks": counts["total_tasks"],
                "completed_tasks": counts["completed_tasks"]
            })

        agent_sum_df = pd.DataFrame(summary_rows).sort_values("task_date", ascending=False)
    else:
        agent_sum_df = pd.DataFrame()

    if not agent_sum_df.empty:
        current_role = str(st.session_state.get("user_role", "")).strip().lower()
        is_admin = (current_role == "admin")

        if is_admin:
            export_sum_df = agent_sum_df.copy()
            export_sum_df['Agent Name'] = export_sum_df.apply(
                lambda r: r['agent_fullname'] if pd.notna(r['agent_fullname']) and r['agent_fullname'] else r['agent_name'],
                axis=1
            )
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
            <p style="margin: 0 0 6px 0; color: #38bdf8 !important; font-size: 16px;">Agent: {ag_disp}</p>
            <p style="margin: 0 0 4px 0; color: #cbd5e1 !important; font-size: 13px;">Date: <b>{t_date}</b></p>
            <p style="margin: 0 0 4px 0; color: #cbd5e1 !important; font-size: 13px;">Total Tasks: <b>{tot}</b> | Completed: <b style="color: #34d399;">{comp}</b></p>
            </div>
            """, unsafe_allow_html=True)

            agent_identifier = str(row['agent_name']).strip()
            agent_allowed = bool(row.get("allow_resubmit"))

            if is_admin:
                resub_toggle = st.checkbox(
                    f"Allow {ag_disp} to Re-submit completed tasks (রি-সাবমিশনের অনুমতি প্রদান করুন)",
                    value=agent_allowed,
                    key=f"resub_perm_{agent_identifier}_{row['task_date']}_{idx}"
                )
                if resub_toggle != agent_allowed:
                    supabase.table("users").update({"allow_resubmit": resub_toggle}).or_(
                        f"username.ilike.{agent_identifier},fullname.ilike.{agent_identifier}"
                    ).execute()
                    st.rerun()

            ct_res = supabase.table("task_assignments").select(
                "id, party_name, task_type, due_amount, sale_amount, payment_collected_actual, remaining_due, created_at"
            ).eq("agent_name", row['agent_name']).eq("status", "Completed").ilike("created_at", f"{row['task_date']}%").execute()

            comp_tasks_df = pd.DataFrame(ct_res.data) if ct_res.data else pd.DataFrame()

            if not comp_tasks_df.empty:
                with st.expander(f"Re-submission Option (ভুলবশত কমপ্লিট হওয়া কাজ পুনরায় একটিভ করুন {len(comp_tasks_df)})", expanded=False):
                    can_do_resubmit = is_admin or agent_allowed
                    if not can_do_resubmit:
                        st.warning("রি-সাবমিশন করার অনুমতি নেই। শুধুমাত্র অ্যাডমিন বা অ্যাডমিন অনুমতি দিলে এই এজেন্ট কাজ পুনরায় একটিভ করতে পারবে।")
                    else:
                        for ct_idx, ct_row in comp_tasks_df.iterrows():
                            st.markdown(f"**Party:** `{ct_row['party_name']}` | **Type:** `{ct_row['task_type']}` | **Collected:** `{ct_row['payment_collected_actual']}`")
                            if st.button("Move to Active Tasks (পুনরায় একটিভ করুন)", key=f"btn_resub_ok_{ct_row['id']}_{idx}"):
                                supabase.table("task_assignments").update({"status": "Pending"}).eq("id", ct_row['id']).execute()

                                # Decrement completed deliveries count
                                ag_res = supabase.table("agent_live_locations").select("completed_deliveries").or_(
                                    f"username.ilike.{agent_identifier}"
                                ).execute()

                                if ag_res.data:
                                    curr_del = ag_res.data[0].get("completed_deliveries", 0) or 0
                                    new_del = max(0, curr_del - 1)
                                    supabase.table("agent_live_locations").update({"completed_deliveries": new_del}).or_(
                                        f"username.ilike.{agent_identifier}"
                                    ).execute()

                                st.success("Task moved back to Active Tasks!")
                                st.rerun()

            if is_admin:
                if st.button(f"🗑️ Delete Tasks ({ag_disp} {t_date})", key=f"del_agent_date_sum_{agent_identifier}_{row['task_date']}_{idx}"):
                    del_tasks = supabase.table("task_assignments").select("id").eq("agent_name", row['agent_name']).ilike("created_at", f"{row['task_date']}%").execute()
                    if del_tasks.data:
                        for dt in del_tasks.data:
                            supabase.table("task_assignments").delete().eq("id", dt["id"]).execute()
                    st.success("Deleted successfully!")
                    st.rerun()

            st.write("---")
    else:
        st.info("No summary records found.")

# ==========================================
# TAB 3: COMPLETED TASKS HISTORY
# ==========================================
with task_tab3:
    from io import BytesIO
    import re

    st.markdown("#### Completed Tasks History (সম্পন্ন কাজ)")

    try:
        from xhtml2pdf import pisa
    except ImportError:
        st.error("xhtml2pdf লাইব্রেরি পাওয়া যায়নি! requirements.txt ফাইলে যুক্ত করুন।")
        pisa = None

    current_user = st.session_state.get("username", st.session_state.get("user", ""))
    current_user_role = st.session_state.get("user_role", "")
    is_admin = (current_user_role == "admin")

    if is_admin:
        with st.expander("🔑 Manage Agent PDF Download Permissions (এজেন্টদের ডাউনলোডের অনুমতি দিন)"):
            try:
                users_res = supabase.table("users").select("username, fullname").neq("role", "admin").execute()
                u_data = users_res.data if users_res.data else []
                all_agents_db = [r["username"] for r in u_data]
                user_display_map = {r["username"]: (r["fullname"] if r.get("fullname") else r["username"]) for r in u_data}
            except Exception:
                all_agents_db = []
                user_display_map = {}

            perm_res = supabase.table("pdf_permissions").select("username").eq("can_download", 1).execute()
            allowed_list = [r["username"] for r in (perm_res.data or [])]

            selected_allowed_agents = st.multiselect(
                "অনুমোদিত এজেন্ট বেছে নিন (যারা PDF ডাউনলোড করতে পারবে):",
                options=all_agents_db,
                default=[ag for ag in allowed_list if ag in all_agents_db],
                format_func=lambda x: user_display_map.get(x, x)
            )

            if st.button("Save Permissions (পারমিশন সেভ করুন)", type="primary"):
                supabase.table("pdf_permissions").update({"can_download": 0}).neq("username", "").execute()
                for ag in selected_allowed_agents:
                    supabase.table("pdf_permissions").upsert({"username": ag, "can_download": 1}).execute()
                st.success("পারমিশন সফলভাবে আপডেট করা হয়েছে!")
                st.rerun()

    if is_admin:
        can_download = True
    else:
        perm_check = supabase.table("pdf_permissions").select("can_download").ilike("username", current_user).execute()
        can_download = True if perm_check.data and perm_check.data[0].get("can_download") == 1 else False

    c_tasks_res = supabase.table("task_assignments").select("*").eq("status", "Completed").order("created_at", desc=True).execute()
    ct_data = c_tasks_res.data if c_tasks_res.data else []

    if ct_data:
        users_res = supabase.table("users").select("username, fullname").execute()
        users_map = {u["username"].lower(): u.get("fullname") for u in (users_res.data or [])}

        locs_res = supabase.table("locations").select("party_name, address, current_due").execute()
        locs_map = {l["party_name"]: l for l in (locs_res.data or [])}

        for t in ct_data:
            ag_lower = str(t.get("agent_name", "")).lower()
            t["agent_fullname"] = users_map.get(ag_lower)
            loc_info = locs_map.get(t.get("party_name"), {})
            t["address"] = loc_info.get("address")
            t["master_due"] = loc_info.get("current_due")

    completed_tasks_df = pd.DataFrame(ct_data) if ct_data else pd.DataFrame()

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
                u_list_res = supabase.table("users").select("username, fullname").execute()
                db_agents = [(u.get("fullname") or u.get("username")) for u in (u_list_res.data or [])]
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
            st.warning(f"⚠️ {selected_date} তারিখে '{selected_agent}' এর কোনো সম্পন্ন হওয়া কাজ পাওয়া যায়নি।")
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

                export_comp_df_final = export_comp_df[[
                    'Agent Name', 'Party Name', 'Task Type', 'Sale Amount (Rs.)',
                    'Collection Amount (Rs.)', 'Task Remaining Due (Rs.)', 'Master Total Due (Rs.)', 'Completed Date'
                ]]

                pdf_clean_df = export_comp_df_final.copy()
                for col in pdf_clean_df.columns:
                    pdf_clean_df[col] = pdf_clean_df[col].apply(clean_text_for_pdf)

                clean_agent_title = clean_text_for_pdf(selected_agent)
                report_title = f"Tasks Report {selected_date} ({clean_agent_title})"
                html_comp_tasks = generate_html_report(report_title, pdf_clean_df)

                col_tc1, col_tc2 = st.columns(2)
                with col_tc1:
                    pdf_buffer = BytesIO()
                    if pisa:
                        pisa_status = pisa.CreatePDF(html_comp_tasks, dest=pdf_buffer)
                        if not pisa_status.err:
                            st.download_button(
                                label=f"📄 Download PDF ({selected_agent})",
                                data=pdf_buffer.getvalue(),
                                file_name=f"report_{selected_date}_{clean_agent_title.replace(' ', '_')}.pdf",
                                mime="application/pdf",
                                type="primary"
                            )
                        else:
                            st.error("PDF তৈরিতে সমস্যা হয়েছে।")
                with col_tc2:
                    if is_admin:
                        if st.button("🗑️ Clear Filtered Tasks History", type="secondary"):
                            task_ids = final_filtered_df['id'].tolist()
                            for r_idx, r in final_filtered_df.iterrows():
                                move_to_recycle_bin("Task", r['party_name'], dict(r))
                            for tid in task_ids:
                                supabase.table("task_assignments").delete().eq("id", tid).execute()
                            st.success("Filtered tasks moved to Recycle Bin!")
                            st.rerun()
            else:
                st.info("🔒 আপনার PDF ডাউনলোড করার অনুমতি নেই। প্রয়োজনে অ্যাডমিনের সাথে যোগাযোগ করুন।")

            st.write("---")

            for idx, row in final_filtered_df.iterrows():
                ag_c_name = row['display_agent']
                st.markdown(f"**Agent:** `{ag_c_name}` | **Party:** `{row['party_name']}` | **Task:** `{row['task_type']}`")
                master_due_text = f" | Master Due: `{row['master_due']}`" if pd.notna(row['master_due']) else ""
                st.markdown(f"Sale: `{row['sale_amount']}` | Collected: `{row['payment_collected_actual']}` | Task Due: `{row['remaining_due']}` {master_due_text}")

                if is_admin:
                    if st.button("Delete Task Record", key=f"del_comp_task_{row['id']}"):
                        move_to_recycle_bin("Task", row['party_name'], dict(row))
                        supabase.table("task_assignments").delete().eq("id", row['id']).execute()
                        st.success("Moved to Recycle Bin!")
                        st.rerun()
                st.write("---")

            if is_admin:
                with st.expander("🗑️ Monthly Bulk Delete (মাসিক ভিত্তিতে ডেটা মুছুন)"):
                    st.warning("⚠️ এখান থেকে কোনো মাসের ডেটা ডিলিট করলে সেটি সরাসরি রিসাইকেল বিনে চলে যাবে।")
                    unique_months = completed_tasks_df['month_year'].dropna().unique().tolist()
                    if unique_months:
                        selected_month_to_delete = st.selectbox("Select Month to Delete (যে মাসের ডেটা মুছতে চান):", unique_months)
                        if st.button(f"Delete All Data for {selected_month_to_delete}", type="primary"):
                            month_df_to_delete = completed_tasks_df[completed_tasks_df['month_year'] == selected_month_to_delete]
                            month_task_ids = month_df_to_delete['id'].tolist()
                            for r_idx, r in month_df_to_delete.iterrows():
                                move_to_recycle_bin("Task", r['party_name'], dict(r))
                            for tid in month_task_ids:
                                supabase.table("task_assignments").delete().eq("id", tid).execute()
                            st.success(f"{selected_month_to_delete} মাসের সমস্ত ডেটা সফলভাবে ডিলিট হয়ে রিসাইকেল বিনে চলে গেছে!")
                            st.rerun()
                    else:
                        st.info("ডিলিট করার মতো কোনো মাসের ডেটা পাওয়া যায়নি।")
    else:
        st.info("No completed tasks history found.")

# ==========================================
# PAGE 5: MASTER DUE LIST, ROUTE MAP, ATTENDANCE, LIVE TRACKING & SETTINGS
# ==========================================

import datetime
import calendar
import pandas as pd
import folium
from streamlit_folium import st_folium

# --- HELPER FUNCTIONS FIX ---
def get_ist_time():
    """IST time calculator"""
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

def safe_ist_now():
    return get_ist_time()

def format_date_display(date_str):
    try:
        parts = str(date_str).split(' ')[0].split('-')
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except Exception:
        pass
    return date_str

def generate_html_report(title, df):
    """Fallback HTML Report Generator"""
    html_data = f"<h2>{title}</h2>"
    html_data += df.to_html(index=False, classes='table table-striped')
    return html_data.encode('utf-8')


# ==========================================
# MENU / ROUTE ROUTING LOGIC
# ==========================================

# ১. Master Due List (যদি এটি ট্যাব হিসেবে থাকে)
if selected_menu == "Master Due List (পার্টি ডিউ)":
    st.write("#### Master Due List & Management (পার্টি ডিউ ম্যানেজমেন্ট)")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        if "master_due_search_key" not in st.session_state:
            st.session_state["master_due_search_key"] = ""
        party_search_query = st.text_input(
            "Search Party (পার্টি সার্চ করুন)",
            placeholder="Type party name...",
            key="master_due_search_input"
        )
    with col_f2:
        current_year_month = get_ist_time().strftime("%Y-%m")
        selected_month = st.selectbox(
            "Select Month (মাস সিলেক্ট করুন)",
            [current_year_month, "All Months (সব মাস)"],
            key="master_due_month_select"
        )
    
    st.write("---")
    st.write("##### Due Summary & Records (ডিউ তালিকা)")
    
    if selected_month != "All Months (সব মাস)":
        st.info(f"Showing records for: {selected_month}")
    else:
        st.info("Showing all time records.")
    
    try:
        if party_search_query.strip():
            q_term = f"%{party_search_query.strip()}%"
            due_res = supabase.table("locations") \
                .select("party_name, current_due") \
                .ilike("party_name", q_term) \
                .order("party_name", desc=False) \
                .execute()
        else:
            due_res = supabase.table("locations") \
                .select("party_name, current_due") \
                .order("party_name", desc=False) \
                .limit(10) \
                .execute()
        
        parties_due_data = due_res.data if due_res.data else []
        
        if parties_due_data:
            df_due_show = pd.DataFrame(parties_due_data)
            df_due_show = df_due_show.rename(columns={"party_name": "Party Name", "current_due": "Current Due"})
            df_due_show = df_due_show[["Party Name", "Current Due"]]
            st.dataframe(df_due_show, use_container_width=True, hide_index=True)
        else:
            st.warning("No data available.")
    except Exception as e:
        st.error(f"⚠️ ডিউ তালিকা লোড করতে সমস্যা হয়েছে: {e}")

# ২. Route Map
elif selected_menu == "Route Map (রুট ম্যাপ)":
    st.write("### Route Map & Locations (রুট ম্যাপ)")
    try:
        route_res = supabase.table("locations") \
            .select("party_name, address, lat, lon, party_phone") \
            .not_.is_("lat", "null") \
            .not_.is_("lon", "null") \
            .order("party_name", desc=False) \
            .execute()
        route_data = route_res.data if route_res.data else []
    except Exception as e:
        route_data = []
        st.error(f"⚠️ লোকেশন ডাটা আনতে সমস্যা: {e}")

    if route_data:
        valid_route_data = []
        for r in route_data:
            try:
                if r.get("lat") is not None and r.get("lon") is not None:
                    lat_v = float(r.get("lat"))
                    lon_v = float(r.get("lon"))
                    valid_route_data.append({
                        "party_name": r.get("party_name"),
                        "address": r.get("address"),
                        "lat": lat_v,
                        "lon": lon_v,
                        "party_phone": r.get("party_phone")
                    })
            except (ValueError, TypeError):
                continue

        if valid_route_data:
            avg_lat = sum([r["lat"] for r in valid_route_data]) / len(valid_route_data)
            avg_lon = sum([r["lon"] for r in valid_route_data]) / len(valid_route_data)
            
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
            
            for idx, r in enumerate(valid_route_data):
                p_n = r["party_name"]
                p_a = r["address"]
                p_lat = r["lat"]
                p_lon = r["lon"]
                p_ph = r["party_phone"]
                
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
                try:
                    folium.Marker(
                        [float(gps_lat), float(gps_lon)],
                        popup="<b>Your Live Location (আপনার লাইভ লোকেশন)</b>",
                        tooltip="You are here",
                        icon=folium.Icon(color="red", icon="user", prefix="fa")
                    ).add_to(r_map)
                except Exception:
                    pass
                    
            folium.LayerControl().add_to(r_map)
            st_folium(r_map, width="100%", height=500, key="route_map_view")
        else:
            st.info("No valid mapped locations available to show on route map. (ম্যাপযুক্ত কোনো বৈধ লোকেশন নেই।)")
    else:
        st.info("No mapped locations available to show on route map. (ম্যাপযুক্ত কোনো লোকেশন নেই।)")

# ৩. Attendance
elif selected_menu == "Attendance (উপস্থিতি)":
    now_dt = safe_ist_now()
    current_year = now_dt.year
    current_month = now_dt.month

    st.write("### Daily & Monthly Attendance (উপস্থিতি ব্যবস্থাপনা)")

    try:
        users_att_res = supabase.table("users").select("username, fullname, role").execute()
        att_users_data = users_att_res.data if users_att_res.data else []
        agent_name_map = {r["username"]: (r.get("fullname") if r.get("fullname") else r["username"]) for r in att_users_data}
    except Exception as e:
        att_users_data = []
        agent_name_map = {}

    att_tab1, att_tab2 = st.tabs([
        "✓ Daily Attendance (আজকের উপস্থিতি ও চেক-ইন)",
        "Monthly & Agent Attendance Report (মাসিক রিপোর্ট)"
    ])

    # TAB 1: DAILY ATTENDANCE
    with att_tab1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%); padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h4 style="margin:0; color: white; font-size: 22px;"> Daily Attendance & Check-in</h4>
        <p style="margin:5px 0 0 0; font-size: 15px; opacity: 0.9;"> আপনার আজকের উপস্থিতি নিশ্চিত করতে নিচের বাটনে ক্লিক করুন।</p>
        </div>
        """, unsafe_allow_html=True)

        today_date_str = safe_ist_now().strftime("%Y-%m-%d")
        today_display_str = safe_ist_now().strftime("%d.%m.%Y")

        with st.form("attendance_form", clear_on_submit=True):
            agent_for_att = st.session_state.get("username", "staff")
            c1, c2 = st.columns(2)
            with c1:
                st.info(f" **আজকের তারিখ:**\n\n**{today_display_str}**")
            with c2:
                st.success(f" **স্টাফের নাম:**\n\n**{agent_name_map.get(agent_for_att, agent_for_att)}**")
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit_att = st.form_submit_button(" Give Attendance / Check-in (উপস্থিতি দিন)", type="primary", use_container_width=True)

            if submit_att:
                try:
                    exist_att = supabase.table("attendance") \
                        .select("id") \
                        .eq("username", agent_for_att) \
                        .eq("date", today_date_str) \
                        .execute()
                    
                    if exist_att.data:
                        st.warning("⚠️ Attendance already given for today! (আজকে ইতিমধ্যে উপস্থিতি দেওয়া হয়েছে!)")
                    else:
                        check_time_str = safe_ist_now().strftime("%H:%M:%S")
                        att_payload = {
                            "username": agent_for_att,
                            "date": today_date_str,
                            "in_time": check_time_str,
                            "status": "Present"
                        }
                        supabase.table("attendance").insert(att_payload).execute()
                        st.success("➕ Attendance recorded successfully! (উপস্থিতি সফলভাবে নথিভুক্ত হয়েছে!)")
                        st.rerun()
                except Exception as e:
                    st.error(f"⚠️ উপস্থিতি এনট্রি দিতে সমস্যা: {e}")

        st.markdown("---")
        st.markdown("#### 📅 Today's Attendance List (আজকের উপস্থিতি তালিকা)")
        
        try:
            today_att_res = supabase.table("attendance") \
                .select("date, username, in_time, status") \
                .eq("date", today_date_str) \
                .order("in_time", desc=True) \
                .execute()
            
            t_att_data = today_att_res.data if today_att_res.data else []
            
            if t_att_data:
                formatted_att = []
                for r in t_att_data:
                    formatted_att.append({
                        "Date": format_date_display(r.get("date")),
                        "Agent Name": agent_name_map.get(r.get("username"), r.get("username")),
                        "Check-in Time": r.get("in_time"),
                        "Status": r.get("status")
                    })

                today_att_df = pd.DataFrame(formatted_att)
                st.dataframe(today_att_df, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ No attendance recorded for today yet. (আজ কেউ উপস্থিতি দেননি।)")
        except Exception as e:
            st.error(f"⚠️ উপস্থিতি ডাটা আনতে সমস্যা: {e}")

    # TAB 2: MONTHLY REPORT & ADMIN DELETIONS
    with att_tab2:
        current_role = st.session_state.get("user_role", "staff")
        current_user = st.session_state.get("username", "staff")

        if current_role == "admin":
            st.write("#### Agent-wise Monthly Attendance & Report Download")
            st.write("নিচে থেকে যেকোনো এজেন্টকে সিলেক্ট করে তার এই মাসের মোট কাজের দিন দেখতে পাবেন এবং তার ব্যক্তিগত রিপোর্ট ডাউনলোড করতে পারবেন:")
            
            try:
                staff_res = supabase.table("users").select("username, fullname").eq("role", "staff").execute()
                staff_list = staff_res.data if staff_res.data else []
            except Exception:
                staff_list = []

            if staff_list:
                selected_rep_agent = st.selectbox(
                    "Select Agent for Report & Summary:",
                    options=[s["username"] for s in staff_list],
                    format_func=lambda x: agent_name_map.get(x, x),
                    key="agent_report_dropdown"
                )

                if selected_rep_agent:
                    total_days_in_month = calendar.monthrange(current_year, current_month)[1]
                    month_prefix = f"{current_year}-{current_month:02d}"

                    att_month_res = supabase.table("attendance") \
                        .select("date") \
                        .eq("username", selected_rep_agent) \
                        .ilike("date", f"{month_prefix}%") \
                        .execute()
                    
                    month_dates = set([r["date"] for r in (att_month_res.data or []) if r.get("date")])
                    days_worked_count = len(month_dates)

                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        st.metric(label="Total Days in This Month", value=f"{total_days_in_month} Days")
                    with col_r2:
                        st.metric(label="Days Worked by Agent", value=f"{days_worked_count} Days")

                    ag_att_res = supabase.table("attendance") \
                        .select("date, in_time, status") \
                        .eq("username", selected_rep_agent) \
                        .order("date", desc=True) \
                        .execute()
                    
                    ag_att_data = ag_att_res.data if ag_att_res.data else []

                    if ag_att_data:
                        agent_rep_df = pd.DataFrame(ag_att_data)
                        agent_rep_df = agent_rep_df.rename(columns={
                            "date": "Date",
                            "in_time": "Check-in Time",
                            "status": "Status"
                        })
                        agent_rep_df['Date'] = agent_rep_df['Date'].apply(lambda x: format_date_display(x))
                        st.dataframe(agent_rep_df, use_container_width=True, hide_index=True)

                        agent_fullname_str = agent_name_map.get(selected_rep_agent, selected_rep_agent)
                        
                        try:
                            html_agent_att = generate_html_report(f"Attendance Report ({agent_fullname_str})", agent_rep_df)
                            st.download_button(
                                label=f"Download Report for {agent_fullname_str}",
                                data=html_agent_att,
                                file_name=f"attendance_{selected_rep_agent}_{current_year}_{current_month:02d}.html",
                                mime="text/html",
                                type="primary",
                                key=f"dl_btn_{selected_rep_agent}"
                            )
                        except Exception:
                            csv_data = agent_rep_df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label=f"Download CSV Report for {agent_fullname_str}",
                                data=csv_data,
                                file_name=f"attendance_{selected_rep_agent}_{current_year}_{current_month:02d}.csv",
                                mime="text/csv",
                                type="primary"
                            )
                    else:
                        st.info(f"ℹ️ এই মাসের জন্য {agent_name_map.get(selected_rep_agent, selected_rep_agent)}-এর কোনো উপস্থিতির রেকর্ড পাওয়া যায়নি।")

            st.write("---")
            st.write("#### Delete Attendance Records (Admin Only)")
            del_mode = st.radio("Delete Option:", ["Delete Single Date", "Delete Full Month Data"], horizontal=True)

            if del_mode == "Delete Single Date":
                col_del1, col_del2 = st.columns(2)
                with col_del1:
                    del_agent = st.selectbox(
                        "Select Agent:",
                        options=[s["username"] for s in staff_list] if staff_list else [],
                        format_func=lambda x: agent_name_map.get(x, x),
                        key="del_agent_select"
                    )
                with col_del2:
                    del_date = st.date_input("Select Date to Delete:", value=safe_ist_now().date(), key="del_date_select")
                
                if st.button("Delete Selected Attendance Record", type="primary", key="btn_del_att"):
                    if staff_list and del_agent:
                        del_date_str = del_date.strftime("%Y-%m-%d")
                        rec_check = supabase.table("attendance") \
                            .select("id") \
                            .eq("username", del_agent) \
                            .eq("date", del_date_str) \
                            .execute()
                        
                        if rec_check.data:
                            supabase.table("attendance").delete().eq("username", del_agent).eq("date", del_date_str).execute()
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
                    m_rec_check = supabase.table("attendance").select("id").ilike("date", f"{month_str}%").execute()
                    
                    if m_rec_check.data:
                        for m_item in m_rec_check.data:
                            supabase.table("attendance").delete().eq("id", m_item["id"]).execute()
                        st.success(f"Successfully deleted all attendance records for {calendar.month_name[target_month]} {target_year}!")
                        st.rerun()
                    else:
                        st.warning(f"No attendance records found for {calendar.month_name[target_month]} {target_year}.")
        else:
            st.write("#### Your Monthly Attendance Report")
            staff_att_res = supabase.table("attendance") \
                .select("date, in_time, status") \
                .eq("username", current_user) \
                .order("date", desc=True) \
                .execute()
            
            staff_att_data = staff_att_res.data if staff_att_res.data else []

            if staff_att_data:
                staff_att_df = pd.DataFrame(staff_att_data)
                staff_att_df = staff_att_df.rename(columns={
                    "date": "Date",
                    "in_time": "Check-in Time",
                    "status": "Status"
                })
                staff_att_df['Date'] = staff_att_df['Date'].apply(lambda x: format_date_display(x))
                st.dataframe(staff_att_df, use_container_width=True, hide_index=True)
            else:
                st.info("You have no attendance records yet.")

# ৪. Live Tracking
elif selected_menu == "Live Tracking (লাইভ ট্র্যাকিং)" and st.session_state.get("user_role") == "admin":
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;">
    <h4 style="margin:0; color: white; font-size: 22px;"> Live Agent Tracking</h4>
    <p style="margin:5px 0 0 0; font-size: 15px; opacity: 0.9;"> এজেন্টদের লাইভ লোকেশন এবং সর্বশেষ আপডেট এখানে দেখুন।</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        live_res = supabase.table("agent_live_locations").select("username, lat, lon, updated_at").order("updated_at", desc=True).execute()
        live_data = live_res.data if live_res.data else []

        if live_data:
            users_res = supabase.table("users").select("username, fullname, phone").execute()
            u_map = {u["username"]: u for u in (users_res.data or [])}
            
            for item in live_data:
                u_info = u_map.get(item["username"], {})
                item["fullname"] = u_info.get("fullname")
                item["phone"] = u_info.get("phone")

        live_df = pd.DataFrame(live_data) if live_data else pd.DataFrame()
    except Exception as e:
        live_df = pd.DataFrame()
        st.error(f"Database query error: {e}")

    if not live_df.empty:
        agent_options = ["All Agents (সব এজেন্ট একসাথে)"]
        for idx, r in live_df.iterrows():
            d_name = f"{r['fullname']} ({r['username']})" if pd.notna(r.get('fullname')) and r['fullname'] else r['username']
            agent_options.append(d_name)
        
        selected_agent_box = st.selectbox("📌 Select Agent to Track:", agent_options)
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
            last_up = r.get('updated_at')

            with st.expander(f"📍 Agent: {name} (ID: {username})", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.info(f" **Phone Number:**\n\n{phone}")
                with c2:
                    st.warning(f" **Last Updated:**\n\n{last_up if pd.notna(last_up) else 'No update'}")

                if pd.notna(lat) and pd.notna(lon):
                    g_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.link_button("📍 Track on Google Maps", url=g_url, type="primary", use_container_width=True)
                else:
                    st.error("⚠️ GPS coordinates not available for this agent.")
    else:
        st.warning("⚠️ কোনো এজেন্টের লাইভ লোকেশন ডাটা পাওয়া যায়নি বা টেবিলটি খালি আছে।")

# ৫. Settings
elif selected_menu == "Settings & Agents (সেটিংসে)" and st.session_state.get("user_role") == "admin":
    st.write("### Settings & Agents Management (কর্মী, অজানা ইউজার ও ম্যানেজমেন্ট)")

    try:
        staff_cnt_res = supabase.table("users").select("id", count="exact").eq("role", "staff").execute()
        total_staff_count = staff_cnt_res.count if staff_cnt_res.count is not None else len(staff_cnt_res.data or [])

        all_cnt_res = supabase.table("users").select("id", count="exact").execute()
        total_users_count = all_cnt_res.count if all_cnt_res.count is not None else len(all_cnt_res.data or [])
    except Exception:
        total_staff_count, total_users_count = 0, 0

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
        "➕ Add Agents & Links",
        "Menu Permissions",
        "Unknown & Blocked Agents",
        "Backup & Restore",
        "Recycle Bin",
        "Admin Password"
    ])

    with set_tab1:
        st.write("#### Add New Staff / Agent & Generate Auto-Login Link")
        clean_base_url = "https://ps-mediseller-app-gcanjbehuut7h9rzk4xzfg.streamlit.app"

        with st.form("add_agent_form", clear_on_submit=True):
            new_uname = st.text_input("Username (ইউজারনেম)")
            new_pass = st.text_input("Password (পাসওয়ার্ড)")
            new_fname = st.text_input("Full Name (পুরো নাম)")
            new_phone = st.text_input("Phone Number (ফোন নম্বর)")
            submit_new_agent = st.form_submit_button("➕ Add Agent (এজেন্ট যুক্ত করুন)", type="primary")

            if submit_new_agent:
                if new_uname.strip() and new_pass.strip() and new_fname.strip():
                    u_target = new_uname.strip()
                    check_exist = supabase.table("users").select("username").eq("username", u_target).execute()
                    
                    if check_exist.data:
                        st.error("⚠️ Username already exists!")
                    else:
                        try:
                            user_payload = {
                                "username": u_target,
                                "password": new_pass.strip(),
                                "role": "staff",
                                "fullname": new_fname.strip(),
                                "phone": new_phone.strip(),
                                "created_at": get_ist_time().strftime("%Y-%m-%d %H:%M:%S"),
                                "is_active": 1
                            }
                            supabase.table("users").insert(user_payload).execute()
                            st.success(f"🎉 New agent '{new_fname.strip()}' added successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"⚠️ এজেন্ট তৈরিতে সমস্যা: {e}")
                else:
                    st.error("⚠️ Username, Password and Full Name are required!")

# ==========================================
# PAGE 5 (CONTINUATION): SETTINGS TABS 2 TO 6
# ==========================================

    # TAB 2: MENU PERMISSIONS
    with set_tab_perm:
        import time
        st.write("### Menu Permissions (মেনু পারমিশন)")
        st.divider()
        try:
            staff_res = supabase.table("users").select("username, fullname").eq("role", "staff").execute()
            staff_data = staff_res.data if staff_res.data else []
            
            if not staff_data:
                st.info("কোনো স্টাফ একাউন্ট পাওয়া যায়নি।")
            else:
                for s in staff_data:
                    s_uname = s.get("username", "")
                    s_fname = s.get("fullname", "")
                    
                    with st.expander(f"Permission Settings: {s_fname} ({s_uname})"):
                        am_res = supabase.table("users").select("allowed_menus").eq("username", s_uname).execute()
                        am_row = am_res.data[0] if am_res.data else {}
                        
                        raw_curr = am_row.get("allowed_menus", "")
                        curr_menus = raw_curr.split(",") if raw_curr else all_basic_menus
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
                                supabase.table("users").update({"allowed_menus": updated_menus_str}).eq("username", s_uname).execute()
                                st.success(f"{s_fname}-এর পারমিশন সফলভাবে আপডেট হয়েছে!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"ডাটাবেজ আপডেট করতে সমস্যা হয়েছে: {e}")
        except Exception as e:
            st.error(f"স্টাফদের তথ্য আনতে সমস্যা হয়েছে: {e}")

    # TAB 3: UNKNOWN & BLOCKED AGENTS
    with set_tab3:
        st.write("### Unknown & Blocked Agents Management")
        st.caption("লিংক দিয়ে প্রবেশ করা নতুন ইউজার এবং ব্লকড এজেন্টদের তালিকা ও পরিচালনা সেকশন।")

        try:
            users_res = supabase.table("users").select("username, fullname, role, is_active, created_at").neq("role", "admin").execute()
            all_users_data = users_res.data if users_res.data else []
        except Exception as e:
            all_users_data = []
            st.error(f"ইউজার তথ্য ডাটাবেজ থেকে আনতে সমস্যা: {e}")

        if "delete_msg" in st.session_state:
            st.success(st.session_state["delete_msg"])
            del st.session_state["delete_msg"]

        if not all_users_data:
            st.info("বর্তমানে কোনো Unknown বা Blocked এজেন্ট পাওয়া যায়নি।")
        else:
            # ১. ড্রপডাউন ফিল্টারিং
            user_options = [row["username"] for row in all_users_data]
            user_dict = {row["username"]: f"{row.get('fullname', '')} (@{row['username']}) [{row.get('role', '').upper()}]" for row in all_users_data}

            st.markdown("##### 📌 সিলেক্ট করুন যাকে ম্যানেজ করতে চান")
            selected_uname = st.selectbox(
                "ইউজারনেম বা আইডি নির্বাচন করুন:",
                options=user_options,
                format_func=lambda x: user_dict.get(x, x)
            )

            if selected_uname:
                u_res = supabase.table("users").select("username, fullname, role, is_active, phone").eq("username", selected_uname).execute()
                u_row = u_res.data[0] if u_res.data else None

                if u_row:
                    s_uname = u_row.get("username")
                    s_fname = u_row.get("fullname")
                    s_role = u_row.get("role")
                    s_act = u_row.get("is_active")
                    s_phone = u_row.get("phone")

                    status_label = "🟢 Active" if s_act == 1 else "🔴 Blocked"
                    role_label = "🔗 Unknown (Link Access)" if s_role == "unknown" else f"👤 {s_role.capitalize()}"

                    # কার্ডের মতো সুন্দর ডিটেইলস ডিসপ্লে
                    st.info(f"""
                    **নাম:** {s_fname}
                    **ইউজারনেম:** `{s_uname}` | **ফোন:** {s_phone}
                    **টাইপ:** {role_label} | **স্ট্যাটাস:** {status_label}
                    """)

                    col1, col2, col3 = st.columns([1, 1, 1])

                    # কলাম ১: ব্লক/আনব্লক অ্যাকশন
                    with col1:
                        if s_act == 1:
                            if st.button("🚫 Block User", key=f"blk_{s_uname}", use_container_width=True):
                                supabase.table("users").update({"is_active": 0}).eq("username", s_uname).execute()
                                st.success(f"'{s_uname}' কে ব্লক করা হয়েছে।")
                                st.rerun()
                        else:
                            if st.button("✅ Unblock User", key=f"unblk_{s_uname}", use_container_width=True):
                                supabase.table("users").update({"is_active": 1}).eq("username", s_uname).execute()
                                st.success(f"'{s_uname}' কে আনব্লক করা হয়েছে।")
                                st.rerun()

                    # কলাম ২: স্টাফ হিসেবে অ্যাপ্রুভ করা (Unknown ইউজারদের জন্য)
                    with col2:
                        if s_role == "unknown":
                            if st.button("✔ Approve as Staff", key=f"appr_{s_uname}", use_container_width=True):
                                supabase.table("users").update({"role": "staff"}).eq("username", s_uname).execute()
                                st.success(f"'{s_uname}' এখন রেজিস্টার্ড Staff!")
                                st.rerun()

                    # কলাম ৩: ডিলিট অ্যাকশন
                    with col3:
                        if st.button("🗑 Delete User", key=f"del_{s_uname}", type="primary", use_container_width=True):
                            supabase.table("users").delete().eq("username", s_uname).execute()
                            st.session_state["delete_msg"] = f"User '{s_uname}' সফলভাবে মুছে ফেলা হয়েছে!"
                            st.rerun()

            st.divider()
            # ২. সামারি টেবিল ও লিস্ট
            st.markdown("##### 📋 সকল এজেন্ট ও অটো-লগইন ইউজারদের সামারি")
            summary_list = []
            for u in all_users_data:
                uname = u.get("username")
                fname = u.get("fullname")
                role = u.get("role")
                is_act = u.get("is_active")
                created = u.get("created_at")

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

    # TAB 4: BACKUP & RESTORE (CLOUD SUPABASE INFO)
    with set_tab4:
        st.markdown("### Database Management & Security")
        st.caption("আপনার ডাটাবেসের ক্লাউড স্ট্যাটাস এবং রিয়েল-টাইম ক্লাউড সিঙ্ক তথ্য।")
        st.divider()

        col_backup, col_restore = st.columns(2, gap="large")

        with col_backup:
            st.markdown("#### Cloud Database Status")
            st.info("আপনার সমস্ত ডাটাবেস রিয়েল-টাইমে Supabase Cloud PostgreSQL-এ নিরাপদভাবে সংরক্ষিত হচ্ছে।")
            st.success("🟢 Supabase Realtime Sync Active")

        with col_restore:
            st.markdown("#### Cloud Backup Management")
            st.warning("⚠️ Supabase ক্লাউড ডাটাবেস স্বয়ংক্রিয়ভাবে দৈনিক ব্যাকআপ গ্রহণ করে। কোনো ম্যানুয়াল রিস্টোর বা ডাটাবেস রিসেট প্রয়োজন হলে Supabase Dashboard ব্যবহার করুন।")

    # TAB 5: RECYCLE BIN
    with set_tab5:
        st.subheader("Recycle Bin (রিসাইকেল বিন)")
        try:
            rec_res = supabase.table("recycle_bin").select("id, item_type, item_title, item_data, deleted_at").execute()
            recycle_rows = rec_res.data if rec_res.data else []

            if recycle_rows:
                display_data = []
                options = {}
                for row in recycle_rows:
                    r_id = row.get("id")
                    item_type = row.get("item_type")
                    item_title = row.get("item_title")
                    item_data = row.get("item_data")
                    deleted_at = row.get("deleted_at")

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
                    selected_id = selected_row.get("id")
                    item_type = selected_row.get("item_type")
                    raw_data = selected_row.get("item_data")

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
                                pass

                    if not data:
                        data = {}
                        st.error("Error: Failed to parse item data for restoration!")
                        st.stop()

                    if item_type == "Location":
                        supabase.table("locations").insert({
                            "party_name": data.get('party_name'),
                            "address": data.get('address'),
                            "party_phone": data.get('party_phone'),
                            "lat": data.get('lat'),
                            "lon": data.get('lon'),
                            "route_order": data.get('route_order'),
                            "current_due": data.get('current_due')
                        }).execute()

                    elif item_type == "Orders":
                        supabase.table("orders").insert({
                            "party_name": data.get('party_name'),
                            "order_details": data.get('order_details'),
                            "order_date": data.get('order_date'),
                            "status": data.get('status', 'Pending'),
                            "payment_collected": data.get('payment_collected', '0')
                        }).execute()

                    elif item_type == "Daily Work":
                        supabase.table("daily_work").insert({
                            "party_name": data.get('party_name', 'N/A'),
                            "activity_type": data.get('activity_type', 'N/A'),
                            "work_date": data.get('work_date', '')
                        }).execute()

                    elif item_type == "Task":
                        supabase.table("task_assignments").insert({
                            "agent_name": data.get('agent_name'),
                            "party_name": data.get('party_name'),
                            "task_type": data.get('task_type'),
                            "due_amount": data.get('due_amount', '0'),
                            "sale_amount": data.get('sale_amount', '0'),
                            "payment_collected_actual": data.get('payment_collected_actual', '0'),
                            "remaining_due": data.get('remaining_due', '0'),
                            "status": data.get('status', 'Pending'),
                            "created_at": data.get('created_at')
                        }).execute()

                    # Delete from recycle bin after restoring
                    supabase.table("recycle_bin").delete().eq("id", selected_id).execute()
                    st.success(f"Successfully restored '{selected_row.get('item_title')}'!")
                    st.rerun()

                if st.button("Clear Recycle Bin"):
                    supabase.table("recycle_bin").delete().neq("id", 0).execute()
                    st.success("Recycle Bin cleared!")
                    st.rerun()
            else:
                st.info("Recycle Bin is empty. (রিসাইকেল বিন ফাঁকা)")
        except Exception as e:
            st.error(f"Error loading Recycle Bin: {e}. ডেটাবেসে recycle_bin টেবিলটি আছে কিনা চেক করুন।")

    # TAB 6: ADMIN PASSWORD
    with set_tab6:
        st.write("#### Admin Password Update (পাসওয়ার্ড পরিবর্তন)")
        with st.form("update_admin_pass"):
            new_pass = st.text_input("New Admin Password", type="password")
            if st.form_submit_button("Update Password", type="primary"):
                if new_pass.strip():
                    supabase.table("users").update({"password": new_pass.strip()}).eq("username", "admin").execute()
                    st.success("Admin Password Updated Successfully!")
                else:
                    st.error("Please enter a valid password.")
