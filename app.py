import streamlit as st

# 페이지 কনফিগারেশন
st.set_page_config(
    page_title="P. S Mediseller - Order Management",
    page_icon="💊",
    layout="centered",
)

# Custom CSS কোড (সাদা বক্স ও অদৃশ্য লেখার সমস্যা সমাধানের জন্য)
st.markdown(
    """
    <style>
        /* মেইন অ্যাপের ব্যাকগ্রাউন্ড */
        .stApp {
            background-color: #0E1117;
            color: #FAFAFA;
        }
        
        /* ইনপুট ফিল্ড এবং টেক্সট বক্সের ব্যাকগ্রাউন্ড সাদা এবং লেখা কালো করার জন্য */
        .stTextInput input, .stTextArea textarea {
            background-color: #ffffff !important;
            color: #000000 !important;
            border-radius: 5px;
            font-weight: 500;
        }
        
        div[data-baseweb="input"] {
            background-color: #ffffff !important;
            color: #000000 !important;
        }
        
        /* প্লেসহোল্ডারের রঙ */
        input::placeholder, textarea::placeholder {
            color: #666666 !important;
        }
        
        /* মূল কন্টেইনার বক্সের স্টাইল */
        .main-container {
            background-color: #1a2233;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #2d3748;
            margin-bottom: 20px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# মূল ইন্টারফেস শুরু
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# ১. পার্টি বা ডাক্তার সার্চ সেクション
st.markdown("### 🔍 পার্টি বা ডাক্তার খুঁজুন ও সিলেক্ট করুন:")
search_query = st.text_input(
    "সার্চ ইনপুট", placeholder="সার্চ করুন...", label_visibility="collapsed"
)

# যদি সার্চ বক্সে কিছু লেখা হয় এবং ম্যাচ না করে
if search_query:
    st.warning(
        "এই নামে কোনো পার্টি পাওয়া যায়নি। সঠিক নাম লিখুন বা নতুন লোকেশন এন্ট্রি"
        " করুন।"
    )

st.write("")

# ২. অর্ডারের বিবরণ সেকশন
st.markdown("### অর্ডারের বিবরণ (যদি অর্ডার থাকে)")
order_details = st.text_area(
    "অর্ডার বিবরণ ইনপুট",
    placeholder="এখানে বিবরণ লিখুন...",
    label_visibility="collapsed",
)

st.write("")

# ৩. অর্ডার জমা দেওয়ার বাটন
if st.button("🛒 অর্ডার জমা দিন", type="primary", use_container_width=True):
    if order_details or search_query:
        st.success("অর্ডার সফলভাবে জমা দেওয়া হয়েছে!")
    else:
        st.error(
            "অনুগ্রহ করে পার্টি নির্বাচন করুন অথবা অর্ডারের বিবরণ লিখুন।"
        )

st.write("")

# ৪. লোকেশন পিন বক্স (যেটি সাদা হয়ে গিয়েছিল)
st.markdown("📍 লোকেশন বা ঠিকানা:")
location_input = st.text_input(
    "লোকেশন ইনপুট",
    placeholder="লোকেশন বা ঠিকানা লিখুন...",
    label_visibility="collapsed",
)

st.markdown("</div>", unsafe_allow_html=True)

# ৫. সাম্প্রতিক অর্ডার ও ভিজিট রিপোর্টসমূহ সেকশন
st.markdown("### 📋 সাম্প্রতিক অর্ডার ও ভিজিট রিপোর্টসমূহ")
st.info("কোনো রিপোর্ট পাওয়া যায়নি।")
