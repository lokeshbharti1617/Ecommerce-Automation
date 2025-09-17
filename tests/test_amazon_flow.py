# tests/test_amazon_flow.py
# Full end-to-end test with manual-pause + cookie save/load

import sys, os, time, json, pathlib
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from utils import config   # BASE_URL, USERNAME, PASSWORD, SEARCH_ITEM

# Debug / artifact paths
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEBUG_DIR = os.path.join(ROOT, "debug")
os.makedirs(DEBUG_DIR, exist_ok=True)
COOKIES_PATH = pathlib.Path(os.path.join(ROOT, "cookies.json"))

def debug_dump(driver, name_prefix):
    """Save screenshot and page source with timestamped name."""
    ts = time.strftime("%Y%m%d_%H%M%S")
    safe_name = f"{name_prefix}_{ts}"
    screenshot_path = os.path.join(DEBUG_DIR, safe_name + ".png")
    html_path = os.path.join(DEBUG_DIR, safe_name + ".html")
    try:
        driver.save_screenshot(screenshot_path)
    except WebDriverException as e:
        print("Could not save screenshot:", e)
    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    except Exception as e:
        print("Could not save page source:", e)
    print(f"[DEBUG] Saved screenshot -> {screenshot_path}")
    print(f"[DEBUG] Saved page source -> {html_path}")
    return screenshot_path, html_path

# ---------------- Cookie helpers ---------------- #
def save_cookies(driver):
    try:
        cookies = driver.get_cookies()
        # Drop any problematic keys
        for c in cookies:
            c.pop("sameSite", None)
        with open(COOKIES_PATH, "w", encoding="utf-8") as f:
            json.dump(cookies, f)
        print("[INFO] Saved cookies to", COOKIES_PATH)
    except Exception as e:
        print("Could not save cookies:", e)

def load_cookies(driver):
    if not COOKIES_PATH.exists():
        return False
    try:
        with open(COOKIES_PATH, "r", encoding="utf-8") as f:
            cookies = json.load(f)
    except Exception as e:
        print("Could not read cookies file:", e)
        return False

    # Navigate to base domain and add cookies
    try:
        driver.get(config.BASE_URL)
        time.sleep(1)
        for c in cookies:
            # ensure cookie dict is acceptable
            c.pop("sameSite", None)
            try:
                driver.add_cookie(c)
            except Exception as e:
                # some cookies may fail to be added; continue
                print("Warning: could not add cookie:", e)
        # Reload to apply cookies
        driver.get(config.BASE_URL)
        time.sleep(1)
        print("[INFO] Loaded cookies from", COOKIES_PATH)
        return True
    except Exception as e:
        print("Could not load cookies into browser:", e)
        return False

# ---------------- Page Classes ---------------- #
class LoginPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 25)

    def open_home(self, url):
        self.driver.get(url)

    def open_login(self):
        # Try the usual top-right account link; fallback to text link if needed
        try:
            self.wait.until(EC.element_to_be_clickable((By.ID, "nav-link-accountList"))).click()
            return
        except TimeoutException:
            pass

        try:
            el = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//*[contains(@href,'/gp/sign-in') or contains(text(),'Sign in') or contains(text(),'Hello, sign in') or contains(text(),'Sign-In')]")))
            el.click()
            return
        except TimeoutException:
            raise

    def _switch_from_create_account_to_signin(self):
        """On create-account page, click the 'Already a customer? Sign in' link if present."""
        try:
            signin_button = self.driver.find_element(By.XPATH,
                "//a[contains(text(),'Sign in') or contains(text(),'Sign-In') or contains(text(),'Already a customer') or contains(@href,'/ap/signin')]")
            signin_button.click()
            self.wait.until(EC.presence_of_element_located((By.ID, "ap_email")))
            return True
        except Exception:
            return False

    def login(self, username, password):
        # if create-account heading present, try to switch
        try:
            heading = self.driver.find_element(By.TAG_NAME, "h1").text.lower()
            if "create account" in heading or "new customer" in heading or "create your amazon account" in heading:
                switched = self._switch_from_create_account_to_signin()
                if not switched:
                    time.sleep(1)
        except Exception:
            pass

        # find email/phone input with fallbacks
        try:
            email = self.wait.until(EC.presence_of_element_located((By.ID, "ap_email")))
        except TimeoutException:
            try:
                email = self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
            except TimeoutException:
                try:
                    email = self.wait.until(EC.presence_of_element_located((By.NAME, "emailOrPhone")))
                except TimeoutException:
                    # try switching from create account and retry
                    if self._switch_from_create_account_to_signin():
                        email = self.wait.until(EC.presence_of_element_located((By.ID, "ap_email")))
                    else:
                        raise TimeoutException("Could not find email/phone input on sign-in page")

        email.clear()
        email.send_keys(username)

        # click continue if present (some flows require)
        try:
            self.wait.until(EC.element_to_be_clickable((By.ID, "continue"))).click()
        except TimeoutException:
            pass

        # password field
        try:
            pwd = self.wait.until(EC.presence_of_element_located((By.ID, "ap_password")))
        except TimeoutException:
            pwd = self.wait.until(EC.presence_of_element_located((By.NAME, "password")))

        pwd.clear()
        pwd.send_keys(password)

        # click sign in (with fallback)
        try:
            self.wait.until(EC.element_to_be_clickable((By.ID, "signInSubmit"))).click()
        except TimeoutException:
            try:
                btn = self.driver.find_element(By.XPATH,
                    "//input[@type='submit' and (contains(@value,'Sign in') or contains(@value,'Sign-In'))] | //button[contains(text(),'Sign in') or contains(text(),'Sign-In')]")
                btn.click()
            except Exception:
                raise

class SearchPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)

    def search_for(self, keyword):
        search_box = self.wait.until(EC.presence_of_element_located((By.ID, "twotabsearchtextbox")))
        search_box.clear()
        search_box.send_keys(keyword)
        search_box.send_keys(Keys.RETURN)

    def open_first_result(self):
        item = self.wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "div.s-main-slot div[data-component-type='s-search-result'] a.a-link-normal.s-no-outline, div.s-main-slot h2 a")
        ))
        item.click()

class ProductPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)

    def switch_to_product_tab(self):
        if len(self.driver.window_handles) > 1:
            self.driver.switch_to.window(self.driver.window_handles[-1])

    def add_to_cart(self):
        self.switch_to_product_tab()
        self.wait.until(EC.element_to_be_clickable((By.ID, "add-to-cart-button"))).click()

    def go_to_cart(self):
        self.wait.until(EC.element_to_be_clickable((By.ID, "nav-cart-count"))).click()

class CartPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)

    def proceed_to_checkout(self):
        try:
            self.wait.until(EC.element_to_be_clickable((By.NAME, "proceedToRetailCheckout"))).click()
        except TimeoutException:
            self.wait.until(EC.element_to_be_clickable((By.ID, "sc-buy-box-ptc-button"))).click()

class PaymentPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 25)

    def reach_payment_section(self):
        locator = (By.XPATH, "//*[contains(text(),'Payment') or contains(text(),'payment method') or contains(.,'Add a credit or debit card') or contains(.,'Choose a payment method')]")
        self.wait.until(EC.presence_of_element_located(locator))
        return True

# ---------------- Test Case & Fixture ---------------- #
@pytest.fixture
def driver():
    options = Options()
    options.add_argument("--start-maximized")
    service = Service(executable_path=r"C:\Users\LOKESH\Desktop\Project automation\chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)
    yield driver
    driver.quit()

def test_end_to_end_flow(driver):
    # Try to load cookies first; if cookies loaded, skip manual login.
    cookies_loaded = False
    try:
        cookies_loaded = load_cookies(driver)
    except Exception as e:
        print("Error while loading cookies:", e)
        cookies_loaded = False

    login = LoginPage(driver)

    # If cookies not loaded, perform manual login with pause then save cookies
    if not cookies_loaded:
        try:
            login.open_home(config.BASE_URL)
        except Exception as e:
            print("Failed to open home:", e)
            raise

        try:
            login.open_login()
        except TimeoutException:
            print("[ERROR] Timeout while opening login. Dumping debug info.")
            debug_dump(driver, "open_login_timeout")
            raise

        # Manual pause for human to solve CAPTCHA/OTP if Amazon blocks
        print("⚠️ Please complete manual login in the opened Chrome window (solve CAPTCHA/OTP).")
        print("When signed in, return to this PowerShell and press Enter to continue...")
        input()

        # after manual sign-in, save cookies for future runs
        try:
            save_cookies(driver)
        except Exception as e:
            print("Warning: could not save cookies:", e)
    else:
        # Cookies loaded; ensure page reflects logged-in state
        try:
            driver.get(config.BASE_URL)
            time.sleep(2)
        except Exception as e:
            print("Could not navigate home after loading cookies:", e)

    # Small stabilizing wait
    time.sleep(1)

    # Proceed with search -> product -> add to cart -> checkout
    search = SearchPage(driver)
    try:
        search.search_for(config.SEARCH_ITEM)
    except TimeoutException:
        print("[ERROR] Timeout in search_for. Dumping debug info.")
        debug_dump(driver, "search_timeout")
        raise

    try:
        search.open_first_result()
    except TimeoutException:
        print("[ERROR] Timeout opening first result. Dumping debug info.")
        debug_dump(driver, "open_first_result_timeout")
        raise

    product = ProductPage(driver)
    try:
        product.add_to_cart()
    except TimeoutException:
        print("[ERROR] Timeout on add_to_cart. Dumping debug info.")
        debug_dump(driver, "add_to_cart_timeout")
        raise

    # Go to cart page directly to be robust
    try:
        driver.get("https://www.amazon.in/gp/cart/view.html")
        time.sleep(1)
    except Exception as e:
        print("Failed to go to cart:", e)
        debug_dump(driver, "goto_cart_failed")
        raise

    cart = CartPage(driver)
    try:
        cart.proceed_to_checkout()
    except TimeoutException:
        print("[ERROR] Timeout on proceed_to_checkout. Dumping debug info.")
        debug_dump(driver, "proceed_to_checkout_timeout")
        raise

    payment = PaymentPage(driver)
    try:
        assert payment.reach_payment_section(), "Payment section not found"
    except TimeoutException:
        print("[ERROR] Timeout waiting for payment section. Dumping debug info.")
        debug_dump(driver, "payment_section_timeout")
        raise

    print("✅ Reached payment section; stopping before OTP/confirmation.")
