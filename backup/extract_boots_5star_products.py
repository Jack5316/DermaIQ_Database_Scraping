#!/usr/bin/env python3
"""
Comprehensive script to extract all 285 5-star rated skincare products from Boots.com.
This script includes robust error handling, batch processing, and detailed logging
to ensure successful extraction of all product data.
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
    logger = logging.getLogger("extract_boots_5star")
    
    # Log uncaught exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Let the default handler handle keyboard interrupts
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception
    
    return logger, log_file

async def extract_product_urls(scraper, max_products=None):
    """
    Extract all 5-star product URLs from Boots.com.
    
    Args:
        scraper: BootsScraper instance
        max_products: Maximum number of products to extract
        
    Returns:
        Set of product URLs
    """
    logger = logging.getLogger("extract_boots_5star")
    
    try:
        # Set up the browser
        await scraper.setup_browser()
        
        # Find all 5-star product URLs
        logger.info("Finding all 5-star product URLs")
        product_urls = await scraper.find_5star_product_urls(max_products=max_products)
        
        if not product_urls:
            logger.error("No 5-star product URLs found")
            return set()
        
        logger.info(f"Found {len(product_urls)} 5-star product URLs")
        
        # Save the URLs to a file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        urls_file = os.path.join(scraper.data_dir, f"boots_5star_urls_{timestamp}.txt")
        with open(urls_file, 'w') as f:
            for url in product_urls:
                f.write(f"{url}\n")
        logger.info(f"Saved URLs to {urls_file}")
        
        return product_urls
    
    except Exception as e:
        logger.error(f"Error extracting product URLs: {str(e)}")
        logger.error(traceback.format_exc())
        return set()

async def process_batch(scraper, batch_urls, batch_number, total_batches):
    """
    Process a batch of product URLs.
    
    Args:
        scraper: BootsScraper instance
        batch_urls: List of product URLs to process
        batch_number: Current batch number
        total_batches: Total number of batches
        
    Returns:
        True if successful, False otherwise
    """
    logger = logging.getLogger("extract_boots_5star")
    
    try:
        logger.info(f"Processing batch {batch_number}/{total_batches} with {len(batch_urls)} products")
        
        # Set up the browser
        await scraper.setup_browser()
        
        # Add the batch URLs to the scraper
        scraper.product_urls = set(batch_urls)
        
        # Scrape the batch
        await scraper.scrape_all_products()
        
        # Save the data
        scraper.save_data(suffix=f"_batch_{batch_number}")
        
        # Close the browser
        await scraper.browser.close()
        
        logger.info(f"Completed batch {batch_number}/{total_batches}")
        return True
    
    except Exception as e:
        logger.error(f"Error processing batch {batch_number}/{total_batches}: {str(e)}")
        logger.error(traceback.format_exc())
        return False

async def main():
    """Main function to run the 5-star scraper."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Extract all 5-star skincare products from Boots.com')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--max-products', type=int, default=None, help='Maximum number of products to scrape')
    parser.add_argument('--batch-size', type=int, default=50, help='Number of products to scrape in each batch')
    parser.add_argument('--resume-from', type=int, default=0, help='Resume scraping from this batch number (1-based)')
    parser.add_argument('--data-dir', type=str, default='data', help='Directory to save data files')
    parser.add_argument('--screenshot-dir', type=str, default='screenshots', help='Directory to save screenshots')
    parser.add_argument('--cache-dir', type=str, default='cache', help='Directory to save cache files')
    parser.add_argument('--log-dir', type=str, default='logs', help='Directory to save log files')
    parser.add_argument('--test', action='store_true', help='Run in test mode with 10 products')
    parser.add_argument('--urls-file', type=str, help='File containing product URLs to scrape (one URL per line)')
    
    args = parser.parse_args()
    
    # Create necessary directories
    os.makedirs(args.data_dir, exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)
    os.makedirs(args.screenshot_dir, exist_ok=True)
    os.makedirs(args.cache_dir, exist_ok=True)
    
    # Set up logging
    logger, log_file = setup_logging(args.log_dir)
    
    # Log startup information
    logger.info("Starting extraction of Boots.com 5-star skincare products")
    logger.info(f"Command line arguments: {args}")
    
    # Set max products for test mode
    if args.test:
        args.max_products = 10
        logger.info("Running in test mode with 10 products")
    
    try:
        # Create the scraper
        scraper = BootsScraper(
            headless=args.headless,
            use_proxies=False,
            respect_robots=True,
            max_retries=5,
            min_delay=3.0,
            max_delay=8.0,
            data_dir=args.data_dir,
            screenshot_dir=args.screenshot_dir,
            cache_dir=args.cache_dir
        )
        
        # Get product URLs
        product_urls = set()
        
        if args.urls_file:
            # Load URLs from file
            logger.info(f"Loading product URLs from {args.urls_file}")
            with open(args.urls_file, 'r') as f:
                for line in f:
                    url = line.strip()
                    if url:
                        product_urls.add(url)
            logger.info(f"Loaded {len(product_urls)} product URLs from file")
        else:
            # Extract URLs from website
            product_urls = await extract_product_urls(scraper, max_products=args.max_products)
            
            # Close the browser after extracting URLs
            await scraper.browser.close()
        
        if not product_urls:
            logger.error("No product URLs to process")
            return 1
        
        # Process in batches
        product_urls_list = list(product_urls)
        if args.max_products:
            product_urls_list = product_urls_list[:args.max_products]
        
        total_products = len(product_urls_list)
        batch_size = min(args.batch_size, total_products)
        total_batches = (total_products + batch_size - 1) // batch_size
        
        logger.info(f"Processing {total_products} products in {total_batches} batches of {batch_size}")
        
        # Process each batch
        successful_batches = 0
        failed_batches = 0
        
        for batch_number in range(1, total_batches + 1):
            if batch_number < args.resume_from:
                logger.info(f"Skipping batch {batch_number}/{total_batches} (resuming from {args.resume_from})")
                continue
            
            start_index = (batch_number - 1) * batch_size
            end_index = min(start_index + batch_size, total_products)
            batch_urls = product_urls_list[start_index:end_index]
            
            # Create a new scraper for each batch to avoid memory issues
            batch_scraper = BootsScraper(
                headless=args.headless,
                use_proxies=False,
                respect_robots=True,
                max_retries=5,
                min_delay=3.0,
                max_delay=8.0,
                data_dir=args.data_dir,
                screenshot_dir=args.screenshot_dir,
                cache_dir=args.cache_dir
            )
            
            # Process the batch
            success = await process_batch(batch_scraper, batch_urls, batch_number, total_batches)
            
            if success:
                successful_batches += 1
            else:
                failed_batches += 1
        
        # Log summary
        logger.info(f"Extraction completed: {successful_batches} successful batches, {failed_batches} failed batches")
        
        if failed_batches > 0:
            logger.warning(f"Some batches failed. Check the log file for details: {log_file}")
            return 1
        
        logger.info("All batches completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
