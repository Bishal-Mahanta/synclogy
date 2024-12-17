from spec.base_scraper import BaseScraper
from db.utils import save_product_to_db
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import json
import logging

class TechScraper(BaseScraper):
    def __init__(self, headless_mode=True):
        # Pass headless_mode parameter to BaseScraper constructor
        super().__init__(headless_mode=headless_mode)

    def search_product(self, product_name):
        self.driver.get('https://www.91mobiles.com/')
        try:
            # Wait until the search box is present
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="autoSuggestTxtBox"]'))
            )
            # Clear and enter the product name into the search box
            search_box.clear()
            search_box.send_keys(str(product_name).replace(' ', '+').replace('++', '+'))

            # Adding a small delay to ensure all typing is registered
            WebDriverWait(self.driver, 3).until(
                EC.text_to_be_present_in_element_value((By.XPATH, '//*[@id="autoSuggestTxtBox"]'), product_name)
            )

            # Wait for the search button to be clickable and interact using ActionChains
            search_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="main_auto_search"]'))
            )
            ActionChains(self.driver).move_to_element(search_button).click().perform()

            # Wait until the search results are loaded
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'hover_blue_link'))
            )
            product_containers = self.driver.find_elements(By.CLASS_NAME, 'hover_blue_link')
            for container in product_containers:
                product_title = container.get_attribute('title')
                if product_name.lower() in product_title.lower():
                    return container.get_attribute('href')

            return product_containers[0].get_attribute('href')  # Fallback
        except Exception as e:
            print(f"Error searching for product '{product_name}': {e}")
            return None

    def extract_technical_details(self, url):
        self.driver.get(url)
        self.driver.implicitly_wait(5)
        specs_data = {}

        try:
            product_name = self.driver.find_element(By.CLASS_NAME, 'h1_pro_head').text.strip()
            specs_data['Name'] = product_name

            specs_tables = self.driver.find_elements(By.CLASS_NAME, 'spec_table')
            for table in specs_tables:
                rows = table.find_elements(By.TAG_NAME, 'tr')
                for row in rows:
                    try:
                        spec_title = row.find_element(By.CLASS_NAME, 'spec_ttle').text.strip()
                        spec_value = row.find_element(By.CLASS_NAME, 'spec_des').text.strip()
                        specs_data[spec_title] = spec_value
                    except Exception:
                        continue
        except Exception as e:
            print(f"Error extracting technical details: {e}")

        product_data = {
            "product_name": specs_data.get("Name", "Unknown"),
            "model_name": specs_data.get("Model", "Unknown"),
            "color": "Unknown",
            "category": "phone",
            "specifications": json.dumps(specs_data),
            "source": "91mobiles"
        }

        # Just return the specs data for now (not saving to DB)
        return specs_data
