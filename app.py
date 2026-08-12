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
    m_click = folium.Map(location=[st.session_state['selected_lat'], st.session_state['selected_lon']], zoom_start=15)
    folium.Marker(
        [st.session_state['selected_lat'], st.session_state['selected_lon']],
        popup="নির্বাচিত স্থান",
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
    
    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input("অক্ষাংশ (Latitude)", value=st.session_state['selected_lat'], format="%.6f")
    with col2:
        lon = st.number_input("দ্রাঘিমাংশ (Longitude)", value=st.session_state['selected_lon'], format="%.6f")

    if st.button("লোকেশন সেভ করুন"):
        if party_name and lat != 0.0 and lon != 0.0:
            c.execute("INSERT INTO locations (party_name, address, lat, lon) VALUES (?, ?, ?, ?)",
                      (party_name, address, lat, lon))
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
            
            popup_text = f"<b>{row['party_name']}</b><br>{row['address']}<br>ক্রম: {row['route_order']}"
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
        st.info("এখনো কোনো লোকেশন সেভ করা হয়নি।")