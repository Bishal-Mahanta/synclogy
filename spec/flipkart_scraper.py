from spec.base_scraper import BaseScraper
from selenium.webdriver.common.by import By
import re

class FlipkartScraper(BaseScraper):
    def search_product(self, product_name):
        search_url = f"https://www.flipkart.com/search?q={product_name.replace(' ', '+')}"
        self.driver.get(search_url)
        product_links = []

        try:
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, "a.CGtC98")
            for element in product_elements:
                try:
                    href = element.get_attribute("href")
                    if href:
                        match = re.search(r"https://www\.flipkart\.com/([a-zA-Z0-9\-]+)", href)
                        if match:
                            parsed_name = match.group(1).replace("-", " ").lower()
                            if product_name.lower() in parsed_name:
                                product_links.append(href)
                except Exception as e:
                    print(f"Error processing product element: {e}")

        except Exception as e:
            print(f"Error fetching product links: {e}")

        return product_links

# Example Usage:
# scraper = FlipkartScraper()
# links = scraper.search_product("Acer Aspire 3")
# scraper.close()
