import os
import time
import glob
import re
import requests
import urllib3 
import pdfplumber
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Disable the annoying SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. SETUP YOUR CLASS DATA HERE
# ==========================================
# Generates roll numbers from 25118001 to 25118114
roll_numbers = [str(r) for r in range(25118001, 25118115)] 

url = "https://mis.nitrr.ac.in/iitmsoBF2zO1QWoLeV7wV7kw7kcHJeahVjzN4t6MFMeyhUykpKfBA9V+F0/3m6SMOr7hf?enc=2vjcaEnhmvfs4iwSJr18eQaN1iwTCkDZLg4FpnIV12/vTB0HoHDs8kZdmyK5DB9t"

session_text = "2025-2026 II" 
semester_text = "II"  # Updated to Semester II

# ==========================================
# 2. SETUP MAC DOWNLOAD FOLDER & CHROME
# ==========================================
# Created a new folder so it doesn't mix with the Semester IV PDFs
download_dir = os.path.join(os.getcwd(), "NITRR_PDF_Results_Sem2")
os.makedirs(download_dir, exist_ok=True)

options = webdriver.ChromeOptions()
print(f"Starting Chrome Browser to fetch {len(roll_numbers)} results...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 15)

# ==========================================
# 3. AUTOMATE THE WEBSITE & FORCE DOWNLOAD
# ==========================================
for roll in roll_numbers:
    try:
        print(f"\nFetching result for Roll No: {roll}...")
        driver.get(url)
        
        # A. Enter Roll Number
        roll_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text']")))
        roll_input.clear()
        roll_input.send_keys(str(roll))
        
        # B. Click "Show"
        show_btn = driver.find_element(By.XPATH, "//a[contains(text(), 'Show')] | //button[contains(text(), 'Show')] | //input[@value='Show']")
        driver.execute_script("arguments[0].click();", show_btn)
        
        time.sleep(3) # Wait for student details to load
        
        # C. Select SESSION Dropdown
        session_dropdown = wait.until(EC.presence_of_element_located((By.XPATH, "//select[contains(@id, 'Session') or contains(@name, 'Session')]")))
        Select(session_dropdown).select_by_visible_text(session_text)
        
        time.sleep(2) # Wait for semester dropdown to populate
        
        # D. Select SEMESTER Dropdown
        semester_dropdown = wait.until(EC.presence_of_element_located((By.XPATH, "//select[contains(@id, 'Sem') or contains(@name, 'Sem')]")))
        Select(semester_dropdown).select_by_visible_text(semester_text)
        
        # E. Click "CBCS Result"
        result_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'CBCS Result') or @value='CBCS Result']")))
        driver.execute_script("arguments[0].click();", result_btn)
        
        # F. GRAB PDF FROM NEW TAB (Bypassing SSL)
        wait.until(EC.number_of_windows_to_be(2)) 
        driver.switch_to.window(driver.window_handles[1]) 
        
        wait.until(lambda d: "http" in d.current_url and "blank" not in d.current_url)
        pdf_url = driver.current_url
        
        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])
            
        # Download the file
        res = session.get(pdf_url, verify=False) 
        
        if res.status_code == 200 and b"%PDF" in res.content[:10]:
            pdf_path = os.path.join(download_dir, f"{roll}.pdf")
            with open(pdf_path, 'wb') as f:
                f.write(res.content)
            print(f"✅ Downloaded: {roll}")
        else:
            print(f"❌ Failed to download PDF for {roll}. (Server returned status {res.status_code})")
            
        # Close the PDF tab and go back to main window
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

    except Exception as e:
        print(f"⚠️ Skipped {roll} (Might not exist or took too long to load)")
        # Clean up any stuck tabs before moving to the next student
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[1])
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

driver.quit()
print("\nAll PDFs downloaded successfully! Now extracting and cleaning data...")

# ==========================================
# 4. EXTRACT & CLEAN DATA FROM PDFS TO EXCEL
# ==========================================
final_data = []
pdf_files = glob.glob(os.path.join(download_dir, "*.pdf"))

if not pdf_files:
    print("No PDFs were found in the folder. Please check if the download worked.")
else:
    for pdf_path in pdf_files:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = pdf.pages[0].extract_text()
                
                # 1. Grab the raw name
                name_match = re.search(r"Name\s*:\s*(.*?)(?=\n|Father)", text, re.IGNORECASE)
                raw_name = name_match.group(1).strip() if name_match else "N/A"
                
                # 2. Chop off the Hindi text/garbled characters!
                clean_name = re.sub(r'[^\x00-\x7F]+.*$', '', raw_name).strip()
                
                # 3. Grab the rest of the data
                roll_match = re.search(r"Roll No\s*:\s*(\d+)", text, re.IGNORECASE)
                spi_match = re.search(r"SPI\s*:\s*([\d.]+)", text, re.IGNORECASE)
                cpi_match = re.search(r"CPI\s*:\s*([\d.]+)", text, re.IGNORECASE)
                
                final_data.append({
                    "Roll No": int(roll_match.group(1)) if roll_match else 0,
                    "Name": clean_name,  # Clean name is used here
                    "SPI": float(spi_match.group(1)) if spi_match else "N/A",
                    "CPI": float(cpi_match.group(1)) if cpi_match else "N/A"
                })
        except Exception as e:
            print(f"Failed to read {pdf_path}: {e}")

    # ==========================================
    # 5. SAVE TO EXCEL
    # ==========================================
    if final_data:
        df = pd.DataFrame(final_data)
        df.sort_values("Roll No", inplace=True)
        
        # Saved under a new name for Semester II
        excel_filename = "Class_Results_Sem2_Compiled.xlsx"
        df.to_excel(excel_filename, index=False)
        print(f"\n🎉 SUCCESS! Extracted {len(df)} results and saved to '{excel_filename}'")