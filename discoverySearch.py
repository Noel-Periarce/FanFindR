import time
import random
import requests
import json
import os
import argparse
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Configuration class for managing script settings
class ScriptConfig:
    def __init__(self, args):
        # User credentials (from GUI)
        self.email = args.email or ""
        self.password = args.password or ""
        
        # Target settings (from GUI)
        self.target_users = args.target_users or 300
        self.posts_per_filter = args.posts_per_filter or 500
        
        # Browser settings (from GUI)
        self.headless = args.headless
        self.use_proxy = not args.no_proxy if hasattr(args, 'no_proxy') else True
        self.enable_fallback = not args.no_fallback if hasattr(args, 'no_fallback') else True
        
        # Performance settings (from GUI)
        self.rate_delay = args.rate_delay or 2
        self.max_retries = args.max_retries or 3
        self.timeout = args.timeout or 30
        
        # Other settings
        self.gui_mode = args.gui if hasattr(args, 'gui') else False
        
        # Validate required settings
        if not self.email or not self.password:
            raise ValueError("Email and password are required")
    
    def print_config(self):
        """Print current configuration (without sensitive data)"""
        print(f"[INFO] Email: {self.email}")
        print(f"[INFO] Target Users: {self.target_users}")
        print(f"[INFO] Posts per Filter: {self.posts_per_filter}")
        print(f"[INFO] Headless Mode: {self.headless}")
        print(f"[INFO] Rate Delay: {self.rate_delay}s")

def log_error(message, critical=False):
    """Log error messages with appropriate severity indicators"""
    if critical:
        print(f"[CRITICAL ERROR] {message}")
    else:
        print(f"[WARNING] {message}")

def log_info(message):
    """Log informational messages"""
    print(f"[INFO] {message}")

def log_success(message):
    """Log success messages"""
    print(f"[SUCCESS] {message}")

def get_users_json_file(email):
    """Generate JSON filename based on email"""
    safe_email = email.replace('@', '_at_').replace('.', '_').replace('/', '_').replace('\\', '_')
    return f"{safe_email}_users.json"

def human_delay(base=0.5, variance=0.3, rate_delay=2):
    """Human-like delay with configurable rate limiting"""
    delay = base + random.uniform(0, variance) + (rate_delay - 2)
    time.sleep(max(0.2, delay))

def human_type(element, text, delay=0.05, variance=0.02):
    """Type text with human-like delays"""
    for char in text:
        element.send_keys(char)
        time.sleep(delay + random.uniform(0, variance))

def load_existing_users(email):
    """Load existing users from user-specific JSON file"""
    users_json_file = get_users_json_file(email)
    
    if os.path.exists(users_json_file):
        try:
            with open(users_json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                users_set = set(data.get('users', []))
                log_info(f"Loaded {len(users_set)} existing users")
                return users_set
        except Exception as e:
            log_error("Error loading existing users")
            return set()
    else:
        log_info("No existing users file found - starting fresh")
        return set()

def save_users_to_json(users_set, email):
    """Save users to user-specific JSON file"""
    users_json_file = get_users_json_file(email)
    
    try:
        existing_data = {}
        if os.path.exists(users_json_file):
            try:
                with open(users_json_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except:
                pass
        
        existing_data.update({
            'users': list(users_set),
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_count': len(users_set),
            'owner_email': email
        })
        
        with open(users_json_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log_error("Error saving users")

def add_user_to_json(username, email):
    """Add a single user to the user-specific JSON file immediately"""
    try:
        existing_users = load_existing_users(email)
        if username not in existing_users:
            existing_users.add(username)
            save_users_to_json(existing_users, email)
            return True
        return False
    except Exception as e:
        log_error("Error adding user to JSON")
        return False

def setup_chrome_driver(config):
    """Setup Chrome driver with enhanced options and fallback strategies"""
    options = uc.ChromeOptions()
    
    options.add_argument("--lang=en-US")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--force-device-scale-factor=0.30")
    if config.headless:
        log_info("Running in headless mode")
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    else:
        log_info("Running in normal mode")
        options.add_argument("--disable-extensions")
        # Set smaller window size - don't maximize
        options.add_argument("--window-size=1000,700")
        options.add_argument("--window-position=200,100")
        options.add_argument("--disable-gpu")
    
    if not config.use_proxy:
        options.add_argument("--no-proxy-server")
        log_info("Proxy disabled")
    
    if config.enable_fallback:
        log_info("Attempting Chrome driver initialization with fallback strategies...")
        
        strategies = [
            ("Full options", options),
            ("Minimal options", uc.ChromeOptions()),
            ("No options", None)
        ]
        
        for strategy_name, chrome_options in strategies:
            try:
                log_info(f"Trying strategy: {strategy_name}")
                if chrome_options is None:
                    driver = uc.Chrome()
                else:
                    driver = uc.Chrome(options=chrome_options)
                    
                # FORCE window size immediately after driver creation
                if not config.headless:
                    log_info("Setting window size to 1000x700...")
                    driver.set_window_size(1000, 700)
                    driver.set_window_position(50, 1500)
                    time.sleep(0.5)  # Give it a moment to resize
                    
                log_success(f"Chrome started successfully with {strategy_name}!")
                return driver
            except Exception as e:
                log_error(f"{strategy_name} failed")
                continue
        
        raise Exception("All Chrome driver strategies failed")
    else:
        log_info("Attempting Chrome driver initialization...")
        driver = uc.Chrome(options=options)
        
        # FORCE window size immediately after driver creation
        if not config.headless:
            log_info("Setting window size to 1000x700...")
            driver.set_window_size(1000, 700)
            driver.set_window_position(50, 1500)
            time.sleep(0.5)  # Give it a moment to resize
            
        return driver
def sync_all_users_list(driver, config, existing_users):
    """
    Sync All Users list in Maloum and compare with local JSON
    Returns True if sync successful, False if failed
    """
    try:
        log_info("Starting All Users list synchronization...")
        
        # Step 1: Navigate to List section
        log_info("Navigating to List section...")
        try:
            list_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                "#root > div > section > div > nav > ul > li:nth-child(5) > button"))
            )
            list_btn.click()
            log_success("List section opened")
            time.sleep(3)
        except Exception as e:
            log_error("Failed to navigate to List section")
            return False
        
        # Step 2: Check if " All Users" list exists
        log_info("Checking if ' All Users' list exists...")
        all_users_found = False
        all_users_count = 0
        
        try:
            # First, scroll through the left column to find " All Users"
            left_column = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#leftColumn"))
            )
            
            list_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[3]/div/div/div[1]/div/div"))
            )
            
            # Scroll through the left column to find " All Users"
            log_info("Scrolling through list container to find ' All Users'...")
            scroll_attempts = 0
            max_scroll_attempts = 10
            all_users_candidates = []
            
            while scroll_attempts < max_scroll_attempts:
                # Look for " All Users" buttons in current view
                all_users_buttons = list_container.find_elements(By.XPATH, ".//button[contains(., ' All Users')]")
                
                for button in all_users_buttons:
                    try:
                        # Extract member count
                        member_text = button.find_element(By.CSS_SELECTOR, "div.mt-0\\.5.text-xs.text-gray-500").text
                        member_count = int(member_text.split()[0])
                        
                        # Check if this button is already in our candidates
                        button_text = button.text.strip()
                        already_found = False
                        for candidate in all_users_candidates:
                            if candidate['text'] == button_text and candidate['count'] == member_count:
                                already_found = True
                                break
                        
                        if not already_found:
                            all_users_candidates.append({
                                'button': button,
                                'count': member_count,
                                'text': button_text
                            })
                            log_info(f"Found ' All Users' candidate with {member_count} members")
                    except Exception as e:
                        log_error("Error reading member count from button")
                        continue
                
                # Scroll down in the left column to find more lists
                driver.execute_script("arguments[0].scrollTop += 300", left_column)
                time.sleep(1)
                scroll_attempts += 1
                log_info(f"Scroll attempt {scroll_attempts}/{max_scroll_attempts} - searching for ' All Users'...")
            
            # Select the " All Users" list with the highest member count
            if all_users_candidates:
                best_candidate = max(all_users_candidates, key=lambda x: x['count'])
                all_users_count = best_candidate['count']
                all_users_button = best_candidate['button']
                
                if len(all_users_candidates) > 1:
                    log_info(f"Found {len(all_users_candidates)} ' All Users' lists, selecting the one with highest count: {all_users_count}")
                else:
                    log_info(f"Found ' All Users' list with {all_users_count} members")
                
                all_users_found = True
                
                # Scroll the selected button into view
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", all_users_button)
                time.sleep(1)
                
                # Click on the selected All Users list
                all_users_button.click()
                log_success(f"Clicked on ' All Users' list with {all_users_count} members")
                time.sleep(3)
            else:
                log_info("' All Users' list not found after scrolling, will create it")
                
        except Exception as e:
            log_error("Error checking for ' All Users' list")
            return False
        
        # Step 3: Create " All Users" list if it doesn't exist
        if not all_users_found:
            log_info("Creating new ' All Users' list...")
            try:
                # Click "New list" button
                new_list_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 
                    "#leftColumn > div > header > div > div.-mr-2.flex.basis-1\\/2.justify-end.mr-0.md\\:-mr-4 > button"))
                )
                new_list_btn.click()
                log_info("Clicked 'New list' button")
                time.sleep(2)
                
                # Type " All Users" in input field
                input_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 
                    "input.input-underline[placeholder='New list']"))
                )
                input_field.clear()
                human_type(input_field, " All Users")
                log_info("Entered ' All Users' as list name")
                time.sleep(1)
                
                # Click create button
                create_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 
                    "button[type='submit']"))
                )
                create_btn.click()
                log_success("Created ' All Users' list")
                time.sleep(3)
                
            except Exception as e:
                log_error("Failed to create ' All Users' list")
                return False
        
        # Step 4: Add all available members
        log_info("Adding all available members to ' All Users' list...")
        try:
            # Click "Add members" button
            add_members_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                "#rightColumn > div.hidden.h-full.md\\:block > div > div > div.mt-4.flex.items-center.justify-between > button"))
            )
            add_members_btn.click()
            log_info("Clicked 'Add members' button")
            time.sleep(3)
            
            # Find the members container
            members_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 
                "#root > div > div > div > div.mx-auto.flex.w-full.max-w-xl.flex-col.relative.md\\:px-4.grow > div.mt-4.grow.px-4.pb-12.md\\:px-0"))
            )
            
            # PHASE 1: Scroll to bottom to load all content first
            log_info("Phase 1: Fast scrolling to bottom to load all available members...")
            scroll_confirmations = 0
            last_height = 0
            scroll_attempt = 0
            
            while scroll_confirmations < 5:
                scroll_attempt += 1
                log_info(f"Scroll attempt {scroll_attempt}, confirmation {scroll_confirmations}/5")
                
                # Get current height before scroll
                current_height = driver.execute_script("return arguments[0].scrollHeight", members_container)
                
                # Scroll to bottom using multiple methods for reliability
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", members_container)
                time.sleep(0.5)
                
                # Alternative scroll method
                driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight)", members_container)
                time.sleep(0.5)
                
                # Force scroll using window scroll as backup
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1.5)
                
                # Check if height changed
                new_height = driver.execute_script("return arguments[0].scrollHeight", members_container)
                log_info(f"Height check: {current_height} -> {new_height}")
                
                if new_height == last_height:
                    scroll_confirmations += 1
                    log_info(f"No height change detected, confirmation {scroll_confirmations}/5")
                else:
                    scroll_confirmations = 0
                    last_height = new_height
                    log_info(f"Height increased! New height: {new_height}, resetting confirmations")
            
            log_success("Finished loading all available members")
            
            # PHASE 2: Go back to top and check all boxes
            log_info("Phase 2: Going back to top to check all boxes...")
            
            # Scroll back to top using multiple methods
            driver.execute_script("arguments[0].scrollTop = 0", members_container)
            driver.execute_script("arguments[0].scrollTo(0, 0)", members_container)
            driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(2)
            
            checked_count = 0
            processed_positions = set()
            
            while True:
                # Get current scroll position
                current_position = driver.execute_script("return arguments[0].scrollTop", members_container)
                max_scroll = driver.execute_script("return arguments[0].scrollHeight - arguments[0].clientHeight", members_container)
                
                log_info(f"Current scroll position: {current_position}, max: {max_scroll}")
                
                # Find all checkboxes in current view
                checkboxes = members_container.find_elements(By.CSS_SELECTOR, 
                    "div.relative.mt-4.flex.flex-col.gap-3 > div > button")
                
                if not checkboxes:
                    log_info("No checkboxes found in current view")
                    break
                
                log_info(f"Found {len(checkboxes)} checkboxes in current view")
                
                # Click all visible unchecked boxes
                boxes_clicked_in_view = 0
                for i, checkbox in enumerate(checkboxes):
                    try:
                        # Get current state
                        class_attr = checkbox.get_attribute("class") or ""
                        
                        # Check if not already selected
                        if "bg-blue" not in class_attr and "selected" not in class_attr:
                            # Scroll the checkbox into view
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", checkbox)
                            time.sleep(0.05)
                            
                            # Click the checkbox
                            checkbox.click()
                            checked_count += 1
                            boxes_clicked_in_view += 1
                            
                            # Show progress every 10 checkboxes
                            if checked_count % 10 == 0 or checked_count <= 20 or i == len(checkboxes) - 1:
                                progress_percentage = (checked_count / len(checkboxes)) * 100
                                log_info(f"Checking boxes... {checked_count}/{len(checkboxes)} ({progress_percentage:.1f}%)")
                            
                            time.sleep(0.02)
                            
                    except Exception as e:
                        continue
                
                log_info(f"Clicked {boxes_clicked_in_view} boxes in this view. Total: {checked_count}")
                
                # If no boxes clicked, we're done
                if boxes_clicked_in_view == 0:
                    log_success(f"No new boxes to check. Total: {checked_count}")
                    break
                
                # Check if we've reached the bottom
                if current_position >= max_scroll:
                    log_success(f"Reached bottom! Total checked: {checked_count}")
                    break
                
                # Check if position already processed
                if current_position in processed_positions:
                    log_info("Position already processed, might be at bottom")
                    break
                
                # Add current position to processed set
                processed_positions.add(current_position)
                
                # Scroll down
                driver.execute_script("arguments[0].scrollTop += 500", members_container)
                time.sleep(0.5)
                
                # Check if scroll position changed
                new_position = driver.execute_script("return arguments[0].scrollTop", members_container)
                if new_position == current_position:
                    log_info("Can't scroll further")
                    break
            
            log_success(f"Finished selecting {checked_count} members")
            
            # Click Save button
            log_info("Clicking Save button...")
            save_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                "#root > div > div > div > div.mx-auto.flex.w-full.max-w-xl.flex-col.relative.md\\:px-4.grow > div.sticky.bottom-0.w-full.border-t.border-t-gray-100.bg-white.px-3.py-3.md\\:px-0 > button"))
            )
            save_btn.click()
            log_success("Saved all members to ' All Users' list")
            time.sleep(5)

            driver.refresh()
            log_info("Page refreshed to ensure updated count is loaded")
            time.sleep(3)  

        except Exception as e:
            log_error("Failed to add members")
            return False
        
        # Step 5: Get updated member count and compare with JSON
        log_info("Checking updated member count...")
        try:
            # Navigate back to List section
            list_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                "#root > div > section > div > nav > ul > li:nth-child(5) > button"))
            )
            list_btn.click()
            time.sleep(3)
            
            # Find updated count
            left_column = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#leftColumn"))
            )
            
            list_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[3]/div/div/div[1]/div/div"))
            )
            
            # Scroll to find updated count
            log_info("Scrolling to find updated ' All Users' count...")
            scroll_attempts = 0
            max_scroll_attempts = 10
            all_users_candidates = []
            
            while scroll_attempts < max_scroll_attempts:
                all_users_buttons = list_container.find_elements(By.XPATH, ".//button[contains(., ' All Users')]")
                
                for button in all_users_buttons:
                    try:
                        member_text = button.find_element(By.CSS_SELECTOR, "div.mt-0\\.5.text-xs.text-gray-500").text
                        member_count = int(member_text.split()[0])
                        
                        button_text = button.text.strip()
                        already_found = False
                        for candidate in all_users_candidates:
                            if candidate['text'] == button_text and candidate['count'] == member_count:
                                already_found = True
                                break
                        
                        if not already_found:
                            all_users_candidates.append({
                                'button': button,
                                'count': member_count,
                                'text': button_text
                            })
                    except Exception as e:
                        continue
                
                driver.execute_script("arguments[0].scrollTop += 300", left_column)
                time.sleep(1)
                scroll_attempts += 1
            
            # Select highest count
            if all_users_candidates:
                best_candidate = max(all_users_candidates, key=lambda x: x['count'])
                maloum_count = best_candidate['count']
                json_count = len(existing_users)
                
                if len(all_users_candidates) > 1:
                    log_info(f"Found {len(all_users_candidates)} lists, using highest: {maloum_count}")
                
                log_info(f"Maloum count: {maloum_count}")
                log_info(f"JSON count: {json_count}")
                
                if json_count >= maloum_count:
                    log_success("JSON file has equal or more users - sync not needed")
                    return True
                else:
                    log_info(f"JSON has fewer users, syncing from Maloum...")
                    
                    # Click on the best candidate
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", best_candidate['button'])
                    time.sleep(1)
                    best_candidate['button'].click()
                    time.sleep(3)
                    
                    # Now collect users from All Users list
                    maloum_users = set()
                    try:
                        # Get the right column container
                        right_column = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "#rightColumn"))
                        )
                        
                        # Find users container
                        users_container = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 
                            "#rightColumn > div.hidden.h-full.md\\:block > div > div > div.mt-4.pb-12 > div.relative.mt-4.flex.flex-col.gap-3"))
                        )
                        
                        log_info("Collecting usernames from All Users list...")
                        
                        # Scroll to load all users
                        scroll_confirmations = 0
                        last_height = 0
                        
                        while scroll_confirmations < 5:
                            current_height = driver.execute_script("return arguments[0].scrollHeight", right_column)
                            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", right_column)
                            time.sleep(1)
                            new_height = driver.execute_script("return arguments[0].scrollHeight", right_column)
                            
                            if new_height == last_height:
                                scroll_confirmations += 1
                            else:
                                scroll_confirmations = 0
                                last_height = new_height
                        
                        # Go back to top and collect usernames
                        driver.execute_script("arguments[0].scrollTop = 0", right_column)
                        time.sleep(2)
                        
                        processed_positions = set()
                        
                        while True:
                            current_position = driver.execute_script("return arguments[0].scrollTop", right_column)
                            max_scroll = driver.execute_script("return arguments[0].scrollHeight - arguments[0].clientHeight", right_column)
                            
                            # Find username elements
                            user_elements = users_container.find_elements(By.CSS_SELECTOR, 
                                "div.flex.min-h-\\[2\\.625rem\\].justify-between.gap-3 a div.text-left div:first-child")
                            
                            if not user_elements:
                                break
                            
                            users_collected = 0
                            for user_element in user_elements:
                                try:
                                    username = user_element.text.strip()
                                    if username and username not in maloum_users:
                                        maloum_users.add(username)
                                        users_collected += 1
                                except:
                                    continue
                            
                            if users_collected == 0:
                                break
                            
                            if current_position >= max_scroll:
                                break
                            
                            if current_position in processed_positions:
                                break
                            
                            processed_positions.add(current_position)
                            driver.execute_script("arguments[0].scrollTop += 500", right_column)
                            time.sleep(0.5)
                            
                            new_position = driver.execute_script("return arguments[0].scrollTop", right_column)
                            if new_position == current_position:
                                break
                        
                        log_success(f"Collected {len(maloum_users)} users from Maloum")
                        
                        # Update JSON
                        updated_users = existing_users.union(maloum_users)
                        save_users_to_json(updated_users, config.email)
                        
                        log_success(f"Updated JSON with {len(updated_users)} total users")
                        return True
                        
                    except Exception as e:
                        log_error("Failed to collect users")
                        return False
            else:
                log_error("Could not find All Users list")
                return False
                
        except Exception as e:
            log_error("Failed to check updated count")
            return False
        
    except Exception as e:
        log_error("Sync process failed")
        return False

def login_to_maloum(driver, config):
    """Handle the login process to Maloum"""
    try:
        log_info("Navigating to Maloum website...")
        driver.get("https://www.maloum.com/en")
    
        if not config.headless:
            driver.set_window_size(1000, 700)
            driver.set_window_position(50, 1500)   
        driver.execute_script("Object.defineProperty(navigator, 'language', {get: function() {return 'en-US';}});")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: function() {return ['en-US', 'en'];}});")       
        time.sleep(3)
        
        # Handle cookie consent
        try:
            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "cmpbntyestxt"))
            )
            cookie_btn.click()
            log_info("Cookie consent accepted")
            time.sleep(2)
        except:
            log_info("No cookie popup found")

        # Click login button
        try:
            login_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                "#w-node-_3bce429c-06f2-53cc-882e-3e390d408fec-3e573e94 > div:nth-child(2) > a.button.header-login-button.w-inline-block > div"))
            )
            login_btn.click()
            log_info("Login button clicked")
            time.sleep(3)
        except Exception as e:
            log_error("Login button not found", critical=True)
            return False

        # Fill login form
        try:
            # Wait for form
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form"))
            )
            
            # Enter email
            email_element = driver.find_element(By.CSS_SELECTOR, 
                "#root > div > div > div > form > div:nth-child(1) > input")
            email_element.clear()
            human_type(email_element, config.email)
            time.sleep(1)
            
            # Enter password
            password_element = driver.find_element(By.CSS_SELECTOR, 
                "#root > div > div > div > form > div:nth-child(2) > div > input")
            password_element.clear()
            human_type(password_element, config.password)
            time.sleep(1)
            
            # Submit form
            submit_element = driver.find_element(By.CSS_SELECTOR, 
                "#root > div > div > div > form > div.pt-6.sm\\:pt-12 > input")
            submit_element.click()
            log_info("Login form submitted")
            
            # Wait for login completion
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button span"))
            )
            log_success("Login successful")
            time.sleep(2)
            return True
            
        except Exception as e:
            log_error("Login form submission failed", critical=True)
            return False
        
    except Exception as e:
        log_error("Login process failed", critical=True)
        return False

def go_to_discovery_page(driver, config):
    """Navigate to Discovery page"""
    try:
        log_info("Navigating to Discovery page...")
        
        discovery_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 
            "#root > div > section > div > nav > ul > li:nth-child(2) > button"))
        )
        discovery_btn.click()
        # Wait for page to load
        time.sleep(5)
        
        # Verify we're on discovery page
        current_url = driver.current_url
        if "search" in current_url:
            log_success("Discovery page loaded")
            return True
        else:
            log_error(f"Failed to reach Discovery page. Current URL: {current_url}")
            return False
            
    except Exception as e:
        log_error("Failed to navigate to Discovery page")
        return False

def apply_random_filter(driver, config):
    """Apply random filter and return to Discovery page"""
    try:
        log_info("Opening filter preferences...")
        
        # Click filter button
        filter_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 
            "#root > div > div > div > header > div.flex.justify-between.px-4.pt-2.sm\\:pt-6 > div.my-auto.flex.md\\:gap-x-1 > a.flex.rounded-md.border-2.border-transparent.p-2.outline-none.focus\\:border-blue-violet.disabled\\:text-gray-300.text-gray-700.hover\\:text-gray-500.active\\:text-gray-800.text-base.shrink-0.hidden.sm\\:block"))
        )
        filter_btn.click()
        time.sleep(3)
        
        # Verify we're on filter page
        current_url = driver.current_url
        if "preferences" not in current_url:
            log_error("Not on filter preferences page")
            return False
        
        log_info("Filter preferences page loaded")
        
        # Select random filter
        filter_index = random.randint(1, 20)
        filter_selector = f"#root > div > div > div > div.mx-auto.flex.w-full.max-w-xl.flex-col.px-4.pt-4.md\\:px-0.md\\:px-4.grow > div:nth-child(2) > div.flex.flex-wrap.gap-2 > button:nth-child({filter_index})"
        
        try:
            filter_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, filter_selector))
            )
            filter_button.click()
            log_info(f"Selected filter #{filter_index}")
            time.sleep(2)
        except:
            log_info("Using default filter selection")
        
        # Save filter
        save_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 
            "#root > div > div > div > div.mx-auto.flex.w-full.max-w-xl.flex-col.px-4.pt-4.md\\:px-0.md\\:px-4.grow > div.sticky.bottom-0.mx-auto.mt-12.flex.w-full.max-w-xl.flex-col.bg-white.py-4 > button"))
        )
        save_btn.click()
        log_info("Filter saved")
        
        # Wait for return to Discovery page
        log_info("Waiting for Discovery page to reload...")
        time.sleep(8)
        
        # Verify we're back on Discovery page
        current_url = driver.current_url
        if "search" not in current_url:
            log_info("Not automatically returned to Discovery, navigating manually...")
            return go_to_discovery_page(driver, config)
        else:
            log_success("Returned to Discovery page with new filter applied")
            return True
            
    except Exception as e:
        log_error("Filter application failed")
        return False

def wait_for_first_post(driver, config):
    """Wait for first post to load without scrolling"""
    try:
        log_info("Waiting for first post to load...")
        
        # Wait for post container to be present
        first_post = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 
            "button.relative.h-full.w-full.overflow-hidden"))
        )
        
        # Additional wait for content to stabilize
        time.sleep(3)
        
        log_success("First post loaded and ready")
        return True
        
    except Exception as e:
        log_error("First post did not load")
        return False

def process_single_post(driver, post_index, config, existing_users, collected_users):
    """Process a single post and collect users from comments"""
    try:
        log_info(f"Processing post #{post_index + 1}")
        
        # Get available posts
        posts = driver.find_elements(By.CSS_SELECTOR, "button.relative.h-full.w-full.overflow-hidden")
        
        if post_index >= len(posts):
            log_info("No more posts available")
            return False
        
        # Click the post
        post = posts[post_index]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", post)
        time.sleep(1)
        post.click()
        
        log_info(f"Opened post #{post_index + 1}")
        time.sleep(3)
        
        # Look for comment button
        try:
            comment_elements = driver.find_elements(By.XPATH, "//button[contains(text(), 'comment')]")
            
            if not comment_elements:
                log_info("No comment button found, going back")
                driver.back()
                time.sleep(2)
                return True
            
            comment_btn = comment_elements[0]
            comment_text = comment_btn.text.strip().lower()
            
            # Check for 0 comments
            if "0 comment" in comment_text:
                log_info("Post has 0 comments, skipping")
                driver.back()
                time.sleep(2)
                return True
            
            # Click comment button
            comment_btn.click()
            log_info("Comment section opened")
            time.sleep(3)
            
        except Exception as e:
            log_info("Comment button not found, going back")
            driver.back()
            time.sleep(2)
            return True
        
        # Check for "No comments yet" message
        try:
            no_comments_elements = driver.find_elements(By.CSS_SELECTOR, "div.py-8.text-center")
            if no_comments_elements and "no comments yet" in no_comments_elements[0].text.lower():
                log_info("No comments yet message found, going back")
                driver.back()
                time.sleep(2)
                return True
        except:
            pass
        
        # Process commenters
        users_found_in_post = process_commenters_sequentially(driver, config, existing_users, collected_users)
        
        if users_found_in_post > 0:
            log_success(f"Found {users_found_in_post} new users in post #{post_index + 1}")
        else:
            log_info(f"No new users found in post #{post_index + 1}")
        
        # Return to Discovery page
        log_info("Returning to Discovery page...")
        discovery_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 
            "#root > div > section > div > nav > ul > li:nth-child(2) > button"))
        )
        discovery_btn.click()
        time.sleep(3)
        
        return True
        
    except Exception as e:
        log_error(f"Error processing post #{post_index + 1}")
        try:
            driver.back()
            time.sleep(2)
        except:
            pass
        return True

def process_commenters_sequentially(driver, config, existing_users, collected_users):
    """Process all commenters in sequence (click one, navigate back to comment URL, click next, etc.)"""
    users_found = 0
    processed_users = set()
    
    # Save the comment section URL for reliable navigation back
    comment_section_url = driver.current_url
    log_info(f"Saved comment section URL: {comment_section_url}")
    
    while True:
        try:
            # Get current commenters
            commenters = driver.find_elements(By.CSS_SELECTOR, "div.flex.justify-between button.notranslate")
            
            if not commenters:
                break
            
            # Find next unprocessed commenter
            target_commenter = None
            target_username = None
            
            for commenter in commenters:
                username = commenter.text.strip()
                
                if (username and 
                    username not in processed_users and 
                    username not in existing_users and 
                    username not in collected_users):
                    target_commenter = commenter
                    target_username = username
                    break
            
            # If no new users found, break
            if not target_commenter or not target_username:
                break
            
            # Click the user
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_commenter)
                time.sleep(1)
                ActionChains(driver).move_to_element(target_commenter).click().perform()
                
                # Add to collections
                collected_users.add(target_username)
                existing_users.add(target_username)
                processed_users.add(target_username)
                users_found += 1
                
                # Save immediately
                add_user_to_json(target_username, config.email)
                
                progress = (len(collected_users) / config.target_users) * 100
                log_success(f"Collected user: {target_username} ({len(collected_users)}/{config.target_users} - {progress:.1f}%)")
                
                # Rate limiting
                human_delay(rate_delay=config.rate_delay)
                
                # Navigate back to comment section using saved URL
                log_info("Navigating back to comment section...")
                driver.get(comment_section_url)
                time.sleep(5)  # Wait for page to reload
                
                # Verify we're back in comments
                current_url = driver.current_url
                if "/comments" not in current_url:
                    log_error("Failed to return to comment section")
                    break
                else:
                    log_info("Successfully returned to comment section")
                
            except Exception as e:
                log_error(f"Error processing user {target_username}")
                processed_users.add(target_username)
                # Try to navigate back to comment section
                try:
                    driver.get(comment_section_url)
                    time.sleep(5)
                except:
                    pass
                continue
            
        except Exception as e:
            log_error(f"Error in commenter processing loop")
            break
    
    return users_found

def main_discovery_loop(driver, config, existing_users, collected_users):
    """Main loop that processes filters and posts until target is reached"""
    filter_cycle = 0
    
    while len(collected_users) < config.target_users:
        filter_cycle += 1
        progress = (len(collected_users) / config.target_users) * 100
        
        log_info(f"Filter cycle #{filter_cycle} - Progress: {len(collected_users)}/{config.target_users} ({progress:.1f}%)")
        
        # Step 1: Go to Discovery page
        if not go_to_discovery_page(driver, config):
            log_error("Failed to reach Discovery page, retrying...")
            time.sleep(5)
            continue
        
        # Step 2: Apply random filter
        if not apply_random_filter(driver, config):
            log_error("Failed to apply filter, continuing with current filter...")
        
        # Step 3: Wait for first post to load
        if not wait_for_first_post(driver, config):
            log_error("First post did not load, trying next filter...")
            continue
        
        # Step 4: Process posts sequentially
        post_index = 0
        posts_processed_in_filter = 0
        max_posts_per_filter = config.posts_per_filter
        
        while (len(collected_users) < config.target_users and 
               posts_processed_in_filter < max_posts_per_filter):
            
            if process_single_post(driver, post_index, config, existing_users, collected_users):
                post_index += 1
                posts_processed_in_filter += 1
                
                # Check if we need to load more posts
                posts = driver.find_elements(By.CSS_SELECTOR, "button.relative.h-full.w-full.overflow-hidden")
                if post_index >= len(posts):
                    log_info("Loading more posts...")
                    driver.execute_script("window.scrollBy(0, 1000);")
                    time.sleep(3)
            else:
                break
        
        log_info(f"Filter cycle #{filter_cycle} complete - processed {posts_processed_in_filter} posts")
        
        # Check if target reached
        if len(collected_users) >= config.target_users:
            log_success("TARGET REACHED!")
            break
        
        # Small delay between filter cycles
        time.sleep(2)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Discovery Search - Simplified Flow")
    
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--password", required=True, help="User password")
    parser.add_argument("--target-users", type=int, help="Target number of users to collect")
    parser.add_argument("--posts-per-filter", type=int, help="Number of posts to process per filter")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--no-proxy", action="store_true", help="Disable proxy usage")
    parser.add_argument("--no-fallback", action="store_true", help="Disable Chrome fallback strategies")
    parser.add_argument("--rate-delay", type=float, help="Rate limiting delay in seconds")
    parser.add_argument("--max-retries", type=int, help="Maximum retry attempts")
    parser.add_argument("--timeout", type=int, help="Request timeout in seconds")
    parser.add_argument("--gui", action="store_true", help="Running from GUI")
    
    args = parser.parse_args()
    
    try:
        # Initialize configuration
        config = ScriptConfig(args)
        
        log_info("Starting Discovery Search - Simplified Flow")
        print("=" * 60)
        config.print_config()
        print("=" * 60)
        
        # Load existing users
        existing_users = load_existing_users(config.email)
        collected_users = set()
        
        # Setup browser
        driver = setup_chrome_driver(config)
        try:
            # Login to Maloum
            if not login_to_maloum(driver, config):
                log_error("Login failed", critical=True)
                return
            # Sync All Users list before starting search
            log_info("Synchronizing ' All Users' list...")
            if not sync_all_users_list(driver, config, existing_users):
                log_error("Failed to sync ' All Users' list, continuing anyway...")
            else:
                log_success("' All Users' list synchronized successfully")

            # Reload existing_users in case it was updated during sync
            existing_users = load_existing_users(config.email)           
            # Start main discovery process
            log_info("Starting main discovery process...")
            main_discovery_loop(driver, config, existing_users, collected_users)
            
            # Final summary
            log_success("Discovery Search Complete!")
            print("=" * 60)
            log_info(f"Users collected this session: {len(collected_users)}")
            log_info(f"Target was: {config.target_users}")
            
            completion_rate = (len(collected_users) / config.target_users) * 100
            log_success(f"Completion rate: {completion_rate:.1f}%")
            
            if len(collected_users) > 0:
                # Final save
                final_users = existing_users.union(collected_users)
                save_users_to_json(final_users, config.email)
                
                log_info(f"Total users in database: {len(final_users)}")
                log_info("Use userListManager.py to sync with Maloum")
                
                if not config.gui_mode:
                    input("\nPress Enter to close...")
            else:
                log_info("No new users were collected this session")
                
        except KeyboardInterrupt:
            log_info("Script stopped by user")
        except Exception as e:
            log_error("Unexpected error", critical=True)
        finally:
            if driver:
                driver.quit()
                log_success("Browser closed")

    except ValueError as e:
        log_error("Configuration error", critical=True)
    except Exception as e:
        log_error("Setup error", critical=True)

if __name__ == "__main__":
    main()