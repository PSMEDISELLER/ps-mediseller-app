import streamlit as st
import pandas as pd
import sqlite3
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from streamlit_js_eval import get_geolocation


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="P.S Mediseller Location App",
    page_icon="🚚",
    layout="wide"
)


# =========================================================
# DATABASE
# =========================================================

DB_FILE = "mediseller_delivery.db"

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()


# Users table
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
""")


# Locations table
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
# পুরোনো database-এর locations table ঠিক করা
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
# SESSION STATE
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


# =========================================================
# LOGIN PAGE
# =========================================================

if not st.session_state["logged_in"]:

    st.title("🔑 লগইন পোর্টাল")
    st.subheader("P.S Mediseller Location App")

    tab1, tab2 = st.tabs(["লগইন", "পাসওয়ার্ড ভুলে গেছেন?"])


    # -----------------------------------------------------
    # LOGIN
    # -----------------------------------------------------

    with tab1:

        username = st.text_input(
            "ইউজারনেম",
            key="login_user"
        )

        password = st.text_input(
            "পাসওয়ার্ড",
            type="password",
            key="login_pass"
        )

        if st.button("লগইন করুন", type="primary"):

            c.execute(
                "SELECT password, role FROM users WHERE username=?",
                (username,)
            )

            user_data = c.fetchone()

            if user_data and user_data[0] == password:

                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["user_role"] = user_data[1]

                st.success("লগইন সফল হয়েছে!")
                st.rerun()

            else:

                st.error("❌ ভুল ইউজারনেম অথবা পাসওয়ার্ড!")


    # -----------------------------------------------------
    # FORGOT PASSWORD
    # -----------------------------------------------------

    with tab2:

        st.write("অ্যাডমিন পাসওয়ার্ড ব্যবহার করে ইউজারের পাসওয়ার্ড পরিবর্তন করুন।")

        f_user = st.text_input(
            "ইউজারনেম",
            key="forgot_user"
        )

        new_pass = st.text_input(
            "নতুন পাসওয়ার্ড",
            type="password",
            key="new_pass_admin"
        )

        admin_pass = st.text_input(
            "বর্তমান অ্যাডমিন পাসওয়ার্ড",
            type="password",
            key="admin_auth"
        )

        if st.button("পাসওয়ার্ড রিসেট করুন"):

            c.execute(
                "SELECT password FROM users WHERE username='admin'"
            )

            admin_data = c.fetchone()

            if admin_data and admin_pass == admin_data[0]:

                c.execute(
                    "SELECT username FROM users WHERE username=?",
                    (f_user,)
                )

                user_exists = c.fetchone()

                if user_exists:

                    if new_pass:

                        c.execute(
                            "UPDATE users SET password=? WHERE username=?",
                            (new_pass, f_user)
                        )

                        conn.commit()

                        st.success(
                            "✅ পাসওয়ার্ড সফলভাবে পরিবর্তন হয়েছে।"
                        )

                    else:

                        st.error("নতুন পাসওয়ার্ড দিন।")

                else:

                    st.error("এই ইউজারনেম পাওয়া যায়নি।")

            else:

                st.error("❌ অ্যাডমিন পাসওয়ার্ড ভুল!")


    st.stop()


# =========================================================
# SIDEBAR USER INFORMATION
# =========================================================

with st.sidebar:

    st.header("👤 ইউজার তথ্য")

    st.write(
        f"ইউজার: **{st.session_state['username']}**"
    )

    if st.session_state["user_role"] == "admin":

        st.success("রোল: ADMIN")

    else:

        st.info("রোল: DELIVERY USER")


    # -----------------------------------------------------
    # CHANGE PASSWORD
    # -----------------------------------------------------

    with st.expander("🔒 পাসওয়ার্ড পরিবর্তন করুন"):

        old_p = st.text_input(
            "পুরোনো পাসওয়ার্ড",
            type="password",
            key="old_password"
        )

        new_p = st.text_input(
            "নতুন পাসওয়ার্ড",
            type="password",
            key="new_password"
        )

        if st.button("পাসওয়ার্ড আপডেট করুন"):

            curr_user = st.session_state["username"]

            c.execute(
                "SELECT password FROM users WHERE username=?",
                (curr_user,)
            )

            db_data = c.fetchone()

            if db_data and old_p == db_data[0]:

                if new_p:

                    c.execute(
                        "UPDATE users SET password=? WHERE username=?",
                        (new_p, curr_user)
                    )

                    conn.commit()

                    st.success(
                        "✅ পাসওয়ার্ড পরিবর্তন হয়েছে।"
                    )

                else:

                    st.error("নতুন পাসওয়ার্ড দিন।")

            else:

                st.error("❌ পুরোনো পাসওয়ার্ড ভুল!")


    st.write("---")


    # -----------------------------------------------------
    # LOGOUT
    # -----------------------------------------------------

    if st.button("🚪 লগআউট"):

        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.session_state["user_role"] = None

        st.rerun()


# =========================================================
# MAIN TITLE
# =========================================================

st.title("🚚 পি এস মেডিসেলার")
st.subheader("ডেলিভারি ও রুট প্ল্যানার")


# =========================================================
# CURRENT GPS LOCATION
# =========================================================

st.sidebar.write("---")
st.sidebar.subheader("📍 GPS")

st.write("📍 **লাইভ লোকেশন:**")

st.info("নিচের বাটনে চাপলে আপনার ব্রাউজার GPS permission চাইবে।")

loc = get_geolocation()

if loc:
    if "error" in loc:
        error_code = loc["error"].get("code")
        error_msg = loc["error"].get("message", "অজানা সমস্যা")

            if error_code == 1:
                st.error("❌ GPS permission দেওয়া হয়নি। Chrome-এ Location → Allow করুন।")
            elif error_code == 2:
                st.error("❌ আপনার বর্তমান GPS location পাওয়া যাচ্ছে না।")
            elif error_code == 3:
                st.error("❌ GPS-এর জন্য সময় শেষ হয়ে গেছে। আবার চেষ্টা করুন।")
            else:
                st.error(f"❌ GPS সমস্যা: {error_msg}")

        elif "coords" in loc:
            gps_lat = loc["coords"]["latitude"]
            gps_lon = loc["coords"]["longitude"]

            st.session_state["selected_lat"] = gps_lat
            st.session_state["selected_lon"] = gps_lon

            st.success("✅ আপনার বর্তমান GPS location পাওয়া গেছে!")

            st.write(f"Latitude: **{gps_lat:.6f}**")
            st.write(f"Longitude: **{gps_lon:.6f}**")

# =========================================================
# ADMIN STATUS
# =========================================================

is_admin = (
    st.session_state["user_role"] == "admin"
)


# =========================================================
# MENU
# =========================================================

menu = [
    "📍 নতুন লোকেশন এড করুন",
    "🔍 পার্টি ও লোকেশন সার্চ",
    "🗺️ রুট প্ল্যানিং ও ম্যাপ"
]

choice = st.sidebar.selectbox(
    "মেনু নির্বাচন করুন",
    menu
)


# =========================================================
# 1. ADD NEW LOCATION
# =========================================================

if choice == "📍 নতুন লোকেশন এড করুন":

    st.header("📍 নতুন পার্টির লোকেশন যোগ করুন")

    col1, col2 = st.columns([1, 2])


    # -----------------------------------------------------
    # GPS
    # -----------------------------------------------------

    with col1:

        st.write("### 📍 লাইভ লোকেশন")

        if st.button("বর্তমান GPS লোকেশন নিন"):

            gps = get_geolocation(
                component_key="add_location_gps"
            )

            if gps and "coords" in gps:

                st.session_state["selected_lat"] = (
                    gps["coords"]["latitude"]
                )

                st.session_state["selected_lon"] = (
                    gps["coords"]["longitude"]
                )

                st.success("লোকেশন পাওয়া গেছে।")

                st.rerun()

            else:

                st.error(
                    "GPS পাওয়া যায়নি। Location Permission চালু করুন।"
                )


    # -----------------------------------------------------
    # PLACE SEARCH
    # -----------------------------------------------------

    with col2:

        st.write("### 🔍 জায়গা সার্চ")

        search_place = st.text_input(
            "স্থান / এলাকার নাম লিখুন"
        )

        if st.button("স্থান খুঁজুন"):

            if search_place:

                try:

                    geolocator = Nominatim(
                        user_agent="ps_mediseller_location_app"
                    )

                    location = geolocator.geocode(
                        search_place + ", West Bengal, India"
                    )

                    if location:

                        st.session_state["selected_lat"] = (
                            location.latitude
                        )

                        st.session_state["selected_lon"] = (
                            location.longitude
                        )

                        st.success(
                            f"✅ {search_place} পাওয়া গেছে।"
                        )

                        st.rerun()

                    else:

                        st.error(
                            "স্থানটি পাওয়া যায়নি।"
                        )

                except Exception:

                    st.error(
                        "স্থান সার্চে সমস্যা হয়েছে।"
                    )

            else:

                st.warning("স্থান লিখুন।")


    # -----------------------------------------------------
    # MAP
    # -----------------------------------------------------

    st.write("---")
    st.write("### 🗺️ ম্যাপে লোকেশন নির্বাচন করুন")

    current_lat = st.session_state["selected_lat"]
    current_lon = st.session_state["selected_lon"]


    m_click = folium.Map(
        location=[current_lat, current_lon],
        zoom_start=15
    )


    folium.Marker(
        [current_lat, current_lon],
        tooltip="নির্বাচিত লোকেশন",
        popup="বর্তমান নির্বাচিত লোকেশন",
        icon=folium.Icon(
            color="red",
            icon="info-sign"
        )
    ).add_to(m_click)


    map_data = st_folium(
        m_click,
        width=900,
        height=450
    )


    # Click map to select location

    if map_data and map_data.get("last_clicked"):

        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lon = map_data["last_clicked"]["lng"]

        st.session_state["selected_lat"] = clicked_lat
        st.session_state["selected_lon"] = clicked_lon

        st.success(
            f"লোকেশন নির্বাচিত হয়েছে: "
            f"{clicked_lat:.6f}, {clicked_lon:.6f}"
        )

        st.rerun()


    # -----------------------------------------------------
    # PARTY INFORMATION
    # -----------------------------------------------------

    st.write("---")
    st.write("### 📝 পার্টির তথ্য")


    party_name = st.text_input(
        "পার্টির নাম"
    )

    address = st.text_input(
        "ঠিকানা / এলাকা"
    )

    party_phone = st.text_input(
        "ফোন নম্বর"
    )


    col_lat, col_lon = st.columns(2)


    with col_lat:

        lat = st.number_input(
            "অক্ষাংশ (Latitude)",
            value=float(st.session_state["selected_lat"]),
            format="%.6f"
        )


    with col_lon:

        lon = st.number_input(
            "দ্রাঘিমাংশ (Longitude)",
            value=float(st.session_state["selected_lon"]),
            format="%.6f"
        )


    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    if st.button(
        "💾 লোকেশন সেভ করুন",
        type="primary"
    ):

        if not party_name:

            st.error("❌ পার্টির নাম দিন।")

        elif not party_phone:

            st.error("❌ ফোন নম্বর দিন।")

        else:

            c.execute(
                """
                INSERT INTO locations
                (
                    party_name,
                    address,
                    party_phone,
                    lat,
                    lon,
                    route_order
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    party_name,
                    address,
                    party_phone,
                    lat,
                    lon,
                    0
                )
            )

            conn.commit()

            st.success(
                "✅ পার্টির লোকেশন সফলভাবে সেভ হয়েছে!"
            )

            st.rerun()


# =========================================================
# 2. SEARCH PARTY
# =========================================================

elif choice == "🔍 পার্টি ও লোকেশন সার্চ":

    st.header("🔍 পার্টি ও লোকেশন সার্চ")


    search_query = st.text_input(
        "পার্টির নাম / এলাকা / ফোন নম্বর দিয়ে সার্চ করুন"
    )


    df = pd.read_sql_query(
        """
        SELECT
            id,
            party_name AS 'পার্টি',
            address AS 'ঠিকানা',
            party_phone AS 'ফোন',
            lat AS 'Latitude',
            lon AS 'Longitude',
            route_order AS 'রুট ক্রম'
        FROM locations
        ORDER BY route_order ASC, id ASC
        """,
        conn
    )


    if search_query:

        search_text = search_query.lower()

        df = df[
            df["পার্টি"].fillna("").str.lower().str.contains(
                search_text
            )
            |
            df["ঠিকানা"].fillna("").str.lower().str.contains(
                search_text
            )
            |
            df["ফোন"].fillna("").str.lower().str.contains(
                search_text
            )
        ]


    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


    # -----------------------------------------------------
    # ADMIN DELETE
    # -----------------------------------------------------

    if is_admin:

        st.write("---")

        st.subheader("🗑️ অ্যাডমিন কন্ট্রোল")


        if not df.empty:

            delete_options = {
                f"{row['পার্টি']} - ID: {row['id']}":
                int(row["id"])
                for _, row in df.iterrows()
            }


            selected_delete = st.selectbox(
                "যে পার্টিটি ডিলিট করবেন:",
                list(delete_options.keys())
            )


            if st.button(
                "🗑️ পার্টি ডিলিট করুন",
                type="primary"
            ):

                delete_id = delete_options[selected_delete]

                c.execute(
                    "DELETE FROM locations WHERE id=?",
                    (delete_id,)
                )

                conn.commit()

                st.success(
                    "✅ পার্টি সফলভাবে ডিলিট হয়েছে।"
                )

                st.rerun()


# =========================================================
# 3. ROUTE PLANNING
# =========================================================

elif choice == "🗺️ রুট প্ল্যানিং ও ম্যাপ":

    st.header("🗺️ ডেলিভারি রুট প্ল্যানিং")


    locations = pd.read_sql_query(
        """
        SELECT *
        FROM locations
        ORDER BY route_order ASC, id ASC
        """,
        conn
    )


    if locations.empty:

        st.info(
            "এখনো কোনো লোকেশন সেভ করা হয়নি।"
        )

    else:

        # -------------------------------------------------
        # ADMIN ROUTE ORDER
        # -------------------------------------------------

        if is_admin:

            st.subheader(
                "📋 ডেলিভারির ক্রম সাজান"
            )


            for _, row in locations.iterrows():

                col1, col2 = st.columns([4, 1])


                with col1:

                    st.write(
                        f"**{row['party_name']}**"
                    )

                    st.caption(
                        f"{row['address']} | "
                        f"📞 {row['party_phone']}"
                    )


                with col2:

                    new_order = st.number_input(
                        f"ক্রম ID {row['id']}",
                        min_value=0,
                        value=int(row["route_order"]),
                        step=1,
                        key=f"route_order_{row['id']}"
                    )


                if new_order != int(row["route_order"]):

                    c.execute(
                        """
                        UPDATE locations
                        SET route_order=?
                        WHERE id=?
                        """,
                        (
                            new_order,
                            int(row["id"])
                        )
                    )

                    conn.commit()


            if st.button(
                "💾 রুট সেভ করুন",
                type="primary"
            ):

                st.success(
                    "✅ রুট সেভ হয়েছে।"
                )

                st.rerun()


        # -------------------------------------------------
        # RELOAD AFTER ROUTE ORDER
        # -------------------------------------------------

        locations = pd.read_sql_query(
            """
            SELECT *
            FROM locations
            ORDER BY route_order ASC, id ASC
            """,
            conn
        )


        # -------------------------------------------------
        # MAP
        # -------------------------------------------------

        start_lat = float(locations.iloc[0]["lat"])
        start_lon = float(locations.iloc[0]["lon"])


        m = folium.Map(
            location=[start_lat, start_lon],
            zoom_start=12
        )


        points = []


        for _, row in locations.iterrows():

            lat_value = float(row["lat"])
            lon_value = float(row["lon"])

            points.append(
                [lat_value, lon_value]
            )


            # Google Maps navigation link

            google_maps_url = (
                "https://www.google.com/maps/dir/?api=1"
                f"&destination={lat_value},{lon_value}"
            )


            popup_html = f"""
            <div style="width:220px">

                <b>{row['party_name']}</b><br>

                📍 {row['address']}<br>

                📞 {row['party_phone']}<br>

                🔢 রুট ক্রম: {row['route_order']}<br><br>

                <a href="tel:{row['party_phone']}"
                   style="
                   display:inline-block;
                   padding:6px 10px;
                   background:#28a745;
                   color:white;
                   text-decoration:none;
                   border-radius:5px;
                   margin-right:5px;
                   ">
                   📞 কল
                </a>

                <a href="{google_maps_url}"
                   target="_blank"
                   style="
                   display:inline-block;
                   padding:6px 10px;
                   background:#4285F4;
                   color:white;
                   text-decoration:none;
                   border-radius:5px;
                   ">
                   🗺️ Navigate
                </a>

            </div>
            """


            marker_color = (
                "red"
                if int(row["route_order"]) == 0
                else "blue"
            )


            folium.Marker(
                location=[lat_value, lon_value],
                popup=folium.Popup(
                    popup_html,
                    max_width=300
                ),
                tooltip=(
                    f"{row['route_order']}. "
                    f"{row['party_name']}"
                ),
                icon=folium.Icon(
                    color=marker_color,
                    icon="info-sign"
                )
            ).add_to(m)


        # -------------------------------------------------
        # ROUTE LINE
        # -------------------------------------------------

        if len(points) > 1:

            folium.PolyLine(
                points,
                color="green",
                weight=4,
                opacity=0.8
            ).add_to(m)


        st_folium(
            m,
            width=1000,
            height=550
        )


        # -------------------------------------------------
        # ROUTE LIST
        # -------------------------------------------------

        st.write("---")
        st.subheader("📋 ডেলিভারি রুট তালিকা")


        route_df = locations[
            [
                "route_order",
                "party_name",
                "address",
                "party_phone"
            ]
        ].copy()


        route_df.columns = [
            "ক্রম",
            "পার্টি",
            "ঠিকানা",
            "ফোন"
        ]


        st.dataframe(
            route_df,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# FOOTER
# =========================================================

st.write("---")
st.caption("P.S Mediseller Location App | Delivery Route Management System")
