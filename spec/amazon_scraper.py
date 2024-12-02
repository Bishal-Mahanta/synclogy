from spec.base_scraper import BaseScraper
from selenium.webdriver.common.by import By

class AmazonScraper(BaseScraper):
    def search_product(self, product_name):
        search_url = f"https://www.amazon.in/s?k={product_name.replace(' ', '+')}"
        self.driver.get(search_url)
        product_links = []

        try:
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, "span.a-size-medium.a-color-base.a-text-normal")
            for element in product_elements:
                try:
                    product_title = element.text.strip()
                    if product_title.lower().startswith(product_name.lower()):
                        parent_a = element.find_element(By.XPATH, "./ancestor::a")
                        href = parent_a.get_attribute("href")
                        product_links.append(href)
                except Exception as e:
                    print(f"Error processing product element: {e}")

        except Exception as e:
            print(f"Error fetching product links: {e}")

        return product_links

# Example Usage:
# scraper = AmazonScraper()
# links = scraper.search_product("iPhone 13")
# scraper.close()
