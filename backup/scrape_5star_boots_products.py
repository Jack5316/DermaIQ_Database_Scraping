#!/usr/bin/env python3
"""
Script to scrape all 5-star rated skincare products from Boots.com.
This script is optimized for handling a large number of products (285+).
"""

import os
import asyncio
import logging
import argparse
from datetime import datetime
from boots_advanced_scraper import BootsScraper

# Configure logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"boots_5star_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("boots_5star_scraper")

async def main_async():
    """Main async function to run the 5-star scraper."""
    parser = argparse.ArgumentParser(description='Boots.com 5-Star Skincare Products Scraper')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--use-proxies', action='store_true', help='Use proxy rotation')
    parser.add_argument('--respect-robots', action='store_true', help='Respect robots.txt')
    parser.add_argument('--max-products', type=int, default=None, help='Maximum number of products to scrape')
    parser.add_argument('--min-delay', type=float, default=3.0, help='Minimum delay between requests in seconds')
    parser.add_argument('--max-delay', type=float, default=10.0, help='Maximum delay between requests in seconds')
    parser.add_argument('--max-retries', type=int, default=5, help='Maximum number of retries for failed requests')
    parser.add_argument('--batch-size', type=int, default=50, help='Number of products to scrape in each batch')
    parser.add_argument('--resume-from', type=int, default=0, help='Resume scraping from this product index')
    
    args = parser.parse_args()
    
    logger.info("Starting 5-star products scraper")
    logger.info(f"Command line arguments: {args}")
    
    # Create data directories
    data_dir = "data"
    screenshot_dir = "screenshots"
    cache_dir = "cache"
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(screenshot_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)
    
    # If max_products is not specified, scrape all 285 products
    if args.max_products is None:
        logger.info("No maximum product limit specified, will attempt to scrape all 5-star products")
    else:
        logger.info(f"Will scrape up to {args.max_products} 5-star products")
    
    # If batch processing is enabled, process in batches
    if args.batch_size and args.batch_size > 0:
        # First, collect all product URLs
        logger.info("Collecting all product URLs first")
        url_collector = BootsScraper(
            headless=args.headless,
            use_proxies=args.use_proxies,
            respect_robots=args.respect_robots,
            max_retries=args.max_retries,
            min_delay=args.min_delay,
            max_delay=args.max_delay,
            data_dir=data_dir,
            screenshot_dir=screenshot_dir,
            cache_dir=cache_dir
        )
        
        try:
            # Set up the browser
            await url_collector.setup_browser()
            
            # Find all 5-star product URLs
            product_urls = await url_collector.find_5star_product_urls(max_products=args.max_products)
            
            # Save the URLs to a file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            urls_file = os.path.join(data_dir, f"boots_5star_urls_{timestamp}.txt")
            with open(urls_file, 'w') as f:
                for url in product_urls:
                    f.write(f"{url}\n")
            logger.info(f"Saved {len(product_urls)} 5-star product URLs to {urls_file}")
            
            # Convert to list for indexing
            product_urls_list = list(product_urls)
            
            # Process in batches
            total_products = len(product_urls_list)
            start_index = args.resume_from
            
            while start_index < total_products:
                end_index = min(start_index + args.batch_size, total_products)
                batch_urls = product_urls_list[start_index:end_index]
                
                logger.info(f"Processing batch of {len(batch_urls)} products (products {start_index+1}-{end_index} of {total_products})")
                
                # Create a new scraper for each batch to avoid memory issues
                batch_scraper = BootsScraper(
                    headless=args.headless,
                    use_proxies=args.use_proxies,
                    respect_robots=args.respect_robots,
                    max_retries=args.max_retries,
                    min_delay=args.min_delay,
                    max_delay=args.max_delay,
                    data_dir=data_dir,
                    screenshot_dir=screenshot_dir,
                    cache_dir=cache_dir
                )
                
                # Set up the browser
                await batch_scraper.setup_browser()
                
                # Add the batch URLs to the scraper
                batch_scraper.product_urls.update(batch_urls)
                
                # Scrape the batch
                await batch_scraper.scrape_all_products()
                
                # Save the data
                batch_scraper.save_data()
                
                # Close the browser
                await batch_scraper.browser.close()
                
                logger.info(f"Completed batch {start_index+1}-{end_index} of {total_products}")
                
                # Move to the next batch
                start_index = end_index
        
        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
        finally:
            # Close the browser
            if url_collector.browser:
                await url_collector.browser.close()
    else:
        # Process all at once
        scraper = BootsScraper(
            headless=args.headless,
            use_proxies=args.use_proxies,
            respect_robots=args.respect_robots,
            max_retries=args.max_retries,
            min_delay=args.min_delay,
            max_delay=args.max_delay,
            data_dir=data_dir,
            screenshot_dir=screenshot_dir,
            cache_dir=cache_dir
        )
        
        # Run the 5-star scraper
        await scraper.run_5star_scraper(max_products=args.max_products)
    
    logger.info("5-star products scraping completed")

def main():
    """Main function to run the scraper."""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
