#!/usr/bin/env python3
"""
Script to run the 5-star product scraper for Boots.com skincare products.
This script is designed to be robust and handle the full 285 products.
"""

import os
import sys
import asyncio
import logging
import argparse
import traceback
from datetime import datetime
from boots_advanced_scraper import BootsScraper

def setup_logging(log_dir="logs"):
    """Set up logging configuration."""
    # Create necessary directories
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/boots_5star_scraper_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger("run_5star_scraper")
    
    # Log uncaught exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Let the default handler handle keyboard interrupts
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception
    
    return logger

async def main():
    """Run the 5-star product scraper with command line arguments."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Boots.com 5-Star Skincare Products Scraper')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--use-proxies', action='store_true', help='Use proxy rotation')
    parser.add_argument('--respect-robots', action='store_true', help='Respect robots.txt')
    parser.add_argument('--max-products', type=int, default=None, help='Maximum number of products to scrape')
    parser.add_argument('--min-delay', type=float, default=3.0, help='Minimum delay between requests in seconds')
    parser.add_argument('--max-delay', type=float, default=8.0, help='Maximum delay between requests in seconds')
    parser.add_argument('--max-retries', type=int, default=5, help='Maximum number of retries for failed requests')
    parser.add_argument('--batch-size', type=int, default=50, help='Number of products to scrape in each batch')
    parser.add_argument('--resume-from', type=int, default=0, help='Resume scraping from this product index')
    parser.add_argument('--data-dir', type=str, default='data', help='Directory to save data files')
    parser.add_argument('--screenshot-dir', type=str, default='screenshots', help='Directory to save screenshots')
    parser.add_argument('--cache-dir', type=str, default='cache', help='Directory to save cache files')
    parser.add_argument('--log-dir', type=str, default='logs', help='Directory to save log files')
    parser.add_argument('--test', action='store_true', help='Run in test mode with 10 products')
    
    args = parser.parse_args()
    
    # Create necessary directories
    os.makedirs(args.data_dir, exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)
    os.makedirs(args.screenshot_dir, exist_ok=True)
    os.makedirs(args.cache_dir, exist_ok=True)
    
    # Set up logging
    logger = setup_logging(args.log_dir)
    
    # Log startup information
    logger.info("Starting 5-star product scraper")
    logger.info(f"Command line arguments: {args}")
    
    # Set max products for test mode
    if args.test:
        args.max_products = 10
        logger.info("Running in test mode with 10 products")
    
    try:
        # Create the scraper with optimized settings
        scraper = BootsScraper(
            headless=args.headless,
            use_proxies=args.use_proxies,
            respect_robots=args.respect_robots,
            max_retries=args.max_retries,
            min_delay=args.min_delay,
            max_delay=args.max_delay,
            data_dir=args.data_dir,
            screenshot_dir=args.screenshot_dir,
            cache_dir=args.cache_dir
        )
        
        # Run the 5-star scraper
        if args.batch_size and args.batch_size > 0:
            logger.info(f"Running in batch mode with batch size {args.batch_size}")
            
            # First, collect all product URLs
            logger.info("Collecting all product URLs first")
            await scraper.setup_browser()
            
            product_urls = await scraper.find_5star_product_urls(max_products=args.max_products)
            logger.info(f"Found {len(product_urls)} 5-star product URLs")
            
            # Save the URLs to a file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            urls_file = os.path.join(args.data_dir, f"boots_5star_urls_{timestamp}.txt")
            with open(urls_file, 'w') as f:
                for url in product_urls:
                    f.write(f"{url}\n")
            logger.info(f"Saved URLs to {urls_file}")
            
            # Close the browser
            await scraper.browser.close()
            
            # Process in batches
            product_urls_list = list(product_urls)
            total_products = len(product_urls_list)
            start_index = args.resume_from
            
            while start_index < total_products:
                end_index = min(start_index + args.batch_size, total_products)
                batch_urls = product_urls_list[start_index:end_index]
                
                logger.info(f"Processing batch {start_index+1}-{end_index} of {total_products}")
                
                # Create a new scraper for each batch
                batch_scraper = BootsScraper(
                    headless=args.headless,
                    use_proxies=args.use_proxies,
                    respect_robots=args.respect_robots,
                    max_retries=args.max_retries,
                    min_delay=args.min_delay,
                    max_delay=args.max_delay,
                    data_dir=args.data_dir,
                    screenshot_dir=args.screenshot_dir,
                    cache_dir=args.cache_dir
                )
                
                # Set up the browser
                await batch_scraper.setup_browser()
                
                # Add the batch URLs to the scraper
                batch_scraper.product_urls.update(batch_urls)
                
                try:
                    # Scrape the batch
                    await batch_scraper.scrape_all_products()
                    
                    # Save the data
                    batch_scraper.save_data(suffix=f"_batch_{start_index+1}_{end_index}")
                    
                    logger.info(f"Completed batch {start_index+1}-{end_index}")
                except Exception as e:
                    logger.error(f"Error processing batch {start_index+1}-{end_index}: {str(e)}")
                    logger.error(traceback.format_exc())
                finally:
                    # Close the browser
                    await batch_scraper.browser.close()
                
                # Move to the next batch
                start_index = end_index
        else:
            # Process all at once
            logger.info("Running all products at once")
            await scraper.run_5star_scraper(max_products=args.max_products)
        
        logger.info("5-star product scraper completed successfully")
    
    except Exception as e:
        logger.error(f"Error running 5-star product scraper: {str(e)}")
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
