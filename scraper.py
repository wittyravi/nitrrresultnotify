import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configurations
URL = "https://mis.nitrr.ac.in/publishedresult.aspx"

# 1. Put your target branch here:
TARGET_TEXT = "B.Tech.[INFORMATION TECHNOLOGY-2019-2020 [CBCS]] [II]" 
# 2. Tell the bot to ONLY look for results published in this year:
TARGET_YEAR = "2026" 

def send_telegram_notification(matched_line):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if bot_token and chat_id:
        try:
            # We now send the EXACT line found, including the date!
            msg = f"🚨 NITRR RESULT ALERT:\n\n{matched_line}\n\nCheck here: {URL}"
            req_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = requests.post(req_url, json={"chat_id": chat_id, "text": msg})
            
            if response.status_code == 200:
                print("✅ Telegram Notification sent successfully!")
            else:
                print(f"❌ Telegram API Rejected it! Reason: {response.text}")
        except Exception as e:
            print(f"Failed to connect to Telegram: {e}")
    else:
        print("Telegram credentials not found in secrets.")

def send_sms_notification(matched_line):
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")
    
    my_phone = "+918770319200" 
    
    if account_sid and auth_token and twilio_phone:
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            payload = {
                "Body": f"🚨 NITRR Result OUT: {matched_line} : https://mis.nitrr.ac.in/publishedresult.aspx ",
                "From": twilio_phone,
                "To": my_phone
            }
            response = requests.post(url, data=payload, auth=(account_sid, auth_token))
            
            if response.status_code in [200, 201]:
                print("✅ Twilio SMS Notification sent successfully!")
            else:
                print(f"❌ Twilio API Rejected it! Code: {response.status_code}, Reason: {response.text}")
        except Exception as e:
            print(f"Failed to connect to Twilio: {e}")
    else:
        print("Twilio credentials not found in secrets.")

def get_published_result_line(driver, search_text, target_year):
    """Scans the visible text line-by-line to ensure BOTH the branch and the year match."""
    try:
        # Get the text exactly as a human sees it on the screen
        body_text = driver.find_element(By.TAG_NAME, "body").text
        lines = body_text.split('\n')
        
        for line in lines:
            # If the line contains the branch text AND the year 2026
            if search_text in line and target_year in line:
                return line # Return the full text (e.g., "B.Tech.[...] [II] - 14/05/2026")
    except Exception as e:
        print(f"Error extracting text: {e}")
    
    return None

def main():
    print("Starting browser...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(10)
    
    try:
        print(f"Opening URL: {URL}")
        driver.get(URL)
        time.sleep(4) 
        
        search_text = TARGET_TEXT.strip()
        
        # 1. Check Front Page
        print("Checking Latest Results on front page...")
        found_line = get_published_result_line(driver, search_text, TARGET_YEAR)
        
        if found_line:
            print(f"Found in Latest Results! -> {found_line}")
            send_telegram_notification(found_line)
            send_sms_notification(found_line)
            return

        # 2. Check Dropdowns
        print("Not on front page. Checking dropdowns...")
        selects = driver.find_elements(By.TAG_NAME, "select")
        if len(selects) >= 2:
            print("Selecting Degree...")
            degree_dropdown = Select(selects[0])
            degree_dropdown.select_by_visible_text("B.Tech.")
            time.sleep(5) 
            
            print("Selecting Branch...")
            selects = driver.find_elements(By.TAG_NAME, "select")
            branch_dropdown = Select(selects[1])
            branch_dropdown.select_by_visible_text("INFORMATION TECHNOLOGY")
            time.sleep(5) 
            
            print("Checking Branch Results...")
            found_line = get_published_result_line(driver, search_text, TARGET_YEAR)
            
            if found_line:
                print(f"Found in Branch Results! -> {found_line}")
                send_telegram_notification(found_line)
                send_sms_notification(found_line)
            else:
                print(f"Result for '{search_text}' in year {TARGET_YEAR} not yet published.")
        else:
            print("Dropdowns not found on the page.")
            
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        print("Closing browser...")
        driver.quit()

if __name__ == "__main__":
    main()
