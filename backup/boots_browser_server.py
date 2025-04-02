#!/usr/bin/env python3
"""
A simple web server that allows us to interact with the Boots website through a browser interface.
This will help us analyze the website structure and identify the correct selectors for 5-star products.
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from playwright.sync_api import sync_playwright

# Configure logging
os.makedirs("logs", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"logs/boots_browser_server_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("boots_browser_server")

# Create Flask app
app = Flask(__name__)

# URL for 5-star skincare products
FIVE_STAR_URL = "https://www.boots.com/beauty/skincare/skincare-all-skincare?criteria.roundedReviewScore=5"

# HTML template for the browser interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Boots Scraper Analyzer</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1, h2 {
            color: #333;
        }
        .control-panel {
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
        }
        button:hover {
            background-color: #45a049;
        }
        input[type="text"] {
            padding: 10px;
            width: 300px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .results {
            margin-top: 20px;
        }
        .log {
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            padding: 10px;
            height: 200px;
            overflow-y: auto;
            font-family: monospace;
            margin-bottom: 20px;
        }
        .screenshot {
            max-width: 100%;
            border: 1px solid #ddd;
            margin-top: 10px;
        }
        .selector-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
        }
        .selector-button {
            background-color: #2196F3;
        }
        .url-list {
            height: 300px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 10px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Boots 5-Star Skincare Products Analyzer</h1>
        
        <div class="control-panel">
            <h2>Navigation</h2>
            <button id="loadPage">Load 5-Star Products Page</button>
            <button id="scrollPage">Scroll Page</button>
            <button id="acceptCookies">Accept Cookies</button>
            <button id="takeScreenshot">Take Screenshot</button>
        </div>
        
        <div class="control-panel">
            <h2>Selector Testing</h2>
            <div class="selector-list">
                <button class="selector-button" data-selector=".product-grid .product-tile">product-grid .product-tile</button>
                <button class="selector-button" data-selector=".product-list-item">product-list-item</button>
                <button class="selector-button" data-selector=".product-card">product-card</button>
                <button class="selector-button" data-selector=".product">product</button>
                <button class="selector-button" data-selector="[data-test='product-tile']">data-test="product-tile"</button>
                <button class="selector-button" data-selector=".product-grid-item">product-grid-item</button>
                <button class="selector-button" data-selector=".product-item">product-item</button>
                <button class="selector-button" data-selector=".plp-grid__item">plp-grid__item</button>
                <button class="selector-button" data-selector=".product-list__item">product-list__item</button>
                <button class="selector-button" data-selector=".product-tile">product-tile</button>
            </div>
            <input type="text" id="customSelector" placeholder="Enter custom CSS selector">
            <button id="testCustomSelector">Test Custom Selector</button>
        </div>
        
        <div class="results">
            <h2>Log</h2>
            <div class="log" id="log"></div>
            
            <h2>Product URLs Found</h2>
            <div class="url-list" id="urlList"></div>
            
            <h2>Screenshot</h2>
            <div id="screenshotContainer"></div>
        </div>
    </div>
    
    <script>
        // Function to add log message
        function addLog(message) {
            const log = document.getElementById('log');
            log.innerHTML += message + '<br>';
            log.scrollTop = log.scrollHeight;
        }
        
        // Function to display screenshot
        function displayScreenshot(base64Image) {
            const container = document.getElementById('screenshotContainer');
            container.innerHTML = `<img class="screenshot" src="data:image/png;base64,${base64Image}">`;
        }
        
        // Function to display URLs
        function displayUrls(urls) {
            const urlList = document.getElementById('urlList');
            urlList.innerHTML = '';
            urls.forEach(url => {
                urlList.innerHTML += `<div>${url}</div>`;
            });
        }
        
        // Load page button
        document.getElementById('loadPage').addEventListener('click', () => {
            addLog('Loading 5-star products page...');
            fetch('/load_page')
                .then(response => response.json())
                .then(data => {
                    addLog(data.message);
                    if (data.screenshot) {
                        displayScreenshot(data.screenshot);
                    }
                })
                .catch(error => {
                    addLog('Error: ' + error);
                });
        });
        
        // Scroll page button
        document.getElementById('scrollPage').addEventListener('click', () => {
            addLog('Scrolling page...');
            fetch('/scroll_page')
                .then(response => response.json())
                .then(data => {
                    addLog(data.message);
                    if (data.screenshot) {
                        displayScreenshot(data.screenshot);
                    }
                })
                .catch(error => {
                    addLog('Error: ' + error);
                });
        });
        
        // Accept cookies button
        document.getElementById('acceptCookies').addEventListener('click', () => {
            addLog('Accepting cookies...');
            fetch('/accept_cookies')
                .then(response => response.json())
                .then(data => {
                    addLog(data.message);
                })
                .catch(error => {
                    addLog('Error: ' + error);
                });
        });
        
        // Take screenshot button
        document.getElementById('takeScreenshot').addEventListener('click', () => {
            addLog('Taking screenshot...');
            fetch('/take_screenshot')
                .then(response => response.json())
                .then(data => {
                    addLog(data.message);
                    if (data.screenshot) {
                        displayScreenshot(data.screenshot);
                    }
                })
                .catch(error => {
                    addLog('Error: ' + error);
                });
        });
        
        // Selector buttons
        document.querySelectorAll('.selector-button').forEach(button => {
            button.addEventListener('click', () => {
                const selector = button.getAttribute('data-selector');
                addLog(`Testing selector: ${selector}`);
                fetch('/test_selector', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({selector: selector}),
                })
                .then(response => response.json())
                .then(data => {
                    addLog(data.message);
                    if (data.urls) {
                        displayUrls(data.urls);
                    }
                    if (data.screenshot) {
                        displayScreenshot(data.screenshot);
                    }
                })
                .catch(error => {
                    addLog('Error: ' + error);
                });
            });
        });
        
        // Custom selector button
        document.getElementById('testCustomSelector').addEventListener('click', () => {
            const selector = document.getElementById('customSelector').value;
            if (!selector) {
                addLog('Please enter a CSS selector');
                return;
            }
            
            addLog(`Testing custom selector: ${selector}`);
            fetch('/test_selector', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({selector: selector}),
            })
            .then(response => response.json())
            .then(data => {
                addLog(data.message);
                if (data.urls) {
                    displayUrls(data.urls);
                }
                if (data.screenshot) {
                    displayScreenshot(data.screenshot);
                }
            })
            .catch(error => {
                addLog('Error: ' + error);
            });
        });
    </script>
</body>
</html>
"""

# Global browser instance
browser = None
page = None

def setup_browser(headless=False):
    """Set up the browser."""
    global browser, page
    
    logger.info("Setting up browser")
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        viewport={"width": 1280, "height": 800}
    )
    page = context.new_page()
    logger.info("Browser set up successfully")

def take_screenshot():
    """Take a screenshot of the current page."""
    if not page:
        return None
    
    os.makedirs("screenshots", exist_ok=True)
    screenshot_path = f"screenshots/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    page.screenshot(path=screenshot_path)
    
    with open(screenshot_path, "rb") as f:
        import base64
        return base64.b64encode(f.read()).decode('utf-8')

@app.route('/')
def index():
    """Render the main page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/load_page')
def load_page():
    """Load the 5-star products page."""
    global page
    
    if not page:
        return jsonify({"message": "Browser not initialized. Please restart the server."})
    
    try:
        logger.info(f"Navigating to {FIVE_STAR_URL}")
        page.goto(FIVE_STAR_URL, wait_until="networkidle")
        screenshot = take_screenshot()
        return jsonify({
            "message": f"Successfully loaded page: {FIVE_STAR_URL}",
            "screenshot": screenshot
        })
    except Exception as e:
        logger.error(f"Error loading page: {str(e)}")
        return jsonify({"message": f"Error loading page: {str(e)}"})

@app.route('/scroll_page')
def scroll_page():
    """Scroll the page to load more products."""
    global page
    
    if not page:
        return jsonify({"message": "Browser not initialized. Please restart the server."})
    
    try:
        logger.info("Scrolling page")
        # Scroll to bottom
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        
        # Scroll back to top
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)
        
        screenshot = take_screenshot()
        return jsonify({
            "message": "Successfully scrolled page",
            "screenshot": screenshot
        })
    except Exception as e:
        logger.error(f"Error scrolling page: {str(e)}")
        return jsonify({"message": f"Error scrolling page: {str(e)}"})

@app.route('/accept_cookies')
def accept_cookies():
    """Accept cookies if the dialog is present."""
    global page
    
    if not page:
        return jsonify({"message": "Browser not initialized. Please restart the server."})
    
    try:
        logger.info("Checking for cookie consent dialog")
        consent_button = page.query_selector('button#onetrust-accept-btn-handler')
        if consent_button:
            logger.info("Found cookie consent dialog, accepting cookies")
            consent_button.click()
            page.wait_for_timeout(2000)
            return jsonify({"message": "Successfully accepted cookies"})
        else:
            return jsonify({"message": "No cookie consent dialog found"})
    except Exception as e:
        logger.error(f"Error accepting cookies: {str(e)}")
        return jsonify({"message": f"Error accepting cookies: {str(e)}"})

@app.route('/take_screenshot')
def api_take_screenshot():
    """Take a screenshot of the current page."""
    global page
    
    if not page:
        return jsonify({"message": "Browser not initialized. Please restart the server."})
    
    try:
        screenshot = take_screenshot()
        return jsonify({
            "message": "Successfully took screenshot",
            "screenshot": screenshot
        })
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        return jsonify({"message": f"Error taking screenshot: {str(e)}"})

@app.route('/test_selector', methods=['POST'])
def test_selector():
    """Test a CSS selector on the current page."""
    global page
    
    if not page:
        return jsonify({"message": "Browser not initialized. Please restart the server."})
    
    try:
        data = request.json
        selector = data.get('selector')
        
        if not selector:
            return jsonify({"message": "No selector provided"})
        
        logger.info(f"Testing selector: {selector}")
        
        # Find elements matching the selector
        elements = page.query_selector_all(selector)
        
        if not elements:
            return jsonify({"message": f"No elements found with selector: {selector}"})
        
        logger.info(f"Found {len(elements)} elements with selector: {selector}")
        
        # Highlight the elements
        page.evaluate(f"""
            const elements = document.querySelectorAll('{selector}');
            elements.forEach(el => {{
                el.style.border = '2px solid red';
            }});
        """)
        
        # Take screenshot with highlighted elements
        screenshot = take_screenshot()
        
        # Extract URLs from elements
        urls = []
        for element in elements:
            # Try to find an anchor tag within the element or the element itself if it's an anchor
            if element.get_attribute('tagName') == 'A':
                href = element.get_attribute('href')
                if href:
                    urls.append(href)
            else:
                # Look for anchor tags within the element
                anchors = element.query_selector_all('a')
                for anchor in anchors:
                    href = anchor.get_attribute('href')
                    if href:
                        urls.append(href)
        
        # Remove highlighting
        page.evaluate(f"""
            const elements = document.querySelectorAll('{selector}');
            elements.forEach(el => {{
                el.style.border = '';
            }});
        """)
        
        return jsonify({
            "message": f"Found {len(elements)} elements with selector: {selector}",
            "urls": urls,
            "screenshot": screenshot
        })
    except Exception as e:
        logger.error(f"Error testing selector: {str(e)}")
        return jsonify({"message": f"Error testing selector: {str(e)}"})

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Boots Browser Server")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    try:
        # Set up browser
        setup_browser(headless=args.headless)
        
        # Run Flask app
        app.run(debug=True, port=args.port)
    except Exception as e:
        logger.error(f"Error running server: {str(e)}")
        sys.exit(1)
    finally:
        # Close browser
        if browser:
            browser.close()
