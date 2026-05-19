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
# USING ELECTRICAL ENG FOR TESTING PURPOSES
TARGET_TEXT = "B.Tech.[INFORMATION TECHNOLOGY-2019-2020 [CBCS]] [IV]"  #B.Tech.[INFORMATION TECHNOLOGY-2019-2020 [CBCS]] [IV] - 14/05/2026


def send_telegram_notification():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if bot_token and chat_id:
        try:
            msg = f"🚨 NITRR RESULT ALERT: \n\n{TARGET_TEXT} is now published!\nCheck here: {URL}"
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

def send_sms_notification():
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")
    
    # Twilio REQUIRES the country code (+91)
    my_phone = "+918770319200" 
    
    if account_sid and auth_token and twilio_phone:
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            payload = {
                "Body": f"🚨 NITRR Result OUT: {TARGET_TEXT}. Check portal : https://mis.nitrr.ac.in/publishedresult.aspx !",
                "From": twilio_phone,
                "To": my_phone
            }
            # Twilio uses HTTP Basic Auth
            response = requests.post(url, data=payload, auth=(account_sid, auth_token))
            
            if response.status_code in [200, 201]:
                print("✅ Twilio SMS Notification sent successfully!")
            else:
                print(f"❌ Twilio API Rejected it! Code: {response.status_code}, Reason: {response.text}")
        except Exception as e:
            print(f"Failed to connect to Twilio: {e}")
    else:
        print("Twilio credentials not found in secrets.")

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
        time.sleep(3) 
        
        if TARGET_TEXT in driver.page_source:
            print("Found in Latest Results!")
            send_telegram_notification()
            send_sms_notification()
            return

        print("Not on front page. Checking dropdowns...")
        selects = driver.find_elements(By.TAG_NAME, "select")
        if len(selects) >= 2:
            degree_dropdown = Select(selects[0])
            degree_dropdown.select_by_visible_text("B.Tech.")
            time.sleep(3) 
            
            branch_dropdown = Select(selects[1])
            branch_dropdown.select_by_visible_text("INFORMATION TECHNOLOGY")
            time.sleep(3) 
            
            if TARGET_TEXT in driver.page_source:
                print("Found in Branch Results!")
                send_telegram_notification()
                send_sms_notification()
            else:
                print("Result not yet published.")
        else:
            print("Dropdowns not found on the page.")
            
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        print("Closing browser...")
        driver.quit()

if __name__ == "__main__":
    main()
