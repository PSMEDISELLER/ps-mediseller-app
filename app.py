import streamlit as st
import pandas as pd
import sqlite3
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from streamlit_js_eval import get_geolocation

# পেজ কনফিগারেশন
st.set_page_config(page_title="পি এস মেডিসেলার", layout="wide")

# ডাটাবেস কানেকশন
st.set_page_config(page_title="P.S Mediseller Location App", layout="wide")

# ১. ইউজার টেবিল তৈরি ও ডিফল্ট ইউজার সেটআপ
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
    c.execute("INSERT INTO users VALUES ('admin', 'admin123', 'admin')")
    c.execute("INSERT INTO users VALUES ('delivery', 'user123', 'staff')")
    conn.commit()

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None

# ২. লগইন ও ফরগট পাসওয়ার্ড স্ক্রিন
if not st.session_state["logged_in"]:
    st.title("🔑 লগইন পোর্টাল - P.S Mediseller")
    tab1, tab2 = st.tabs(["লগইন", "পাসওয়ার্ড ভুলে গেছেন?"])
    
    with tab1:
        username = st.text_input("ইউজারনেম", key="login_user")
        password = st.text_input("পাসওয়ার্ড", type="password", key="login_pass")
        if st.button("লগইন করুন"):
            c.execute("SELECT password, role FROM users WHERE username=?", (username,))
            user_data = c.fetchone()
            if user_data and user_data[0] == password:
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = user_data[1]
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("ভুল ইউজারনেম বা পাসওয়ার্ড!")
                
    with tab2:
        st.write("যে ইউজারের পাসওয়ার্ড রিসেট করতে চান তার তথ্য দিন:")
        f_user = st.text_input("ইউজারনেম", key="forgot_user")
        new_pass = st.text_input("নতুন পাসওয়ার্ড", type="password", key="new_pass_admin")
        admin_pass = st.text_input("মেইন অ্যাডমিন পাসওয়ার্ড", type="password", key="admin_auth")
        
        if st.button("পাসওয়ার্ড রিসেট করুন"):
            c.execute("SELECT password FROM users WHERE username='admin'")
            real_admin_pass = c.fetchone()[0]
            if admin_pass == real_admin_pass:
                c.execute("UPDATE users SET password=? WHERE username=?", (new_pass, f_user))
                conn.commit()
                st.success("পাসওয়ার্ড সফলভাবে পরিবর্তন করা হয়েছে! এখন লগইন ট্যাবে গিয়ে লগইন করুন।")
            else:
                st.error("অ্যাডমিন পাসওয়ার্ড ভুল!")
    st.stop()

# ৩. সাইডবারে ইউজার তথ্য, পাসওয়ার্ড পরিবর্তন ও লগআউট অপশন
with st.sidebar:
    st.write(f"👤 ইউজার: **{st.session_state.get('username')}**")
    st.write(f"রোল: `{st.session_state.get('user_role')}`")
    
    with st.expander("🔒 পাসওয়ার্ড পরিবর্তন করুন"):
        old_p = st.text_input("পুরোনো পাসওয়ার্ড", type="password", key="old_p")
        new_p = st.text_input("নতুন পাসওয়ার্ড", type="password", key="new_p")
        if st.button("আপডেট পাসওয়ার্ড"):
            curr_user = st.session_state.get("username")
            c.execute("SELECT password FROM users WHERE username=?", (curr_user,))
            db_pass = c.fetchone()[0]
            if old_p == db_pass:
                c.execute("UPDATE users SET password=? WHERE username=?", (new_p, curr_user))
                conn.commit()
                st.success("পাসওয়ার্ড সফলভাবে পরিবর্তন হয়েছে!")
            else:
                st.error("পুরোনো পাসওয়ার্ড ভুল!")
                
    st.write("---")
    if st.button("লগআউট (Logout)"):
        st.session_state["logged_in"] = False
        st.session_state["user_role"] = None
        st.session_state["username"] = None
        st.rerun()
# ================= ২. সাইডবারে লগআউট বাটন =================
with st.sidebar:
    st.write(f"👤 ইউজার: **{st.session_state.get('user_role')}**")
    if st.button("লগআউট (Logout)"):
        st.session_state["logged_in"] = False
        st.session_state["user_role"] = None
        st.rerun()
# =========================================================
# ===================================================
conn = sqlite3.connect('mediseller_delivery.db', check_same_thread=False)
c = conn.cursor()

# টেবিল তৈরি
c.execute('''
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        party_name TEXT,
        address TEXT,
        lat REAL,
        lon REAL,
        route_order INTEGER DEFAULT 0
    )
''')
conn.commit()

st.title("🚚 পি এস মেডিসেলার - ডেলিভারি ও রুট প্ল্যানার")

# সাইডবার - রোল ও অ্যাডমিন কন্ট্রোল
st.sidebar.header("🔐 সিস্টেম এক্সেস")
user_role = st.sidebar.radio("আপনার রোল সিলেক্ট করুন:", ["ডেলিভারি ম্যান / ইউজার", "অ্যাডমিন (মেইন কন্ট্রোল)"])

if user_role == "অ্যাডমিন (মেইন কন্ট্রোল)":
    password = st.sidebar.text_input("অ্যাডমিন পাসওয়ার্ড দিন:", type="password")
    is_admin = (password == "admin123")
    if not is_admin and password != "":
        st.sidebar.error("ভুল পাসওয়ার্ড!")
else:
    is_admin = False

# মেনু নির্বাচন
menu = ["📍 নতুন লোকেশন এড করুন", "🔍 পার্টি ও লোকেশন সার্চ", "🗺️ রুট প্ল্যানিং ও ম্যাপ"]
choice = st.sidebar.selectbox("মেনু নির্বাচন করুন", menu)

# ১. নতুন লোকেশন এড করা (লাইভ GPS ইন্টিগ্রেশনসহ)
if choice == "📍 নতুন লোকেশন এড করুন":
    st.subheader("নতুন পার্টির ডেলিভারি লোকেশন যোগ করুন")
    
    # সেশন স্টেট ইনিশিয়ালাইজেশন
    if 'selected_lat' not in st.session_state:
        st.session_state['selected_lat'] = 22.8620
    if 'selected_lon' not in st.session_state:
        st.session_state['selected_lon'] = 87.3320

    col_gps, col_search = st.columns([1, 2])
    
    # ডিভাইস GPS ক্যাপচার
    with col_gps:
        st.write("📍 **লাইভ লোকেশন:**")
        loc = get_geolocation()
        if loc and 'coords' in loc:
            st.session_state['selected_lat'] = loc['coords']['latitude']
            st.session_state['selected_lon'] = loc['coords']['longitude']
            st.success("আপনার বর্তমান লোকেশন পাওয়া গেছে!")

    # স্থান সার্চ
    with col_search:
        search_place = st.text_input("অথবা স্থানের নাম লিখে সার্চ করুন:")
        if st.button("স্থান খুঁজুন"):
            if search_place:
                try:
                    geolocator = Nominatim(user_agent="mediseller_app")
                    location = geolocator.geocode(search_place + ", West Bengal, India")
                    if location:
                        st.session_state['selected_lat'] = location.latitude
                        st.session_state['selected_lon'] = location.longitude
                        st.success(f"'{search_place}' খুঁজে পাওয়া গেছে!")
                    else:
                        st.error("স্থানটি পাওয়া যায়নি।")
                except Exception as e:
                    st.error("সমস্যা হয়েছে, ম্যাপ ব্যবহার করুন।")

    st.write("👉 **ম্যাপে ক্লিক করে বা পিন সরিয়েও লোকেশন সেট করতে পারেন:**")

    # ম্যাপ ডিসপ্লে
    m_click = folium.Map(location=[st.session_state['selected_lat'], st.session_state['selected_lon']], zoom_start=15, tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google Maps')
        
    gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={st.session_state['selected_lat']},{st.session_state['selected_lon']}"

    folium.Marker(
            [st.session_state['selected_lat'], st.session_state['selected_lon']],
            popup=f'<a href="{gmaps_url}" target="_blank" style="display:inline-block; padding:6px 10px; background:#4285F4; color:white; border-radius:4px; text-decoration:none; font-weight:bold;">Google Maps-এ নেভিগেট করুন</a>',
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m_click)

    map_data = st_folium(m_click, width=800, height=400)
    
    if map_data and map_data.get("last_clicked"):
        st.session_state['selected_lat'] = map_data["last_clicked"]["lat"]
        st.session_state['selected_lon'] = map_data["last_clicked"]["lng"]

    st.markdown("---")
    st.write("📝 **পার্টির তথ্য পূরণ করুন:**")
    
    party_name = st.text_input("পার্টির নাম (Party Name)")
    address = st.text_input("ঠিকানা / এরিয়া (Address)")
    party_phone = st.text_input("ফোন নম্বর:")
    
    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input("অক্ষাংশ (Latitude)", value=st.session_state['selected_lat'], format="%.6f")
    with col2:
        lon = st.number_input("দ্রাঘিমাংশ (Longitude)", value=st.session_state['selected_lon'], format="%.6f")

    if st.button("লোকেশন সেভ করুন"):
        if party_name and lat != 0.0 and lon != 0.0:
            c.execute("INSERT INTO locations (party_name, address, phone, lat, lon) VALUES (?, ?, ?, ?, ?)",
                      (party_name, address, party_phone, lat, lon))       
            conn.commit()
            st.success(f"'{party_name}' এর লোকেশন সফলভাবে সেভ হয়েছে!")
        else:
            st.warning("অনুগ্রহ করে পার্টির নাম দিন।")

# ২. পার্টি ও লোকেশন সার্চ
elif choice == "🔍 পার্টি ও লোকেশন সার্চ":
    st.subheader("পার্টি নাম বা স্থান দিয়ে তথ্য খুঁজুন")
    search_query = st.text_input("পার্টির নাম বা এলাকা লিখে সার্চ করুন:")
    
    df = pd.read_sql_query("SELECT id, party_name as 'পার্টি', address as 'ঠিকানা', lat as 'Lat', lon as 'Lon', route_order as 'রুট ক্রম' FROM locations", conn)
    
    if search_query:
        df = df[df['পার্টি'].str.contains(search_query, case=False, na=False) | 
                df['ঠিকানা'].str.contains(search_query, case=False, na=False)]
    
    st.dataframe(df, use_container_width=True)
    
    if is_admin:
        st.markdown("---")
        st.subheader("⚠️ অ্যাডমিন কন্ট্রোল: রেকর্ড মুছে ফেলুন")
        del_id = st.number_input("যে রেকর্ড ডিলিট করতে চান তার ID দিন:", min_value=1, step=1)
        if st.button("রেকর্ড মুছুন"):
            c.execute("DELETE FROM locations WHERE id = ?", (del_id,))
            conn.commit()
            st.success(f"ID {del_id} ডিলিট করা হয়েছে।")
            st.rerun()

# ৩. রুট প্ল্যানিং ও ম্যাপ
elif choice == "🗺️ রুট প্ল্যানিং ও ম্যাপ":
    st.subheader("ডেলিভারি রুট ম্যাপ ও সিকোয়েন্স সাজানো")
    
    locations = pd.read_sql_query("SELECT * FROM locations ORDER BY route_order ASC", conn)
    
    if not locations.empty:
        if is_admin:
            st.write("📋 **ডেলিভারির ক্রম সাজান (রুট প্ল্যানিং):**")
            for idx, row in locations.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.write(f"**{row['party_name']}** ({row['address']})")
                new_order = col2.number_input(f"ক্রম (ID: {row['id']})", value=int(row['route_order']), key=f"ord_{row['id']}")
                if new_order != row['route_order']:
                    c.execute("UPDATE locations SET route_order = ? WHERE id = ?", (new_order, row['id']))
                    conn.commit()
            if st.button("রুট সেভ করুন"):
                st.rerun()

        start_lat = locations.iloc[0]['lat']
        start_lon = locations.iloc[0]['lon']
        
        m = folium.Map(location=[start_lat, start_lon], zoom_start=12)
        
        points = []
        for idx, row in locations.iterrows():
            pos = [row['lat'], row['lon']]
            points.append(pos)
            
           popup_text = f"<b>{row['party_name']}</b><br>{row['address']}<br>ক্রম: {row['route_order']}<br><a href='tel:{row.get('phone', '')}' style='display:inline-block; margin-top:5px; padding:3px 8px; background:#28a745; color:white; border-radius:3px; text-decoration:none;'>📞 কল করুন</a>"
            folium.Marker(
                location=pos,
                popup=popup_text,
                tooltip=f"{row['party_name']} (ক্রম: {row['route_order']})",
                icon=folium.Icon(color="red" if row['route_order'] == 0 else "blue", icon="info-sign")
            ).add_to(m)
        
        if len(points) > 1:
            folium.PolyLine(points, color="green", weight=3, opacity=0.8).add_to(m)
            
        st_folium(m, width=900, height=500)
    else:
        # ================= অ্যাডমিন ডিলিট সেকশন =================
if st.session_state.get("user_role") == "admin":
    st.write("---")
    st.subheader("🗑️ পার্টি ডিলিট করুন (অ্যাডমিন মোড)")
    
    # ডেটাবেস থেকে সব পার্টির তালিকা আনা
    c.execute("SELECT id, party_name FROM locations")
    all_parties = c.fetchall()
    
    if all_parties:
        party_dict = {f"{p[1]} (ID: {p[0]})": p[0] for p in all_parties}
        selected_party = st.selectbox("যে পার্টিটি মুছে ফেলতে চান তা সিলেক্ট করুন:", list(party_dict.keys()))
        
        if st.button("পার্টিটি ডিলিট করুন", type="primary"):
            target_id = party_dict[selected_party]
            c.execute("DELETE FROM locations WHERE id=?", (target_id,))
            conn.commit()
            st.success("পার্টি সফলভাবে ডিলিট করা হয়েছে!")
            st.rerun()
        st.info("এখনো কোনো লোকেশন সেভ করা হয়নি।")
