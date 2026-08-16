import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Doctor & Location Entry",
    page_icon="📍",
    layout="centered"
)

# Custom Styling for Dark Background & UI
st.markdown("""
    <style>
    .stApp {
        background-color: #0d1117;
        color: #ffffff;
    }
    </style>
""", unsafe_allow_html=True)

# Main Container
with st.container():
    
    # Main Heading
    st.markdown("""
        <h2 style='font-size: 18px; line-height: 1.4; margin-bottom: 20px; font-weight: bold; color: #ffffff;'>
            📍 Add New Location & Doctor/Party Entry <br>
            <span style='font-size: 14px; color: #9ca3af; font-weight: normal;'>(নতুন লোকেশন ও ডক্টর/পার্টি এন্ট্রি)</span>
        </h2>
    """, unsafe_allow_html=True)

    # Top Navigation Tabs (উপর-নিচে সাজানো)
    st.markdown("""
        <div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 24px;">
            <div style="background: #161b22; border: 1px solid #30363d; padding: 14px 16px; border-radius: 10px; display: flex; align-items: center; gap: 10px; font-size: 14px; color: #ffffff;">
                <span>🏠</span> 
                <span>General Location (সাধারণ লোকেশন ম্যাপসহ)</span>
            </div>
            <div style="background: #1f2937; border: 2px solid #3b82f6; padding: 14px 16px; border-radius: 10px; display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: bold; color: #ffffff;">
                <span>👨‍⚕️</span> 
                <span>Doctor/Party Details (ডক্টর বা স্পেশাল পার্টির বিবরণ)</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Form Card Section
    st.markdown("""
        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 14px; padding: 16px; box-sizing: border-box;">
            <h3 style="font-size: 15px; line-height: 1.4; margin-top: 0; margin-bottom: 16px; color: #f3f4f6;">
                2. Doctor or Special Party Details <br>
                <span style="font-size: 12px; color: #9ca3af; font-weight: normal;">(ডাক্তার বা স্পেশাল পার্টির বিবরণ ম্যাপ ছাড়া)</span>
            </h3>
        </div>
    """, unsafe_allow_html=True)

    # Input Form
    with st.form("doctor_entry_form"):
        
        # Doctor/Party Name
        st.markdown("""
            <div style="background: #1e3a8a; color: #93c5fd; padding: 8px 12px; border-radius: 6px 6px 0 0; font-size: 13px; border: 1px solid #2563eb; border-bottom: none; margin-top: 10px;">
                Doctor/Party Name (ডাক্তার/পার্টির নাম)
            </div>
        """, unsafe_allow_html=True)
        doctor_name = st.text_input("", label_visibility="collapsed", key="doc_name")

        # Address/Chamber
        st.markdown("""
            <div style="background: #1e3a8a; color: #93c5fd; padding: 8px 12px; border-radius: 6px 6px 0 0; font-size: 13px; border: 1px solid #2563eb; border-bottom: none; margin-top: 10px;">
                Address/Chamber (ঠিকানা/চেম্বার)
            </div>
        """, unsafe_allow_html=True)
        address = st.text_input("", label_visibility="collapsed", key="doc_address")

        # Phone Number
        st.markdown("""
            <div style="background: #1e3a8a; color: #93c5fd; padding: 8px 12px; border-radius: 6px 6px 0 0; font-size: 13px; border: 1px solid #2563eb; border-bottom: none; margin-top: 10px;">
                Phone Number (ফোন নম্বর)
            </div>
        """, unsafe_allow_html=True)
        phone = st.text_input("", label_visibility="collapsed", key="doc_phone")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Submit Button
        submitted = st.form_submit_button("💾 Save Doctor/Party (ডাক্তার/পার্টি সেভ করুন)")
        
        if submitted:
            if doctor_name and address and phone:
                st.success(f"সফলভাবে সেভ হয়েছে! (ডাক্তার: {doctor_name})")
            else:
                st.warning("অনুগ্রহ করে সবগুলি ফিল্ড পূরণ করুন।")
