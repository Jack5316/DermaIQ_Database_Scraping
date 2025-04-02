#!/usr/bin/env python3
"""
Test script for the Boots Advanced Scraper.
This script runs the scraper with a limited number of products to verify functionality.
"""

import asyncio
import logging
from boots_advanced_scraper import BootsScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_boots_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_boots_scraper")

async def test_scraper():
    """Run a test of the Boots scraper with limited scope."""
    logger.info("Starting test scraper run")
    
    # Create a scraper instance with test settings
    scraper = BootsScraper(
        headless=False,  # Set to False to see the browser for debugging
        use_proxies=False,  # Disable proxies for testing
        respect_robots=True,
        max_retries=2,
        min_delay=1.0,  # Shorter delays for testing
        max_delay=3.0
    )
    
    # Run the scraper with limited scope
    await scraper.run(
        max_categories=2,  # Only scrape 2 categories
        max_products_per_category=3,  # Only get 3 products per category
        max_total_products=5  # Maximum of 5 products total
    )
    
    logger.info("Test scraper run completed")

async def test_specific_product():
    """Test scraping a specific product URL."""
    logger.info("Testing specific product scraping")
    
    # Create a scraper instance
    scraper = BootsScraper(
        headless=False,  # Set to False to see the browser for debugging
        use_proxies=False,
        respect_robots=True
    )
    
    # Set up the browser
    await scraper.setup_browser()
    
    try:
        # Test with a known product URL
        test_url = "https://www.boots.com/cerave-sa-smoothing-cleanser-with-salicylic-acid-236ml-10276177"
        
        logger.info(f"Scraping test product: {test_url}")
        product_data = await scraper.scrape_product(test_url)
        
        # Print the extracted data
        logger.info("Product data extracted:")
        for key, value in product_data.items():
            if isinstance(value, list) and len(value) > 10:
                logger.info(f"{key}: {value[:5]} ... (and {len(value)-5} more)")
            else:
                logger.info(f"{key}: {value}")
        
        # Save the test data
        scraper.save_data()
        
    finally:
        # Close the browser
        if scraper.browser:
            await scraper.browser.close()
    
    logger.info("Specific product test completed")

def main():
    """Main function to run the test."""
    # Uncomment the test you want to run
    asyncio.run(test_scraper())
    # asyncio.run(test_specific_product())

if __name__ == "__main__":
    main()
