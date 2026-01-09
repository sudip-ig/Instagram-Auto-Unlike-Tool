import time
import random
import os
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# Constants for paths
COOKIES_FILE = "session_cookies.pkl"

class InstagramBot:
    def __init__(self, log_callback=None, stats_callback=None):
        self.driver = None
        self.log_callback = log_callback
        self.stats_callback = stats_callback
        self.is_running = False
        self.stop_requested = False
        self.total_unliked = 0

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
            
    def update_stats(self, count):
        self.total_unliked += count
        if self.stats_callback:
            self.stats_callback(self.total_unliked)

    def start_browser(self, headless=False):
        self.log(f"Starting browser... (Headless: {headless})")
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        
        options.add_argument("--disable-notifications")
        options.add_argument("--start-maximized")
        # Optimization for speed and stability
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Anti-detection features
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(60)
        self.log("Browser started.")

    def save_cookies(self):
        try:
            with open(COOKIES_FILE, "wb") as file:
                pickle.dump(self.driver.get_cookies(), file)
            self.log("Session cookies saved successfully.")
        except Exception as e:
            self.log(f"Failed to save cookies: {str(e)}")

    def load_cookies(self):
        if not os.path.exists(COOKIES_FILE):
            self.log("No saved session found.")
            return False
            
        try:
            self.driver.get("https://www.instagram.com/") # Need to be on domain to set cookies
            with open(COOKIES_FILE, "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception:
                        pass
            self.log("Session cookies loaded.")
            self.driver.refresh()
            return True
        except Exception as e:
            self.log(f"Failed to load cookies: {str(e)}")
            return False

    def login(self, username, password, headless=False):
        try:
            self.start_browser(headless=headless)
            
            # Try loading cookies first
            if self.load_cookies():
                time.sleep(3)
                if self._is_logged_in():
                    self.log("Restored session successfully!")
                    return True
                else:
                    self.log("Saved session expired. Logging in manually...")
            
            self.log(f"Navigating to login page...")
            self.driver.get("https://www.instagram.com/accounts/login/")
            
            wait = WebDriverWait(self.driver, 15)
            username_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
            password_input = self.driver.find_element(By.NAME, "password")

            self.log("Entering credentials...")
            username_input.clear()
            username_input.send_keys(username)
            time.sleep(random.uniform(0.5, 1.0))
            
            password_input.clear()
            password_input.send_keys(password)
            time.sleep(random.uniform(0.5, 1.0))
            
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            self.log("Waiting for login completion...")
            time.sleep(5) 
            
            # Check for 2FA
            if "challenge" in self.driver.current_url:
                self.log("2FA Challenge detected! Please resolve it in the browser.")
                if headless:
                    self.log("CRITICAL: Cannot solve 2FA in headless mode. Please uncheck 'Headless' and restart to login.")
                    return False
                
                # Wait for user to solve
                start_time = time.time()
                while "challenge" in self.driver.current_url:
                    if time.time() - start_time > 180: # 3 min timeout
                        self.log("Timeout waiting for 2FA.")
                        return False
                    time.sleep(1)
            
            if self._is_logged_in():
                self.save_cookies()
                return True
            else:
                self.log("Login failed or could not verify success.")
                return False
                
        except Exception as e:
            self.log(f"Login failed: {str(e)}")
            return False

    def _is_logged_in(self):
        # fast check for common elements present only when logged in
        try:
            return len(self.driver.find_elements(By.CSS_SELECTOR, "svg[aria-label='Home']")) > 0 or \
                   len(self.driver.find_elements(By.CSS_SELECTOR, "svg[aria-label='Search']")) > 0 or \
                   "login" not in self.driver.current_url
        except:
            return False

    def navigate_to_likes(self):
        self.log("Navigating to 'Your Activity' -> 'Likes'...")
        self.driver.get("https://www.instagram.com/your_activity/interactions/likes/")
        time.sleep(4)

    def _find_clickable(self, selectors, timeout=5):
        wait = WebDriverWait(self.driver, timeout)
        for by, pattern in selectors:
            try:
                element = wait.until(EC.element_to_be_clickable((by, pattern)))
                return element
            except:
                continue
        return None

    def process_unlike(self, batch_size=100, delay_range=(1, 3)):
        if not self.driver:
            self.log("Browser not started.")
            return

        # Ensure we are on the likes page
        if "interactions/likes" not in self.driver.current_url:
             self.navigate_to_likes()
        
        try:
            # 1. Click "Select" button
            self.log("Looking for 'Select' button...")
            select_selectors = [
                (By.XPATH, "//button[contains(text(), 'Select')]"),
                (By.XPATH, "//div[text()='Select']"),
                (By.XPATH, "//span[text()='Select']"),
                (By.XPATH, "//*[text()='Select']")
            ]
            
            # Check if we are already in selection mode (if 'Cancel' is present)
            cancel_present = False
            try:
                if self.driver.find_element(By.XPATH, "//*[text()='Cancel']").is_displayed():
                    cancel_present = True
            except:
                pass
                
            if not cancel_present:
                select_btn = self._find_clickable(select_selectors)
                if not select_btn:
                    self.log("Could not find 'Select' button.")
                    return
                select_btn.click()
                self.log("Clicked 'Select'.")
                time.sleep(2)
            else:
                self.log("Already in selection mode.")

            # 2. Select posts
            self.log(f"Selecting up to {batch_size} posts...")
            
            count = 0
            visited_urls = set()
            consecutive_no_new_posts = 0
            
            while count < batch_size:
                if self.stop_requested:
                    self.log("Process stopped by user.")
                    break
                
                # Find all potential post images
                images = self.driver.find_elements(By.TAG_NAME, "img")
                
                # Filter for valid, visible, and unvisited images
                new_candidates = []
                for img in images:
                    try:
                        if img.is_displayed() and img.size['width'] > 50 and img.size['height'] > 50:
                            src = img.get_attribute('src')
                            if src and src not in visited_urls:
                                new_candidates.append((img, src))
                    except:
                        pass # Stale element
                
                if not new_candidates:
                    self.log("No new posts visible. Scrolling...")
                    self.driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(3)
                    consecutive_no_new_posts += 1
                    if consecutive_no_new_posts > 5:
                        self.log("Reached end of list or cannot find more posts.")
                        break
                    continue
                
                consecutive_no_new_posts = 0
                
                for img, src in new_candidates:
                    if count >= batch_size:
                        break
                    if self.stop_requested:
                        break
                        
                    try:
                        # Click the PARENT of the image (overlay/anchor)
                        parent = img.find_element(By.XPATH, "./..")
                        parent.click()
                        
                        visited_urls.add(src)
                        count += 1
                        time.sleep(random.uniform(*delay_range))
                    except Exception:
                        # Fallback to direct click
                        try:
                            img.click()
                            visited_urls.add(src)
                            count += 1
                            time.sleep(random.uniform(*delay_range))
                        except:
                            pass
                            
                # Scroll down to load more if we haven't reached the target
                if count < batch_size:
                    self.driver.execute_script("window.scrollBy(0, 600);")
                    time.sleep(2)
            
            self.log(f"Selected {count} posts.")
            if count == 0: return

            # 3. Click "Unlike" button
            self.log("Clicking 'Unlike'...")
            action_selectors = [
                (By.XPATH, "//button[contains(text(), 'Unlike')]"),
                (By.XPATH, "//div[text()='Unlike']"),
                (By.XPATH, "//span[text()='Unlike']"),
                (By.CSS_SELECTOR, "button[type='button']"),
            ]
            
            action_btn = self._find_clickable(action_selectors)
            if not action_btn:
                self.log("Could not find 'Unlike' action button.")
                return

            action_btn.click()
            time.sleep(1)

            # 4. Confirm dialog
            self.log("Confirming...")
            confirm_btn = self._find_clickable(action_selectors)
            if confirm_btn:
                confirm_btn.click()
                self.update_stats(count)
                self.log(f"Successfully unliked {count} posts.")
            else:
                self.log("Confirmation dialog not found.")

            time.sleep(3)
            
        except Exception as e:
            self.log(f"Error in process loop: {e}")

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
