#!/usr/bin/env python3
"""
Test script for the CoinCodex scraper
Run this to test the scraper locally before pushing to GitHub
"""

import subprocess
import sys
import os
import unittest
from unittest.mock import patch, mock_open
from datetime import datetime

def test_scraper():
    """Test the scraper functionality"""
    print("Testing CoinCodex scraper...")
    
    try:
        # Check if requirements are installed
        import selenium
        print("✅ Selenium installed")
    except ImportError:
        print("❌ Selenium not found. Install with: pip install -r requirements.txt")
        return False
    
    # Run the scraper
    try:
        print("Running scraper...")
        result = subprocess.run([sys.executable, "scraper.py"], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Scraper ran successfully")
            print("Output:", result.stdout)
            
            # Check if README was updated
            if os.path.exists("README.md"):
                print("✅ README.md exists")
                with open("README.md", "r", encoding="utf-8") as f:
                    content = f.read()
                    if "Last updated:" in content:
                        print("✅ README.md appears to be updated")
                        
                        # Check for new features
                        if "Short-Term" in content and "Price Targets" in content:
                            print("✅ Short-term price targets found")
                        if "Prediction Accuracy Analysis" in content:
                            print("✅ Prediction accuracy section found")
                        if "Market Summary" in content:
                            print("✅ Market summary tables found")
                        
                        return True
            
        else:
            print("❌ Scraper failed")
            print("Error:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Scraper timed out")
        return False
    except Exception as e:
        print(f"❌ Error running scraper: {e}")
        return False

class TestScraperFunctions(unittest.TestCase):
    """Unit tests for scraper functions"""
    
    def setUp(self):
        # Import scraper functions for testing
        sys.path.append('.')
        self.scraper = __import__('scraper')
    
    def test_parse_old_readme_predictions(self):
        """Test parsing old README predictions"""
        mock_readme_content = """
### Ethereum (ETH)

#### Short-Term Ethereum (ETH) Price Targets
| Date | Prediction | Potential ROI |
| -----| -----------| --------------|
| Aug 14, 2025 | **$ 4,620.60** | 0.16% |
| Aug 15, 2025 | **$ 4,670.85** | 1.24% |

### Bitcoin (BTC)

#### Short-Term Bitcoin (BTC) Price Targets
| Date | Prediction | Potential ROI |
| -----| -----------| --------------|
| Aug 14, 2025 | **$ 121,075** | 1.02% |
"""
        
        with patch('builtins.open', mock_open(read_data=mock_readme_content)):
            with patch('os.path.exists', return_value=True):
                with patch('datetime.datetime') as mock_datetime:
                    mock_datetime.now.return_value.strftime.return_value = "Aug 14, 2025"
                    
                    predictions = self.scraper.parse_old_readme_predictions()
                    
                    self.assertIn('Ethereum (ETH)', predictions)
                    self.assertIn('Bitcoin (BTC)', predictions)
                    self.assertEqual(predictions['Ethereum (ETH)'], 4620.60)
                    self.assertEqual(predictions['Bitcoin (BTC)'], 121075.0)
    
    def test_calculate_prediction_accuracy(self):
        """Test prediction accuracy calculation"""
        old_predictions = {
            'Ethereum (ETH)': 4620.60,
            'Bitcoin (BTC)': 121075.0
        }
        
        crypto_data = {
            'Ethereum (ETH)': {'current_price': '4621.00'},
            'Bitcoin (BTC)': {'current_price': '121,080.00'}
        }
        
        accuracy_results = self.scraper.calculate_prediction_accuracy(old_predictions, crypto_data)
        
        self.assertIn('Ethereum (ETH)', accuracy_results)
        self.assertIn('Bitcoin (BTC)', accuracy_results)
        
        # Check Ethereum accuracy (very close prediction)
        eth_result = accuracy_results['Ethereum (ETH)']
        self.assertAlmostEqual(eth_result['predicted_price'], 4620.60)
        self.assertAlmostEqual(eth_result['actual_price'], 4621.00)
        self.assertGreater(eth_result['accuracy'], 99)  # Should be very accurate
        
        # Check Bitcoin accuracy
        btc_result = accuracy_results['Bitcoin (BTC)']
        self.assertAlmostEqual(btc_result['predicted_price'], 121075.0)
        self.assertAlmostEqual(btc_result['actual_price'], 121080.0)
        self.assertGreater(btc_result['accuracy'], 99)  # Should be very accurate
    
    def test_clean_text(self):
        """Test text cleaning function"""
        dirty_text = "   Price: $4,620.60  \n  &amp; more   "
        clean = self.scraper.clean_text(dirty_text)
        
        self.assertEqual(clean, "Price: $4,620.60 & more")
    
    def test_extract_market_data(self):
        """Test market data extraction"""
        sample_text = "According to our current Ethereum price prediction, the price is predicted to rise by 10.93% and reach $ 5,125.77 by September 12, 2025. The sentiment is Bullish while the Fear & Greed Index is showing 73 (Greed). Ethereum recorded 20/30 (67%) green days with 8.33% price volatility."
        
        current_price = "4621.00"
        market_data = self.scraper.extract_market_data(sample_text, current_price)
        
        self.assertEqual(market_data['current_price'], "4621.00")
        self.assertIn('price_prediction', market_data)
        self.assertIn('sentiment', market_data)
        self.assertEqual(market_data['sentiment'], 'Bullish')

def run_unit_tests():
    """Run unit tests for scraper functions"""
    print("\nRunning unit tests...")
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestScraperFunctions)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("✅ All unit tests passed!")
        return True
    else:
        print("❌ Some unit tests failed!")
        return False

if __name__ == "__main__":
    # Run integration test
    success = test_scraper()
    
    # Run unit tests
    unit_success = run_unit_tests()
    
    if success and unit_success:
        print("\n🎉 All tests passed! Ready to deploy.")
    else:
        print("\n💥 Tests failed. Check the errors above.")
        sys.exit(1)