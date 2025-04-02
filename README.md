# Boots.com Skincare Products Scraper

A comprehensive scraper for extracting skincare product information from Boots.com, with a focus on building a database of cosmetics products.

## Project Summary (April 2025)

### Overview
This project provides tools to scrape detailed product information from Boots.com, including:
- Product names and brands
- Ingredients lists
- Country of origin
- Hazards and cautions
- How to use instructions
- Product details

### Latest Results
As of April 2025, the scraper has successfully processed:
- **3,633 total products** from Boots.com
- **3,286 unique brands** identified
- **1,429 products (39.3%)** with ingredients information
- **Average of 15.2 ingredients** per product
- **1,152 products (31.7%)** with country of origin information

### Key Features
- **Concurrent Scraping**: Uses ThreadPoolExecutor to process multiple products simultaneously
- **Robust Error Handling**: Implements retry logic with configurable attempts and delays
- **Rate Limiting Protection**: Detects and handles rate limiting with automatic pausing
- **Progress Tracking**: Saves progress at regular intervals to allow resuming interrupted scrapes
- **Data Validation**: Validates extracted data to ensure quality and relevance
- **Comprehensive Reporting**: Generates detailed summaries of the scraped data

## Improvement Areas

### 1. Missing Data Fields
Currently, we're not capturing hazards/cautions, product details, or how-to-use information. This could be because:
- These fields don't exist on many product pages
- Our selectors need refinement to better target these sections

**Next Steps:**
- Analyze a sample of product pages to identify the correct selectors for these fields
- Implement more flexible extraction logic that can handle variations in page structure
- Add validation for these fields to ensure we're capturing relevant information

### 2. Ingredient Coverage
Only 39.3% of products have ingredients listed. This is likely because:
- Not all cosmetic products on Boots.com list their ingredients
- Our ingredient extraction logic might need further enhancement for certain page layouts

**Next Steps:**
- Expand ingredient extraction to look for additional HTML patterns
- Implement advanced text processing to better identify ingredient lists
- Consider using AI-based extraction for more complex page layouts
- Add a confidence score for extracted ingredients

### 3. Error Handling for Failed URLs
Several URLs failed with "Failed to extract meaningful data" messages, suggesting:
- These pages have a different structure than what our scraper expects
- They might be error pages or redirects

**Next Steps:**
- Implement specific handling for error pages and redirects
- Add detailed logging for failed URLs to better understand failure patterns
- Create a separate process to retry failed URLs with different extraction strategies
- Consider using headless browser automation for particularly challenging pages

## Configuration

The scraper uses the following configuration constants:
- `MAX_WORKERS`: 4 (number of concurrent threads)
- `SAVE_INTERVAL`: 10 (save progress every 10 products)
- `MAX_RETRIES`: 3 (maximum retry attempts for failed requests)
- `RETRY_DELAY`: 3 (seconds to wait between retries)
- `MIN_DELAY` and `MAX_DELAY`: Random delay between requests
- `RATE_LIMIT_PAUSE`: 60 (seconds to pause if rate limiting is detected)

## Features

- **Advanced Scraping Capabilities**: Handles dynamic content loading, pagination, and product details extraction
- **Batch Processing**: Processes products in batches to prevent memory issues and allow for resuming interrupted scrapes
- **Error Handling**: Robust error recovery mechanisms to handle network issues and website changes
- **Data Export**: Saves data in structured CSV format for easy analysis
- **Proxy Support**: Optional proxy rotation to avoid IP blocking
- **User-Agent Rotation**: Mimics different browsers to avoid detection
- **Robots.txt Compliance**: Respects website crawling policies

## Scripts

- `boots_advanced_scraper.py`: The main scraper class with all functionality
- `extract_boots_5star_products.py`: Comprehensive script to extract all 285 5-star rated skincare products
- `scrape_boots_5star.py`: Simplified script for 5-star product extraction
- `debug_5star_scraper.py`: Debugging tool with detailed logging and screenshots
- `run_5star_scraper.py`: Batch processing script with resumable scraping

## Usage

### Extracting All 5-Star Skincare Products

To scrape all 285 5-star rated skincare products:

```bash
python3 extract_boots_5star_products.py
```

### Test Mode

To test the scraper with a small batch of products:

```bash
python3 extract_boots_5star_products.py --test
```

### Batch Processing

To process products in batches of a specific size:

```bash
python3 extract_boots_5star_products.py --batch-size 20
```

### Resuming a Scrape

If a scrape is interrupted, you can resume from a specific batch:

```bash
python3 extract_boots_5star_products.py --resume-from 3
```

### Headless Mode

For faster scraping without a browser UI:

```bash
python3 extract_boots_5star_products.py --headless
```

### Using a Pre-Existing URL List

If you already have a list of product URLs:

```bash
python3 extract_boots_5star_products.py --urls-file data/boots_5star_urls.txt
```

## Output Files

The scraper generates several output files in the `data` directory:

- `boots_products_[timestamp].csv`: Main product data
- `boots_ingredients_[timestamp].csv`: Extracted ingredients
- `boots_key_ingredients_[timestamp].csv`: Key ingredients highlighted in product descriptions
- `boots_5star_urls_[timestamp].txt`: List of all 5-star product URLs
- `boots_stats_[timestamp].json`: Scraping statistics

## Requirements

- Python 3.7+
- Playwright
- BeautifulSoup4
- Pandas
- Requests
- aiohttp

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install playwright beautifulsoup4 pandas requests aiohttp
   ```
3. Install Playwright browsers:
   ```bash
   playwright install
   ```

## Troubleshooting

If you encounter issues:

1. Check the logs in the `logs` directory
2. Examine screenshots in the `screenshots` directory
3. Try running in debug mode:
   ```bash
   python3 debug_5star_scraper.py
   ```
4. Increase retry attempts:
   ```bash
   python3 extract_boots_5star_products.py --max-retries 10
   ```

## License

This project is for educational purposes only. Always respect website terms of service and robots.txt policies when scraping.
