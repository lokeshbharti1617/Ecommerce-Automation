from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

service = Service(executable_path=r"C:\Users\LOKESH\Desktop\Project automation\chromedriver.exe")
options = Options()
options.add_argument("--headless=new")  # run headless to test without UI
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(service=service, options=options)
driver.get("https://www.google.com")
print("Title:", driver.title)
time.sleep(1)
driver.quit()
