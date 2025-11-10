"""Configuration for scraper to work in different environments"""
import os

def get_chrome_options():
    """Get Chrome options based on environment"""
    from selenium.webdriver.chrome.options import Options

    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    # For Render/production environments
    if os.getenv('RENDER') or os.path.exists('/usr/bin/chromium'):
        chrome_options.binary_location = '/usr/bin/chromium'

    return chrome_options
