#!/usr/bin/env python3
"""
Boots Website Inspector

This script provides an interactive way to inspect the Boots website using Playwright.
It helps with developing and debugging the scraper by allowing you to:
1. Navigate to specific URLs
2. Take screenshots
3. Extract product information
4. Test selectors

Usage:
    python boots_inspector.py
"""

import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

class BootsInspector:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.screenshots_dir = "screenshots"
        
        # Create screenshots directory if it doesn't exist
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
    
    async def initialize(self):
        """Initialize the browser and page."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page = await self.context.new_page()
        
        # Set up event listeners
        self.page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
        self.page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))
        
        print("Browser initialized successfully.")
    
    async def navigate(self, url):
        """Navigate to a URL."""
        try:
            print(f"Navigating to: {url}")
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for the page to load
            try:
                await self.page.wait_for_load_state("networkidle", timeout=15000)
            except Exception as e:
                print(f"Warning: Page load state timeout: {str(e)}")
            
            # Accept cookies if the cookie banner appears
            try:
                cookie_accept_button = await self.page.query_selector('button#onetrust-accept-btn-handler, .cookie-accept-button, [data-testid="cookie-accept-button"]')
                if cookie_accept_button:
                    await cookie_accept_button.click()
                    print("Accepted cookies")
                    await self.page.wait_for_timeout(2000)  # Wait for cookie banner to disappear
            except Exception as e:
                print(f"Warning: Could not handle cookie banner: {str(e)}")
            
            print(f"Successfully navigated to: {url}")
            return True
        except Exception as e:
            print(f"Error navigating to {url}: {str(e)}")
            return False
    
    async def take_screenshot(self, name=None):
        """Take a screenshot of the current page."""
        try:
            if name is None:
                name = f"page_{len(os.listdir(self.screenshots_dir)) + 1}"
            
            filename = os.path.join(self.screenshots_dir, f"{name}.png")
            await self.page.screenshot(path=filename)
            print(f"Screenshot saved to: {filename}")
            return filename
        except Exception as e:
            print(f"Error taking screenshot: {str(e)}")
            return None
    
    async def test_selector(self, selector):
        """Test a CSS selector and return the number of matching elements."""
        try:
            elements = await self.page.query_selector_all(selector)
            print(f"Found {len(elements)} elements matching selector: {selector}")
            
            # Print the first 5 elements' text content
            for i, element in enumerate(elements[:5]):
                text = await element.text_content()
                print(f"  {i+1}. {text.strip()[:100]}")
            
            return len(elements)
        except Exception as e:
            print(f"Error testing selector {selector}: {str(e)}")
            return 0
    
    async def extract_product_links(self, selector='a[href*="/beauty/skincare/"]'):
        """Extract product links from the current page."""
        try:
            links = await self.page.query_selector_all(selector)
            print(f"Found {len(links)} potential product links with selector: {selector}")
            
            product_urls = []
            for link in links:
                href = await link.get_attribute('href')
                if href:
                    # Make sure it's an absolute URL
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = f"https://www.boots.com{href}"
                        else:
                            href = f"https://www.boots.com/{href}"
                    
                    # Filter for actual product URLs
                    if (('/beauty/skincare/' in href or '/beauty/brands/' in href) and 
                        not href.endswith('/beauty/skincare') and 
                        not '/category/' in href and
                        not '?' in href):
                        product_urls.append(href)
            
            # Print the first 10 product URLs
            print(f"Found {len(product_urls)} product URLs")
            for i, url in enumerate(product_urls[:10]):
                print(f"  {i+1}. {url}")
            
            # Save to file
            with open("product_urls.json", "w") as f:
                json.dump(product_urls, f, indent=2)
            print(f"Saved {len(product_urls)} product URLs to product_urls.json")
            
            return product_urls
        except Exception as e:
            print(f"Error extracting product links: {str(e)}")
            return []
    
    async def extract_product_info(self, url=None):
        """Extract product information from the current page or a specific URL."""
        try:
            if url:
                await self.navigate(url)
            
            # Take a screenshot
            await self.take_screenshot("product_page")
            
            # Extract product information
            product_data = {}
            
            # Product name
            try:
                name_element = await self.page.query_selector('h1.product-title, .product-name h1, [data-test="product-title"]')
                if name_element:
                    product_data['name'] = await name_element.text_content()
                    print(f"Product name: {product_data['name']}")
            except Exception as e:
                print(f"Error extracting product name: {str(e)}")
            
            # Product brand
            try:
                brand_element = await self.page.query_selector('.brand-name, .product-brand, [data-test="product-brand"]')
                if brand_element:
                    product_data['brand'] = await brand_element.text_content()
                    print(f"Product brand: {product_data['brand']}")
            except Exception as e:
                print(f"Error extracting product brand: {str(e)}")
            
            # Product price
            try:
                price_element = await self.page.query_selector('.product-price, .price, [data-test="product-price"]')
                if price_element:
                    product_data['price'] = await price_element.text_content()
                    print(f"Product price: {product_data['price']}")
            except Exception as e:
                print(f"Error extracting product price: {str(e)}")
            
            # Product description
            try:
                desc_element = await self.page.query_selector('.product-description, .description, [data-test="product-description"]')
                if desc_element:
                    product_data['description'] = await desc_element.text_content()
                    print(f"Product description: {product_data['description'][:100]}...")
            except Exception as e:
                print(f"Error extracting product description: {str(e)}")
            
            # Product ingredients
            try:
                ingredients_element = await self.page.query_selector('.ingredients, .product-ingredients, [data-test="product-ingredients"]')
                if ingredients_element:
                    product_data['ingredients'] = await ingredients_element.text_content()
                    print(f"Product ingredients: {product_data['ingredients'][:100]}...")
            except Exception as e:
                print(f"Error extracting product ingredients: {str(e)}")
            
            # Save to file
            with open("product_info.json", "w") as f:
                json.dump(product_data, f, indent=2)
            print(f"Saved product information to product_info.json")
            
            return product_data
        except Exception as e:
            print(f"Error extracting product information: {str(e)}")
            return {}
    
    async def search_products(self, search_term):
        """Search for products on the Boots website."""
        try:
            search_url = f"https://www.boots.com/search?q={search_term.replace(' ', '+')}"
            await self.navigate(search_url)
            
            # Take a screenshot
            await self.take_screenshot(f"search_{search_term.replace(' ', '_')}")
            
            # Scroll down to load more products
            for i in range(3):
                await self.page.evaluate(f"window.scrollBy(0, {800 * (i+1)})")
                await self.page.wait_for_timeout(1000)
            
            # Extract product links
            return await self.extract_product_links()
        except Exception as e:
            print(f"Error searching for products: {str(e)}")
            return []
    
    async def close(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()
            print("Browser closed.")

async def main():
    inspector = BootsInspector()
    await inspector.initialize()
    
    try:
        while True:
            print("\nBoots Website Inspector")
            print("1. Navigate to URL")
            print("2. Take screenshot")
            print("3. Test selector")
            print("4. Extract product links")
            print("5. Extract product information")
            print("6. Search for products")
            print("7. Exit")
            
            choice = input("Enter your choice (1-7): ")
            
            if choice == "1":
                url = input("Enter URL: ")
                await inspector.navigate(url)
            elif choice == "2":
                name = input("Enter screenshot name (or leave empty for auto-name): ")
                if not name:
                    name = None
                await inspector.take_screenshot(name)
            elif choice == "3":
                selector = input("Enter CSS selector: ")
                await inspector.test_selector(selector)
            elif choice == "4":
                selector = input("Enter CSS selector for links (or leave empty for default): ")
                if not selector:
                    selector = 'a[href*="/beauty/skincare/"]'
                await inspector.extract_product_links(selector)
            elif choice == "5":
                url = input("Enter product URL (or leave empty for current page): ")
                if not url:
                    url = None
                await inspector.extract_product_info(url)
            elif choice == "6":
                search_term = input("Enter search term: ")
                await inspector.search_products(search_term)
            elif choice == "7":
                break
            else:
                print("Invalid choice. Please try again.")
    finally:
        await inspector.close()

if __name__ == "__main__":
    asyncio.run(main())
