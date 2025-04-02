#!/usr/bin/env python3
"""
Script to scrape all 5-star rated skincare products from Boots.com.
Uses the correct URL and optimized settings for reliable extraction.
"""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime
from boots_advanced_scraper import BootsScraper

# Set up argument parser
parser = argparse.ArgumentParser(description='Boots.com 5-Star Skincare Products Scraper')
parser.add_argument('--headless', action='store_true', help='Run in headless mode')
parser.add_argument('--max-products', type=int, default=None, help='Maximum number of products to scrape')
parser.add_argument('--batch-size', type=int, default=50, help='Number of products to scrape in each batch')
parser.add_argument('--test', action='store_true', help='Run in test mode with 10 products')
args = parser.parse_args()

# Create necessary directories
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)
os.makedirs("cache", exist_ok=True)

# Configure logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"logs/boots_5star_scraper_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("scrape_boots_5star")

async def main():
    """Main function to run the 5-star scraper."""
    logger.info("Starting Boots.com 5-star skincare products scraper")
    logger.info(f"Command line arguments: {args}")
    
    # Set max products for test mode
    if args.test:
        args.max_products = 10
        logger.info("Running in test mode with 10 products")
    
    # Create the scraper
    scraper = BootsScraper(
        headless=args.headless,
        use_proxies=False,
        respect_robots=True,
        max_retries=5,
        min_delay=3.0,
        max_delay=8.0,
        data_dir="data",
        screenshot_dir="screenshots",
        cache_dir="cache"
    )
    
    try:
        # Set up the browser
        await scraper.setup_browser()
        
        # Find all 5-star product URLs
        logger.info("Finding all 5-star product URLs")
        product_urls = await scraper.find_5star_product_urls(max_products=args.max_products)
        
        if not product_urls:
            logger.error("No 5-star product URLs found")
            await scraper.browser.close()
            return 1
        
        logger.info(f"Found {len(product_urls)} 5-star product URLs")
        
        # Save the URLs to a file
        urls_file = os.path.join("data", f"boots_5star_urls_{timestamp}.txt")
        with open(urls_file, 'w') as f:
            for url in product_urls:
                f.write(f"{url}\n")
        logger.info(f"Saved URLs to {urls_file}")
        
        # Process in batches if batch size is specified
        if args.batch_size and args.batch_size > 0:
            logger.info(f"Processing in batches of {args.batch_size} products")
            
            # Convert to list for batch processing
            product_urls_list = list(product_urls)
            total_products = len(product_urls_list)
            
            # Process each batch
            for start_index in range(0, total_products, args.batch_size):
                end_index = min(start_index + args.batch_size, total_products)
                batch_urls = product_urls_list[start_index:end_index]
                
                logger.info(f"Processing batch {start_index+1}-{end_index} of {total_products}")
                
                # Add the batch URLs to the scraper
                scraper.product_urls = set(batch_urls)
                
                # Scrape the batch
                await scraper.scrape_all_products()
                
                # Save the data
                scraper.save_data(suffix=f"_batch_{start_index+1}_{end_index}")
                
                logger.info(f"Completed batch {start_index+1}-{end_index}")
        else:
            # Process all at once
            logger.info("Processing all products at once")
            
            # Add the URLs to the scraper
            scraper.product_urls = product_urls
            
            # Scrape all products
            await scraper.scrape_all_products()
            
            # Save the data
            scraper.save_data()
        
        logger.info("Scraping completed successfully")
    
    except Exception as e:
        logger.error(f"Error in scraper: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    finally:
        # Close the browser
        if scraper.browser:
            await scraper.browser.close()
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
