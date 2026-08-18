"INSERT INTO users (username, password, role, fullname, phone, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_uname.strip(), new_pass.strip(), "staff", new_fname.strip(), new_phone.strip(), get_ist_time().strftime("%Y-%m-%d %H:%M:%S"), 1)
            )
            conn.commit()
            st.success(f"Agent '{new_fname.strip()}' added successfully! (সফলভাবে যুক্ত হয়েছে!)")
            st.rerun()
          except sqlite3.IntegrityError:
            st.error("Username already exists! Choose another username. (ইউজারনেমটি ইতিমধ্যে আছে!)")
        else:
          st.error("Username, Password, and Full Name are required! (সব তথ্য প্রদান করুন।)")

    st.write("---")
    st.write("#### 👥 Existing Staff & Agents List (বর্তমান কর্মী তালিকা)")
    users_df = pd.read_sql_query("SELECT username AS 'Username', fullname AS 'Full Name', phone AS 'Phone', created_at AS 'Created At' FROM users WHERE role='staff' ORDER BY created_at DESC", conn)
    
    if not users_df.empty:
      users_df['Created At'] = users_df['Created At'].apply(lambda x: format_date_display(x))
      st.dataframe(users_df, use_container_width=True)
      
      st.write("#### 🗑️ Delete Agent (কর্মী সরান)")
      c.execute("SELECT username, fullname FROM users WHERE role='staff'")
      del_staff_list = c.fetchall()
      
      if del_staff_list:
        agent_to_del = st.selectbox(
            "Select Agent to Delete",
            [s[0] for s in del_staff_list],
            format_func=lambda x: next((s[1] for s in del_staff_list if s[0] == x), x)
        )
        if st.button("🗑️ Delete Selected Agent", type="secondary"):
          c.execute("DELETE FROM users WHERE username=?", (agent_to_del,))
          c.execute("DELETE FROM agent_live_locations WHERE username=?", (agent_to_del,))
          conn.commit()
          st.success("Agent deleted successfully!")
          st.rerun()
    else:
      st.info("No staff agents added yet.")

  with set_tab2:
    st.write("#### 🔑 Change Admin Password (পাসওয়ার্ড পরিবর্তন)")
    with st.form("change_admin_pass_form", clear_on_submit=True):
      curr_pass = st.text_input("Current Admin Password", type="password")
      new_admin_pass = st.text_input("New Admin Password", type="password")
      confirm_admin_pass = st.text_input("Confirm New Admin Password", type="password")
      submit_pass_change = st.form_submit_button("🔑 Update Password (পাসওয়ার্ড আপডেট)", type="primary")

      if submit_pass_change:
        c.execute("SELECT password FROM users WHERE username='admin'")
        adm_pass_row = c.fetchone()
        
        if adm_pass_row and adm_pass_row[0] == curr_pass:
          if new_admin_pass.strip() and new_admin_pass == confirm_admin_pass:
            c.execute("UPDATE users SET password=? WHERE username='admin'", (new_admin_pass.strip(),))
            conn.commit()
            st.success("Admin password changed successfully! (পাসওয়ার্ড সফলভাবে পরিবর্তিত হয়েছে!)")
          else:
            st.error("New passwords do not match or are empty!")
        else:
          st.error("Incorrect current admin password!")
