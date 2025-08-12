#!/usr/bin/env python3
"""
Test script for the CoinCodex scraper
Run this to test the scraper locally before pushing to GitHub
"""

import subprocess
import sys
import os

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

if __name__ == "__main__":
    success = test_scraper()
    if success:
        print("\n🎉 All tests passed! Ready to deploy.")
    else:
        print("\n💥 Tests failed. Check the errors above.")
        sys.exit(1)