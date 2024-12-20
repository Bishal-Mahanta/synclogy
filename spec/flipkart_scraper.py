from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time
import random
import re
import logging

class FlipkartScraper:
    def __init__(self, headless_mode=True):
        options = webdriver.ChromeOptions()
        if headless_mode:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-cookies")
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        logging.info("Initialized FlipkartScraper with headless mode: %s", headless_mode)

    def search_product(self, product_name):
        """
        Searches Flipkart for a product and retrieves the links of matching items.
        Matches the input product name with the parsed product name from the URL.
        """
        logging.info("Searching for: %s", product_name)
        search_url = f"https://www.flipkart.com/search?q={product_name.replace(' ', '+').replace('++', '+')}"
        logging.info("Search URL: %s", search_url)
        self.driver.get(search_url)

        time.sleep(random.uniform(2, 5))  # Random delay to mimic human behavior

        product_links = []
        try:
            # Locate all product link elements
            product_elements_selectors = [
                "a.CGtC98",
                "a.wjcEIp"
            ]
            for selector in product_elements_selectors:
                product_elements = self.driver.find_elements(By.CSS_SELECTOR, selector) 
                for element in product_elements:
                    try:
                        href = element.get_attribute("href")
                        if href:
                            parsed_name_match = re.search(r"https://www\.flipkart\.com/([a-zA-Z0-9\-]+)", href)
                            if parsed_name_match:
                                parsed_name = parsed_name_match.group(1).replace("-", " ").replace("/", "").strip().lower()
                                logging.info("Parsed product name from URL: %s", parsed_name)

                                # Check if parsed name contains the input product name
                                if parsed_name.startswith(product_name.lower().replace("-", "")):
                                    product_links.append((parsed_name, href))
                                    logging.info("Matching product found: %s", href)
                    except Exception as e:
                        logging.error("Error processing product element: %s", e)

        except Exception as e:
            logging.error("Error fetching product links: %s", e)

        return product_links

    def extract_product_details(self, link):
        """
        Extracts product details from a given Flipkart product link.
        """
        logging.info("Extracting details from: %s", link)
        self.driver.get(link)
        # self.driver.implicitly_wait(random.uniform(2,4))
        time.sleep(random.uniform(2, 4))  # Random delay to mimic human behavior

        product_details = {
            "Product Name": "NA",
            "Offer Price": "NA",
            "MRP": "NA",
            "Description": "NA",
            "Meta Title": "NA",
            "Meta Keywords": "NA",
            "Meta Description": "NA",
            "Unique": "NA",
            "Images": []
        }

        try:
            # Extract product name
            product_name_element = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.VU-ZEz"))
            )
            product_details["Product Name"] = product_name_element.text.strip()

            # Extract offer price
            try:
                offer_price_element = self.driver.find_element(By.CSS_SELECTOR, "div.Nx9bqj.CxhGGd")
                product_details["Offer Price"] = offer_price_element.text.strip()
            except NoSuchElementException:
                logging.warning("Offer price not found for product: %s", link)

            # Extract MRP
            try:
                # Attempt to extract MRP using JavaScript
                mrp_element = self.driver.execute_script(
                    "let el = document.querySelector('.yRaY8j'); return el ? el.textContent : null;"
                )
                if mrp_element:
                    product_details["MRP"] = mrp_element.strip()
                else:
                    raise NoSuchElementException("MRP element not found with .yRaY8j selector")
            except NoSuchElementException:
                try:
                    # Fallback to locating the element directly with Selenium
                    mrp_element = self.driver.find_element(By.CSS_SELECTOR, "div.Nx9bqj.CxhGGd")
                    product_details["MRP"] = mrp_element.text.strip()
                except NoSuchElementException:
                    logging.warning("MRP not found for product: %s", link)


            # Extract description
            try:
                description_element = self.driver.find_element(By.CSS_SELECTOR, "div.w9jEaj>p")
                product_details["Description"] = description_element.text.strip()
            except NoSuchElementException:
                logging.warning("Description not found for product: %s", link)

            # Extract meta title, keywords, and description
            try:
                product_details["Meta Title"] = str(self.driver.find_element(By.CSS_SELECTOR, "head > meta[property='og:title']").get_attribute("content")).replace('On Flipkart.com', '')
                product_details["Meta Keywords"] = str(self.driver.find_element(By.CSS_SELECTOR, "head > meta[name='Keywords']").get_attribute("content")).replace('Flipkart', '')
                product_details["Meta Description"] = str(self.driver.find_element(By.CSS_SELECTOR, "head > meta[property='og:description']").get_attribute("content")).replace(' to shop at Flipkart', '')
            except NoSuchElementException:
                logging.warning("Meta information not found for product: %s", link)

            # Extract Unique Number for Flipkart
            try:
                # Split URL on '/' and '=' and look for a segment starting with 'itm'
                unique_id = None
                for segment in link.split('/'):
                    if 'itm' in segment:  # Check if 'itm' exists in the segment
                        unique_id = segment.split('itm')[-1][:12]  # Extract the 12-character unique ID
                        break
                product_details["Unique"] = unique_id
            except:
                logging.warning("Unable to get the Unique ID for: %s", link)

            # Extract images
            image_elements = self.driver.find_elements(By.CSS_SELECTOR, "img._0DkuPH")
            image_urls = [img.get_attribute("src") for img in image_elements if img.get_attribute("src")]

            # Apply Flipkart-specific URL manipulation logic
            def manipulate_flipkart_urls(urls):
                """
                Manipulates Flipkart image URLs to keep only '1664/1664' resolution and replace 'q=70' with 'q=100'.
                """
                manipulated_urls = set()  # Use a set to avoid duplicates
                for url in urls:
                    if '128/128' in url:  # Replace '128/128' with '1664/1664'
                        url_1664 = url.replace('128/128', '1664/1664').replace('q=70', 'q=100')
                        manipulated_urls.add(url_1664)
                return list(manipulated_urls)


            manipulated_images = manipulate_flipkart_urls(image_urls)
            product_details["Images"] = manipulated_images
            logging.info(f"Extracted {len(product_details['Images'])} manipulated images.")
            
        except Exception as e:
            logging.error("Error extracting product details: %s", e)

        return product_details
    
    def extract_additional_table_data(self, link):
        """
        Extracts additional table data from Flipkart product page after clicking the required button.
        - Clicks the button with selector 'button.QqFHMw._4FgsLt' if present.
        - Extracts data where column head is in td.col.col-3-12 and data is in td.col.col-9-12 > ul > li.
        """
        logging.info("Extracting additional table data from: %s", link)
        self.driver.get(link)
        time.sleep(random.uniform(2, 4))  # Mimic human browsing behavior

        additional_data = []

        try:
            # Click on the button to expand additional data, if present
            try:
                expand_button = self.driver.find_element(By.CSS_SELECTOR, "._4FgsLt")
                expand_button.click()
                logging.info("Clicked on the expand button.")
                time.sleep(random.uniform(2, 4))  # Wait for the expanded content to load
            except NoSuchElementException:
                logging.warning("Expand button not found; continuing with existing content.")

            # Locate all rows with additional table data
            rows = self.driver.find_elements(By.CSS_SELECTOR, "tr.row")
            for row in rows:
                try:
                    column_head = row.find_element(By.CSS_SELECTOR, "td.col.col-3-12").text.strip()
                    data_elements = row.find_elements(By.CSS_SELECTOR, "td.col.col-9-12 > ul > li")
                    data = ", ".join([element.text.strip() for element in data_elements if element.text.strip()])

                    if column_head and data:
                        additional_data.append({"Header": column_head, "Data": data})
                except NoSuchElementException:
                    logging.warning("Missing elements in row; skipping.")
        except Exception as e:
            logging.error("Error extracting additional table data: %s", e)

        return additional_data



    def close(self):
        logging.info("Closing the Flipkart scraper.")
        self.driver.quit()

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = FlipkartScraper(headless_mode=False)
    product_name = "Apple Iphone 13 Pro Max Silver"
    links = scraper.search_product(product_name)
    for link in links:
        print(link)
    if links:
        details = scraper.extract_product_details(links[0][1])
        print(details)
    scraper.close()