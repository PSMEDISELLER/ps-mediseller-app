from datetime import datetime, timedelta
import math
import folium
from geopy.geocoders import Nominatim
import pandas as pd
import sqlite3
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation


# =========================================================
# PAGE CONFIGURATION & PWA / INSTALL SETTINGS
# =========================================================

st.set_page_config(
    page_title="P.S Mediseller",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# PWA Metadata for Add to Home Screen (App Installation)
st.markdown(
    """
    <head>
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="application-name" content="P.S Mediseller">
        <meta name="apple-mobile-web-app-title" content="P.S Mediseller">
        <meta name="theme-color" content="#FF4B4B">
    </head>
""",
    unsafe_allow_html=True,
)


# =========================================================
# DATABASE (Real-time Sync & Data Safe Persistence)
# =========================================================

DB_FILE = "mediseller_delivery.db"


def get_db_connection():
  return sqlite3.connect(DB_FILE, check_same_thread=False)


conn = get_db_connection()
c = conn.cursor()

# টেবিল ক্রিয়েশন
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

c.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    party_name TEXT NOT NULL,
    order_details TEXT,
    order_date TEXT NOT NULL,
    status TEXT DEFAULT 'Pending'
)
""")

# ডাটাবেस কলাম আপডেট চেক (মাইগ্রেশন সেফটি)
c.execute("PRAGMA table_info(locations)")
existing_columns = [row[1] for row in c.fetchall()]

if "party_phone" not in existing_columns:
  c.execute("ALTER TABLE locations ADD COLUMN party_phone TEXT")

if "route_order" not in existing_columns:
  c.execute("ALTER TABLE locations ADD COLUMN route_order INTEGER DEFAULT 0")
conn.commit()


# =========================================================
# DEFAULT USERS CREATION
# =========================================================

c.execute("SELECT COUNT(*) FROM users")
user_count = c.fetchone()[0]

if user_count == 0:
  c.execute(
      "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
      ("admin", "admin123", "admin"),
  )
  c.execute(
      "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
      ("delivery", "user123", "staff"),
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

  st.info(
      "📲 **ফোনে অ্যাপ হিসেবে ইনস্টল করুন:**\n\nব্রাউজারের ৩টি ডট (⋮) মেনুতে"
      " ক্লিক করে **'Install App'** বা **'Add to Home screen'** অপশনে চাপ"
      " দিন।"
  )

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
            c.execute(
                "UPDATE users SET password=? WHERE username=?",
                (new_pass, f_user),
            )
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
          c.execute(
              "UPDATE users SET password=? WHERE username=?",
              (new_p, curr_user),
          )
          conn.commit()
          st.success("✅ আপনার পাসওয়ার্ড সফলভাবে পরিবর্তন হয়েছে।")
        else:
          st.error("নতুন পাসওয়ার্ড দিন।")
      else:
        st.error("❌ পুরোনো পাসওয়ার্ড ভুল!")

  if st.session_state["user_role"] == "admin":
    with st.expander("⚙️ অ্যাডমিন কন্ট্রোল (ইউজার ম্যানেজমেন্ট)"):
      c.execute("SELECT username, role FROM users")
      all_users = c.fetchall()
      user_list = [u[0] for u in all_users]

      selected_u = st.selectbox("ইউজার নির্বাচন করুন", user_list)

      new_u_id = st.text_input(
          "নতুন ইউজার ID (Username)", value=selected_u, key="edit_u_id"
      )
      new_u_pass = st.text_input(
          "নতুন পাসওয়ার্ড (ঐচ্ছিক)", type="password", key="edit_u_pass"
      )

      if st.button("💾 আইডি/পাসওয়ার্ড আপডেট করুন"):
        if not new_u_id.strip():
          st.error("❌ ইউজার আইডি ফাঁকা রাখা যাবে না।")
        else:
          try:
            if new_u_id != selected_u:
              c.execute(
                  "UPDATE users SET username=? WHERE username=?",
                  (new_u_id, selected_u),
              )
              if selected_u == st.session_state["username"]:
                st.session_state["username"] = new_u_id
                if "user" in st.query_params:
                  st.query_params["user"] = new_u_id

            if new_u_pass.strip():
              c.execute(
                  "UPDATE users SET password=? WHERE username=?",
                  (new_u_pass, new_u_id),
              )

            conn.commit()
            st.success(
                f"✅ {new_u_id}-এর আইডি/পাসওয়ার্ড সফলভাবে আপডেট হয়েছে!"
            )
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

c.execute("SELECT id, party_name, order_date FROM orders WHERE status='Pending'")
pending_orders_check = c.fetchall()
now_time = datetime.now()
delayed_orders = []
for p_ord in pending_orders_check:
  try:
    ord_dt = datetime.strptime(p_ord[2], "%Y-%m-%d %H:%M:%S")
    if now_time - ord_dt > timedelta(hours=24):
      delayed_orders.append(f"{p_ord[1]}")
  except:
    pass

if delayed_orders:
  st.error(
      "⚠️ **সতর্কবার্তা!** নিম্নলিখিত পার্টিগুলোর অর্ডার ২৪ ঘণ্টার বেশি সময় ধরে"
      " পেন্ডিং আছে: "
      + ", ".join(delayed_orders)
  )

loc = get_geolocation(component_key="global_gps")

gps_lat = None
gps_lon = None

if loc and "coords" in loc:
  gps_lat = loc["coords"]["latitude"]
  gps_lon = loc["coords"]["longitude"]
  st.success(f"✅ জিপিএস অ্যাক্টিভ (Lat: {gps_lat:.4f}, Lon: {gps_lon:.4f})")

is_admin = st.session_state["user_role"] == "admin"


# =========================================================
# MENU
# =========================================================

menu = [
    "📍 নতুন লোকেশন এড করুন",
    "🔍 পার্টি ও লোকেশন সার্চ",
    "🗺️ রুট প্ল্যানিং ও ম্যাপ",
    "📦 পেন্ডিং অর্ডার ও বিলিং",
]

choice = st.sidebar.selectbox("মেনু নির্বাচন করুন", menu)


# =========================================================
# 1. ADD NEW LOCATION & ORDER ENTRY (GOOGLE MAP STYLE: BLUE DOT + RED PIN)
# =========================================================

if choice == "📍 নতুন লোকেশন এড করুন":

  st.header("📍 নতুন পার্টির লোকেশন ও অর্ডার যোগ করুন")
  col1, col2 = st.columns([1, 1])

  with col1:
    st.write("### 📍 বর্তমান জিপিএস কোঅর্ডিনেট")
    st.info(
        f"অক্ষাংশ (Lat):"
        f" {st.session_state['selected_lat']:.6f}\n\nদ্রাঘিমাংশ (Lon):"
        f" {st.session_state['selected_lon']:.6f}"
    )

    if st.button("🔄 কারেন্ট লোকেশনে পিন সেট করুন", type="secondary"):
      if gps_lat and gps_lon:
        st.session_state["selected_lat"] = gps_lat
        st.session_state["selected_lon"] = gps_lon
        st.success("✅ লাল পিনটি আপনার বর্তমান জিপিএস লোকেশনে সেট হয়েছে!")
        st.rerun()
      else:
        st.warning(
            "⚠️ GPS সিগন্যাল পাওয়া যাচ্ছে না, ফোনের লোকেশন অন ও পারমিশন চেক করুন।"
        )

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
    st.write("### 📦 পার্টির নতুন অর্ডার এন্ট্রি করুন")

    c.execute("SELECT DISTINCT party_name FROM locations ORDER BY party_name ASC")
    all_parties_db = [row[0] for row in c.fetchall()]

    # অর্ডার ফর্ম (সাবমিটের পর ফিল্ডগুলো অটোমেটিক খালি হয়ে যাবে)
    with st.form("order_entry_form", clear_on_submit=True):
      order_party_name = st.selectbox(
          "পার্টি নির্বাচন করুন",
          ["-- সিলেক্ট করুন --"] + all_parties_db,
          key="order_party_selectbox",
      )
      order_details_input = st.text_area(
          "অর্ডারের বিবরণ (কি অর্ডার দিচ্ছে)", key="order_details_text"
      )

      submitted_order = st.form_submit_button(
          "🛒 অর্ডার জমা দিন", type="primary"
      )

      if submitted_order:
        if order_party_name == "-- সিলেক্ট করুন --":
          st.error("❌ অনুগ্রহ করে সঠিক পার্টি নির্বাচন করুন।")
        elif not order_details_input.strip():
          st.error("❌ অর্ডারের বিবরণ লিখুন।")
        else:
          current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          c.execute(
              "INSERT INTO orders (party_name, order_details, order_date,"
              " status) VALUES (?, ?, ?, ?)",
              (
                  order_party_name,
                  order_details_input,
                  current_timestamp,
                  "Pending",
              ),
          )
          conn.commit()
          st.success(f"✅ {order_party_name}-এর অর্ডার সফলভাবে সেভ হয়েছে!")

  st.write("---")
  st.write("### 🗺️ গুগল ম্যাপ স্টাইল ম্যাপ ইন্টারফেস")
  st.caption(
      "🔵 **ব্লু ডট (Blue Dot):** আপনার বর্তমান জিপিএস লোকেশন।\n🔴 **লাল পিন"
      " (Red Pin):** আপনি যেখানে পিন বসাতে চান (ম্যাপে ক্লিক করুন অথবা পিনটি টেনে"
      " যেকোনো জায়গায় নিয়ে যান)।"
  )

  map_center_lat = (
      gps_lat if gps_lat else float(st.session_state["selected_lat"])
  )
  map_center_lon = (
      gps_lon if gps_lon else float(st.session_state["selected_lon"])
  )

  google_tiles = "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"

  m_click = folium.Map(
      location=[map_center_lat, map_center_lon],
      zoom_start=16,
      tiles=google_tiles,
      attr="Google Maps",
  )

  if gps_lat and gps_lon:
    folium.CircleMarker(
        location=[gps_lat, gps_lon],
        radius=10,
        color="#ffffff",
        weight=3,
        fill=True,
        fill_color="#1a73e8",
        fill_opacity=1.0,
        popup="আপনার বর্তমান লোকেশন (Blue Dot)",
        tooltip="Current Location",
    ).add_to(m_click)

  current_lat = float(st.session_state["selected_lat"])
  current_lon = float(st.session_state["selected_lon"])

  folium.Marker(
      [current_lat, current_lon],
      tooltip="পিনটি টেনে সঠিক স্থানে বসান বা ম্যাপে ক্লিক করুন",
      popup="নির্বাচিত লোকেশন",
      icon=folium.Icon(color="red", icon="map-marker", prefix="fa"),
      draggable=True,
  ).add_to(m_click)

  map_data = st_folium(m_click, width=900, height=480, key="interactive_map")

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
    if (abs(st.session_state["selected_lat"] - updated_lat) > 0.0001) or (
        abs(st.session_state["selected_lon"] - updated_lon) > 0.0001
    ):
      st.session_state["selected_lat"] = updated_lat
      st.session_state["selected_lon"] = updated_lon
      st.rerun()

  st.write("---")
  st.write("### 📝 নতুন পার্টি সেভ করুন")

  # নতুন পার্টি সেভ করার ফর্ম (clear_on_submit=True দেওয়ায় সাবমিটের পর নাম, ঠিকানা ও ফোন নম্বর অটোমেটিক মুছে যাবে)
  with st.form("new_location_form", clear_on_submit=True):
    party_name = st.text_input("পার্টি / দোকানের নাম")
    address = st.text_input("ঠিকানা / এলাকা")
    party_phone = st.text_input("ফোন নম্বর")

    col_lat, col_lon = st.columns(2)
    with col_lat:
      lat = st.number_input(
          "অক্ষাংশ (Latitude)",
          value=float(st.session_state["selected_lat"]),
          format="%.6f",
      )
    with col_lon:
      lon = st.number_input(
          "দ্রাঘিমাংশ (Longitude)",
          value=float(st.session_state["selected_lon"]),
          format="%.6f",
      )

    submitted_location = st.form_submit_button(
        "💾 লোকেশন সেভ করুন", type="primary"
    )

    if submitted_location:
      if not party_name or not party_phone:
        st.error("❌ পার্টির নাম ও ফোন নম্বর অবশ্যই দিন।")
      else:
        c.execute(
            "INSERT INTO locations (party_name, address, party_phone, lat, lon,"
            " route_order) VALUES (?, ?, ?, ?, ?, ?)",
            (party_name, address, party_phone, lat, lon, 0),
        )
        conn.commit()
        st.success("✅ পার্টির লোকেশন সফলভাবে সেভ হয়েছে!")


# =========================================================
# 2. SEARCH PARTY
# =========================================================

elif choice == "🔍 পার্টি ও লোকেশন সার্চ":

  st.header("🔍 পার্টি ও লোকেশন সার্চ")

  search_query = st.text_input("পার্টির নাম / এলাকা / ফোন নম্বর দিয়ে সার্চ করুন")

  df = pd.read_sql_query(
      "SELECT * FROM locations ORDER BY route_order ASC, id ASC", conn
  )

  if search_query:
    search_text = search_query.lower()
    df = df[
        df["party_name"].fillna("").str.lower().str.contains(search_text)
        | df["address"].fillna("").str.lower().str.contains(search_text)
        | df["party_phone"].fillna("").str.lower().str.contains(search_text)
    ]

  if not df.empty:
    df["Google Maps Direction"] = df.apply(
        lambda row: (
            "https://www.google.com/maps/dir/?api=1&destination="
            f"{row['lat']},{row['lon']}"
        ),
        axis=1,
    )

    st.subheader("📋 পার্টির তালিকা")

    st.dataframe(
        df[[
            "route_order",
            "party_name",
            "address",
            "party_phone",
            "Google Maps Direction",
        ]],
        column_config={
            "route_order": "ক্রম",
            "party_name": "পার্টি",
            "address": "ঠিকানা",
            "party_phone": "ফোন নম্বর",
            "Google Maps Direction": st.column_config.LinkColumn(
                "গুগল ম্যাপস", display_text="🗺️ Direction"
            ),
        },
        use_container_width=True,
        hide_index=True,
    )
  else:
    st.warning("কোনো পার্টির তথ্য পাওয়া যায়নি।")

  if is_admin and not df.empty:
    st.write("---")
    st.subheader("🗑️ অ্যাডমিন কন্ট্রোল")

    delete_options = {
        f"{row['party_name']} - ID: {row['id']}": int(row["id"])
        for _, row in df.iterrows()
    }
    selected_delete = st.selectbox(
        "যে পার্টিটি ডিলিট করবেন:", list(delete_options.keys())
    )

    if st.button("🗑️ পার্টি ডিলিট করুন", type="primary"):
      c.execute(
          "DELETE FROM locations WHERE id=?", (delete_options[selected_delete],)
      )
      conn.commit()
      st.success("✅ পার্টি সফলভাবে ডিলিট হয়েছে।")
      st.rerun()


# =========================================================
# 3. ROUTE PLANNING & MAP
# =========================================================

elif choice == "🗺️ রুট প্ল্যানিং ও ম্যাপ":

  st.header("🗺️ স্মার্ট ডেলিভারি ও কালেকশন রুট প্ল্যানার")

  locations_df = pd.read_sql_query("SELECT * FROM locations", conn)

  if locations_df.empty:
    st.info("এখনো কোনো লোকেশন সেভ করা হয়নি।")
  else:
    st.subheader("🎯 আজকের ডেলিভারি ও কালেকশন পার্টি নির্বাচন করুন")

    party_names_list = locations_df["party_name"].tolist()
    selected_parties = st.multiselect(
        "পার্টির নাম সার্চ করে সিলেক্ট করুন:",
        party_names_list,
        default=party_names_list,
    )

    if selected_parties:
      st.write("---")
      st.subheader("💰 পেমেন্ট ও ডেলিভারি বিবরণ এন্ট্রি করুন")

      route_input_data = []
      for p_name in selected_parties:
        p_row = locations_df[locations_df["party_name"] == p_name].iloc[0]

        with st.expander(f"🏢 {p_name} ({p_row['address']})"):
          col_d, col_p = st.columns(2)
          with col_d:
            del_item = st.text_input(
                f"ডেলিভারি বিবরণ", value="মেডিসিন ডেলিভারি", key=f"del_{p_name}"
            )
          with col_p:
            pay_amt = st.text_input(
                f"কালেকশন পেমেন্ট (টাকা)", value="0", key=f"pay_{p_name}"
            )

          route_input_data.append({
              "party_name": p_name,
              "address": p_row["address"],
              "party_phone": p_row["party_phone"],
              "lat": float(p_row["lat"]),
              "lon": float(p_row["lon"]),
              "delivery_info": del_item,
              "payment_info": pay_amt,
          })

      if st.button("🚀 শর্টকাট রুট ও ম্যাপ তৈরি করুন", type="primary"):
        home_lat = gps_lat if gps_lat else route_input_data[0]["lat"]
        home_lon = gps_lon if gps_lon else route_input_data[0]["lon"]

        unvisited = route_input_data.copy()
        optimized_route = []
        curr_lat, curr_lon = home_lat, home_lon

        while unvisited:
          next_stop = min(
              unvisited,
              key=lambda x: math.sqrt(
                  (x["lat"] - curr_lat) ** 2 + (x["lon"] - curr_lon) ** 2
              ),
          )
          optimized_route.append(next_stop)
          curr_lat, curr_lon = next_stop["lat"], next_stop["lon"]
          unvisited.remove(next_stop)

        st.session_state["optimized_route"] = optimized_route
        st.session_state["home_coords"] = (home_lat, home_lon)
        st.success("✅ শর্টকাট রুট সফলভাবে সাজানো হয়েছে!")
        st.rerun()

    if "optimized_route" in st.session_state and st.session_state["optimized_route"]:
      route = st.session_state["optimized_route"]
      h_lat, h_lon = st.session_state["home_coords"]

      st.write("---")
      st.subheader("🗺️ লাইভ রুট ম্যাপ")

      google_tiles = "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"
      m = folium.Map(
          location=[h_lat, h_lon],
          zoom_start=13,
          tiles=google_tiles,
          attr="Google Maps",
      )

      folium.Marker(
          location=[h_lat, h_lon],
          popup="🏠 হোম / গুদাম (স্টার্ট পয়েন্ট)",
          tooltip="Start & End Point",
          icon=folium.Icon(color="green", icon="home"),
      ).add_to(m)

      points = [[h_lat, h_lon]]
      for idx, stop in enumerate(route, 1):
        lat_val, lon_val = stop["lat"], stop["lon"]
        points.append([lat_val, lon_val])

        gmaps_url = (
            "https://www.google.com/maps/dir/?api=1&destination="
            f"{lat_val},{lon_val}"
        )
        popup_html = f"""
                <div style="width:220px">
                    <b>{idx}. {stop['party_name']}</b><br>
                    📍 {stop['address']}<br>
                    📞 {stop['party_phone']}<br>
                    📦 ডেলিভারি: {stop['delivery_info']}<br>
                    💵 পেমেন্ট: ₹{stop['payment_info']}<br><br>
                    <a href="tel:{stop['party_phone']}" style="padding:4px 6px; background:#28a745; color:white; text-decoration:none; border-radius:3px;">📞 কল</a>
                    <a href="{gmaps_url}" target="_blank" style="padding:4px 6px; background:#4285F4; color:white; text-decoration:none; border-radius:3px;">🗺️ Navigate</a>
                </div>
                """

        folium.Marker(
            location=[lat_val, lon_val],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{idx}. {stop['party_name']}",
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(m)

      points.append([h_lat, h_lon])
      folium.PolyLine(points, color="red", weight=4, opacity=0.8).add_to(m)
      st_folium(m, width=1000, height=550)

      st.write("---")
      st.subheader("📋 ক্রমানুসারে ডেলিভারি ও পেমেন্ট তালিকা")

      table_df = pd.DataFrame([{
          "ক্রম": i + 1,
          "পার্টি": s["party_name"],
          "ঠিকানা": s["address"],
          "ফোন": s["party_phone"],
          "ডেলিভারি": s["delivery_info"],
          "কালেকশন পেমেন্ট": f"₹{s['payment_info']}",
          "গুগল ম্যাপস নেভিগেশন": (
              "https://www.google.com/maps/dir/?api=1&destination="
              f"{s['lat']},{s['lon']}"
          ),
      } for i, s in enumerate(route)])

      st.dataframe(
          table_df,
          column_config={
              "গুগল ম্যাপস নেভিগেশন": st.column_config.LinkColumn(
                  "নেভিগেশন লিংক", display_text="🗺️ Direction"
              )
          },
          use_container_width=True,
          hide_index=True,
      )


# =========================================================
# 4. PENDING ORDERS & BILLING SECTION
# =========================================================

elif choice == "📦 পেন্ডিং অর্ডার ও বিলিং":

  st.header("📦 পার্টির পেন্ডিং অর্ডার ও বিলিং ম্যানেজমেন্ট")

  orders_df = pd.read_sql_query(
      "SELECT * FROM orders ORDER BY order_date DESC", conn
  )

  if orders_df.empty:
    st.info("বর্তমানে কোনো অর্ডার জমা নেই।")
  else:
    unique_dates = orders_df["order_date"].str.split(" ").str[0].unique()
    selected_date_filter = st.selectbox(
        "📅 তারিখ অনুযায়ী অর্ডার ফিল্টার করুন",
        ["সকল তারিখ"] + list(unique_dates),
    )

    if selected_date_filter != "সকল তারিখ":
      orders_df = orders_df[
          orders_df["order_date"].str.startswith(selected_date_filter)
      ]

    st.subheader("📋 অর্ডারের তালিকা ও স্ট্যাটাস")

    for _, row in orders_df.iterrows():
      order_id = row["id"]
      p_name = row["party_name"]
      details = row["order_details"]
      o_date = row["order_date"]
      status = row["status"]

      is_delayed = False
      try:
        if status == "Pending" and (
            datetime.now()
            - datetime.strptime(o_date, "%Y-%m-%d %H:%M:%S")
            > timedelta(hours=24)
        ):
          is_delayed = True
      except:
        pass

      col_box1, col_box2 = st.columns([3, 1])
      with col_box1:
        if is_delayed:
          st.markdown(f"🔴 **[২৪ ঘণ্টা পার হয়েছে!] পার্টি:** {p_name}")
        else:
          st.markdown(f"🟢 **পার্টি:** {p_name}")

        st.write(f"📝 **অর্ডারের বিবরণ:** {details}")
        st.caption(f"🕒 সময়: {o_date} | স্ট্যাটাস: **{status}**")

      with col_box2:
        if status == "Pending":
          if st.button(
              "✅ Order Done (বিলিং সম্পন্ন)", key=f"done_btn_{order_id}"
          ):
            c.execute(
                "UPDATE orders SET status='Completed' WHERE id=?", (order_id,)
            )
            conn.commit()
            st.success("অর্ডার কমপ্লিট করা হয়েছে!")
            st.rerun()
        else:
          st.success("সম্পন্ন হয়েছে ✅")
      st.write("---")


# =========================================================
# FOOTER
# =========================================================

st.write("---")
st.caption("P.S Mediseller Location App | Delivery Route Management System")
