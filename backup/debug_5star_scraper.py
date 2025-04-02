#!/usr/bin/env python3
"""
Debug script for the 5-star product scraper.
This script focuses on finding and extracting URLs for all 5-star skincare products
from Boots.com, with detailed logging and error handling.
"""

import os
import sys
import asyncio
import logging
import traceback
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from boots_advanced_scraper import BootsScraper

# Configure logging
os.makedirs("logs", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"logs/debug_5star_scraper_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("debug_5star_scraper")

# URL for 5-star skincare products
FIVE_STAR_URL = "https://www.boots.com/beauty/skincare/skincare-all-skincare?criteria.roundedReviewScore=5"

async def debug_find_5star_urls():
    """Debug function to find all 5-star skincare product URLs."""
    logger.info("Starting debug session for finding 5-star product URLs")
    
    # Create necessary directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("screenshots", exist_ok=True)
    
    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = await context.new_page()
            
            # Navigate to the 5-star products page
            logger.info(f"Navigating to {FIVE_STAR_URL}")
            await page.goto(FIVE_STAR_URL, wait_until="networkidle")
            
            # Take a screenshot of the initial page
            await page.screenshot(path="screenshots/initial_page.png")
            logger.info("Took screenshot of initial page")
            
            # Handle cookie consent if present
            try:
                logger.info("Checking for cookie consent dialog")
                consent_button = await page.query_selector('button#onetrust-accept-btn-handler')
                if consent_button:
                    logger.info("Found cookie consent dialog, accepting cookies")
                    await consent_button.click()
                    await page.wait_for_timeout(2000)  # Wait for dialog to disappear
            except Exception as e:
                logger.warning(f"Error handling cookie consent: {str(e)}")
            
            # Get the total number of products
            logger.info("Trying to find total product count")
            try:
                # Wait for the product count element to be visible
                await page.wait_for_selector('.plp__results-count', timeout=10000)
                
                # Get the product count text
                product_count_element = await page.query_selector('.plp__results-count')
                if product_count_element:
                    product_count_text = await product_count_element.text_content()
                    logger.info(f"Product count text: {product_count_text}")
                    
                    # Extract the number from text like "285 results"
                    import re
                    count_match = re.search(r'(\d+)', product_count_text)
                    if count_match:
                        total_products = int(count_match.group(1))
                        logger.info(f"Total products found: {total_products}")
                    else:
                        logger.warning("Could not extract product count from text")
                        total_products = 285  # Default to expected count
                else:
                    logger.warning("Product count element not found")
                    total_products = 285  # Default to expected count
            except Exception as e:
                logger.error(f"Error getting product count: {str(e)}")
                total_products = 285  # Default to expected count
            
            # Scroll down to load all products
            logger.info("Starting to scroll to load all products")
            
            # Function to get current product count
            async def get_current_product_count():
                products = await page.query_selector_all('.product')
                return len(products)
            
            # Initial product count
            current_count = await get_current_product_count()
            logger.info(f"Initial product count: {current_count}")
            
            # Take a screenshot of the products
            await page.screenshot(path="screenshots/products_initial.png")
            
            # Scroll until we have all products or no new products are loaded
            max_scroll_attempts = 30
            scroll_attempts = 0
            last_count = 0
            
            while current_count < total_products and scroll_attempts < max_scroll_attempts:
                scroll_attempts += 1
                logger.info(f"Scroll attempt {scroll_attempts}/{max_scroll_attempts}, current products: {current_count}/{total_products}")
                
                # Scroll to the bottom of the page
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                
                # Wait for new products to load
                await page.wait_for_timeout(3000)
                
                # Check if we need to click "Load more" button
                try:
                    load_more_button = await page.query_selector('button.load-more-button')
                    if load_more_button:
                        logger.info("Found 'Load more' button, clicking it")
                        await load_more_button.click()
                        await page.wait_for_timeout(3000)
                except Exception as e:
                    logger.warning(f"Error with 'Load more' button: {str(e)}")
                
                # Get updated product count
                current_count = await get_current_product_count()
                logger.info(f"After scroll {scroll_attempts}, product count: {current_count}")
                
                # Take a screenshot after scrolling
                if scroll_attempts % 5 == 0:
                    await page.screenshot(path=f"screenshots/products_after_scroll_{scroll_attempts}.png")
                
                # If count hasn't increased, try a different approach
                if current_count == last_count:
                    logger.warning(f"Product count hasn't increased after scroll {scroll_attempts}")
                    
                    # Try to click "Show more" or similar buttons
                    try:
                        show_more_selectors = [
                            'button.show-more',
                            'button.load-more',
                            'button[data-test="load-more"]',
                            'button:has-text("Show more")',
                            'button:has-text("Load more")'
                        ]
                        
                        for selector in show_more_selectors:
                            button = await page.query_selector(selector)
                            if button:
                                logger.info(f"Found button with selector '{selector}', clicking it")
                                await button.click()
                                await page.wait_for_timeout(3000)
                                break
                    except Exception as e:
                        logger.warning(f"Error clicking 'Show more' button: {str(e)}")
                    
                    # Try JavaScript scroll
                    logger.info("Trying JavaScript scroll")
                    await page.evaluate("window.scrollBy(0, 500)")
                    await page.wait_for_timeout(2000)
                
                last_count = current_count
            
            # Final screenshot
            await page.screenshot(path="screenshots/products_final.png")
            logger.info(f"Final product count after scrolling: {current_count}/{total_products}")
            
            # Extract product URLs
            logger.info("Extracting product URLs")
            product_urls = set()
            
            # Get page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find all product links
            product_elements = soup.select('.product')
            logger.info(f"Found {len(product_elements)} product elements with BeautifulSoup")
            
            for product in product_elements:
                link_element = product.select_one('a.product-title, a.product-link, a[data-test="product-link"]')
                if link_element and 'href' in link_element.attrs:
                    href = link_element['href']
                    
                    # Ensure it's a full URL
                    if href.startswith('/'):
                        href = f"https://www.boots.com{href}"
                    
                    # Ensure it's a product URL
                    if '/product/' in href or '/skincare/' in href:
                        product_urls.add(href)
                        logger.info(f"Added product URL: {href}")
            
            # Save URLs to file
            url_file = f"data/boots_5star_urls_{timestamp}.txt"
            with open(url_file, 'w') as f:
                for url in product_urls:
                    f.write(f"{url}\n")
            
            logger.info(f"Saved {len(product_urls)} product URLs to {url_file}")
            
            # Close browser
            await browser.close()
            
            return product_urls
    
    except Exception as e:
        logger.error(f"Error in debug_find_5star_urls: {str(e)}")
        logger.error(traceback.format_exc())
        return set()

async def main():
    """Main function."""
    try:
        # Find 5-star product URLs
        product_urls = await debug_find_5star_urls()
        
        if product_urls:
            logger.info(f"Successfully found {len(product_urls)} 5-star product URLs")
            
            # Create a test scraper to scrape a few products
            logger.info("Creating test scraper to scrape 5 products")
            scraper = BootsScraper(
                headless=False,
                use_proxies=False,
                respect_robots=True,
                max_retries=3,
                min_delay=2.0,
                max_delay=5.0,
                data_dir="data",
                screenshot_dir="screenshots",
                cache_dir="cache"
            )
            
            # Set up the browser
            await scraper.setup_browser()
            
            # Add the first 5 product URLs to the scraper
            test_urls = list(product_urls)[:5]
            scraper.product_urls.update(test_urls)
            
            # Scrape the test products
            logger.info(f"Scraping {len(test_urls)} test products")
            await scraper.scrape_all_products()
            
            # Save the data
            scraper.save_data(suffix="_debug_test")
            
            # Close the browser
            await scraper.browser.close()
            
            logger.info("Debug test completed successfully")
        else:
            logger.error("Failed to find any 5-star product URLs")
    
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
