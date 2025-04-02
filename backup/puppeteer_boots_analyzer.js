/**
 * Puppeteer script to analyze the Boots website structure and extract 5-star skincare product URLs.
 * This script uses Puppeteer to interact with the website and extract product information.
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// URL for 5-star skincare products
const FIVE_STAR_URL = 'https://www.boots.com/beauty/skincare/skincare-all-skincare?criteria.roundedReviewScore=5';

// Create necessary directories
const screenshotsDir = path.join(__dirname, 'screenshots');
const dataDir = path.join(__dirname, 'data');

if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
}

if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
}

// Log function
function log(message) {
    const timestamp = new Date().toISOString();
    console.log(`${timestamp} - ${message}`);
    fs.appendFileSync(path.join(dataDir, 'puppeteer_log.txt'), `${timestamp} - ${message}\n`);
}

// Main function
async function analyzeBoodsWebsite() {
    log('Starting Boots website analysis');
    
    const browser = await puppeteer.launch({
        headless: false,
        defaultViewport: { width: 1280, height: 800 },
        args: ['--window-size=1280,800']
    });
    
    try {
        const page = await browser.newPage();
        
        // Set user agent
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
        
        // Navigate to the 5-star products page
        log(`Navigating to ${FIVE_STAR_URL}`);
        await page.goto(FIVE_STAR_URL, { waitUntil: 'networkidle2' });
        
        // Take a screenshot of the initial page
        await page.screenshot({ path: path.join(screenshotsDir, 'initial_page.png') });
        log('Took screenshot of initial page');
        
        // Handle cookie consent if present
        try {
            log('Checking for cookie consent dialog');
            const consentButton = await page.$('button#onetrust-accept-btn-handler');
            if (consentButton) {
                log('Found cookie consent dialog, accepting cookies');
                await consentButton.click();
                await page.waitForTimeout(2000); // Wait for dialog to disappear
            }
        } catch (e) {
            log(`Error handling cookie consent: ${e.message}`);
        }
        
        // Wait for page to load completely
        await page.waitForTimeout(5000);
        
        // Take another screenshot after handling cookies
        await page.screenshot({ path: path.join(screenshotsDir, 'after_cookies.png') });
        
        // Try to find the total number of products
        let totalProducts = 285; // Default value
        try {
            // Common selectors for product count
            const countSelectors = [
                '.plp__results-count',
                '.product-count',
                '.results-count',
                '[data-test="product-count"]',
                '.total-items'
            ];
            
            for (const selector of countSelectors) {
                const countElement = await page.$(selector);
                if (countElement) {
                    const countText = await page.evaluate(el => el.textContent, countElement);
                    log(`Found count element with text: ${countText}`);
                    
                    // Try to extract the number from text like "285 products"
                    const match = countText.match(/(\d+)/);
                    if (match) {
                        totalProducts = parseInt(match[1]);
                        log(`Extracted count of ${totalProducts} products`);
                        break;
                    }
                }
            }
        } catch (e) {
            log(`Error finding product count: ${e.message}`);
        }
        
        log(`Using count of ${totalProducts} 5-star rated products`);
        
        // Analyze page structure
        log('Analyzing page structure');
        
        // Get all elements on the page
        const allElements = await page.evaluate(() => {
            const elements = Array.from(document.querySelectorAll('*'));
            return elements.map(el => ({
                tag: el.tagName.toLowerCase(),
                id: el.id,
                classes: Array.from(el.classList),
                attributes: Array.from(el.attributes).map(attr => ({ name: attr.name, value: attr.value }))
            }));
        });
        
        // Save page structure to file
        fs.writeFileSync(
            path.join(dataDir, 'page_structure.json'),
            JSON.stringify(allElements, null, 2)
        );
        log(`Saved page structure with ${allElements.length} elements`);
        
        // Try different selectors for product elements
        const productSelectors = [
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
        
        for (const selector of productSelectors) {
            try {
                const elements = await page.$$(selector);
                log(`Found ${elements.length} elements with selector: ${selector}`);
                
                if (elements.length > 0) {
                    // Highlight the first element
                    await page.evaluate((selector) => {
                        const el = document.querySelector(selector);
                        if (el) {
                            el.style.border = '5px solid red';
                            el.scrollIntoView();
                        }
                    }, selector);
                    
                    // Take a screenshot with highlighted element
                    await page.screenshot({ 
                        path: path.join(screenshotsDir, `${selector.replace(/[^a-zA-Z0-9]/g, '_')}_highlight.png`) 
                    });
                    
                    // Remove highlight
                    await page.evaluate((selector) => {
                        const el = document.querySelector(selector);
                        if (el) {
                            el.style.border = '';
                        }
                    }, selector);
                }
            } catch (e) {
                log(`Error with selector ${selector}: ${e.message}`);
            }
        }
        
        // Scroll down to load all products
        log('Scrolling to load all products');
        
        for (let i = 1; i <= 10; i++) {
            log(`Scroll ${i}/10`);
            await page.evaluate(() => {
                window.scrollBy(0, window.innerHeight);
            });
            await page.waitForTimeout(2000);
            
            // Take screenshot after each scroll
            await page.screenshot({ path: path.join(screenshotsDir, `scroll_${i}.png`) });
        }
        
        // Scroll back to top
        await page.evaluate(() => {
            window.scrollTo(0, 0);
        });
        await page.waitForTimeout(1000);
        
        // Try to find product links
        log('Looking for product links');
        
        const productLinks = await page.evaluate(() => {
            const links = Array.from(document.querySelectorAll('a'));
            return links
                .filter(link => {
                    const href = link.href;
                    return href && (href.includes('/product/') || href.includes('/skincare/'));
                })
                .map(link => ({
                    href: link.href,
                    text: link.textContent.trim(),
                    classes: Array.from(link.classList),
                    parent: {
                        tag: link.parentElement.tagName.toLowerCase(),
                        classes: Array.from(link.parentElement.classList)
                    }
                }));
        });
        
        log(`Found ${productLinks.length} potential product links`);
        
        // Save product links to file
        fs.writeFileSync(
            path.join(dataDir, 'product_links.json'),
            JSON.stringify(productLinks, null, 2)
        );
        
        // Extract unique product URLs
        const productUrls = [...new Set(productLinks.map(link => link.href))];
        log(`Found ${productUrls.length} unique product URLs`);
        
        if (productUrls.length > 0) {
            // Save URLs to file
            fs.writeFileSync(
                path.join(dataDir, 'boots_5star_urls.txt'),
                productUrls.join('\n')
            );
            log(`Saved ${productUrls.length} product URLs to boots_5star_urls.txt`);
        } else {
            log('No product URLs found');
        }
        
        // Get page HTML for further analysis
        const html = await page.content();
        fs.writeFileSync(path.join(dataDir, 'page_content.html'), html);
        log('Saved page HTML content');
        
        // Check if there are any iframes that might contain products
        const iframes = await page.$$('iframe');
        log(`Found ${iframes.length} iframes on the page`);
        
        for (let i = 0; i < iframes.length; i++) {
            try {
                const src = await page.evaluate(iframe => iframe.src, iframes[i]);
                log(`Iframe ${i+1} src: ${src}`);
            } catch (e) {
                log(`Error getting iframe ${i+1} src: ${e.message}`);
            }
        }
        
        // Check for any JavaScript-loaded content
        log('Analyzing JavaScript-loaded content');
        
        // Look for network requests that might contain product data
        const client = await page.target().createCDPSession();
        await client.send('Network.enable');
        
        const requests = [];
        client.on('Network.requestWillBeSent', request => {
            requests.push({
                url: request.request.url,
                method: request.request.method,
                type: request.type
            });
        });
        
        // Refresh the page to capture network requests
        await page.reload({ waitUntil: 'networkidle2' });
        await page.waitForTimeout(5000);
        
        // Save network requests to file
        fs.writeFileSync(
            path.join(dataDir, 'network_requests.json'),
            JSON.stringify(requests, null, 2)
        );
        log(`Saved ${requests.length} network requests`);
        
        // Look for API requests that might contain product data
        const apiRequests = requests.filter(req => 
            req.url.includes('/api/') || 
            req.url.includes('.json') ||
            req.url.includes('graphql')
        );
        
        log(`Found ${apiRequests.length} potential API requests`);
        
        if (apiRequests.length > 0) {
            fs.writeFileSync(
                path.join(dataDir, 'api_requests.json'),
                JSON.stringify(apiRequests, null, 2)
            );
            log('Saved API requests to file');
        }
        
        log('Analysis completed');
        
    } catch (error) {
        log(`Error: ${error.message}`);
        log(error.stack);
    } finally {
        await browser.close();
        log('Browser closed');
    }
}

// Run the analysis
analyzeBoodsWebsite().catch(error => {
    log(`Fatal error: ${error.message}`);
    log(error.stack);
    process.exit(1);
});
