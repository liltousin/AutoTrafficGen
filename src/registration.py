import os
import platform
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

from fake_useragent import UserAgent
from undetected_chromedriver import Chrome, ChromeOptions

from database import connect_to_db
from state_machine import StateMachine

# Global configuration
URL = "https://galaxy.mobstudio.ru/web/"  # Updated Galaxy URL
NUM_THREADS = 1  # Number of threads to run

# Path to the original chromedriver executable (for Windows only)
ORIGINAL_DRIVER_PATH = os.path.expanduser("~\\AppData\\Roaming\\undetected_chromedriver\\undetected_chromedriver.exe")


# Configure Selenium options
def configure_driver(proxy):
    if not proxy:
        raise ValueError("A proxy must be provided.")

    ua = UserAgent()
    user_agent = ua.random  # Generate a random User-Agent

    options = ChromeOptions()
    # options.add_argument("--headless")  # Run in headless mode
    options.add_argument(f"--user-agent={user_agent}")  # Set random User-Agent
    options.add_argument("--auto-open-devtools-for-tabs")  # Open DevTools for network inspection
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--proxy-server={proxy}")

    if platform.system() == "Windows":
        # Create a unique temporary directory for each process (Windows only)
        temp_dir = tempfile.mkdtemp()
        driver_path = os.path.join(temp_dir, "chromedriver.exe")

        # Copy the original driver to the temporary directory
        if os.path.exists(ORIGINAL_DRIVER_PATH):
            shutil.copy(ORIGINAL_DRIVER_PATH, driver_path)
        else:
            raise FileNotFoundError(f"Original chromedriver not found at {ORIGINAL_DRIVER_PATH}")

        # Use the unique driver path
        return Chrome(options=options, driver_executable_path=driver_path)
    else:
        # Use default behavior for non-Windows systems
        return Chrome(options=options)


# Function to fetch the best proxies without duplicate real_ip
def fetch_best_proxies(conn):
    try:
        cur = conn.cursor()

        # Fetch the best proxies without duplicate real_ip
        cur.execute(
            """
            WITH ranked_proxies AS (
                SELECT id, ip, port, protocol, real_ip, score,
                       ROW_NUMBER() OVER (PARTITION BY real_ip ORDER BY score DESC) AS rank
                FROM proxies
                WHERE score > 0.5
            )
            SELECT id, ip, port, protocol, real_ip
            FROM ranked_proxies
            WHERE rank = 1
            ORDER BY score DESC
            LIMIT %s
            FOR UPDATE SKIP LOCKED;
            """,
            (NUM_THREADS,),
        )
        proxies = cur.fetchall()
        return proxies
    except Exception as e:
        print(f"Error fetching proxies: {e}")
        return []


# Function to run Selenium with a proxy and state machine
def worker(proxy):
    driver = None
    try:
        driver = configure_driver(proxy)
        state_machine = StateMachine(driver, URL, proxy)
        state_machine.run()
        print(f"State machine completed successfully for proxy {proxy}")

    except Exception as e:
        print(f"Error with proxy {proxy}: {e}")
    finally:
        if driver:
            driver.quit()


# Main function to manage registration threads
def run_registration_threads():
    try:
        conn = connect_to_db()

        while True:
            # Fetch the best proxies
            proxies = fetch_best_proxies(conn)

            if not proxies:
                print("No proxies available. Retrying in 10 seconds.")
                time.sleep(10)
                continue

            with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
                executor.map(lambda proxy_data: worker(f"{proxy_data[3]}://{proxy_data[1]}:{proxy_data[2]}"), proxies)

    except Exception as e:
        print(f"Error in registration process: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    run_registration_threads()
