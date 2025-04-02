# DermaIQ Scraping Project Guidelines

## Commands
- Run main scraper: `python3 cosmetics_scraper.py`
- Run 5-star product scraper: `python3 extract_boots_5star_products.py`
- Run test scraper: `python3 extract_boots_5star_products.py --test`
- Analyze ingredients data: `python3 analyze_ingredients.py`
- Run single test: `python3 test_ingredients_list.py`
- Lint code: `black *.py`

## Code Style
- **Formatting**: Use Black formatter
- **Imports**: Standard library imports first, then third-party, then local
- **Documentation**: Docstrings for all functions including args and returns
- **Naming**: snake_case for functions/variables, UPPER_CASE for constants
- **Error Handling**: Use try/except with specific exception types
- **Logging**: Print statements for now; use detailed messages for debugging
- **Constants**: Define configuration constants at module top level
- **Types**: Optional type hints but maintain consistent style
- **Retry Logic**: Implement with exponential backoff where appropriate

## Best Practices
- Save progress at regular intervals (SAVE_INTERVAL constant)
- Respect website's rate limits with randomized delays
- Use ThreadPoolExecutor for concurrent operations
- Validate extracted data before storage
- Generate summary statistics after scraping