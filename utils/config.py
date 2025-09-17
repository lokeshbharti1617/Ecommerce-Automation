from dotenv import load_dotenv
import os
load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://www.amazon.in")
USERNAME = os.getenv("USERNAME", "")
PASSWORD = os.getenv("PASSWORD", "")
SEARCH_ITEM = os.getenv("SEARCH_ITEM", "mobile phone")
