from spec.base_scraper import BaseScraper
from db.utils import save_product_to_db
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json

class TechScraper(BaseScraper):
    def search_product(self, product_name):
        self.driver.get('https://www.91mobiles.com/')
        try:
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="autoSuggestTxtBox"]'))
            )
            search_box.clear()
            search_box.send_keys(product_name)

            search_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="main_auto_search"]'))
            )
            search_button.click()

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

        save_product_to_db(product_data)
        return specs_data
