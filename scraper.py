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
TARGET_TEXT = "B.Tech.[ELECTRICAL ENGINEERING-2019-2020 [CBCS]] [IV]" 

def send_telegram_notification():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if bot_token and chat_id:
        try:
            msg = f"🚨 NITRR RESULT ALERT: \n\n{TARGET_TEXT} is now published!\nCheck here: {URL}"
            req_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = requests.post(req_url, json={"chat_id": chat_id, "text": msg})
            
            # This checks if Telegram ACTUALLY accepted the message
            if response.status_code == 200:
                print("✅ Telegram Notification sent successfully!")
            else:
                print(f"❌ Telegram API Rejected it! Reason: {response.text}")
        except Exception as e:
            print(f"Failed to connect to Telegram: {e}")
    else:
        print("Telegram credentials not found in secrets.")

def send_sms_notification():
    api_key = os.environ.get("FAST2SMS_API_KEY")
    phone = "8770319200" # Your phone number
    
    if api_key:
        try:
            url = "https://www.fast2sms.com/dev/bulkV2"
            payload = f"message=NITRR Result is OUT: {TARGET_TEXT}&language=english&route=q&numbers={phone}"
            headers = {'authorization': api_key, 'Content-Type': "application/x-www-form-urlencoded"}
            response = requests.post(url, data=payload, headers=headers)
            
            # This checks if Fast2SMS ACTUALLY accepted the message
            if response.status_code == 200:
                print("✅ SMS Notification sent successfully!")
            else:
                print(f"❌ Fast2SMS API Rejected it! Code: {response.status_code}, Reason: {response.text}")
        except Exception as e:
            print(f"Failed to connect to Fast2SMS: {e}")
    else:
        print("Fast2SMS API Key not found in secrets.")

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
