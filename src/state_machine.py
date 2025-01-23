import random
import time

from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By


class StateMachine:
    def __init__(self, driver, url, proxy):
        self.driver = driver
        self.url = url
        self.proxy = proxy

    def run(self):
        print(f"Starting StateMachine with proxy: {self.proxy}")

        state_func = self.open_site_state

        while state_func:
            state_func = state_func()

        print("StateMachine finished.")

        # Wait for user input to continue
        input("Press Enter to continue...")

    def random_delay(self, min_sec=1.0, max_sec=2.0):
        time.sleep(random.uniform(min_sec, max_sec))

    def human_reaction_delay(self):
        time.sleep(random.uniform(0.4, 1.0))

    def wait_for_element(self, by, value, timeout=30):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try finding the element in the main document
                element = self.driver.find_element(by, value)
                return element, None  # Return the element and None as no iframe is needed
            except NoSuchElementException:
                # If not found, iterate over iframes
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    self.driver.switch_to.frame(iframe)
                    try:
                        element = self.driver.find_element(by, value)
                        return element, iframe  # Return the element and the iframe it was found in
                    except NoSuchElementException:
                        # If not found, continue to next iframe
                        self.driver.switch_to.default_content()
                        continue
                    finally:
                        self.driver.switch_to.default_content()
            time.sleep(0.5)
        return None, None

    def log_page_details(self):
        try:
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            self.driver.save_screenshot("screenshot.png")
            print("Page source and screenshot saved for analysis.")
        except Exception as e:
            print(f"Error logging page details: {e}")

    def open_site_state(self):
        print("State: open_site_state")
        try:
            self.driver.get(self.url)
            while True:
                state = self.driver.execute_script("return document.readyState")
                if state == "complete":
                    break
                time.sleep(0.5)

            print("Site loaded, proceeding to click_create_character_state")
            self.random_delay(2, 4)  # Random delay before moving to the next state
            return self.click_create_character_state

        except WebDriverException as e:
            print(f"Error opening site: {e}, retrying open_site_state")
            return self.open_site_state

    def click_create_character_state(self):
        print("State: click_create_character_state")
        try:
            button, iframe = self.wait_for_element(By.XPATH, '//*[text()="Создать персонаж"]', timeout=30)
            if button:
                if iframe:
                    self.driver.switch_to.frame(iframe)
                    print("Switched to iframe context.")

                self.human_reaction_delay()
                button.click()
                print("Clicked 'Создать персонаж', proceeding to click_gender_state")

                self.driver.switch_to.default_content()  # Return to main context if switched
                self.random_delay(2, 4)  # Random delay before moving to the next state
                return self.click_gender_state
            else:
                print("Button 'Создать персонаж' not found, logging details.")
                self.log_page_details()
                return self.click_create_character_state

        except WebDriverException as e:
            print(f"Error in click_create_character_state: {e}, logging details and retrying.")
            self.log_page_details()
            return self.click_create_character_state

    def click_gender_state(self):
        print("State: click_gender_state")
        try:
            gender_button, iframe = self.wait_for_element(By.XPATH, '//*[text()="Женский"]', timeout=30)
            if gender_button:
                if iframe:
                    self.driver.switch_to.frame(iframe)
                    print("Switched to iframe context.")

                self.human_reaction_delay()
                gender_button.click()
                print("Clicked 'Женский', proceeding to click_next_state.")

                self.driver.switch_to.default_content()  # Return to main context if switched

                self.random_delay(2, 4)  # Random delay before moving to the next state
                return self.click_next_state
            else:
                print("Gender button 'Женский' not found, logging details.")
                self.log_page_details()
                return self.click_gender_state

        except WebDriverException as e:
            print(f"Error in click_gender_state: {e}, logging details and retrying.")
            self.log_page_details()
            return self.click_gender_state

    def click_next_state(self):
        print("State: click_next_state")
        try:
            next_button, iframe = self.wait_for_element(By.XPATH, '//*[text()="Далее"]', timeout=30)
            if next_button:
                if iframe:
                    self.driver.switch_to.frame(iframe)
                    print("Switched to iframe context.")

                self.human_reaction_delay()
                next_button.click()
                print("Clicked 'Далее', finishing process.")

                self.driver.switch_to.default_content()  # Return to main context if switched

                self.random_delay(2, 4)  # Random delay before finishing
                return None
            else:
                print("Button 'Далее' not found, logging details.")
                self.log_page_details()
                return self.click_next_state

        except WebDriverException as e:
            print(f"Error in click_next_state: {e}, logging details and retrying.")
            self.log_page_details()
            return self.click_next_state
