import streamlit as st
import pandas as pd
import sqlite3
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from streamlit_js_eval import get_geolocation


# =========================================================
# PAGE CONFIGURATION & PWA / INSTALL SETTINGS
# =========================================================

st.set_page_config(
    page_title="P.S Mediseller",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# PWA Metadata for Add to Home Screen (App Installation)
st.markdown("""
    <head>
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="application-name" content="P.S Mediseller">
        <meta name="apple-mobile-web-app-title" content="P.S Mediseller">
        <meta name="theme-color" content="#FF4B4B">
    </head>
""", unsafe_allow_html=True)


# =========================================================
# DATABASE (Real-time Sync Friendly)
# =========================================================

DB_FILE = "mediseller_delivery.db"

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

conn = get_db_connection()
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    party_name TEXT NOT NULL,
    address TEXT,
    party_phone TEXT,
    lat REAL,
    lon REAL,
    route_order INTEGER DEFAULT 0
)
""")

c.execute("PRAGMA table_info(locations)")
existing_columns = [row[1] for row in c.fetchall()]

if "party_phone" not in existing_columns:
    c.execute("ALTER TABLE locations ADD COLUMN party_phone TEXT")

if "route_order" not in existing_columns:
    c.execute("ALTER TABLE locations ADD COLUMN route_order INTEGER DEFAULT 0")
conn.commit()


# =========================================================
# DEFAULT USERS
# =========================================================

c.execute("SELECT COUNT(*) FROM users")
user_count = c.fetchone()[0]

if user_count == 0:
    c.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin", "admin123", "admin")
    )
    c.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        ("delivery", "user123", "staff")
    )
    conn.commit()


# =========================================================
# SESSION & AUTO-LOGIN MANAGEMENT
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "username" not in st.session_state:
    st.session_state["username"] = None

if "user_role" not in st.session_state:
    st.session_state["user_role"] = None

if "selected_lat" not in st.session_state:
    st.session_state["selected_lat"] = 22.8620

if "selected_lon" not in st.session_state:
    st.session_state["selected_lon"] = 87.3320

query_params = st.query_params
if not st.session_state["logged_in"]:
    saved_user = query_params.get("user", None)
    if saved_user:
        c.execute("SELECT role FROM users WHERE username=?", (saved_user,))
        role_data = c.fetchone()
        if role_data:
            st.session_state["logged_in"] = True
            st.session_state["username"] = saved_user
            st.session_state["user_role"] = role_data[0]


# =========================================================
# LOGIN PAGE
# =========================================================

if not st.session_state["logged_in"]:

    st.title("🔑 লগইন পোর্টাল")
    st.subheader("P.S Mediseller Location App")

    # লগইন পেজেই ইনস্টল নির্দেশিকা
    st.info("📲 **ফোনে অ্যাপ হিসেবে ইনস্টল করুন:**\n\nব্রাউজারের ৩টি ডট (⋮) মেনুতে ক্লিক করে **'Install App'** বা **'Add to Home screen'** অপশনে চাপ দিন।")

    tab1, tab2 = st.tabs(["লগইন", "পাসওয়ার্ড ভুলে গেছেন?"])

    with tab1:
        username = st.text_input("ইউজারনেম", key="login_user")
        password = st.text_input("পাসওয়ার্ড", type="password", key="login_pass")
        remember_me = st.checkbox("আমাকে মনে রাখুন (Auto Login)", value=True)

        if st.button("লগইন করুন", type="primary"):
            c.execute("SELECT password, role FROM users WHERE username=?", (username,))
            user_data = c.fetchone()

            if user_data and user_data[0] == password:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["user_role"] = user_data[1]

                if remember_me:
                    st.query_params["user"] = username

                st.success("লগইন সফল হয়েছে!")
                st.rerun()
            else:
                st.error("❌ ভুল ইউজারনেম অথবা পাসওয়ার্ড!")

    with tab2:
        st.write("অ্যাডমিন পাসওয়ার্ড ব্যবহার করে ইউজারের পাসওয়ার্ড পরিবর্তন করুন।")
        f_user = st.text_input("ইউজারনেম", key="forgot_user")
        new_pass = st.text_input("নতুন পাসওয়ার্ড", type="password", key="new_pass_admin")
        admin_pass = st.text_input("বর্তমান অ্যাডমিন পাসওয়ার্ড", type="password", key="admin_auth")

        if st.button("পাসওয়ার্ড রিসেট করুন"):
            c.execute("SELECT password FROM users WHERE username='admin'")
            admin_data = c.fetchone()

            if admin_data and admin_pass == admin_data[0]:
                c.execute("SELECT username FROM users WHERE username=?", (f_user,))
                user_exists = c.fetchone()

                if user_exists:
                    if new_pass:
                        c.execute("UPDATE users SET password=? WHERE username=?", (new_pass, f_user))
                        conn.commit()
                        st.success("✅ পাসওয়ার্ড সফলভাবে পরিবর্তন হয়েছে।")
                    else:
                        st.error("নতুন পাসওয়ার্ড দিন।")
                else:
                    st.error("এই ইউজারনেম পাওয়া যায়নি।")
            else:
                st.error("❌ অ্যাডমিন পাসওয়ার্ড ভুল!")

    st.stop()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.header("👤 ইউজার তথ্য")
    st.write(f"ইউজার: **{st.session_state['username']}**")

    if st.session_state["user_role"] == "admin":
        st.success("রোল: ADMIN")
    else:
        st.info("রোল: DELIVERY USER")

    with st.expander("📲 ফোনে অ্যাপ হিসেবে ইনস্টল করুন"):
        st.write("**Android Chrome এ:**")
        st.caption("১. উপরে ডানদিকের ৩টি ডট-এ (⋮) ক্লিক করুন।")
        st.caption("২. **'Add to Home screen'** বা **'Install App'** নির্বাচন করুন।")

    st.write("---")

    with st.expander("🔒 নিজ পাসওয়ার্ড পরিবর্তন করুন"):
        old_p = st.text_input("পুরোনো পাসওয়ার্ড", type="password", key="old_password")
        new_p = st.text_input("নতুন পাসওয়ার্ড", type="password", key="new_password")

        if st.button("পাসওয়ার্ড আপডেট করুন"):
            curr_user = st.session_state["username"]
            c.execute("SELECT password FROM users WHERE username=?", (curr_user,))
            db_data = c.fetchone()

            if db_data and old_p == db_data[0]:
                if new_p:
                    c.execute("UPDATE users SET password=? WHERE username=?", (new_p, curr_user))
                    conn.commit()
                    st.success("✅ পাসওয়ার্ড পরিবর্তন হয়েছে।")
                else:
                    st.error("নতুন পাসওয়ার্ড দিন।")
            else:
                st.error("❌ পুরোনো পাসওয়ার্ড ভুল!")

    if st.session_state["user_role"] == "admin":
        with st.expander("⚙️ অ্যাডমিন কন্ট্রোল (ID ও পাসওয়ার্ড ম্যানেজমেন্ট)"):
            c.execute("SELECT username, role FROM users")
            all_users = c.fetchall()
            user_list = [u[0] for u in all_users]

            selected_u = st.selectbox("ইউজার নির্বাচন করুন", user_list)
            
            new_u_id = st.text_input("নতুন ইউজার ID (Username)", value=selected_u, key="edit_u_id")
            new_u_pass = st.text_input("নতুন পাসওয়ার্ড (ঐচ্ছিক)", type="password", key="edit_u_pass")

            if st.button("💾 আইডি/পাসওয়ার্ড আপডেট করুন"):
                if not new_u_id.strip():
                    st.error("❌ ইউজার আইডি ফাঁকা রাখা যাবে না।")
                else:
                    try:
                        if new_u_id != selected_u:
                            c.execute("UPDATE users SET username=? WHERE username=?", (new_u_id, selected_u))
                            if selected_u == st.session_state["username"]:
                                st.session_state["username"] = new_u_id
                                if "user" in st.query_params:
                                    st.query_params["user"] = new_u_id

                        if new_u_pass.strip():
                            c.execute("UPDATE users SET password=? WHERE username=?", (new_u_pass, new_u_id))

                        conn.commit()
                        st.success("✅ আইডি/পাসওয়ার্ড সফলভাবে আপডেট হয়েছে!")
                        st.rerun()

                    except sqlite3.IntegrityError:
                        st.error("❌ এই ইউজার আইডিটি আগেই অন্য কেউ ব্যবহার করছে।")

    st.write("---")

    if st.button("🚪 লগআউট"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.session_state["user_role"] = None
        st.query_params.clear()
        st.rerun()


# =========================================================
# MAIN TITLE & GPS
# =========================================================

st.title("🚚 পি এস মেডিসেলার")
st.subheader("ডেলিভারি ও রুট প্ল্যানার")

st.write("📍 **লাইভ GPS লোকেশন ট্র্যাকিং:**")

loc = get_geolocation(component_key="global_gps")

gps_lat = None
gps_lon = None

if loc and "coords" in loc:
    gps_lat = loc["coords"]["latitude"]
    gps_lon = loc["coords"]["longitude"]
    st.success(f"✅ আপনার বর্তমান GPS লোকেশন অ্যাক্টিভ (Lat: {gps_lat:.6f}, Lon: {gps_lon:.6f})")

is_admin = (st.session_state["user_role"] == "admin")


# =========================================================
# MENU
# =========================================================

menu = [
    "📍 নতুন লোকেশন এড করুন",
    "🔍 পার্টি ও লোকেশন সার্চ",
    "🗺️ রুট প্ল্যানিং ও ম্যাপ"
]

choice = st.sidebar.selectbox("মেনু নির্বাচন করুন", menu)


# =========================================================
# 1. ADD NEW LOCATION
# =========================================================

if choice == "📍 নতুন লোকেশন এড করুন":

    st.header("📍 নতুন পার্টির লোকেশন যোগ করুন")
    col1, col2 = st.columns([1, 1])

    with col1:
        st.write("### 📍 বর্তমান জিপিএস কোঅর্ডিনেট")
        st.info(f"অক্ষাংশ (Lat): {st.session_state['selected_lat']:.6f}\n\nদ্রাঘিমাংশ (Lon): {st.session_state['selected_lon']:.6f}")
        
        if st.button("🔄 বর্তমান লোকেশন রিফ্রেশ করুন", type="secondary"):
            if gps_lat and gps_lon:
                st.session_state["selected_lat"] = gps_lat
                st.session_state["selected_lon"] = gps_lon
                st.success("✅ লাল পিনটি আপনার বর্তমান কারেন্ট লোকেশনে সেট হয়েছে!")
                st.rerun()
            else:
                st.warning("⚠️ GPS সিগন্যাল পাওয়া যাচ্ছে না, অনুগ্রহ করে লোকেশন পারমিশন চেক করুন।")

    with col2:
        st.write("### 🔍 জায়গা সার্চ")
        search_place = st.text_input("স্থান / এলাকার নাম লিখুন")

        if st.button("স্থান খুঁজুন"):
            if search_place:
                try:
                    geolocator = Nominatim(user_agent="ps_mediseller_location_app")
                    location = geolocator.geocode(search_place + ", West Bengal, India")

                    if location:
                        st.session_state["selected_lat"] = location.latitude
                        st.session_state["selected_lon"] = location.longitude
                        st.success(f"✅ {search_place} পাওয়া গেছে।")
                        st.rerun()
                    else:
                        st.error("স্থানটি পাওয়া যায়নি।")
                except Exception:
                    st.error("স্থান সার্চে সমস্যা হয়েছে।")
            else:
                st.warning("স্থান লিখুন।")

        st.write("---")
        st.write("### 🔍 পার্টি সার্চ করুন")
        
        c.execute("SELECT party_name, address, party_phone, lat, lon FROM locations ORDER BY party_name ASC")
        saved_parties = c.fetchall()

        if saved_parties:
            party_options = ["-- পার্টি বেছে নিন --"] + [f"{p[0]} ({p[1]})" for p in saved_parties]
            selected_party_str = st.selectbox("পার্টির নাম লিখে খুঁজুন", party_options, key="quick_party_select")

            if selected_party_str != "-- পার্টি বেছে নিন --":
                idx = party_options.index(selected_party_str) - 1
                p_name, p_address, p_phone, p_lat, p_lon = saved_parties[idx]
                
                if (st.session_state["selected_lat"] != p_lat) or (st.session_state["selected_lon"] != p_lon):
                    st.session_state["selected_lat"] = p_lat
                    st.session_state["selected_lon"] = p_lon
                    st.rerun()

                gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={p_lat},{p_lon}"
                
                st.success(f"🏢 **পার্টির নাম:** {p_name}")
                st.write(f"📞 **ফোন:** {p_phone if p_phone else 'নাই'}")
                st.write(f"📍 **ঠিকানা:** {p_address if p_address else 'নাই'}")
                st.link_button("🗺️ গুগল ম্যাপস ডাইরেকশন (Navigate)", gmaps_url, type="primary")

        else:
            st.caption("এখনো কোনো পার্টি সেভ করা হয়নি।")

    st.write("---")
    st.write("### 🗺️ ম্যাপে লোকেশন নির্বাচন করুন")
    st.caption("💡 **টিপস:** ম্যাপের লাল পিনটি (Marker) হাত দিয়ে বা মাউস দিয়ে টেনে (Drag করে) যেকোনো জায়গায় বসান, অথবা ম্যাপের যেকোনো খালি জায়গায় সরাসরি ক্লিক করুন।")

    current_lat = float(st.session_state["selected_lat"])
    current_lon = float(st.session_state["selected_lon"])

    google_tiles = 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}'
    
    m_click = folium.Map(
        location=[current_lat, current_lon], 
        zoom_start=15,
        tiles=google_tiles,
        attr="Google Maps"
    )
    
    folium.Marker(
        [current_lat, current_lon],
        tooltip="পিনটি টেনে সঠিক স্থানে বসান",
        popup="নির্বাচিত লোকেশন",
        icon=folium.Icon(color="red", icon="info-sign"),
        draggable=True
    ).add_to(m_click)

    map_data = st_folium(m_click, width=900, height=450, key="interactive_map")

    updated_lat = None
    updated_lon = None

    if map_data:
        if map_data.get("last_marker_dragged"):
            updated_lat = map_data["last_marker_dragged"]["lat"]
            updated_lon = map_data["last_marker_dragged"]["lng"]
        elif map_data.get("last_clicked"):
            updated_lat = map_data["last_clicked"]["lat"]
            updated_lon = map_data["last_clicked"]["lng"]

    if updated_lat and updated_lon:
        if (abs(st.session_state["selected_lat"] - updated_lat) > 0.0001) or (abs(st.session_state["selected_lon"] - updated_lon) > 0.0001):
            st.session_state["selected_lat"] = updated_lat
            st.session_state["selected_lon"] = updated_lon
            st.rerun()

    st.write("---")
    st.write("### 📝 নতুন পার্টি সেভ করুন")

    party_name = st.text_input("পার্টি / দোকানের নাম")
    address = st.text_input("ঠিকানা / এলাকা")
    party_phone = st.text_input("ফোন নম্বর")

    col_lat, col_lon = st.columns(2)
    with col_lat:
        lat = st.number_input("অক্ষাংশ (Latitude)", value=float(st.session_state["selected_lat"]), format="%.6f")
    with col_lon:
        lon = st.number_input("দ্রাঘিমাংশ (Longitude)", value=float(st.session_state["selected_lon"]), format="%.6f")

    if st.button("💾 লোকেশন সেভ করুন", type="primary"):
        if not party_name:
            st.error("❌ পার্টির নাম দিন।")
        elif not party_phone:
            st.error("❌ ফোন নম্বর দিন।")
        else:
            c.execute(
                "INSERT INTO locations (party_name, address, party_phone, lat, lon, route_order) VALUES (?, ?, ?, ?, ?, ?)",
                (party_name, address, party_phone, lat, lon, 0)
            )
            conn.commit()
            st.success("✅ পার্টির লোকেশন সফলভাবে সেভ হয়েছে!")
            st.rerun()


# =========================================================
# 2. SEARCH PARTY
# =========================================================

elif choice == "🔍 পার্টি ও লোকেশন সার্চ":

    st.header("🔍 পার্টি ও লোকেশন সার্চ")

    search_query = st.text_input("পার্টির নাম / এলাকা / ফোন নম্বর দিয়ে সার্চ করুন")

    df = pd.read_sql_query("SELECT * FROM locations ORDER BY route_order ASC, id ASC", conn)

    if search_query:
        search_text = search_query.lower()
        df = df[
            df["party_name"].fillna("").str.lower().str.contains(search_text) |
            df["address"].fillna("").str.lower().str.contains(search_text) |
            df["party_phone"].fillna("").str.lower().str.contains(search_text)
        ]

    if not df.empty:
        df["Google Maps Direction"] = df.apply(
            lambda row: f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}", 
            axis=1
        )

        st.subheader("📋 পার্টির তালিকা")

        st.dataframe(
            df[["route_order", "party_name", "address", "party_phone", "Google Maps Direction"]],
            column_config={
                "route_order": "ক্রম",
                "party_name": "পার্টি",
                "address": "ঠিকানা",
                "party_phone": "ফোন নম্বর",
                "Google Maps Direction": st.column_config.LinkColumn(
                    "গুগল ম্যাপস নেভিগেশন",
                    display_text="🗺️ Direction"
                )
            },
            use_container_width=True,
            hide_index=True
        )

    else:
        st.warning("কোনো পার্টির তথ্য পাওয়া যায়নি।")

    if is_admin and not df.empty:
        st.write("---")
        st.subheader("🗑️ অ্যাডমিন কন্ট্রোল")

        delete_options = {f"{row['party_name']} - ID: {row['id']}": int(row["id"]) for _, row in df.iterrows()}
        selected_delete = st.selectbox("যে পার্টিটি ডিলিট করবেন:", list(delete_options.keys()))

        if st.button("🗑️ পার্টি ডিলিট করুন", type="primary"):
            c.execute("DELETE FROM locations WHERE id=?", (delete_options[selected_delete],))
            conn.commit()
            st.success("✅ পার্টি সফলভাবে ডিলিট হয়েছে।")
            st.rerun()


# =========================================================
# 3. ROUTE PLANNING & MAP
# =========================================================

elif choice == "🗺️ রুট প্ল্যানিং ও ম্যাপ":

    st.header("🗺️ ডেলিভারি রুট প্ল্যানিং")

    locations = pd.read_sql_query("SELECT * FROM locations ORDER BY route_order ASC, id ASC", conn)

    if locations.empty:
        st.info("এখনো কোনো লোকেশন সেভ করা হয়নি।")
    else:
        if is_admin:
            st.subheader("📋 ডেলিভারির ক্রম সাজান")

            for _, row in locations.iterrows():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{row['party_name']}**")
                    st.caption(f"{row['address']} | 📞 {row['party_phone']}")
                with col2:
                    new_order = st.number_input(
                        f"ক্রম ID {row['id']}",
                        min_value=0,
                        value=int(row["route_order"]),
                        step=1,
                        key=f"route_order_{row['id']}"
                    )

                if new_order != int(row["route_order"]):
                    c.execute("UPDATE locations SET route_order=? WHERE id=?", (new_order, int(row["id"])))
                    conn.commit()

            if st.button("💾 রুট সেভ করুন", type="primary"):
                st.success("✅ রুট সেভ হয়েছে।")
                st.rerun()

        locations = pd.read_sql_query("SELECT * FROM locations ORDER BY route_order ASC, id ASC", conn)

        start_lat = float(locations.iloc[0]["lat"])
        start_lon = float(locations.iloc[0]["lon"])

        google_tiles = 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}'

        m = folium.Map(
            location=[start_lat, start_lon], 
            zoom_start=12,
            tiles=google_tiles,
            attr="Google Maps"
        )
        points = []

        for _, row in locations.iterrows():
            lat_val, lon_val = float(row["lat"]), float(row["lon"])
            points.append([lat_val, lon_val])

            google_maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat_val},{lon_val}"

            popup_html = f"""
            <div style="width:200px">
                <b>{row['party_name']}</b><br>
                📍 {row['address']}<br>
                📞 {row['party_phone']}<br><br>
                <a href="tel:{row['party_phone']}" style="padding:5px 8px; background:#28a745; color:white; text-decoration:none; border-radius:4px;">📞 কল</a>
                <a href="{google_maps_url}" target="_blank" style="padding:5px 8px; background:#4285F4; color:white; text-decoration:none; border-radius:4px;">🗺️ Navigate</a>
            </div>
            """

            folium.Marker(
                location=[lat_val, lon_val],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{row['route_order']}. {row['party_name']}",
                icon=folium.Icon(color="red" if int(row["route_order"]) == 0 else "blue", icon="info-sign")
            ).add_to(m)

        if len(points) > 1:
            folium.PolyLine(points, color="green", weight=4, opacity=0.8).add_to(m)

        st_folium(m, width=1000, height=550)

        st.write("---")
        st.subheader("📋 ডেলিভারি রুট তালিকা")

        locations["Google Maps Direction"] = locations.apply(
            lambda row: f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}", 
            axis=1
        )

        st.dataframe(
            locations[["route_order", "party_name", "address", "party_phone", "Google Maps Direction"]],
            column_config={
                "route_order": "ক্রম",
                "party_name": "পার্টি",
                "address": "ঠিকানা",
                "party_phone": "ফোন",
                "Google Maps Direction": st.column_config.LinkColumn(
                    "গুগল ম্যাপস ডাইরেকশন",
                    display_text="🗺️ Direction"
                )
            },
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# FOOTER
# =========================================================

st.write("---")
st.caption("P.S Mediseller Location App | Delivery Route Management System")
