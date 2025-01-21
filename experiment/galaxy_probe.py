import json
import time
import urllib.parse

import undetected_chromedriver as uc
from fake_useragent import UserAgent
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

LOCALSTORAGE_FILE = "localstorage.json"
URL = "https://galaxy.mobstudio.ru/web/"  # Updated Galaxy URL
COOKIES_FILE = "cookies.json"
LOG_FILE = "log.log"
PROXY = "socks4://139.162.136.140:1080"  # Replace with your proxy if needed


# Configure Selenium options
def configure_driver(proxy=PROXY):
    ua = UserAgent()
    user_agent = ua.random  # Generate a random User-Agent

    options = uc.ChromeOptions()
    # options.add_argument("--headless")  # Run in headless mode
    options.add_argument(f"--user-agent={user_agent}")  # Set random User-Agent
    options.add_argument("--auto-open-devtools-for-tabs")  # Open DevTools for network inspection
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    if proxy:
        options.add_argument(f"--proxy-server={proxy}")

    return uc.Chrome(options=options)


# Function to decode JSON strings inside cookies or localStorage
def decode_json_strings(data):
    if isinstance(data, str):
        try:
            decoded = urllib.parse.unquote(data)
            deserialized = json.loads(decoded)
            # Recursively decode nested JSON strings
            return decode_json_strings(deserialized)
        except (json.JSONDecodeError, TypeError):
            return urllib.parse.unquote(data)
    elif isinstance(data, dict):
        return {key: decode_json_strings(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [decode_json_strings(item) for item in data]
    return data


# Function to log changes to a file
def log_changes(log_message):
    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {log_message}\n")


# Function to save localStorage to a file
def save_localstorage_to_file(driver, file_path):
    localstorage = driver.execute_script("return window.localStorage;")
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(localstorage, file, ensure_ascii=False)


# Function to load localStorage from a file
def load_localstorage_from_file(driver, file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            localstorage = json.load(file)
            for key, value in localstorage.items():
                driver.execute_script(f"window.localStorage.setItem('{key}', '{value}');")
    except FileNotFoundError:
        print("LocalStorage file not found. Proceeding without loading localStorage.")


# Function to save cookies to a file
def save_cookies_to_file(driver, file_path):
    cookies = driver.get_cookies()
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(cookies, file, ensure_ascii=False)


# Function to load cookies from a file
def load_cookies_from_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# Function to add cookies via DevTools Protocol
def add_cookies_via_devtools(driver, cookies):
    for cookie in cookies:
        driver.execute_cdp_cmd(
            "Network.setCookie",
            {
                "name": cookie["name"],
                "value": cookie["value"],
                "domain": cookie["domain"],
                "path": cookie.get("path", "/"),
                "secure": cookie.get("secure", False),
                "httpOnly": cookie.get("httpOnly", False),
                "sameSite": cookie.get("sameSite", "None"),
                "expires": cookie.get("expiry"),
            },
        )


# Main function
def main():
    try:
        driver = configure_driver()
        driver.get(URL)

        # Load cookies and localStorage from files and apply
        try:
            cookies = load_cookies_from_file(COOKIES_FILE)
            add_cookies_via_devtools(driver, cookies)
            load_localstorage_from_file(driver, LOCALSTORAGE_FILE)
            driver.refresh()  # Refresh to apply cookies and localStorage
        except FileNotFoundError:
            print("Cookies or LocalStorage file not found. Proceeding without loading them.")

        print("Driver is ready for manual inspection. Press Ctrl+C to exit.")

        previous_cookies = driver.get_cookies()
        previous_localstorage = driver.execute_script("return window.localStorage;")

        # wait 3.5 seconds on the web page before trying anything
        time.sleep(3.5)

        # Wait for 3 seconds until finding the element
        wait = WebDriverWait(driver, 10)
        element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[text()="Создать персонаж"]')))
        print("Product name: " + element.text)

        while True:
            time.sleep(1)  # Keep the browser open for manual inspection

            current_cookies = driver.get_cookies()
            if previous_cookies != current_cookies:
                decoded_cookies = decode_json_strings(current_cookies)
                log_changes(f"Cookies have changed: {json.dumps(decoded_cookies, ensure_ascii=False, indent=2)}")
                save_cookies_to_file(driver, COOKIES_FILE)  # Update cookies file immediately
                previous_cookies = current_cookies

            current_localstorage = driver.execute_script("return window.localStorage;")
            if previous_localstorage != current_localstorage:
                decoded_localstorage = decode_json_strings(current_localstorage)
                log_changes(
                    f"LocalStorage has changed: {json.dumps(decoded_localstorage, ensure_ascii=False, indent=2)}"
                )
                save_localstorage_to_file(driver, LOCALSTORAGE_FILE)  # Update localStorage file immediately
                previous_localstorage = current_localstorage

    except Exception as e:
        print(f"An error occurred during the session: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
