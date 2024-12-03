from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random

class BaseScraper:
    def __init__(self, headless_mode=True):
        options = webdriver.ChromeOptions()
        if headless_mode:
            options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=options)

    def load_page(self, url, timeout=10):
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            time.sleep(random.uniform(2, 5))
            return self.driver.page_source
        except TimeoutException:
            print(f"Timeout while loading page: {url}")
            return None

    def close(self):
        self.driver.quit()
