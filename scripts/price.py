import logging
from dataclasses import dataclass
from typing import List, Optional
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from decimal import Decimal
import random

@dataclass
class Product:
    title: str
    price: Decimal
    vendor: str
    link: str
    currency: str

class GoogleShoppingScraper:
    SELECTORS = {
        'container': ['div.KZmu8e', 'div.sh-dgr__content'],
        'title': ['h3.tAxDx', 'h4.A2sOrd'],
        'price': ['span.a8Pemb', 'span.HRLxBb'],
        'vendor': ['div.aULzUe', 'div.IuHnof'],
        'link': ['a.Lq5OHe', 'a.shntl']
    }

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
    ]

    def __init__(self, headless: bool = True, proxy: str = None):
        self.setup_logging()
        self.headless = headless
        self.proxy = proxy
        self.driver = None
        self.initialize_driver()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler('scraper.log'), logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)

    def initialize_driver(self):
        """Initialize or reinitialize the web driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.driver = self.setup_driver(self.headless, self.proxy)

    def normalize_browser(self):
        """Attempt to normalize the browser state"""
        try:
            self.driver.delete_all_cookies()
            self.driver.execute_script("window.localStorage.clear();")
            self.driver.execute_script("window.sessionStorage.clear();")
            return True
        except Exception as e:
            self.logger.error(f"Error normalizing browser: {str(e)}")
            return False

    def setup_driver(self, headless: bool, proxy: str) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        options.add_argument(f'user-agent={random.choice(self.USER_AGENTS)}')
        
        if headless:
            options.add_argument('--headless')
        if proxy:
            options.add_argument(f'--proxy-server={proxy}')
            
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def retry_with_recovery(self, func, *args, max_retries=3, **kwargs):
        """Generic retry function with browser recovery"""
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    self.logger.info("Attempting recovery...")
                    
                    # Try normalizing first
                    if not self.normalize_browser():
                        # If normalization fails, reinitialize driver
                        self.logger.info("Reinitializing driver...")
                        self.initialize_driver()
                    
                    time.sleep(random.uniform(3, 6))  # Random delay between retries
                else:
                    self.logger.error("Max retries reached. Operation failed.")
                    raise
        
    def wait_and_find_element(self, parent, selectors: List[str], timeout: int = 5) -> Optional[str]:
        end_time = time.time() + timeout
        while time.time() < end_time:
            for selector in selectors:
                try:
                    element = parent.find_element(By.CSS_SELECTOR, selector)
                    return element
                except NoSuchElementException:
                    continue
            time.sleep(0.5)
        return None

    def extract_price(self, price_text: str) -> Decimal:
        """Extract price value handling Indian currency format"""
        # Remove currency symbols and whitespace
        clean_price = ''.join(c for c in price_text if c.isdigit() or c in ',.').strip()
        
        # Handle Indian number format (1,44,900.00)
        if ',' in clean_price:
            parts = clean_price.split('.')
            main_part = parts[0].replace(',', '')
            decimal_part = parts[1] if len(parts) > 1 else '00'
            return Decimal(f"{main_part}.{decimal_part}")
        
        return Decimal(clean_price or '0')

    def clean_url(self, url: str) -> str:
        """Extract actual vendor URL from Google redirect URL"""
        try:
            # Extract URL parameter from Google redirect
            vendor_url = re.search(r'url=([^&]+)', url).group(1)
            # URL decode the extracted URL
            from urllib.parse import unquote
            return unquote(vendor_url).split('?')[0]
        except:
            return url

    def is_refurbished(self, title: str, link: str) -> bool:
        """Check if product is refurbished"""
        keywords = ['refurbished', 'renewed', 'reconditioned', 'pre-owned']
        return any(keyword in title.lower() or keyword in link.lower() for keyword in keywords)

    def scrape_product(self, product_element) -> Optional[Product]:
        try:
            title_elem = self.wait_and_find_element(product_element, self.SELECTORS['title'])
            price_elem = self.wait_and_find_element(product_element, self.SELECTORS['price'])
            vendor_elem = self.wait_and_find_element(product_element, self.SELECTORS['vendor'])
            link_elem = self.wait_and_find_element(product_element, self.SELECTORS['link'])

            if all([title_elem, price_elem, vendor_elem, link_elem]):
                price = self.extract_price(price_elem.text)
                
                # Skip products with unrealistic prices (e.g., 1 INR)
                if price < 1000:  # Minimum reasonable price threshold
                    return None
                    
                return Product(
                    title=title_elem.text,
                    price=price,
                    vendor=vendor_elem.text,
                    link=self.clean_url(link_elem.get_attribute('href')),
                    currency='INR '
                )
        except Exception as e:
            self.logger.warning(f"Error extracting product: {str(e)}")
        return None

    def search_products(self, query: str, max_retries: int = 3) -> List[Product]:
        def _search():
            products = []
            search_url = f"https://www.google.com/search?tbm=shop&q={'+'.join(query.split())}"
            
            self.driver.get(search_url)
            time.sleep(random.uniform(2, 4))
            
            product_elements = None
            for selector in self.SELECTORS['container']:
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    product_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if product_elements:
                        break
                except TimeoutException:
                    continue
            
            if not product_elements:
                raise Exception("No product elements found")

            for element in product_elements:
                product = self.scrape_product(element)
                if product:
                    products.append(product)
            
            if not products:
                raise Exception("No valid products found")
                
            return products

        for attempt in range(max_retries):
            try:
                self.logger.info(f"Attempting search for query: '{query}', attempt {attempt + 1}")
                return self.retry_with_recovery(_search)
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    self.logger.info("Retrying search with recovery...")
                    time.sleep(random.uniform(5, 10))  # Delay before retry
                else:
                    self.logger.error("Max retries reached. Exiting search.")
                    raise


    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

def main():
    scraper = None
    try:
        scraper = GoogleShoppingScraper(headless=True)
        products = scraper.search_products("Apple iPhone 16 Pro Max (White Titanium, 256 GB)")
        for product in products:
            print(f"\nTitle: {product.title}")
            print(f"Price: {product.currency}{product.price}")
            print(f"Vendor: {product.vendor}")
            print(f"Link: {product.link}")
    except Exception as e:
        logging.error(f"Main execution failed: {str(e)}")
        if scraper:
            # Try to restart the entire process once
            try:
                scraper.initialize_driver()
                products = scraper.search_products("Apple iPhone 16 Pro Max (White Titanium, 256 GB)")
                for product in products:
                    print(f"\nTitle: {product.title}")
                    print(f"Price: {product.currency}{product.price}")
                    print(f"Vendor: {product.vendor}")
                    print(f"Link: {product.link}")
            except Exception as retry_error:
                logging.error(f"Retry attempt failed: {str(retry_error)}")
    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    main()
