from datetime import datetime
import sqlite3
import pytz
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="P.S MEDISELLER", page_icon="💊", layout="wide"
)


# Helper function for IST time
def get_ist_time():
  try:
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist)
  except Exception:
    return datetime.now()


# Database Connection & Initialization
def get_connection():
  conn = sqlite3.connect("ps_mediseller.db", check_same_thread=False)
  return conn


def init_db():
  conn = get_connection()
  c = conn.cursor()
  # Locations table
  c.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_name TEXT NOT NULL,
            address TEXT,
            party_phone TEXT,
            lat REAL,
            lon REAL
        )
    """)
  # Daily work table
  c.execute("""
        CREATE TABLE IF NOT EXISTS daily_work (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_name TEXT NOT NULL,
            activity_type TEXT,
            work_date TEXT
        )
    """)
  conn.commit()
  conn.close()


init_db()

# Custom CSS for styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 24px;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 20px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="main-header">💊 P.S MEDISELLER (Allopathy & Ayurvedic'
    " Wholesaler)</p>",
    unsafe_allow_html=True,
)

conn = get_connection()
c = conn.cursor()

# Sidebar navigation
menu = st.sidebar.selectbox(
    "Navigation (মেনু)",
    ["Add Location / Party (পার্টি যোগ করুন)", "Daily Work & Visits (ডেইলি ওয়ার্ক)"],
)

if menu == "Add Location / Party (পার্টি যোগ করুন)":
  st.subheader("📍 Add New Party / Location (নতুন পার্টি ও লোকেশন যোগ করুন)")

  tab1, tab2 = st.tabs(
      ["With Map Party (ম্যাপ সহ)", "Without Map Party (ম্যাপ ছাড়া)"]
  )

  with tab1:
    st.write("ম্যাপ থেকে লোকেশন সিলেক্ট করে পার্টি যোগ করুন:")
    p_name = st.text_input("Party Name (পার্টির নাম)", key="map_p_name")
    p_phone = st.text_input("Phone Number (ফোন নম্বর)", key="map_p_phone")
    p_addr = st.text_input("Address (ঠিকানা)", key="map_p_addr")

    # Initializing map coordinates in session state if not present
    if "selected_lat" not in st.session_state:
      st.session_state["selected_lat"] = 22.5726  # Default fallback (Lat)
    if "selected_lon" not in st.session_state:
      st.session_state["selected_lon"] = 88.3639  # Default fallback (Lon)

    st.info(
        f"Selected Coordinates: Lat: {st.session_state['selected_lat']}, Lon:"
        f" {st.session_state['selected_lon']}"
    )

    submitted_loc = st.button("Save With Map Party (সেভ করুন)")

    if submitted_loc:
      if p_name.strip() and p_phone.strip():
        c.execute(
            "SELECT id FROM locations WHERE LOWER(party_name) = LOWER(?) OR"
            " party_phone = ?",
            (p_name.strip(), p_phone.strip()),
        )
        existing_check = c.fetchone()

        if existing_check:
          st.error("Party name or phone already exists! (ইতিমধ্যে সেভ করা আছে!)")
        else:
          try:
            current_date_str = get_ist_time().strftime("%Y-%m-%d")

            # 1. Save location in locations table
            c.execute(
                "INSERT INTO locations (party_name, address, party_phone, lat,"
                " lon) VALUES (?, ?, ?, ?, ?)",
                (
                    p_name.strip(),
                    p_addr,
                    p_phone.strip(),
                    st.session_state["selected_lat"],
                    st.session_state["selected_lon"],
                ),
            )

            # 2. Automatically record visit in daily_work table
            c.execute(
                "INSERT INTO daily_work (party_name, activity_type,"
                " work_date) VALUES (?, ?, ?)",
                (p_name.strip(), "Visit (ভিজিট)", current_date_str),
            )

            conn.commit()
            st.success(
                "Location saved and visit recorded successfully! (সফলভাবে সেভ"
                " হয়েছে!)"
            )
            st.rerun()
          except sqlite3.IntegrityError:
            st.error("Party already exists! (ইতিমধ্যে আছে!)")
      else:
        st.error("Party name and phone required. (নাম ও ফোন আবশ্যক।)")

  with tab2:
    st.write("ম্যাপ ছাড়াই সরাসরি পার্টি যোগ করুন:")
    nomap_name = st.text_input("Party Name (পার্টির নাম)", key="nomap_p_name")
    nomap_phone = st.text_input("Phone Number (ফোন নম্বর)", key="nomap_p_phone")
    nomap_addr = st.text_input("Address (ঠিকানা)", key="nomap_p_addr")

    submitted_nomap = st.button("Save Without Map Party (সেভ করুন)")

    if submitted_nomap:
      if nomap_name.strip() and nomap_phone.strip():
        c.execute(
            "SELECT id FROM locations WHERE LOWER(party_name) = LOWER(?) OR"
            " party_phone = ?",
            (nomap_name.strip(), nomap_phone.strip()),
        )
        existing_check = c.fetchone()

        if existing_check:
          st.error("Party name or phone already exists! (ইতিমধ্যে সেভ করা আছে!)")
        else:
          try:
            current_date_str = get_ist_time().strftime("%Y-%m-%d")

            # 1. Save location in locations table
            c.execute(
                "INSERT INTO locations (party_name, address, party_phone, lat,"
                " lon) VALUES (?, ?, ?, ?, ?)",
                (
                    nomap_name.strip(),
                    nomap_addr,
                    nomap_phone.strip(),
                    0.0,
                    0.0,
                ),
            )

            # 2. Automatically record visit in daily_work table
            c.execute(
                "INSERT INTO daily_work (party_name, activity_type,"
                " work_date) VALUES (?, ?, ?)",
                (nomap_name.strip(), "Visit (ভিজিট)", current_date_str),
            )

            conn.commit()
            st.success(
                "Party saved and visit recorded successfully! (সেভ হয়েছে!)"
            )
            st.rerun()
          except sqlite3.IntegrityError:
            st.error("Party already exists!")
      else:
        st.error("Party name and phone required.")

elif menu == "Daily Work & Visits (ডেইলি ওয়ার্ক)":
  st.subheader("📋 Daily Work & Recent Visits (ডেইলি ওয়ার্ক ও ভিজিট লিস্ট)")
  c.execute(
      "SELECT id, party_name, activity_type, work_date FROM daily_work ORDER BY"
      " id DESC"
  )
  rows = c.fetchall()
  if rows:
    for row in rows:
      st.write(
          f"🆔 **ID:** {row[0]} | 🏢 **Party:** {row[1]} | 📌 **Activity:**"
          f" {row[2]} | 📅 **Date:** {row[3]}"
      )
  else:
    st.info("No records found in daily work. (কোনো এন্ট্রি পাওয়া যায়নি)")

conn.close()
