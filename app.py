from datetime import datetime, timedelta
import folium
import pandas as pd
import sqlite3
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation, streamlit_js_eval

# [DATABASE SETUP REMAINS SAME]
DB_FILE = "mediseller_delivery.db"
def get_db_connection(): return sqlite3.connect(DB_FILE, check_same_thread=False)
conn = get_db_connection()
c = conn.cursor()

# (এখানে আগের টেবিল ক্রিয়েশন ও আপডেট কোডগুলো কার্যকর থাকবে)

# =========================================================
# MAIN APP NAVIGATION
# =========================================================
st.title("পি এস মেডিসেলার - স্মার্ট ডেলিভারি")

# [LOGIN/GPS TRACKING CODE REMAINS SAME]
# (এখানে আগের লগইন ও হিডেন জিপিএস ট্র্যাকার কোড ব্যবহার করুন)

# =========================================================
# 1. NEW LOCATION & ORDER ENTRY (সার্চযোগ্য ও মাল্টি-এন্ট্রি)
# =========================================================
if selected_menu == "📍 নতুন লোকেশন এড":
    c.execute("SELECT DISTINCT party_name FROM locations")
    all_parties = [r[0] for r in c.fetchall()]
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("### 📍 লোকেশন ও অর্ডার")
        with st.form("combined_entry_form", clear_on_submit=True):
            # সার্চযোগ্য পার্টি নেম
            search_party = st.text_input("পার্টির নাম লিখুন (সার্চ)")
            filtered = [p for p in all_parties if search_party.lower() in p.lower()]
            p_name = st.selectbox("পার্টি নির্বাচন করুন", filtered if filtered else all_parties)
            
            p_addr = st.text_input("ঠিকানা")
            p_phone = st.text_input("ফোন নম্বর")
            ord_details = st.text_area("অর্ডারের বিবরণ")
            
            submitted = st.form_submit_button("💾 সেভ করুন (লোকেশন + অর্ডার)")
            if submitted:
                # একই সাথে দুটো সেভ করা
                c.execute("INSERT OR IGNORE INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, ?, ?)",
                          (p_name, p_addr, p_phone, st.session_state["selected_lat"], st.session_state["selected_lon"]))
                c.execute("INSERT INTO orders (party_name, order_details, order_date, status) VALUES (?, ?, ?, ?)",
                          (p_name, ord_details, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Pending"))
                conn.commit()
                st.success("লোকেশন ও অর্ডার সফলভাবে সেভ হয়েছে!")

    # [MAP WITH BLUE DOT & REFRESH LOGIC]
    with col2:
        if st.button("🔄 ম্যাপ রিফ্রেশ (কারেন্ট লোকেশন)"):
            loc = get_geolocation()
            if loc:
                st.session_state["selected_lat"] = loc["coords"]["latitude"]
                st.session_state["selected_lon"] = loc["coords"]["longitude"]
                st.rerun()

        m = folium.Map(location=[st.session_state["selected_lat"], st.session_state["selected_lon"]], zoom_start=18)
        # ব্লু ডট (কারেন্ট লোকেশন)
        folium.Marker([st.session_state["selected_lat"], st.session_state["selected_lon"]], 
                      icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)
        
        map_data = st_folium(m, width=500, height=400)
        if map_data and map_data.get("last_clicked"):
            st.session_state["selected_lat"] = map_data["last_clicked"]["lat"]
            st.session_state["selected_lon"] = map_data["last_clicked"]["lng"]

# =========================================================
# 2. DUE CLEAR & DELIVERY (টিক চিহ্ন সিস্টেম ও পাশাপাশি চেক-বক্স)
# =========================================================
elif selected_menu == "📋 ডিউ ক্লিয়ার ও ডেলিভারি প্ল্যান":
    st.write("### 📋 কাজের তালিকা")
    
    with st.form("assign_form"):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            sel_pt = st.selectbox("পার্টি নির্বাচন", all_parties)
            is_delivery = st.checkbox("ডেলিভারি")
            is_due = st.checkbox("ডিউ কালেকশন")
        with col_c2:
            d_amount = st.text_input("টাকার পরিমাণ", "0")
            submit_task = st.form_submit_button("কাজ যুক্ত করুন")

        if submit_task:
            task_type = "ডেলিভারি" if (is_delivery and not is_due) else ("ডিউ কালেকশন" if (is_due and not is_delivery) else "উভয়ই")
            c.execute("INSERT INTO task_assignments ...") # আগের ডাটাবেস ইনসার্ট লজিক
            conn.commit()
            st.rerun()
