import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
import random

class AmazonScraper:
    def __init__(self):
        """
        Initializes the Amazon scraper.
        """
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        logging.info("Initialized AmazonScraper.")

    def search_product(self, product_name):
        """
        Searches Amazon for a product and retrieves the links of matching items.
        """
        logging.info(f"Searching Amazon for: {product_name}")
        search_url = f"https://www.amazon.in/s?k={product_name.replace(' ', '+').replace('++', '+')}"
        self.driver.get(search_url)

        time.sleep(2)  # Mimic human browsing behavior
        product_links = []

        try:
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, "span.a-size-medium.a-color-base.a-text-normal")
            for element in product_elements:
                try:
                    product_title = element.text.strip()
                    if product_name.lower() in product_title.lower():
                        parent_a = element.find_element(By.XPATH, "./ancestor::a")
                        href = parent_a.get_attribute("href")
                        logging.info(f"Matching product found: {product_title}")
                        product_links.append(href)
                except Exception as e:
                    logging.error(f"Error processing product element: {e}")

        except Exception as e:
            logging.error(f"Error fetching product links: {e}")

        return product_links
    
    def extract_price_details(self):
        """
        Robust method to extract price details from Amazon product page
        """
        price_details = {
            "Offer Price": "NA",
            "MRP": "NA"
        }
        # Comprehensive price selectors
        price_selectors = {
            "Offer Price": [
                "span.aok-align-center:nth-child(3) > span:nth-child(2) > span.a-price-whole",
                "span.a-price-whole",
                "span.a-offscreen",
                "div.a-section.a-spacing-none.aok-align-center > span.a-price-whole",
                "span[data-a-size='xl'] > span.a-offscreen",
                "div.a-price.a-size-medium.a-color-price > span.a-offscreen"
            ],
            "MRP": [
                "span.a-text-price > span.a-offscreen",
                "span.a-price.a-text-price > span.a-offscreen",
                "span.a-text-price > span.a-offscreen",
                "span.a-text-price > span:nth-child(2)",
                "span.aok-align-center:nth-child(3) > span:nth-child(2) > span.a-price-whole",
                "span.a-text-price > span",
                "span.basisPrice > span.a-offscreen",
                "div.a-row.a-size-base.a-color-secondary > span"
            ]
        }
        # Attempt to extract prices
        for price_type, selectors in price_selectors.items():
            for selector in selectors:
                try:
                    price_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    extracted_price = price_element.text.strip()
                    
                    # Additional cleaning
                    extracted_price = extracted_price.replace('₹', '').replace(',', '').strip()
                    
                    if extracted_price:
                        price_details[price_type] = extracted_price
                        break
                except NoSuchElementException:
                    continue
                except Exception as e:
                    logging.warning(f"Error extracting {price_type}: {e}")
        return price_details

    def extract_product_details(self, link):
        """
        Extracts general product details from an Amazon product page.
        """
        logging.info(f"Extracting details from: {link}")
        self.driver.get(link)
        time.sleep(2)  # Allow page to load

        product_details = {
            "Product Name": "NA",
            "Offer Price": "NA",
            "MRP": "NA",
            "Description": "NA",
            "Images": [],
        }

        try:
            # Product Name
            try:
                product_name_element = self.wait.until(EC.presence_of_element_located((By.ID, "productTitle")))
                product_details["Product Name"] = product_name_element.text.strip()
            except Exception:
                logging.warning("Product name not found.")

            # Price Details
            try:
                price_info = self.extract_price_details()
                product_details.update(price_info)
            except Exception as e:
                logging.error(f"Price extraction failed: {e}")


            # Description
            try:
                desc_elements = self.driver.find_elements(By.CSS_SELECTOR, "ul.a-unordered-list > li > span")
                product_details["Description"] = " ".join([desc.text.strip() for desc in desc_elements])
            except Exception:
                logging.warning("Description not found.")

        except Exception as e:
            logging.error(f"Error extracting product details: {e}")
            
        # Image Extraction
        try:
            # Wait for thumbnails container
            thumbnails_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#altImages"))
            )

            # Find all thumbnail images
            thumbnail_elements = thumbnails_container.find_elements(
                By.CSS_SELECTOR, "li.a-declarative img")

            actions = ActionChains(self.driver)
            image_urls = []

            for index, thumb in enumerate(thumbnail_elements, 1):
                try:
                    # Use JavaScript to handle click and scrolling
                    self.driver.execute_script("""
                        arguments[0].scrollIntoView({block: 'center'});
                        arguments[0].click();
                    """, thumb)
                    
                    time.sleep(1)  # Wait for image to load

                    # Find large images using multiple selectors
                    large_image_selectors = [
                        "img.a-dynamic-image", 
                        "img#landingImage", 
                        "div#imageBlock img"
                    ]

                    for selector in large_image_selectors:
                        large_images = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for img in large_images:
                            src = img.get_attribute('src')
                            alt_src = img.get_attribute('data-old-hires')
                            
                            for url in [src, alt_src]:
                                if url and url not in image_urls and url.startswith('http'):
                                    image_urls.append(url)

                except Exception as click_error:
                    logging.warning(f"Thumbnail interaction failed: {click_error}")

            # Apply Amazon-specific URL filtering logic
            def filter_amazon_urls(urls):
                allowed_suffixes = ['_SL1200_', '_SL1500_', '_SY355_']
                return [url for url in urls if any(suffix in url for suffix in allowed_suffixes)]

            filtered_images = filter_amazon_urls(image_urls)
            product_details["Images"] = list(set(filtered_images))
            logging.info(f"Extracted {len(product_details['Images'])} unique images after filtering.")

        except Exception as e:
            logging.error(f"Image extraction failed: {e}")

        return product_details

    def close(self):
        """
        Closes the browser instance.
        """
        logging.info("Closing the Amazon scraper.")
        self.driver.quit()
