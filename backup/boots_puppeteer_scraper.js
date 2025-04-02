/**
 * Boots.com Puppeteer Scraper
 * 
 * This script uses Puppeteer to scrape 5-star skincare products from Boots.com,
 * focusing on extracting ingredients, country of origin, hazards and cautions,
 * how to use, and product details.
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const { Parser } = require('json2csv');

// Base URLs
const BASE_URL = 'https://www.boots.com';
const SKINCARE_URL = `${BASE_URL}/beauty/skincare/skincare-all-skincare`;
const FIVE_STAR_URL = `${SKINCARE_URL}?criteria.roundedReviewScore=5`;

// User agents for rotation
const USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
];

// Create directories if they don't exist
const dataDir = path.join(__dirname, 'data');
const screenshotsDir = path.join(__dirname, 'screenshots');
if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir);
}
if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir);
}

// Helper function for random delays
const randomDelay = async (min = 1000, max = 5000) => {
    const delay = Math.floor(Math.random() * (max - min + 1)) + min;
    console.log(`Waiting ${delay}ms...`);
    return new Promise(resolve => setTimeout(resolve, delay));
};

// Helper function to get a random user agent
const getRandomUserAgent = () => {
    return USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
};

// Main scraper function
async function scrapeBoots5StarSkincare() {
    console.log('Starting Boots 5-star skincare scraper');
    
    const browser = await puppeteer.launch({
        headless: false, // Set to true for production
        defaultViewport: { width: 1280, height: 800 },
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        // Create a new page with random user agent
        const page = await browser.newPage();
        const userAgent = getRandomUserAgent();
        await page.setUserAgent(userAgent);
        console.log(`Using user agent: ${userAgent}`);
        
        // Enable request interception to capture network requests
        await page.setRequestInterception(true);
        
        // Store product data from network requests
        let productData = [];
        let productUrls = [];
        
        // Listen for network requests
        page.on('request', request => {
            request.continue();
        });
        
        // Listen for network responses
        page.on('response', async response => {
            const url = response.url();
            
            // Look for API responses containing product data
            if (url.includes('/api/') && url.includes('products')) {
                try {
                    const responseText = await response.text();
                    const data = JSON.parse(responseText);
                    
                    if (data && data.products) {
                        console.log(`Found ${data.products.length} products in API response`);
                        productData.push(...data.products);
                    }
                } catch (error) {
                    console.error(`Error parsing API response: ${error.message}`);
                }
            }
        });
        
        // Navigate to the 5-star skincare page
        console.log(`Navigating to ${FIVE_STAR_URL}`);
        await page.goto(FIVE_STAR_URL, { waitUntil: 'networkidle2' });
        
        // Handle cookie consent if present
        try {
            const cookieConsentButton = await page.$('#onetrust-accept-btn-handler');
            if (cookieConsentButton) {
                console.log('Accepting cookies');
                await cookieConsentButton.click();
                await page.waitForTimeout(2000);
            }
        } catch (error) {
            console.log('No cookie consent dialog found or error handling it');
        }
        
        // Take a screenshot of the initial page
        await page.screenshot({ path: path.join(screenshotsDir, 'initial_page.png') });
        
        // Scroll down to load all products
        console.log('Scrolling to load all products');
        
        // Calculate the number of scrolls needed (assuming ~24 products per page)
        const totalProducts = 285; // Default value
        const productsPerPage = 24;
        const numScrolls = Math.ceil(totalProducts / productsPerPage);
        
        for (let i = 0; i < numScrolls; i++) {
            console.log(`Scroll ${i+1}/${numScrolls}`);
            await page.evaluate(() => {
                window.scrollBy(0, window.innerHeight);
            });
            await page.waitForTimeout(2000);
            
            // Try clicking "Load more" button if present
            try {
                const loadMoreSelectors = [
                    'button.load-more',
                    'button.show-more',
                    'button[data-test="load-more"]',
                    'button:has-text("Load more")',
                    'button:has-text("Show more")'
                ];
                
                for (const selector of loadMoreSelectors) {
                    const loadMoreButton = await page.$(selector);
                    if (loadMoreButton) {
                        console.log(`Found load more button with selector: ${selector}`);
                        await loadMoreButton.click();
                        await page.waitForTimeout(5000);
                        break;
                    }
                }
            } catch (error) {
                console.log(`Error clicking load more button: ${error.message}`);
            }
        }
        
        // Take a screenshot after scrolling
        await page.screenshot({ path: path.join(screenshotsDir, 'after_scrolling.png') });
        
        // Extract product URLs from the page
        console.log('Extracting product URLs from the page');
        
        // Try different selectors for product cards
        const productCardSelectors = [
            '.product-grid .product-tile',
            '.product-list-item',
            '.product-card',
            '.product',
            '[data-test="product-tile"]',
            '.product-grid-item',
            '.product-item',
            '.plp-grid__item',
            '.product-list__item',
            '.product-tile',
            'article.product',
            'div[data-component="product"]',
            'li.product'
        ];
        
        for (const selector of productCardSelectors) {
            const productCards = await page.$$(selector);
            console.log(`Found ${productCards.length} product cards with selector: ${selector}`);
            
            if (productCards.length > 0) {
                for (const card of productCards) {
                    try {
                        // Extract URL from the card
                        const link = await card.$('a');
                        if (link) {
                            const href = await page.evaluate(el => el.href, link);
                            if (href) {
                                productUrls.push(href);
                                console.log(`Found product URL: ${href}`);
                            }
                        }
                    } catch (error) {
                        console.log(`Error extracting URL from product card: ${error.message}`);
                    }
                }
                
                // If we found product cards with this selector, no need to try others
                if (productUrls.length > 0) {
                    break;
                }
            }
        }
        
        // If no product cards found, look for product links directly
        if (productUrls.length === 0) {
            console.log('No product cards found, looking for product links directly');
            
            // Get all links on the page
            const links = await page.$$('a');
            console.log(`Found ${links.length} links on the page`);
            
            for (const link of links) {
                try {
                    const href = await page.evaluate(el => el.href, link);
                    if (href && (href.includes('/product/') || (href.includes('/beauty/skincare/') && !href.endsWith('skincare')))) {
                        productUrls.push(href);
                        console.log(`Found product URL: ${href}`);
                    }
                } catch (error) {
                    console.log(`Error extracting URL from link: ${error.message}`);
                }
            }
        }
        
        // Remove duplicates
        productUrls = [...new Set(productUrls)];
        console.log(`Found ${productUrls.length} unique product URLs`);
        
        // If no product URLs found from the page, use the product data from network requests
        if (productUrls.length === 0 && productData.length > 0) {
            console.log(`Using ${productData.length} products from network requests`);
            
            // Extract URLs from product data
            for (const product of productData) {
                if (product.url) {
                    const url = product.url.startsWith('/') ? `${BASE_URL}${product.url}` : product.url;
                    productUrls.push(url);
                    console.log(`Found product URL from API: ${url}`);
                }
            }
            
            // Remove duplicates again
            productUrls = [...new Set(productUrls)];
            console.log(`Found ${productUrls.length} unique product URLs from API`);
        }
        
        // Save URLs to file
        if (productUrls.length > 0) {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const urlFile = path.join(dataDir, `boots_5star_urls_${timestamp}.txt`);
            fs.writeFileSync(urlFile, productUrls.join('\n'));
            console.log(`Saved ${productUrls.length} product URLs to ${urlFile}`);
        } else {
            console.log('No product URLs found');
            
            // If no product URLs found, use test URLs
            const testProductUrls = [
                'https://www.boots.com/beauty/skincare/face-skincare/cleansers-and-toners/no7-radiant-results-revitalising-cleansing-wipes-30s-10263822',
                'https://www.boots.com/beauty/skincare/face-skincare/face-serums/no7-laboratories-firming-booster-serum-30ml-10263820',
                'https://www.boots.com/beauty/skincare/face-skincare/face-moisturisers-and-creams/no7-protect-and-perfect-intense-advanced-day-cream-spf15-50ml-10263818'
            ];
            
            console.log(`Using ${testProductUrls.length} test product URLs`);
            productUrls = testProductUrls;
        }
        
        // Scrape product details
        console.log(`Scraping details for ${productUrls.length} products`);
        
        const scrapedProducts = [];
        
        for (let i = 0; i < productUrls.length; i++) {
            const url = productUrls[i];
            console.log(`Scraping product ${i+1}/${productUrls.length}: ${url}`);
            
            try {
                // Navigate to the product page
                await randomDelay(2000, 5000);
                await page.goto(url, { waitUntil: 'networkidle2' });
                
                // Take a screenshot of the product page
                const productId = url.split('/').pop().split('?')[0];
                await page.screenshot({ path: path.join(screenshotsDir, `${productId}.png`) });
                
                // Extract product information
                const productInfo = await extractProductInfo(page, url);
                scrapedProducts.push(productInfo);
                
                // Save progress after each product
                saveProductsToCSV(scrapedProducts);
                
            } catch (error) {
                console.error(`Error scraping product ${url}: ${error.message}`);
                scrapedProducts.push({ url, error: error.message });
                saveProductsToCSV(scrapedProducts);
            }
        }
        
        console.log(`Scraped ${scrapedProducts.length} products`);
        
    } catch (error) {
        console.error(`Error in main scraper: ${error.message}`);
    } finally {
        // Close the browser
        await browser.close();
        console.log('Browser closed');
    }
}

// Function to extract product information from a product page
async function extractProductInfo(page, url) {
    console.log(`Extracting product information from ${url}`);
    
    const productInfo = {
        url,
        timestamp: new Date().toISOString()
    };
    
    try {
        // Product name
        const nameSelectors = [
            'h1.product-details__name',
            '.product-title',
            '.product-name',
            'h1[data-test="product-name"]',
            'h1'
        ];
        
        for (const selector of nameSelectors) {
            const nameElement = await page.$(selector);
            if (nameElement) {
                productInfo.name = await page.evaluate(el => el.textContent.trim(), nameElement);
                console.log(`Found product name: ${productInfo.name}`);
                break;
            }
        }
        
        // Brand
        const brandSelectors = [
            '.product-details__brand',
            '.product-brand',
            '[data-test="product-brand"]',
            '.brand'
        ];
        
        for (const selector of brandSelectors) {
            const brandElement = await page.$(selector);
            if (brandElement) {
                productInfo.brand = await page.evaluate(el => el.textContent.trim(), brandElement);
                console.log(`Found brand: ${productInfo.brand}`);
                break;
            }
        }
        
        // Price
        const priceSelectors = [
            '.product-details__price',
            '.product-price',
            '[data-test="product-price"]',
            '.price'
        ];
        
        for (const selector of priceSelectors) {
            const priceElement = await page.$(selector);
            if (priceElement) {
                productInfo.price = await page.evaluate(el => el.textContent.trim(), priceElement);
                console.log(`Found price: ${productInfo.price}`);
                break;
            }
        }
        
        // Description
        const descriptionSelectors = [
            '.product-details__description',
            '.product-description',
            '[data-test="product-description"]',
            '.description'
        ];
        
        for (const selector of descriptionSelectors) {
            const descriptionElement = await page.$(selector);
            if (descriptionElement) {
                productInfo.description = await page.evaluate(el => el.textContent.trim(), descriptionElement);
                console.log(`Found description (truncated): ${productInfo.description.substring(0, 50)}...`);
                break;
            }
        }
        
        // Ingredients
        // First try to find and click an "Ingredients" tab or button
        const ingredientTabSelectors = [
            'button:has-text("Ingredients")',
            'a:has-text("Ingredients")',
            'div[data-tab="ingredients"]',
            '#tab-ingredients'
        ];
        
        for (const selector of ingredientTabSelectors) {
            const tab = await page.$(selector);
            if (tab) {
                console.log(`Found ingredients tab with selector: ${selector}`);
                await tab.click();
                await page.waitForTimeout(1000);
                break;
            }
        }
        
        // Now try to extract the ingredients
        const ingredientSelectors = [
            '.product-details__ingredients',
            '.product-ingredients',
            '[data-test="product-ingredients"]',
            '.ingredients',
            '#ingredients'
        ];
        
        for (const selector of ingredientSelectors) {
            const ingredientsElement = await page.$(selector);
            if (ingredientsElement) {
                productInfo.ingredients = await page.evaluate(el => el.textContent.trim(), ingredientsElement);
                console.log(`Found ingredients (truncated): ${productInfo.ingredients.substring(0, 50)}...`);
                break;
            }
        }
        
        // Country of origin
        const countrySelectors = [
            '.country-of-origin',
            '[data-test="country-of-origin"]'
        ];
        
        for (const selector of countrySelectors) {
            const countryElement = await page.$(selector);
            if (countryElement) {
                productInfo.country_of_origin = await page.evaluate(el => el.textContent.trim(), countryElement);
                console.log(`Found country of origin: ${productInfo.country_of_origin}`);
                break;
            }
        }
        
        // How to use
        const howToUseSelectors = [
            '.how-to-use',
            '[data-test="how-to-use"]'
        ];
        
        for (const selector of howToUseSelectors) {
            const howToUseElement = await page.$(selector);
            if (howToUseElement) {
                productInfo.how_to_use = await page.evaluate(el => el.textContent.trim(), howToUseElement);
                console.log(`Found how to use (truncated): ${productInfo.how_to_use.substring(0, 50)}...`);
                break;
            }
        }
        
        // Hazards and cautions
        const hazardsSelectors = [
            '.hazards',
            '.cautions',
            '[data-test="hazards-cautions"]'
        ];
        
        for (const selector of hazardsSelectors) {
            const hazardsElement = await page.$(selector);
            if (hazardsElement) {
                productInfo.hazards_cautions = await page.evaluate(el => el.textContent.trim(), hazardsElement);
                console.log(`Found hazards and cautions (truncated): ${productInfo.hazards_cautions.substring(0, 50)}...`);
                break;
            }
        }
        
        // Rating
        const ratingSelectors = [
            '.rating',
            '.product-rating',
            '[data-test="product-rating"]'
        ];
        
        for (const selector of ratingSelectors) {
            const ratingElement = await page.$(selector);
            if (ratingElement) {
                productInfo.rating = await page.evaluate(el => el.textContent.trim(), ratingElement);
                console.log(`Found rating: ${productInfo.rating}`);
                break;
            }
        }
        
        // Review count
        const reviewCountSelectors = [
            '.review-count',
            '.product-review-count',
            '[data-test="product-review-count"]'
        ];
        
        for (const selector of reviewCountSelectors) {
            const reviewCountElement = await page.$(selector);
            if (reviewCountElement) {
                productInfo.review_count = await page.evaluate(el => el.textContent.trim(), reviewCountElement);
                console.log(`Found review count: ${productInfo.review_count}`);
                break;
            }
        }
        
        return productInfo;
        
    } catch (error) {
        console.error(`Error extracting product information: ${error.message}`);
        return { url, error: error.message };
    }
}

// Function to save products to CSV
function saveProductsToCSV(products) {
    try {
        if (products.length === 0) {
            console.log('No products to save');
            return;
        }
        
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const csvFile = path.join(dataDir, `boots_5star_products_${timestamp}.csv`);
        
        const fields = Object.keys(products[0]);
        const json2csvParser = new Parser({ fields });
        const csv = json2csvParser.parse(products);
        
        fs.writeFileSync(csvFile, csv);
        console.log(`Saved ${products.length} products to ${csvFile}`);
        
    } catch (error) {
        console.error(`Error saving products to CSV: ${error.message}`);
    }
}

// Run the scraper
scrapeBoots5StarSkincare()
    .then(() => console.log('Scraper completed'))
    .catch(error => console.error(`Scraper failed: ${error.message}`));
