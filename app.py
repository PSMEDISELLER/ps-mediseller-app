from flask import Flask, render_template_string, request

app = Flask(__name__)

# সম্পূর্ণ HTML ও CSS লেআউট
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Doctor & Location Entry</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0d1117; font-family: sans-serif; color: #ffffff;">

    <div style="max-width: 480px; margin: 0 auto; padding: 16px; min-height: 100vh; box-sizing: border-box;">
        
        <!-- Main Heading -->
        <h2 style="font-size: 18px; line-height: 1.4; margin-bottom: 20px; font-weight: bold;">
            📍 Add New Location & Doctor/Party Entry <br>
            <span style="font-size: 14px; color: #9ca3af; font-weight: normal;">(নতুন লোকেশন ও ডক্টর/পার্টি এন্ট্রি)</span>
        </h2>

        <!-- Top Navigation Tabs (উপর-নিচে সাজানো) -->
        <div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 24px;">
            
            <!-- ১. জেনারেল লোকেশন অপশন -->
            <div style="background: #161b22; border: 1px solid #30363d; padding: 14px 16px; border-radius: 10px; cursor: pointer; display: flex; align-items: center; gap: 10px; font-size: 14px;">
                <span>🏠</span> 
                <span>General Location (সাধারণ লোকেশন ম্যাপসহ)</span>
            </div>
            
            <!-- ২. ডক্টর অপশন (সিলেক্টেড লুক) -->
            <div style="background: #1f2937; border: 2px solid #3b82f6; padding: 14px 16px; border-radius: 10px; cursor: pointer; display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: bold;">
                <span>👨‍⚕️</span> 
                <span>Doctor/Party Details (ডক্টর বা স্পেশাল পার্টির বিবরণ)</span>
            </div>

        </div>

        <!-- Form Card Section -->
        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 14px; padding: 16px; box-sizing: border-box;">
            
            <h3 style="font-size: 15px; line-height: 1.4; margin-top: 0; margin-bottom: 16px; color: #f3f4f6;">
                2. Doctor or Special Party Details <br>
                <span style="font-size: 12px; color: #9ca3af; font-weight: normal;">(ডাক্তার বা স্পেশাল পার্টির বিবরণ ম্যাপ ছাড়া)</span>
            </h3>

            <form action="/submit" method="POST">
                <!-- Doctor/Party Name Field -->
                <div style="margin-bottom: 14px;">
                    <div style="background: #1e3a8a; color: #93c5fd; padding: 8px 12px; border-radius: 6px 6px 0 0; font-size: 13px; border: 1px solid #2563eb; border-bottom: none;">
                        Doctor/Party Name (ডাক্তার/পার্টির নাম)
                    </div>
                    <input type="text" name="doctor_name" required style="width: 100%; padding: 12px; background: #0d1117; border: 1px solid #30363d; border-radius: 0 0 6px 6px; color: white; outline: none; box-sizing: border-box; font-size: 14px;" />
                </div>

                <!-- Address/Chamber Field -->
                <div style="margin-bottom: 14px;">
                    <div style="background: #1e3a8a; color: #93c5fd; padding: 8px 12px; border-radius: 6px 6px 0 0; font-size: 13px; border: 1px solid #2563eb; border-bottom: none;">
                        Address/Chamber (ঠিকানা/চেম্বার)
                    </div>
                    <input type="text" name="address" required style="width: 100%; padding: 12px; background: #0d1117; border: 1px solid #30363d; border-radius: 0 0 6px 6px; color: white; outline: none; box-sizing: border-box; font-size: 14px;" />
                </div>

                <!-- Phone Number Field -->
                <div style="margin-bottom: 20px;">
                    <div style="background: #1e3a8a; color: #93c5fd; padding: 8px 12px; border-radius: 6px 6px 0 0; font-size: 13px; border: 1px solid #2563eb; border-bottom: none;">
                        Phone Number (ফোন নম্বর)
                    </div>
                    <input type="text" name="phone" required style="width: 100%; padding: 12px; background: #0d1117; border: 1px solid #30363d; border-radius: 0 0 6px 6px; color: white; outline: none; box-sizing: border-box; font-size: 14px;" />
                </div>

                <!-- Save Button -->
                <button type="submit" style="width: 100%; background: #2563eb; color: white; border: none; padding: 14px; border-radius: 8px; font-size: 14px; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px;">
                    💾 Save Doctor/Party (ডাক্তার/পার্টি সেভ করুন)
                </button>
            </form>

        </div>

    </div>

</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/submit', methods=['POST'])
def submit():
    doctor_name = request.form.get('doctor_name')
    address = request.form.get('address')
    phone = request.form.get('phone')
    
    # এখানে ডেটাবেস বা ফাইলে ডেটা সেভ করার কোড যোগ করতে পারেন
    return f"""
    <body style="background: #0d1117; color: white; font-family: sans-serif; text-align: center; padding-top: 50px;">
        <h2 style="color: #3b82f6;">সফলভাবে সেভ হয়েছে!</h2>
        <p>নাম: {doctor_name}</p>
        <p>ঠিকানা: {address}</p>
        <p>ফোন: {phone}</p>
        <br>
        <a href="/" style="color: #93c5fd; text-decoration: none; background: #1e3a8a; padding: 10px 20px; border-radius: 6px;">ফিরে যান</a>
    </body>
    """

if __name__ == '__main__':
    app.run(debug=True, port=5000)
