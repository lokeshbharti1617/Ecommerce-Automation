from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class LoginPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)

    def open_home(self, url):
        self.driver.get(url)

    def open_login(self):
        self.wait.until(EC.element_to_be_clickable((By.ID, "nav-link-accountList"))).click()

    def login(self, username, password):
        email = self.wait.until(EC.presence_of_element_located((By.ID, "ap_email")))
        email.clear()
        email.send_keys(username)
        self.wait.until(EC.element_to_be_clickable((By.ID, "continue"))).click()
        pwd = self.wait.until(EC.presence_of_element_located((By.ID, "ap_password")))
        pwd.clear()
        pwd.send_keys(password)
        self.wait.until(EC.element_to_be_clickable((By.ID, "signInSubmit"))).click()
