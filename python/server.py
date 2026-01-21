from flask import Flask, jsonify, request, Response
import json
import threading
import time
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask_cors import CORS
import os


# ========================
# 📧 EMAIL CONFIGURATION
# ========================
SENDER_EMAIL = "ovinenterprises.main@gmail.com"   
SENDER_PASSWORD = "ixlz wuhy uouu thiz" 
MANAGER_EMAIL = "ovinenterprises.main@gmail.com" 

# ========================
# PATH SETUP
# ========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
BID_FILE_PATH = os.path.join(PUBLIC_DIR, "bid1.json")

os.makedirs(PUBLIC_DIR, exist_ok=True)

# ========================
# FLASK SETUP
# ========================
app = Flask(__name__)
CORS(app)

@app.route("/api/data", methods=["GET"])
def get_data():
    """Return the bid data"""
    try:
        with open(BID_FILE_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "bid1.json not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ PDF PROXY ROUTE
@app.route("/api/proxy-pdf", methods=["GET"])
def proxy_pdf():
    pdf_url = request.args.get('url')
    if not pdf_url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        # Backend requests aren't blocked by CORS
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = requests.get(pdf_url, headers=headers, stream=True)
        return Response(resp.iter_content(chunk_size=1024), content_type='application/pdf')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ CONTACT ROUTE (Smart Logic: Bid vs General)
@app.route("/api/contact", methods=["POST"])
def send_email():
    data = request.json
    name = data.get('name')
    user_email = data.get('email')
    phone = data.get('phone')
    message = data.get('message')
    
    # Check karega ki Bid Data hai ya nahi
    bid_no = data.get('bid_no', 'General Inquiry')
    bid_name = data.get('bid_name', 'N/A')

    if not all([name, user_email, phone, message]):
        return jsonify({"error": "All fields are required"}), 400

    # ✅ LOGIC: Mail Body Change based on Source
    if bid_no != 'General Inquiry':
        # CASE 1: PARTICIPATE BUTTON SE AAYA HAI
        subject = f"🔔 Bid Inquiry: {bid_no} (from {name})"
        body = f"""
        Hello Manager,
        
        A user wants to PARTICIPATE in a Bid.
        
        📦 Bid Details:
        --------------------------------------
        🔢 Bid No:    {bid_no}
        📋 Item Name: {bid_name}
        --------------------------------------
        
        👤 Lead Details:
        Name:   {name}
        Phone:  {phone}
        Email:  {user_email}
        
        📝 Message:
        {message}
        """
    else:
        # CASE 2: NORMAL CONTACT US SE AAYA HAI
        subject = f"📩 New General Inquiry from {name}"
        body = f"""
        Hello Manager,
        
        You have received a new contact request from the website.
        
        👤 Lead Details:
        --------------------------------------
        Name:   {name}
        Phone:  {phone}
        Email:  {user_email}
        --------------------------------------
        
        📝 Message:
        {message}
        """

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = MANAGER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Sending Logic
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()

        return jsonify({"message": "Email sent successfully!"}), 200

    except Exception as e:
        print(f"Mail Error: {e}")
        return jsonify({"error": str(e)}), 500


# ========================
# SCRAPER FUNCTION (FULL CODE)
# ========================
def scrape_data():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)

    try:
        driver.get("https://bidplus.gem.gov.in/all-bids")
        time.sleep(3)

        print("⚙️ Starting scraping (10 bids per page)...")

        # Load existing data if available
        if os.path.exists(BID_FILE_PATH):
            with open(BID_FILE_PATH, "r", encoding="utf-8") as f:
                try:
                    data_list = json.load(f)
                except:
                    data_list = []
        else:
            data_list = []

        total_pages = 3700

        for current_page in range(1, total_pages + 1):
            print(f"\n📄 Scraping page {current_page}")

            try:
                wait.until(EC.presence_of_all_elements_located((By.XPATH, '//*[@id="bidCard"]/div')))
                bid_cards = driver.find_elements(By.XPATH, '//*[@id="bidCard"]/div')[:10]
            except Exception:
                print(f"⚠️ Could not find bid cards on page {current_page}, skipping...")
                continue

            for i, bid_div in enumerate(bid_cards, start=1):
                try:
                    bid_anchor = bid_div.find_element(By.XPATH, ".//p[1]/a")
                    bid_no = bid_anchor.text.strip()
                    bid_link = bid_anchor.get_attribute("href")
                    item = bid_div.find_element(By.XPATH, ".//div[3]/div/div[1]/div[1]/a").text.strip()
                    quantity = bid_div.find_element(By.XPATH, ".//div[3]/div/div[1]/div[2]").text.strip()
                    department = bid_div.find_element(By.XPATH, ".//div[3]/div/div[2]/div[2]").text.strip()
                    start_date = bid_div.find_element(By.XPATH, ".//div[3]/div/div[3]/div[1]/span").text.strip()
                    end_date = bid_div.find_element(By.XPATH, ".//div[3]/div/div[3]/div[2]/span").text.strip()

                    bid_data = {
                        "page": current_page,
                        "bid_no": bid_no,
                        "bid_link": bid_link,
                        "items": item,
                        "quantity": quantity,
                        "department_name": department,
                        "start_date": start_date,
                        "end_date": end_date
                    }

                    if not any(b.get("bid_no") == bid_no for b in data_list):
                        data_list.append(bid_data)
                        print(f"✅ Scraped ({i}/10): {bid_no}")
                    else:
                        print(f"⏩ Skipped duplicate bid: {bid_no}")

                except Exception as e:
                    print(f"⚠️ Error parsing bid card {i}: {e}")

            # Save progress after every page
            with open(BID_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(data_list, f, indent=4, ensure_ascii=False)

            print(f"💾 Saved {len(data_list)} bids so far.")

            # Pagination Logic
            if current_page == 1:
                next_xpath = '//*[@id="light-pagination"]/a[7]'
            elif current_page == 2:
                next_xpath = '//*[@id="light-pagination"]/a[8]'
            elif current_page == 3:
                next_xpath = '//*[@id="light-pagination"]/a[8]'
            elif current_page == 4:
                next_xpath = '//*[@id="light-pagination"]/a[9]'
            else:
                next_xpath = '//*[@id="light-pagination"]/a[10]'

            try:
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, next_xpath)))
                ActionChains(driver).move_to_element(next_button).click().perform()
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ Could not click next button at page {current_page}: {e}")
                break

    except Exception as main_e:
        print(f"❌ Scraper crashed: {main_e}")
    finally:
        driver.quit()
        print("🛑 Driver closed.")


# ========================
# BACKGROUND SCRAPER RUNNER
# ========================
def run_scraper_in_background():
    scrape_data() 
    print("✅ Scraper finished one full cycle. Restarting in 1 hour...")
    time.sleep(3600)
    run_scraper_in_background()


# ========================
# MAIN ENTRY POINT
# ========================
if __name__ == "__main__":
    threading.Thread(target=run_scraper_in_background, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



# from flask import Flask, jsonify, request, Response
# import json
# import threading
# import time
# import requests
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.action_chains import ActionChains
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from flask_cors import CORS
# import os

# # ========================
# # 📧 EMAIL CONFIGURATION
# # ========================
 
# SENDER_EMAIL = "ovinenterprises.main@gmail.com"   
# SENDER_PASSWORD = "ixlz wuhy uouu thiz" 
# MANAGER_EMAIL = "ovinenterprises.main@gmail.com" 



# # ========================
# # PATH SETUP
# # ========================
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# PUBLIC_DIR = os.path.join(BASE_DIR, "..", "public")
# BID_FILE_PATH = os.path.join(PUBLIC_DIR, "bid1.json")

# os.makedirs(PUBLIC_DIR, exist_ok=True)

# # ========================
# # FLASK SETUP
# # ========================
# app = Flask(__name__)
# CORS(app)

# @app.route("/api/data", methods=["GET"])
# def get_data():
#     """Return the bid data"""
#     try:
#         with open(BID_FILE_PATH, "r", encoding="utf-8") as file:
#             data = json.load(file)
#         return jsonify(data)
#     except FileNotFoundError:
#         return jsonify({"error": "bid1.json not found"}), 404
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# # ✅ PDF PROXY ROUTE
# @app.route("/api/proxy-pdf", methods=["GET"])
# def proxy_pdf():
#     pdf_url = request.args.get('url')
#     if not pdf_url:
#         return jsonify({"error": "No URL provided"}), 400
#     try:
#         # Backend requests aren't blocked by CORS
#         headers = {
#             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
#         }
#         resp = requests.get(pdf_url, headers=headers, stream=True)
#         return Response(resp.iter_content(chunk_size=1024), content_type='application/pdf')
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# # ✅ CONTACT ROUTE (Smart Logic: Bid vs General)
# @app.route("/api/contact", methods=["POST"])
# def send_email():
#     data = request.json
#     name = data.get('name')
#     user_email = data.get('email')
#     phone = data.get('phone')
#     message = data.get('message')
    
#     # Check karega ki Bid Data hai ya nahi
#     bid_no = data.get('bid_no', 'General Inquiry')
#     bid_name = data.get('bid_name', 'N/A')

#     if not all([name, user_email, phone, message]):
#         return jsonify({"error": "All fields are required"}), 400

#     # ✅ LOGIC: Mail Body Change based on Source
#     if bid_no != 'General Inquiry':
#         # CASE 1: PARTICIPATE BUTTON SE AAYA HAI
#         subject = f"🔔 Bid Inquiry: {bid_no} (from {name})"
#         body = f"""
#         Hello Manager,
        
#         A user wants to PARTICIPATE in a Bid.
        
#         📦 Bid Details:
#         --------------------------------------
#         🔢 Bid No:    {bid_no}
#         📋 Item Name: {bid_name}
#         --------------------------------------
        
#         👤 Lead Details:
#         Name:   {name}
#         Phone:  {phone}
#         Email:  {user_email}
        
#         📝 Message:
#         {message}
#         """
#     else:
#         # CASE 2: NORMAL CONTACT US SE AAYA HAI
#         subject = f"📩 New General Inquiry from {name}"
#         body = f"""
#         Hello Manager,
        
#         You have received a new contact request from the website.
        
#         👤 Lead Details:
#         --------------------------------------
#         Name:   {name}
#         Phone:  {phone}
#         Email:  {user_email}
#         --------------------------------------
        
#         📝 Message:
#         {message}
#         """

#     try:
#         msg = MIMEMultipart()
#         msg['From'] = SENDER_EMAIL
#         msg['To'] = MANAGER_EMAIL
#         msg['Subject'] = subject
#         msg.attach(MIMEText(body, 'plain'))

#         # Sending Logic
#         server = smtplib.SMTP('smtp.gmail.com', 587)
#         server.starttls()
#         server.login(SENDER_EMAIL, SENDER_PASSWORD)
#         server.send_message(msg)
#         server.quit()

#         return jsonify({"message": "Email sent successfully!"}), 200

#     except Exception as e:
#         print(f"Mail Error: {e}")
#         return jsonify({"error": str(e)}), 500


# # ========================
# # ✅ ASYNC EMAIL SENDER (Background Function)
# # ========================
# def send_async_email(user_email, phone):
#     """Ye function background me chalega taaki frontend na atke"""
#     try:
#         subject = f"📱 New Mandatory Phone Number: {user_email}"
#         body = f"""
#         Hello Admin,

#         A user has completed the mandatory phone number verification step.

#         👤 User Details:
#         --------------------------------------
#         Email:  {user_email}
#         Phone:  {phone}
#         --------------------------------------

#         Please ensure this is updated in the records.
#         """

#         msg = MIMEMultipart()
#         msg['From'] = SENDER_EMAIL
#         msg['To'] = MANAGER_EMAIL
#         msg['Subject'] = subject
#         msg.attach(MIMEText(body, 'plain'))

#         server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15) # Timeout added
#         server.starttls()
#         server.login(SENDER_EMAIL, SENDER_PASSWORD)
#         server.send_message(msg)
#         server.quit()
#         print(f"✅ [Background] Email sent successfully for {user_email}")

#     except Exception as e:
#         print(f"❌ [Background] Email Failed: {e}")

# # ========================
# # ✅ ROUTE: UPDATE PHONE (Non-Blocking)
# # ========================
# @app.route("/api/update-phone", methods=["POST"])
# def update_phone_number():
#     data = request.json
#     user_email = data.get('email')
#     phone = data.get('phone')

#     # 1. Validation: Check agar phone number strictly 10 digits ka hai
#     if not phone or not str(phone).isdigit() or len(str(phone)) != 10:
#         return jsonify({"error": "Invalid Phone Number. Must be exactly 10 digits."}), 400
    
#     if not user_email:
#         return jsonify({"error": "Email is required"}), 400

#     # 2. Start Background Thread for Email (User won't wait for this)
#     threading.Thread(target=send_async_email, args=(user_email, phone)).start()

#     # 3. Respond Immediately to Frontend
#     print(f"✅ Phone request accepted for {user_email}: {phone}")
#     return jsonify({"message": "Phone number saved successfully!"}), 200


# # ========================
# # SCRAPER FUNCTION (FULL CODE)
# # ========================
# def scrape_data():
#     chrome_options = Options()
#     chrome_options.add_argument("--headless")
#     chrome_options.add_argument("--no-sandbox")
#     chrome_options.add_argument("--disable-dev-shm-usage")

#     driver = webdriver.Chrome(options=chrome_options)
#     wait = WebDriverWait(driver, 10)

#     try:
#         driver.get("https://bidplus.gem.gov.in/all-bids")
#         time.sleep(3)

#         print("⚙️ Starting scraping (10 bids per page)...")

#         # Load existing data if available
#         if os.path.exists(BID_FILE_PATH):
#             with open(BID_FILE_PATH, "r", encoding="utf-8") as f:
#                 try:
#                     data_list = json.load(f)
#                 except:
#                     data_list = []
#         else:
#             data_list = []

#         total_pages = 3700

#         for current_page in range(1, total_pages + 1):
#             print(f"\n📄 Scraping page {current_page}")

#             try:
#                 wait.until(EC.presence_of_all_elements_located((By.XPATH, '//*[@id="bidCard"]/div')))
#                 bid_cards = driver.find_elements(By.XPATH, '//*[@id="bidCard"]/div')[:10]
#             except Exception:
#                 print(f"⚠️ Could not find bid cards on page {current_page}, skipping...")
#                 continue

#             for i, bid_div in enumerate(bid_cards, start=1):
#                 try:
#                     bid_anchor = bid_div.find_element(By.XPATH, ".//p[1]/a")
#                     bid_no = bid_anchor.text.strip()
#                     bid_link = bid_anchor.get_attribute("href")
#                     item = bid_div.find_element(By.XPATH, ".//div[3]/div/div[1]/div[1]/a").text.strip()
#                     quantity = bid_div.find_element(By.XPATH, ".//div[3]/div/div[1]/div[2]").text.strip()
#                     department = bid_div.find_element(By.XPATH, ".//div[3]/div/div[2]/div[2]").text.strip()
#                     start_date = bid_div.find_element(By.XPATH, ".//div[3]/div/div[3]/div[1]/span").text.strip()
#                     end_date = bid_div.find_element(By.XPATH, ".//div[3]/div/div[3]/div[2]/span").text.strip()

#                     bid_data = {
#                         "page": current_page,
#                         "bid_no": bid_no,
#                         "bid_link": bid_link,
#                         "items": item,
#                         "quantity": quantity,
#                         "department_name": department,
#                         "start_date": start_date,
#                         "end_date": end_date
#                     }

#                     if not any(b.get("bid_no") == bid_no for b in data_list):
#                         data_list.append(bid_data)
#                         print(f"✅ Scraped ({i}/10): {bid_no}")
#                     else:
#                         print(f"⏩ Skipped duplicate bid: {bid_no}")

#                 except Exception as e:
#                     print(f"⚠️ Error parsing bid card {i}: {e}")

#             # Save progress after every page
#             with open(BID_FILE_PATH, "w", encoding="utf-8") as f:
#                 json.dump(data_list, f, indent=4, ensure_ascii=False)

#             print(f"💾 Saved {len(data_list)} bids so far.")

#             # Pagination Logic
#             if current_page == 1:
#                 next_xpath = '//*[@id="light-pagination"]/a[7]'
#             elif current_page == 2:
#                 next_xpath = '//*[@id="light-pagination"]/a[8]'
#             elif current_page == 3:
#                 next_xpath = '//*[@id="light-pagination"]/a[8]'
#             elif current_page == 4:
#                 next_xpath = '//*[@id="light-pagination"]/a[9]'
#             else:
#                 next_xpath = '//*[@id="light-pagination"]/a[10]'

#             try:
#                 next_button = wait.until(EC.element_to_be_clickable((By.XPATH, next_xpath)))
#                 ActionChains(driver).move_to_element(next_button).click().perform()
#                 time.sleep(2)
#             except Exception as e:
#                 print(f"⚠️ Could not click next button at page {current_page}: {e}")
#                 break

#     except Exception as main_e:
#         print(f"❌ Scraper crashed: {main_e}")
#     finally:
#         driver.quit()
#         print("🛑 Driver closed.")


# # ========================
# # BACKGROUND SCRAPER RUNNER
# # ========================
# def run_scraper_in_background():
#     scrape_data() 
#     print("✅ Scraper finished one full cycle. Restarting in 1 hour...")
#     time.sleep(3600)
#     run_scraper_in_background()


# # ========================
# # MAIN ENTRY POINT
# # ========================
# if __name__ == "__main__":
#     threading.Thread(target=run_scraper_in_background, daemon=True).start()
#     print("🚀 Flask API running at http://127.0.0.1:5000/api/data")
#     app.run(debug=True)






# from flask import Flask, jsonify, request, Response
# from flask_cors import CORS
# import json
# import threading
# import requests
# import smtplib
# import os
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart

# # ========================
# # 🔐 ENV CONFIG (RENDER SAFE)
# # ========================
# SENDER_EMAIL = os.getenv("SENDER_EMAIL")
# SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
# MANAGER_EMAIL = os.getenv("MANAGER_EMAIL")

# # ========================
# # 📂 FILE PATH (RENDER SAFE)
# # ========================
# PUBLIC_DIR = "/tmp/public"
# BID_FILE_PATH = os.path.join(PUBLIC_DIR, "bid1.json")
# os.makedirs(PUBLIC_DIR, exist_ok=True)

# # ========================
# # 🚀 FLASK SETUP
# # ========================
# app = Flask(__name__)
# CORS(app)

# # ========================
# # 📄 GET BID DATA
# # ========================
# @app.route("/api/data", methods=["GET"])
# def get_data():
#     try:
#         with open(BID_FILE_PATH, "r", encoding="utf-8") as f:
#             return jsonify(json.load(f))
#     except FileNotFoundError:
#         return jsonify({"error": "bid1.json not found"}), 404
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# # ========================
# # 📄 PDF PROXY
# # ========================
# @app.route("/api/proxy-pdf", methods=["GET"])
# def proxy_pdf():
#     pdf_url = request.args.get("url")
#     if not pdf_url:
#         return jsonify({"error": "No URL provided"}), 400

#     try:
#         headers = {"User-Agent": "Mozilla/5.0"}
#         r = requests.get(pdf_url, headers=headers, stream=True, timeout=15)
#         return Response(r.iter_content(1024), content_type="application/pdf")
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# # ========================
# # 📧 EMAIL SENDER
# # ========================
# def send_email(subject, body):
#     msg = MIMEMultipart()
#     msg["From"] = SENDER_EMAIL
#     msg["To"] = MANAGER_EMAIL
#     msg["Subject"] = subject
#     msg.attach(MIMEText(body, "plain"))

#     server = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
#     server.starttls()
#     server.login(SENDER_EMAIL, SENDER_PASSWORD)
#     server.send_message(msg)
#     server.quit()

# # ========================
# # 📩 CONTACT API
# # ========================
# @app.route("/api/contact", methods=["POST"])
# def contact():
#     data = request.json
#     name = data.get("name")
#     email = data.get("email")
#     phone = data.get("phone")
#     message = data.get("message")
#     bid_no = data.get("bid_no", "General Inquiry")
#     bid_name = data.get("bid_name", "N/A")

#     if not all([name, email, phone, message]):
#         return jsonify({"error": "All fields required"}), 400

#     subject = f"Bid Inquiry: {bid_no}" if bid_no != "General Inquiry" else "New General Inquiry"

#     body = f"""
# Name: {name}
# Email: {email}
# Phone: {phone}

# Bid No: {bid_no}
# Item: {bid_name}

# Message:
# {message}
# """

#     try:
#         threading.Thread(
#             target=send_email,
#             args=(subject, body),
#             daemon=True
#         ).start()

#         return jsonify({"message": "Email sent successfully"}), 200

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# # ========================
# # 📱 UPDATE PHONE (ASYNC)
# # ========================
# @app.route("/api/update-phone", methods=["POST"])
# def update_phone():
#     data = request.json
#     email = data.get("email")
#     phone = data.get("phone")

#     if not phone or not phone.isdigit() or len(phone) != 10:
#         return jsonify({"error": "Invalid phone"}), 400

#     def bg_task():
#         send_email(
#             "New Phone Submission",
#             f"Email: {email}\nPhone: {phone}"
#         )

#     threading.Thread(target=bg_task, daemon=True).start()
#     return jsonify({"message": "Phone saved"}), 200

# # ========================
# # 🏁 ENTRY POINT (RENDER SAFE)
# # ========================
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)



