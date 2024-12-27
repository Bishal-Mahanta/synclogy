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

        time.sleep(3)  # Mimic human browsing behavior
        product_links = []

        try:
            # Method 1: Your original logic (Do not modify)
            try:
                product_elements = self.driver.find_elements(By.CSS_SELECTOR, "a.a-link-normal.s-line-clamp-4")
                for element in product_elements:
                    try:
                        if product_name in element.get_attribute('href').split('/'):
                            # href = f"www.amazon.in{element.get_attribute('href')}"
                            href = element.get_attribute('href')
                            logging.info(f"Matching product found: {product_name}")
                            product_links.append(href)
                    except Exception as e:
                        logging.error(f"Error processing product element with method 1: {e}")
            except Exception as e:
                logging.error(f"Error in method 1 for finding product links: {e}")

            # Method 2: Your original logic (Do not modify)
            if not product_links:  # Use method 2 only if method 1 did not find links
                logging.warning("No links found with the first method. Attempting fallback method...")
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
                            logging.error(f"Error processing product element with method 2: {e}")
                except Exception as e:
                    logging.error(f"Error in fallback method for finding product links: {e}")

        except Exception as e:
            logging.error(f"Error during product search: {e}")

        # Deduplicate product links
        product_links = list(set(product_links))

        if product_links:
            logging.info(f"Total matching product links found: {len(product_links)}")
        else:
            logging.warning("No matching product links found.")

        return product_links

    
    def extract_price_details(self):
        """
        Robust method to extract price details from Amazon product page
        """
        price_details = {
            "Offer Price": "NA",
            "Amazon.in Price": "NA"
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
            "Amazon.in Price": [
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
            "Description": "NA",
            "Meta Title": "NA",
            "Meta Keywords": "NA",
            "Meta Description": "NA",
            "Unique": "NA",
            "Images": [],
            "Amazon.in Price": "NA",
            "Amazon.in URL": "NA"
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

            # Extract Amazon.in URL
            try:
                # Save the link provided for future reference
                product_details["Amazon.in URL"] = link
            except:
                logging.error("Amazon.in URL unable to extract")


            # Description
            try:
                desc_elements = self.driver.find_elements(By.CSS_SELECTOR, "ul.a-unordered-list > li.a-spacing-mini > span")
                product_details["Description"] = " ".join([desc.text.strip() for desc in desc_elements])
            except Exception:
                logging.warning("Description not found.")

            # Extract meta title, keywords, and description
            try:
                product_details["Meta Title"] = self.driver.find_element(By.CSS_SELECTOR, '#a-page > meta[name="title"]').get_attribute("content")
                product_details["Meta Description"] = self.driver.find_element(By.CSS_SELECTOR, '#a-page > meta[name="description"]').get_attribute("content")
                product_details["Meta Keywords"] = self.driver.find_element(By.CSS_SELECTOR, 'meta[name="keywords"]').get_attribute("content")
            except NoSuchElementException:
                logging.warning("Meta information not found for product: %s", link)

            # Extract Unique Number for Amazon
            try:
                product_details["Unique"] = str(link.split('/')[5]).replace('?th=1', '')
            except:
                logging.warning("Unable to get the Unique ID for: %s", link)

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
                """
                Filters and modifies Amazon image URLs:
                - Replaces '_SL1200_', '_SL1500_', '_SY355_' with '_SL1664_'.
                - Ensures all URLs are unique using a set.
                """
                allowed_suffixes = ['_SL1200_', '_SL1500_', '_SY355_']
                modified_urls = set()

                for url in urls:
                    for suffix in allowed_suffixes:
                        if suffix in url:
                            modified_url = url.replace(suffix, '_SL1664_')
                            modified_urls.add(modified_url)
                            break  # Stop checking other suffixes once a match is found

                return list(modified_urls)


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
