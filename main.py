import os
import re
import shutil
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ================= ACCOUNT CONFIGURATION =================
ACCOUNTS = [  
    {
        "name": "kh2 fb7",
        "country_code": "+880",
        "phone": "1863006261",
        "password": "Alamin143@",
    },
    {
        "name": "Mama",
        "country_code": "+880",
        "phone": "1789095816",
        "password": "Alamin143@",
    },
    {
        "name": "khalu 3 s13",
        "country_code": "+880",
        "phone": "1793965546",
        "password": "Alamin143@",
    },
    {
        "name": "Jamirul",
        "country_code": "+880",
        "phone": "1750450182",
        "password": "Alamin143#",
    },   
]

LOGIN_URL = "https://www.zenquantai.com/#/pages/login/login"
TRADE_URL = "https://www.zenquantai.com/#/pages/UITransaction/trade"
WAIT_AFTER_INJECT = 10
DEFAULT_FALLBACK_WAIT = 3600

recent_claim_history = []

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}h {minutes:02d}m {secs:02d}s"

def parse_remaining_seconds(text):
    if not text:
        return 0
    text = text.lower().strip()
    if "claimable" in text:
        return 0
    total_sec = 0
    if ":" in text:
        parts = text.split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
        except Exception:
            pass

    h_match = re.search(r"(\d+)\s*h", text)
    m_match = re.search(r"(\d+)\s*m", text)
    s_match = re.search(r"(\d+)\s*s", text)

    if h_match:
        total_sec += int(h_match.group(1)) * 3600
    if m_match:
        total_sec += int(m_match.group(1)) * 60
    if s_match:
        total_sec += int(s_match.group(1))

    return total_sec

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless=new")

    try:
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        print(f"⚠️ Chrome Driver Setup Issue: {e}")
        return None

def extract_country_code(text):
    match = re.search(r"\+\d+", text)
    return match.group(0) if match else None

def select_country_by_code(driver, wait, country_code):
    try:
        try:
            country_selector = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//uni-view[contains(@class, 'w-full theme_Login_Input_bg')]//uni-view[contains(@class, 'flex items-center')]"))
            )
            driver.execute_script("arguments[0].click();", country_selector)
        except Exception:
            country_selector = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//uni-view[contains(text(), '+')]"))
            )
            driver.execute_script("arguments[0].click();", country_selector)

        time.sleep(1.5)
        country_items = driver.find_elements(By.XPATH, "//uni-view[contains(@class, 'country-list-row')]")
        for item in country_items:
            try:
                extracted = extract_country_code(item.text)
                if extracted and extracted == country_code:
                    driver.execute_script("arguments[0].click();", item)
                    time.sleep(1)
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False

def handle_activity_notice(driver):
    try:
        time.sleep(1)
        driver.execute_script("""
            var buttons = document.querySelectorAll('.btnCalcel, .btnCancel');
            for (var i = 0; i < buttons.length; i++) {
                if (buttons[i].textContent.includes('Cancel') || buttons[i].textContent.includes('取消')) {
                    buttons[i].click();
                }
            }
        """)
        return True
    except Exception:
        return True

def login(driver, wait, phone, password, country_code):
    try:
        if not select_country_by_code(driver, wait, country_code):
            select_country_by_code(driver, wait, "+880")

        inputs = driver.find_elements(By.CSS_SELECTOR, "input.uni-input-input")
        if len(inputs) >= 2:
            inputs[0].clear()
            inputs[0].send_keys(phone)
            inputs[1].clear()
            inputs[1].send_keys(password)
        else:
            return False

        time.sleep(0.5)
        login_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "uni-view.zq-cta")))
        driver.execute_script("arguments[0].click();", login_btn)

        time.sleep(3)
        handle_activity_notice(driver)

        if "/pages/UITransaction/trade" not in driver.current_url:
            driver.get(TRADE_URL)
            time.sleep(2)
            handle_activity_notice(driver)

        return True
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False

def check_and_get_card_timers(driver):
    time.sleep(2)
    min_time = None
    has_claimable = False
    try:
        timer_texts = driver.execute_script("""
            var texts = [];
            var elements = document.querySelectorAll('.trade-pos__claim, .trade-dur--on, uni-view');
            for(var i=0; i<elements.length; i++){
                var t = elements[i].textContent.trim();
                if(t.includes('Claimable') || t.match(/\\d+h\\s*\\d+m/) || t.match(/\\d+m\\s*\\d+s/) || t.match(/\\d+:\\d+/)){
                    texts.push(t);
                }
            }
            return texts;
        """)

        for text in timer_texts:
            if "Claimable" in text:
                has_claimable = True
                return 0
            sec = parse_remaining_seconds(text)
            if sec > 0:
                if min_time is None or sec < min_time:
                    min_time = sec

        if has_claimable:
            return 0
        if min_time is not None:
            return min_time
    except Exception as e:
        print(f"⚠️ Timer checking error: {e}")

    return DEFAULT_FALLBACK_WAIT

def click_claimable_button(driver, wait):
    try:
        claim_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//uni-view[contains(@class, 'trade-pos__claim')]")))
        driver.execute_script("arguments[0].click();", claim_btn)
        time.sleep(2)
        return True
    except Exception:
        return False

def perform_claim(driver, wait, claim_number=1):
    try:
        if not click_claimable_button(driver, wait):
            return False
        handle_activity_notice(driver)
        try:
            confirm = driver.find_element(By.CSS_SELECTOR, "uni-view.btnConfirm, uni-button.btnConfirm")
            if confirm.is_displayed():
                driver.execute_script("arguments[0].click();", confirm)
                time.sleep(1)
        except Exception:
            pass
        print(f"✅ Claim #{claim_number} completed!")
        return True
    except Exception as e:
        print(f"❌ Claim #{claim_number} failed: {e}")
        return False

def drain_all_claims(driver, wait, account_name, max_loops=10):
    claimed_any = False
    for attempt in range(max_loops):
        if perform_claim(driver, wait, attempt + 1):
            claimed_any = True
            time.sleep(2)
        else:
            break
    if claimed_any:
        now_str = datetime.now().strftime("%H:%M")
        recent_claim_history.append(f"{account_name} ({now_str})")
        if len(recent_claim_history) > 5:
            recent_claim_history.pop(0)
    return claimed_any

def get_balance(driver):
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "uni-text.trade-inject-balance__num span, .trade-inject-balance__num span, .available-balance span")
        for elem in elements:
            val = elem.text.strip()
            if val and val != "0":
                return val
        return "0"
    except Exception:
        return "0"

def select_duration(driver, wait, duration="Plus"):
    try:
        elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{duration}')]")
        for elem in elements:
            if elem.is_displayed():
                driver.execute_script("arguments[0].click();", elem)
                time.sleep(1)
                return True
        return False
    except Exception:
        return False

def click_confirm_button(driver, wait):
    try:
        confirm_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "uni-button.zq-cert__confirm, .btnConfirm")))
        driver.execute_script("arguments[0].click();", confirm_btn)
        time.sleep(1)
        return True
    except Exception:
        return False

def perform_injection(driver, wait, duration="Plus", account_name=""):
    try:
        drain_all_claims(driver, wait, account_name, max_loops=3)
        amount = get_balance(driver)
        if amount == "0" or not amount:
            return False
        select_duration(driver, wait, duration)
        amount_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.uni-input-input[type='text']")))
        driver.execute_script("arguments[0].value = '';", amount_input)
        amount_input.send_keys(amount)
        time.sleep(1)
        inject_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "uni-button.trade-submit")))
        driver.execute_script("arguments[0].click();", inject_btn)
        handle_activity_notice(driver)
        time.sleep(WAIT_AFTER_INJECT)
        click_confirm_button(driver, wait)
        time.sleep(2)
        return True
    except Exception as e:
        print(f"❌ {duration} injection failed: {e}")
        return False

def run_account_cycle(account):
    driver = setup_driver()
    if not driver:
        return

    wait = WebDriverWait(driver, 20)
    account_name = account["name"]

    try:
        print(f"\n--- Starting session for: {account_name} ---")
        driver.get(LOGIN_URL)
        time.sleep(2)
        handle_activity_notice(driver)

        if not login(driver, wait, account["phone"], account["password"], account.get("country_code", "+880")):
            print(f"❌ Login failed for {account_name}")
            return

        if "/pages/UITransaction/trade" not in driver.current_url:
            driver.get(TRADE_URL)
            time.sleep(2)
            handle_activity_notice(driver)

        drain_all_claims(driver, wait, account_name, max_loops=10)
        perform_injection(driver, wait, "Plus", account_name)
        perform_injection(driver, wait, "3Hours", account_name)
        drain_all_claims(driver, wait, account_name, max_loops=3)

        print(f"✅ [{account_name}] Cycle completed successfully.")
    except Exception as e:
        print(f"⚠️ Error processing {account_name}: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

def main():
    print("=" * 65)
    print("🚀 SEQUENTIAL MULTI-ACCOUNT TRADING BOT STARTED")
    print("=" * 65)
    
    while True:
        print("\n" + "🔄 Beginning new execution round for all accounts..." + "\n")
        for acc in ACCOUNTS:
            run_account_cycle(acc)
            time.sleep(5)
            
        print("\n💤 All accounts finished. Waiting 2 hours for the next cycle...")
        time.sleep(7200)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")
