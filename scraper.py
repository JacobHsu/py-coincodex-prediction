#!/usr/bin/env python3
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import os

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def clean_text(text):
    """Clean and format text, handling colorful text elements"""
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Handle common HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    
    return text

def extract_price_predictions(driver, crypto_name):
    """Extract price prediction content from the page"""
    predictions = []
    
    try:
        # Wait for page to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Wait a bit more for dynamic content
        time.sleep(5)
        
        # Find all paragraph elements with the specific attributes
        paragraphs = driver.find_elements(By.CSS_SELECTOR, "p[_ngcontent-coincodex][apprenderdynamiccomponents]")
        
        for p in paragraphs:
            text = clean_text(p.text)
            if text and len(text) > 50:  # Only include substantial content
                predictions.append(text)
        
        # If no specific paragraphs found, look for general prediction content
        if not predictions:
            # Look for divs or sections containing prediction text
            content_elements = driver.find_elements(By.XPATH, "//p[contains(text(), 'prediction') or contains(text(), 'price') or contains(text(), '$') or contains(text(), 'forecast')]")
            
            for element in content_elements:
                text = clean_text(element.text)
                if text and len(text) > 50:
                    predictions.append(text)
        
        # Remove duplicates while preserving order
        unique_predictions = []
        seen = set()
        for pred in predictions:
            if pred not in seen:
                unique_predictions.append(pred)
                seen.add(pred)
        
        # Only return first 2 predictions as requested
        return unique_predictions[:2]
    
    except Exception as e:
        print(f"Error extracting predictions for {crypto_name}: {e}")
        return []

def extract_price_targets_table(driver, crypto_name):
    """Extract Short-Term Price Targets table data"""
    try:
        # Wait for table to load
        time.sleep(3)
        
        # Look for table with headers that match price targets
        table_selectors = [
            "table",
            ".table",
            ".price-targets",
            ".predictions-table",
            "[class*='table']",
            ".data-table"
        ]
        
        price_targets = []
        
        for selector in table_selectors:
            try:
                tables = driver.find_elements(By.CSS_SELECTOR, selector)
                for table in tables:
                    # Check if this table contains price target data
                    table_text = table.text.lower()
                    if any(keyword in table_text for keyword in ['target', 'price', 'date', 'change', '%']):
                        # Try to extract table headers and data
                        headers = []
                        rows_data = []
                        
                        # Get headers
                        header_elements = table.find_elements(By.CSS_SELECTOR, "th, thead td")
                        if header_elements:
                            headers = [th.text.strip() for th in header_elements if th.text.strip()]
                        
                        # Get data rows
                        row_elements = table.find_elements(By.CSS_SELECTOR, "tr")
                        for row in row_elements:
                            cells = row.find_elements(By.CSS_SELECTOR, "td")
                            if cells and len(cells) >= 2:  # At least 2 columns
                                row_data = [cell.text.strip() for cell in cells]
                                # Filter rows that contain price or percentage data
                                row_text = ' '.join(row_data).lower()
                                if any(indicator in row_text for indicator in ['$', '%', 'price', 'target']):
                                    rows_data.append(row_data)
                        
                        if headers and rows_data:
                            price_targets.append({
                                'headers': headers,
                                'rows': rows_data[:5]  # Limit to first 5 rows
                            })
                            print(f"Found price targets table for {crypto_name} with {len(rows_data)} rows")
                            return price_targets[0]  # Return first valid table
                            
            except Exception as e:
                continue
        
        # Alternative approach: Look for specific text patterns that indicate price targets
        try:
            # Look for text containing date and price patterns
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'target') or contains(text(), 'Target')]")
            for element in elements:
                parent = element.find_element(By.XPATH, "./..")
                text = parent.text
                if '$' in text and any(month in text for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                    # Extract structured data from text
                    lines = text.split('\n')
                    target_data = []
                    for line in lines:
                        if '$' in line and any(month in line for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                            target_data.append(line.strip())
                    
                    if target_data:
                        return {
                            'headers': ['Date', 'Price Target'],
                            'rows': [[item.split()[0] if item.split() else '', item] for item in target_data[:5]]
                        }
        except:
            pass
        
        print(f"Could not find price targets table for {crypto_name}")
        return None
        
    except Exception as e:
        print(f"Error extracting price targets table for {crypto_name}: {e}")
        return None

def extract_current_price(driver, crypto_name):
    """Extract current price from the webpage"""
    try:
        # Wait for price elements to load
        time.sleep(2)
        
        # More comprehensive selectors for current price on CoinCodex
        price_selectors = [
            # Common price display elements
            ".price",
            ".current-price", 
            ".price-value",
            ".coin-price",
            "[data-price]",
            "[data-testid='price']",
            # Header price areas
            "h1 + div .price",
            ".header-price",
            ".coin-header .price",
            # Table or stat areas that might contain current price
            ".stats .price",
            ".market-stats .price",
            ".price-stats .value",
            # Generic large price displays
            ".large-price",
            ".main-price",
            # Look for elements with price-like classes
            "[class*='price']",
            "[class*='Price']"
        ]
        
        for selector in price_selectors:
            try:
                price_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in price_elements:
                    price_text = element.text.strip()
                    # Look for substantial dollar amounts (adjust for Gold vs Crypto)
                    if "Gold" in crypto_name:
                        # Gold prices are usually $1000-$3000 per ounce
                        price_match = re.search(r'\$[\d,]{3,}\.?\d*', price_text)
                    else:
                        # Crypto prices can be $4000+ 
                        price_match = re.search(r'\$[\d,]{4,}\.?\d*', price_text)
                    
                    if price_match:
                        print(f"Found current price for {crypto_name} using selector {selector}: {price_match.group(0)}")
                        return price_match.group(0)
            except:
                continue
        
        # Try looking in page title or header areas
        try:
            header_elements = driver.find_elements(By.CSS_SELECTOR, "h1, h2, .title, .header")
            for element in header_elements:
                text = element.text.strip()
                if "Gold" in crypto_name:
                    price_match = re.search(r'\$[\d,]{3,}\.?\d*', text)
                else:
                    price_match = re.search(r'\$[\d,]{4,}\.?\d*', text)
                if price_match:
                    print(f"Found current price for {crypto_name} in header: {price_match.group(0)}")
                    return price_match.group(0)
        except:
            pass
        
        # Fallback: scan all text on page for price patterns
        try:
            # Get all elements that might contain price information
            all_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '$') and string-length(text()) < 50]")
            
            for element in all_elements:
                text = element.text.strip()
                # Look for price patterns in shorter text elements
                if "Gold" in crypto_name:
                    price_match = re.search(r'\$[\d,]{3,}\.?\d*', text)
                else:
                    price_match = re.search(r'\$[\d,]{4,}\.?\d*', text)
                if price_match and not any(word in text.lower() for word in ['prediction', 'target', 'forecast', 'reach', 'expected']):
                    print(f"Found potential current price for {crypto_name}: {price_match.group(0)} in text: {text[:50]}...")
                    return price_match.group(0)
        except:
            pass
        
        print(f"Could not find current price for {crypto_name}")
        return None
        
    except Exception as e:
        print(f"Error extracting current price for {crypto_name}: {e}")
        return None

def extract_market_data(text, current_price=None):
    """Extract market data for the table from prediction text"""
    data = {}
    
    # Use provided current price or try to calculate from prediction
    if current_price:
        data['current_price'] = current_price.replace('$', '').replace(',', '')
    else:
        # Try to calculate current price from prediction and percentage
        price_match = re.search(r'\$\s?([\d,]+\.?\d*)', text)
        percent_match = re.search(r'([-+]?\d+\.\d+)%', text)
        
        if price_match and percent_match:
            target_price = float(price_match.group(1).replace(',', ''))
            percent_change = float(percent_match.group(1))
            
            # Calculate current price: target = current * (1 + percent_change/100)
            current_calc = target_price / (1 + percent_change/100)
            data['current_price'] = f"{current_calc:,.0f}"
    
    # Extract price prediction
    price_match = re.search(r'\$\s?([\d,]+\.?\d*)', text)
    if price_match:
        data['price_prediction'] = f"${price_match.group(1)}"
    
    # Extract percentage change
    percent_match = re.search(r'([-+]?\d+\.\d+)%', text)
    if percent_match:
        data['percentage_change'] = f"{percent_match.group(1)}%"
    
    # Extract green days (different formats for crypto vs gold)
    green_days_match = re.search(r'(\d+/\d+\s*\(\d+%\))\s*green days', text)
    if green_days_match:
        data['green_days'] = green_days_match.group(1)
    else:
        # Try gold format: "Gold recorded 43 green days"
        gold_days_match = re.search(r'recorded (\d+) green days', text)
        if gold_days_match:
            data['green_days'] = f"{gold_days_match.group(1)} days"
    
    # Extract sentiment (multiple formats)
    if 'Bullish' in text:
        data['sentiment'] = 'Bullish'
    elif 'Bearish' in text:
        data['sentiment'] = 'Bearish'
    elif 'sentiment investor is Neutral' in text or 'sentiment is Neutral' in text:
        data['sentiment'] = 'Neutral'
    
    # Extract Fear & Greed Index
    fear_greed_match = re.search(r'(\d+\s*\([^)]+\))', text)
    if fear_greed_match:
        data['fear_greed'] = fear_greed_match.group(1)
    
    # Extract volatility
    volatility_match = re.search(r'(\d+\.\d+)%\s*price volatility', text)
    if volatility_match:
        data['volatility'] = f"{volatility_match.group(1)}%"
    
    return data

def format_prediction_text(text):
    """Format prediction text with bold markdown for important values"""
    # Make percentages bold
    text = re.sub(r'([-+]?\d+\.\d+%)', r'**\1**', text)
    
    # Make dollar amounts bold
    text = re.sub(r'(\$\s?[\d,]+\.?\d*)', r'**\1**', text)
    
    # Make sentiment indicators bold
    text = re.sub(r'\b(Bullish|Bearish)\b', r'**\1**', text)
    
    # Make Fear & Greed Index bold
    text = re.sub(r'(\d+\s*\([^)]+\))', r'**\1**', text)
    
    # Make green days ratio bold
    text = re.sub(r'(\d+/\d+\s*\(\d+%\))', r'**\1**', text)
    
    # Make buy/sell recommendations bold
    text = re.sub(r'\b(buy|sell)\s+(Bitcoin|Ethereum|BTC|ETH)\b', r'**\1 \2**', text, flags=re.IGNORECASE)
    
    return text

def update_readme(crypto_data):
    """Update README.md with the scraped predictions for multiple cryptocurrencies"""
    current_time = datetime.now().strftime("%Y-%m-%d")
    
    readme_content = f"""# Cryptocurrency & Asset Price Predictions

**Sources:** 
- [CoinCodex Ethereum Price Prediction](https://coincodex.com/crypto/ethereum/price-prediction/)
- [CoinCodex Bitcoin Price Prediction](https://coincodex.com/crypto/bitcoin/price-prediction/)
- [CoinCodex Ripple Price Prediction](https://coincodex.com/crypto/ripple/price-prediction/)
- [CoinCodex Gold Forecast](https://coincodex.com/precious-metal/gold/forecast/)

*Last updated: {current_time}*

## Current Price Predictions from CoinCodex

"""
    
    for crypto_name, crypto_info in crypto_data.items():
        readme_content += f"### {crypto_name}\n\n"
        
        # Handle both old and new data structure
        if isinstance(crypto_info, dict) and 'predictions' in crypto_info:
            predictions = crypto_info['predictions']
            current_price = crypto_info['current_price']
            price_targets = crypto_info.get('price_targets')
        else:
            # Backwards compatibility
            predictions = crypto_info
            current_price = None
            price_targets = None
        
        if predictions:
            # Extract market data from first prediction for table
            market_data = extract_market_data(predictions[0], current_price) if predictions else {}
            
            # Create market summary table
            readme_content += "#### Market Summary\n"
            readme_content += "| Current Price | Price Prediction | Green Days | Sentiment | Fear & Greed Index | Volatility |\n"
            readme_content += "|---------------|------------------|------------|-----------|-------------------|------------|\n"
            readme_content += f"| ${market_data.get('current_price', 'N/A')} | **{market_data.get('price_prediction', 'N/A')}** | **{market_data.get('green_days', 'N/A')}** | **{market_data.get('sentiment', 'N/A')}** | **{market_data.get('fear_greed', 'N/A')}** | **{market_data.get('volatility', 'N/A')}** |\n\n"
            
            # Add price targets table if available
            if price_targets and price_targets.get('headers') and price_targets.get('rows'):
                readme_content += f"#### Short-Term {crypto_name} Price Targets\n"
                
                # Create table headers
                headers = price_targets['headers']
                readme_content += "| " + " | ".join(headers) + " |\n"
                readme_content += "|" + "|".join([" " + "-"*(len(h)+1) for h in headers]) + "|\n"
                
                # Add table rows
                for row in price_targets['rows']:
                    if len(row) == len(headers):
                        formatted_row = []
                        for cell in row:
                            # Clean up cell content
                            cleaned_cell = cell.replace('Buy', '').replace('Short', '').strip()
                            
                            # Bold only price values (with $), but not percentages
                            if '$' in cleaned_cell:
                                formatted_row.append(f"**{cleaned_cell}**")
                            else:
                                formatted_row.append(cleaned_cell)
                        readme_content += "| " + " | ".join(formatted_row) + " |\n"
                readme_content += "\n"
            
            # Add formatted predictions (only first 2)
            readme_content += "#### Analysis\n"
            for prediction in predictions[:2]:
                formatted_text = format_prediction_text(prediction)
                readme_content += f"{formatted_text}\n\n"
        else:
            readme_content += "No predictions available at this time.\n\n"
        
        readme_content += "---\n\n"
    
    readme_content += """---

**About**

This data is automatically scraped from CoinCodex using automated tools for cryptocurrency price analysis and prediction tracking.

**Disclaimer**: This information is for educational purposes only and should not be considered as financial advice. Always do your own research before making investment decisions.
"""
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    total_predictions = sum(
        len(crypto_info['predictions']) if isinstance(crypto_info, dict) and 'predictions' in crypto_info 
        else len(crypto_info) if isinstance(crypto_info, list) else 0 
        for crypto_info in crypto_data.values()
    )
    
    total_price_targets = sum(
        len(crypto_info.get('price_targets', {}).get('rows', [])) if isinstance(crypto_info, dict) and crypto_info.get('price_targets') 
        else 0 
        for crypto_info in crypto_data.values()
    )
    
    print(f"README.md updated with {total_predictions} total predictions and {total_price_targets} price targets")

def main():
    print("Starting CoinCodex multi-cryptocurrency price prediction scraper...")
    
    # Define cryptocurrencies and assets to scrape
    cryptos = {
        "Ethereum (ETH)": "https://coincodex.com/crypto/ethereum/price-prediction/",
        "Bitcoin (BTC)": "https://coincodex.com/crypto/bitcoin/price-prediction/",
        "Ripple (XRP)": "https://coincodex.com/crypto/ripple/price-prediction/",
        "Gold": "https://coincodex.com/precious-metal/gold/forecast/"
    }
    
    crypto_data = {}
    driver = None
    
    try:
        driver = setup_driver()
        print("WebDriver initialized")
        
        for crypto_name, url in cryptos.items():
            print(f"Scraping {crypto_name} from {url}")
            
            try:
                driver.get(url)
                
                # Extract current price first
                current_price = extract_current_price(driver, crypto_name)
                print(f"Current price for {crypto_name}: {current_price}")
                
                # Extract predictions
                predictions = extract_price_predictions(driver, crypto_name)
                
                # Extract price targets table
                price_targets = extract_price_targets_table(driver, crypto_name)
                
                # Store all data
                crypto_data[crypto_name] = {
                    'predictions': predictions,
                    'current_price': current_price,
                    'price_targets': price_targets
                }
                print(f"Found {len(predictions)} predictions for {crypto_name}")
                
                # Wait between requests to be respectful
                time.sleep(3)
                
            except Exception as e:
                print(f"Error scraping {crypto_name}: {e}")
                crypto_data[crypto_name] = {'predictions': [], 'current_price': None, 'price_targets': None}
        
        # Update README with all collected data
        update_readme(crypto_data)
        print("README.md has been updated successfully with multi-crypto data")
        
    except Exception as e:
        print(f"Error during scraping: {e}")
        # Create a basic README even if scraping fails
        update_readme({"Ethereum (ETH)": {'predictions': [], 'current_price': None, 'price_targets': None}, 
                      "Bitcoin (BTC)": {'predictions': [], 'current_price': None, 'price_targets': None},
                      "Ripple (XRP)": {'predictions': [], 'current_price': None, 'price_targets': None},
                      "Gold": {'predictions': [], 'current_price': None, 'price_targets': None}})
        
    finally:
        if driver:
            driver.quit()
            print("WebDriver closed")

if __name__ == "__main__":
    main()