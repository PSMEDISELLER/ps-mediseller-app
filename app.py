# ==============================================================================
# PART 1: IMPORTS, SUPABASE SETUP & LOGIN SYSTEM
# ==============================================================================
import streamlit as st
import pandas as pd
import datetime
import calendar
import re
import ast
import json
import time
from io import BytesIO
import folium
from streamlit_folium import st_folium
from supabase import create_client, Client

try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="P.S MEDISELLER", layout="wide", page_icon="💊")

# 2. SUPABASE CONNECTION (১০০% Supabase নির্ভর)
@st.cache_resource
def init_supabase():
    # Streamlit Secrets থেকে URL এবং KEY নিন
    SUPABASE_URL = st.secrets["https://dcihrmyfgurcefjbwwxz.supabase.co"]
    SUPABASE_KEY = st.secrets["sb_publishable_ow-a8EnUYYA-Ux4nqSo9bw_BwHInsE_"]
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

# 3. HELPER FUNCTIONS
def get_ist_time():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

def safe_ist_now():
    return get_ist_time()

# 4. SESSION STATE INITIALIZATION
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "fullname" not in st.session_state:
    st.session_state["fullname"] = ""
if "user_role" not in st.session_state:
    st.session_state["user_role"] = ""

# 5. LOGIN SYSTEM (Fix: Admin Login & Fullname Fetch)
if not st.session_state["logged_in"]:
    st.markdown("<h2 style='text-align: center; color: #2563eb;'>P.S MEDISELLER - LOGIN</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            login_user = st.text_input("Username (ইউজারনেম)")
            login_pass = st.text_input("Password (পাসওয়ার্ড)", type="password")
            submit_login = st.form_submit_button("লগইন করুন", type="primary", use_container_width=True)
            
            if submit_login:
                if login_user and login_pass:
                    try:
                        # Supabase থেকে ইউজার চেক
                        res = supabase.table("users").select("*").eq("username", login_user.strip()).execute()
                        user_data = res.data
                        
                        if user_data:
                            db_user = user_data[0]
                            if db_user["password"] == login_pass.strip():
                                if db_user.get("is_active", 1) == 0:
                                    st.error("আপনার একাউন্টটি ব্লক করা হয়েছে। অ্যাডমিনের সাথে যোগাযোগ করুন।")
                                else:
                                    st.session_state["logged_in"] = True
                                    st.session_state["username"] = db_user["username"]
                                    # Fix: Full Name Fetching
                                    st.session_state["fullname"] = db_user.get("fullname") or db_user["username"]
                                    st.session_state["user_role"] = db_user.get("role", "staff")
                                    st.session_state["allowed_menus"] = db_user.get("allowed_menus", "")
                                    st.success(f"লগইন সফল হয়েছে! স্বাগতম {st.session_state['fullname']}")
                                    time.sleep(1)
                                    st.rerun()
                            else:
                                st.error("পাসওয়ার্ড ভুল হয়েছে!")
                        else:
                            st.error("ইউজারনেম পাওয়া যায়নি!")
                    except Exception as e:
                        st.error(f"লগইন এরর: {e}")
                else:
                    st.warning("ইউজারনেম এবং পাসওয়ার্ড প্রদান করুন।")
    st.stop() # লগইন না হওয়া পর্যন্ত কোড এখানে থেমে থাকবে

# ==============================================================================
# PART 2: SIDEBAR MENU ROUTING & DASHBOARD (FRONT PAGE)
# ==============================================================================

current_user = st.session_state["username"]
current_fullname = st.session_state["fullname"]
current_role = st.session_state["user_role"]
is_admin = (current_role == "admin")

# 1. DEFINE MENUS
all_basic_menus = ["Dashboard (ড্যাশবোর্ড)", "Locations (লোকেশন)", "Orders (অর্ডার)", "Tasks (টাস্ক)", "Master Due List (পার্টি ডিউ)", "Route Map (রুট ম্যাপ)", "Attendance (উপস্থিতি)"]
admin_only_menus = ["Live Tracking (লাইভ ট্র্যাকিং)", "Settings & Agents (সেটিংসে)"]

# 2. ROLE BASED MENU FILTERING
if is_admin:
    display_menus = all_basic_menus + admin_only_menus
else:
    allowed_str = st.session_state.get("allowed_menus", "")
    if allowed_str:
        allowed_list = [m.strip() for m in allowed_str.split(",") if m.strip() in all_basic_menus]
        display_menus = allowed_list if allowed_list else ["Dashboard (ড্যাশবোর্ড)"]
    else:
        display_menus = all_basic_menus

# 3. SIDEBAR UI
with st.sidebar:
    st.markdown(f"### 👤 {current_fullname}")
    st.markdown(f"**Role:** {current_role.capitalize()}")
    st.divider()
    
    selected_menu = st.radio("📌 মেনু নির্বাচন করুন:", display_menus)
    st.divider()
    
    if st.button("🚪 Logout (লগআউট)"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ==============================================================================
# MENU 1: DASHBOARD (FRONT PAGE)
# ==============================================================================
if selected_menu == "Dashboard (ড্যাশবোর্ড)":
    # Fix: Showing Full Name properly on Front Page
    st.markdown(f"<h2 style='color: #2563eb;'>স্বাগতম, {current_fullname}! 👋</h2>", unsafe_allow_html=True)
    st.write("P.S MEDISELLER ম্যানেজমেন্ট প্যানেলে আপনাকে স্বাগতম। বামদিকের মেনু থেকে আপনার কাজ নির্বাচন করুন।")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("📅 আজকের তারিখ:\n\n**" + safe_ist_now().strftime('%d %b, %Y') + "**")
    with col2:
        st.success("👤 লগইন স্ট্যাটাস:\n\n**Active**")
    with col3:
        st.warning("🔑 আপনার রোল:\n\n**" + current_role.capitalize() + "**")
    
    # Save Agent Live Location (Background process for tracking)
    if not is_admin:
        try:
            loc_payload = {
                "username": current_user,
                "updated_at": get_ist_time().strftime("%Y-%m-%d %H:%M:%S")
            }
            # Only updates time if GPS isn't provided here, proper GPS tracking comes from JS/Browser if added
            supabase.table("agent_live_locations").upsert(loc_payload).execute()
        except Exception:
            pass

# ==============================================================================
# PART 3: LOCATIONS & ORDERS MANAGEMENT
# ==============================================================================

# MENU 2: LOCATIONS
elif selected_menu == "Locations (লোকেশন)":
    st.header("📍 Locations & Parties (পার্টি ও রুট)")
    
    tab_add, tab_view = st.tabs(["+ Add New Party", "View All Parties"])
    
    with tab_add:
        with st.form("add_location_form", clear_on_submit=True):
            p_name = st.text_input("Party Name (পার্টির নাম)*")
            p_phone = st.text_input("Phone Number (ফোন নম্বর)")
            p_address = st.text_area("Address (ঠিকানা)")
            p_due = st.number_input("Opening Due Amount (বকেয়া)", min_value=0.0, value=0.0)
            
            sub_loc = st.form_submit_button("পার্টি সেভ করুন", type="primary")
            if sub_loc:
                if p_name.strip():
                    try:
                        payload = {
                            "party_name": p_name.strip(),
                            "party_phone": p_phone.strip(),
                            "address": p_address.strip(),
                            "current_due": p_due
                        }
                        supabase.table("locations").insert(payload).execute()
                        st.success("পার্টির তথ্য সফলভাবে ডাটাবেসে সেভ হয়েছে!")
                    except Exception as e:
                        st.error(f"Error saving location: {e}")
                else:
                    st.warning("পার্টির নাম দেওয়া বাধ্যতামূলক!")

    with tab_view:
        try:
            loc_res = supabase.table("locations").select("*").order("party_name").execute()
            if loc_res.data:
                df_loc = pd.DataFrame(loc_res.data)
                st.dataframe(df_loc[['party_name', 'party_phone', 'address', 'current_due']], use_container_width=True)
            else:
                st.info("কোনো পার্টির তথ্য পাওয়া যায়নি।")
        except Exception as e:
            st.error(f"Error fetching locations: {e}")

# MENU 3: ORDERS
elif selected_menu == "Orders (অর্ডার)":
    st.header("📦 Order Management (অর্ডার গ্রহণ)")
    
    try:
        party_res = supabase.table("locations").select("party_name").execute()
        parties = [p["party_name"] for p in (party_res.data or [])]
    except Exception:
        parties = []

    with st.form("add_order_form", clear_on_submit=True):
        selected_party = st.selectbox("Select Party (পার্টি নির্বাচন করুন)", parties if parties else ["No party available"])
        order_details = st.text_area("Order Details (অর্ডারের বিবরণ - ওষুধের নাম ও পরিমাণ)")
        
        sub_order = st.form_submit_button("অর্ডার কনফার্ম করুন", type="primary")
        
        if sub_order:
            if selected_party != "No party available" and order_details.strip():
                try:
                    ord_payload = {
                        "party_name": selected_party,
                        "order_details": order_details.strip(),
                        "order_date": safe_ist_now().strftime("%Y-%m-%d %H:%M:%S"),
                        "status": "Pending",
                        "agent_name": current_user
                    }
                    supabase.table("orders").insert(ord_payload).execute()
                    st.success("অর্ডারটি সফলভাবে গৃহীত হয়েছে!")
                except Exception as e:
                    st.error(f"Error saving order: {e}")
            else:
                st.warning("পার্টি নির্বাচন করুন এবং অর্ডারের বিবরণ লিখুন।")

# ==============================================================================
# PART 4: TASKS MANAGEMENT (ASSIGN, ACTIVE, COMPLETED)
# ==============================================================================

elif selected_menu == "Tasks (টাস্ক)":
    st.header("📋 Task Management (কাজ পরিচালনা)")
    
    # 3টি প্রধান ট্যাব (টাস্ক পরিচালনার জন্য)
    task_tabs = st.tabs(["Active Tasks (চলমান কাজ)", "Assign Task (কাজ দিন)", "Task History (সম্পন্ন কাজ)"])
    
    # TAB 1: ACTIVE TASKS (চলমান কাজ)
    with task_tabs[0]:
        st.subheader("আপনার বর্তমান চলমান কাজসমূহ")
        
        try:
            if is_admin:
                active_res = supabase.table("task_assignments").select("*").eq("status", "Pending").execute()
            else:
                active_res = supabase.table("task_assignments").select("*").eq("status", "Pending").eq("agent_name", current_user).execute()
            
            active_tasks = active_res.data if active_res.data else []
        except Exception as e:
            active_tasks = []
            st.error(f"Error fetching active tasks: {e}")

        if not active_tasks:
            st.info("আপনার কোনো পেন্ডিং কাজ নেই।")
        else:
            for task in active_tasks:
                with st.expander(f"Task for: {task['party_name']} | Type: {task['task_type']}"):
                    st.write(f"**Agent:** {task['agent_name']}")
                    st.write(f"**Due Amount (Old):** {task.get('due_amount', 0)}")
                    
                    with st.form(f"complete_task_{task['id']}"):
                        sale_amt = st.number_input("New Sale Amount (নতুন সেলস ৳)", min_value=0.0, value=0.0)
                        col_amt = st.number_input("Collection Amount (কালেকশন ৳)", min_value=0.0, value=0.0)
                        
                        sub_comp = st.form_submit_button("কাজ সম্পন্ন করুন (Complete)", type="primary")
                        if sub_comp:
                            try:
                                # বকেয়া হিসাব
                                old_due = float(task.get('due_amount') or 0)
                                new_remaining = (old_due + sale_amt) - col_amt
                                
                                # ১. Task Table আপডেট
                                update_payload = {
                                    "status": "Completed",
                                    "sale_amount": sale_amt,
                                    "payment_collected_actual": col_amt,
                                    "remaining_due": new_remaining,
                                    "completed_at": safe_ist_now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                                supabase.table("task_assignments").update(update_payload).eq("id", task['id']).execute()
                                
                                # ২. Location (Party) Table এর Current Due আপডেট
                                supabase.table("locations").update({"current_due": new_remaining}).eq("party_name", task['party_name']).execute()
                                
                                st.success("কাজটি সফলভাবে সম্পন্ন হয়েছে!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error completing task: {e}")

    # TAB 2: ASSIGN TASK (Admin Only)
    with task_tabs[1]:
        if is_admin:
            st.subheader("নতুন কাজ অ্যাসাইন করুন")
            
            try:
                agents_res = supabase.table("users").select("username").eq("role", "staff").execute()
                agents = [a["username"] for a in (agents_res.data or [])]
                
                party_res = supabase.table("locations").select("party_name, current_due").execute()
                parties = [p["party_name"] for p in (party_res.data or [])]
                party_due_map = {p["party_name"]: p["current_due"] for p in (party_res.data or [])}
            except Exception:
                agents, parties, party_due_map = [], [], {}
                
            with st.form("assign_task_form", clear_on_submit=True):
                sel_agent = st.selectbox("Select Agent (এজেন্ট)", agents if agents else ["No agent found"])
                sel_party = st.selectbox("Select Party (পার্টি)", parties if parties else ["No party found"])
                sel_task_type = st.selectbox("Task Type", ["Delivery & Collection", "Only Delivery", "Only Collection"])
                
                sub_assign = st.form_submit_button("কাজ অ্যাসাইন করুন", type="primary")
                if sub_assign:
                    if sel_agent != "No agent found" and sel_party != "No party found":
                        try:
                            t_payload = {
                                "agent_name": sel_agent,
                                "party_name": sel_party,
                                "task_type": sel_task_type,
                                "due_amount": party_due_map.get(sel_party, 0),
                                "status": "Pending",
                                "created_at": safe_ist_now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            supabase.table("task_assignments").insert(t_payload).execute()
                            st.success(f"কাজটি {sel_agent} কে সফলভাবে দেওয়া হয়েছে।")
                        except Exception as e:
                            st.error(f"Error assigning task: {e}")
        else:
            st.info("শুধুমাত্র অ্যাডমিনরা নতুন কাজ অ্যাসাইন করতে পারবেন।")

    # TAB 3: TASK HISTORY
    with task_tabs[2]:
        st.subheader("Completed Tasks (সম্পন্ন কাজ)")
        try:
            comp_res = supabase.table("task_assignments").select("*").eq("status", "Completed").order("completed_at", desc=True).limit(50).execute()
            if comp_res.data:
                df_comp = pd.DataFrame(comp_res.data)
                st.dataframe(df_comp[['agent_name', 'party_name', 'task_type', 'sale_amount', 'payment_collected_actual', 'remaining_due']], use_container_width=True)
            else:
                st.info("কোনো সম্পন্ন কাজ পাওয়া যায়নি।")
        except Exception as e:
            st.error(f"Error fetching history: {e}")

# ==============================================================================
# PART 5: DUE LIST, MAP & ATTENDANCE
# ==============================================================================

# MENU 5: MASTER DUE LIST
elif selected_menu == "Master Due List (পার্টি ডিউ)":
    st.header("💰 Master Due List (সকল পার্টির বকেয়া)")
    try:
        due_res = supabase.table("locations").select("party_name, current_due").order("party_name").execute()
        if due_res.data:
            df_due = pd.DataFrame(due_res.data)
            df_due = df_due.rename(columns={"party_name": "Party Name", "current_due": "Total Due (৳)"})
            st.dataframe(df_due, use_container_width=True)
            
            # Total Due Calculation
            total_market_due = df_due["Total Due (৳)"].sum()
            st.success(f"**বাজারে মোট বকেয়া (Total Market Due): ৳ {total_market_due:,.2f}**")
        else:
            st.info("কোনো ডিউ রেকর্ড পাওয়া যায়নি।")
    except Exception as e:
        st.error(f"Error fetching dues: {e}")

# MENU 6: ROUTE MAP
elif selected_menu == "Route Map (রুট ম্যাপ)":
    st.header("🗺️ Route Map & Locations (পার্টি ম্যাপ)")
    try:
        route_res = supabase.table("locations").select("party_name, lat, lon, address").not_.is_("lat", "null").not_.is_("lon", "null").execute()
        valid_routes = [r for r in (route_res.data or []) if r.get("lat") and r.get("lon")]
        
        if valid_routes:
            avg_lat = sum(float(r["lat"]) for r in valid_routes) / len(valid_routes)
            avg_lon = sum(float(r["lon"]) for r in valid_routes) / len(valid_routes)
            
            m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)
            for r in valid_routes:
                folium.Marker(
                    [float(r["lat"]), float(r["lon"])],
                    popup=f"<b>{r['party_name']}</b><br>{r.get('address', '')}",
                    icon=folium.Icon(color="blue", icon="info-sign")
                ).add_to(m)
                
            st_folium(m, width="100%", height=500)
        else:
            st.info("ম্যাপে দেখানোর মতো কোনো জিপিএস (GPS) লোকেশন ডাটাবেসে নেই।")
    except Exception as e:
        st.error(f"Error loading map: {e}")

# MENU 7: ATTENDANCE
elif selected_menu == "Attendance (উপস্থিতি)":
    st.header("📅 Daily Attendance (উপস্থিতি)")
    
    today_str = safe_ist_now().strftime("%Y-%m-%d")
    
    with st.form("att_form", clear_on_submit=True):
        st.write(f"**তারিখ:** {today_str} | **স্টাফ:** {current_fullname}")
        sub_att = st.form_submit_button("✅ Check-in (আজকের উপস্থিতি দিন)", type="primary", use_container_width=True)
        
        if sub_att:
            try:
                # Check if already given
                check_att = supabase.table("attendance").select("id").eq("username", current_user).eq("date", today_str).execute()
                if check_att.data:
                    st.warning("আপনি ইতিমধ্যে আজকের উপস্থিতি দিয়েছেন!")
                else:
                    att_payload = {
                        "username": current_user,
                        "date": today_str,
                        "in_time": safe_ist_now().strftime("%H:%M:%S"),
                        "status": "Present"
                    }
                    supabase.table("attendance").insert(att_payload).execute()
                    st.success("আজকের উপস্থিতি সফলভাবে রেকর্ড করা হয়েছে!")
            except Exception as e:
                st.error(f"Error submitting attendance: {e}")

# ==============================================================================
# PART 6: LIVE TRACKING & SETTINGS (ADMIN ONLY)
# ==============================================================================

elif selected_menu == "Live Tracking (লাইভ ট্র্যাকিং)" and is_admin:
    st.header("📡 Live Agent Tracking (এজেন্ট ট্র্যাকিং)")
    
    try:
        live_res = supabase.table("agent_live_locations").select("*").order("updated_at", desc=True).execute()
        if live_res.data:
            for loc in live_res.data:
                with st.expander(f"Agent: {loc['username']} | Last Updated: {loc['updated_at']}", expanded=True):
                    if loc.get('lat') and loc.get('lon'):
                        g_url = f"https://www.google.com/maps/search/?api=1&query={loc['lat']},{loc['lon']}"
                        st.link_button("View on Google Maps", g_url, type="primary")
                    else:
                        st.warning("GPS Co-ordinates Not Available yet. (কেবল লগইন রেকর্ড রয়েছে)")
        else:
            st.info("কোনো ট্র্যাকিং ডাটা পাওয়া যায়নি।")
    except Exception as e:
        st.error(f"Error fetching tracking data: {e}")

elif selected_menu == "Settings & Agents (সেটিংসে)" and is_admin:
    st.header("⚙️ Settings & Management")
    
    set_tabs = st.tabs(["Add Agent", "Admin Password", "Recycle Bin"])
    
    # TAB 1: ADD NEW AGENT
    with set_tabs[0]:
        st.subheader("নতুন স্টাফ যুক্ত করুন")
        with st.form("add_agent_form", clear_on_submit=True):
            n_user = st.text_input("Username (ইংরেজি ছোট হাতের অক্ষরে)")
            n_pass = st.text_input("Password")
            n_full = st.text_input("Full Name (পুরো নাম)")
            sub_ag = st.form_submit_button("Add Agent", type="primary")
            
            if sub_ag and n_user and n_pass and n_full:
                try:
                    check_u = supabase.table("users").select("username").eq("username", n_user.strip()).execute()
                    if check_u.data:
                        st.error("এই ইউজারনেমটি ইতিমধ্যে বিদ্যমান!")
                    else:
                        payload = {
                            "username": n_user.strip(),
                            "password": n_pass.strip(),
                            "fullname": n_full.strip(),
                            "role": "staff",
                            "is_active": 1,
                            "allowed_menus": ",".join(all_basic_menus)
                        }
                        supabase.table("users").insert(payload).execute()
                        st.success("নতুন এজেন্ট সফলভাবে যুক্ত হয়েছে!")
                except Exception as e:
                    st.error(f"Error: {e}")
                    
    # TAB 2: UPDATE ADMIN PASSWORD
    with set_tabs[1]:
        st.subheader("অ্যাডমিন পাসওয়ার্ড পরিবর্তন")
        with st.form("admin_pass_form"):
            new_admin_pass = st.text_input("New Password", type="password")
            sub_pass = st.form_submit_button("পাসওয়ার্ড আপডেট করুন", type="primary")
            if sub_pass and new_admin_pass:
                try:
                    # Fix: Admin Password update was failing previously due to incorrect targeting.
                    supabase.table("users").update({"password": new_admin_pass}).eq("username", "admin").execute()
                    st.success("পাসওয়ার্ড সফলভাবে পরিবর্তিত হয়েছে!")
                except Exception as e:
                    st.error(f"Error updating password: {e}")

    # TAB 3: RECYCLE BIN / DATABASE RESET
    with set_tabs[2]:
        st.subheader("ডেটাবেস ম্যানেজমেন্ট")
        st.warning("পুরো ডেটাবেস Supabase ক্লাউডে রিয়েল-টাইম সিঙ্ক হচ্ছে। কোনো টেবিলের ডেটা মুছলে সরাসরি ক্লাউড থেকে মুছে যাবে।")
        if st.button("Clear Old Attendance Data (1 মাস আগের)", type="secondary"):
            st.info("Supabase ড্যাশবোর্ড থেকে SQL Query রান করে এটি ডিলিট করা সবচেয়ে নিরাপদ।")
