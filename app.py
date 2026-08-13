from datetime import datetime, timedelta
import folium
import pandas as pd
import sqlite3
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation, streamlit_js_eval

# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(page_title="P.S Mediseller", layout="wide")

# =========================================================
# DATABASE SETUP
# =========================================================
DB_FILE = "mediseller_delivery.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# টেবিল তৈরি
c.executescript("""
CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY AUTOINCREMENT, party_name TEXT, address TEXT, party_phone TEXT, lat REAL, lon REAL);
CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, party_name TEXT, order_details TEXT, order_date TEXT, status TEXT DEFAULT 'Pending');
CREATE TABLE IF NOT EXISTS task_assignments (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_name TEXT, party_name TEXT, task_type TEXT, due_amount TEXT, status TEXT DEFAULT 'Pending', created_at TEXT);
CREATE TABLE IF NOT EXISTS agent_live_locations (username TEXT PRIMARY KEY, lat REAL, lon REAL, last_updated TEXT, completed_deliveries INTEGER DEFAULT 0, completed_dues INTEGER DEFAULT 0);
""")
conn.commit()

# =========================================================
# STATE INITIALIZATION
# =========================================================
if "selected_lat" not in st.session_state: st.session_state["selected_lat"] = 22.8620
if "selected_lon" not in st.session_state: st.session_state["selected_lon"] = 87.3320

# =========================================================
# MAIN APP
# =========================================================
st.title("🚚 পি এস মেডিসেলার - স্মার্ট ডেলিভারি")

menu = ["📍 নতুন লোকেশন ও অর্ডার", "🔍 সার্চ ও রুট", "📋 ডিউ ক্লিয়ার ও ডেলিভারি", "📊 লাইভ ট্র্যাকিং"]
selected_menu = st.sidebar.selectbox("মেনু", menu)

# =========================================================
# 1. নতুন লোকেশন ও অর্ডার (সার্চযোগ্য ও মাল্টি-এন্ট্রি)
# =========================================================
if selected_menu == "📍 নতুন লোকেশন ও অর্ডার":
    col1, col2 = st.columns([1, 1])
    
    c.execute("SELECT DISTINCT party_name FROM locations")
    all_parties = [r[0] for r in c.fetchall()]

    with col1:
        st.write("### 📝 পার্টি ও অর্ডার এন্ট্রি")
        with st.form("combined_form", clear_on_submit=True):
            search_p = st.text_input("পার্টির নাম লিখুন (সার্চ)")
            filtered = [p for p in all_parties if search_p.lower() in p.lower()]
            p_name = st.selectbox("পার্টি সিলেক্ট করুন", filtered if filtered else all_parties)
            
            p_addr = st.text_input("ঠিকানা")
            p_phone = st.text_input("ফোন নম্বর")
            ord_details = st.text_area("অর্ডারের বিবরণ")
            
            if st.form_submit_button("💾 ডাটা সেভ করুন"):
                c.execute("INSERT OR IGNORE INTO locations (party_name, address, party_phone, lat, lon) VALUES (?, ?, ?, ?, ?)",
                          (p_name, p_addr, p_phone, st.session_state["selected_lat"], st.session_state["selected_lon"]))
                c.execute("INSERT INTO orders (party_name, order_details, order_date) VALUES (?, ?, ?)",
                          (p_name, ord_details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                st.success("সেভ হয়েছে!")

    with col2:
        st.write("### 🗺️ ম্যাপ সিলেকশন")
        if st.button("🔄 ম্যাপ রিফ্রেশ (কারেন্ট লোকেশন)"):
            loc = get_geolocation()
            if loc and "coords" in loc:
                st.session_state["selected_lat"] = loc["coords"]["latitude"]
                st.session_state["selected_lon"] = loc["coords"]["longitude"]
                st.rerun()

        m = folium.Map(location=[st.session_state["selected_lat"], st.session_state["selected_lon"]], zoom_start=18)
        folium.CircleMarker([st.session_state["selected_lat"], st.session_state["selected_lon"]], 
                            radius=10, color="blue", fill=True, fill_color="blue", popup="আপনার বর্তমান অবস্থান").add_to(m)
        
        map_data = st_folium(m, height=400)
        if map_data and map_data.get("last_clicked"):
            st.session_state["selected_lat"] = map_data["last_clicked"]["lat"]
            st.session_state["selected_lon"] = map_data["last_clicked"]["lng"]

# =========================================================
# 2. ডিউ ক্লিয়ার ও ডেলিভারি (টিক চিহ্ন সিস্টেম)
# =========================================================
elif selected_menu == "📋 ডিউ ক্লিয়ার ও ডেলিভারি":
    st.write("### ✅ কাজের ধরণ সিলেক্ট করুন")
    c.execute("SELECT DISTINCT party_name FROM locations")
    all_parties = [r[0] for r in c.fetchall()]
    
    with st.form("task_form"):
        p_name = st.selectbox("পার্টি", all_parties if all_parties else ["-- পার্টি নেই --"])
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            is_delivery = st.checkbox("ডেলিভারি")
            is_due = st.checkbox("ডিউ কালেকশন")
        with col_c2:
            due_amt = st.text_input("ডিউ টাকা", "0")
        
        if st.form_submit_button("🎯 কাজ যুক্ত করুন"):
            if p_name != "-- পার্টি নেই --":
                t_type = "ডেলিভারি + ডিউ" if (is_delivery and is_due) else ("ডেলিভারি" if is_delivery else "ডিউ কালেকশন")
                c.execute("INSERT INTO task_assignments (party_name, task_type, due_amount, created_at) VALUES (?, ?, ?, ?)",
                          (p_name, t_type, due_amt, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                st.success("কাজ যুক্ত হয়েছে!")
            else:
                st.error("আগে পার্টি যোগ করুন।")

    c.execute("DELETE FROM task_assignments WHERE (strftime('%s','now') - strftime('%s', created_at)) > 86400")
    conn.commit()

# =========================================================
# 3. সার্চ ও রুট
# =========================================================
elif selected_menu == "🔍 সার্চ ও রুট":
    st.write("### 🗺️ রুট প্ল্যানিং")
    df = pd.read_sql_query("SELECT * FROM locations", conn)
    st.dataframe(df)
    
    m = folium.Map(location=[22.86, 87.33], zoom_start=12)
    coords = df[['lat', 'lon']].values.tolist() if not df.empty and 'lat' in df.columns else []
    if coords:
        folium.PolyLine(coords, color="red").add_to(m)
        for _, row in df.iterrows():
            folium.Marker([row['lat'], row['lon']], popup=row['party_name']).add_to(m)
    st_folium(m, height=500)

# =========================================================
# 4. লাইভ ট্র্যাকিং
# =========================================================
elif selected_menu == "📊 লাইভ ট্র্যাকিং":
    st.write("### 📊 এজেন্ট ট্র্যাকিং")
    c.execute("SELECT username, lat, lon, last_updated, completed_deliveries, completed_dues FROM agent_live_locations")
    agents_data = c.fetchall()
    if agents_data:
        for ag in agents_data:
            st.write(f"এজেন্ট: **{ag[0]}** | শেষ আপডেট: {ag[3]}")
    else:
        st.info("কোনো লাইভ ডাটা পাওয়া যায়নি।")
