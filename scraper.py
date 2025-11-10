import requests
import gzip
import time
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET
from urllib.parse import urlparse
import csv
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class ClinicScraper:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.stop_requested = False
        self.driver = None

    def setup_driver(self):
        """Initialize Selenium WebDriver"""
        if self.driver is None:
            self.log('Setting up headless browser...')

            try:
                from scraper_config import get_chrome_options
                chrome_options = get_chrome_options()
            except ImportError:
                # Fallback to default options if config not available
                chrome_options = Options()
                chrome_options.add_argument('--headless=new')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--window-size=1920,1080')
                chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                self.log('Browser ready')
            except Exception as e:
                self.log(f'Error setting up browser: {str(e)}', 'error')
                raise

    def close_driver(self):
        """Close Selenium WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def log(self, message, level='info'):
        """Send log message via callback"""
        if self.progress_callback:
            self.progress_callback({
                'type': 'log',
                'level': level,
                'message': message
            })

    def update_progress(self, current, total, status=''):
        """Send progress update via callback"""
        if self.progress_callback:
            self.progress_callback({
                'type': 'progress',
                'current': current,
                'total': total,
                'status': status
            })

    def stop(self):
        """Request scraper to stop"""
        self.stop_requested = True

    def get_sitemap_urls(self, sitemap_url):
        """Download and parse sitemap to get clinic URLs"""
        self.log('Downloading sitemap index...')

        try:
            response = self.session.get(sitemap_url, timeout=30)
            response.raise_for_status()

            # Decompress gzip content
            decompressed = gzip.decompress(response.content)

            # Parse XML
            root = ET.fromstring(decompressed)

            # Extract URLs (handle XML namespace)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            # Check if this is a sitemap index
            sub_sitemaps = root.findall('.//ns:sitemap/ns:loc', namespace)

            all_urls = []

            if sub_sitemaps:
                # This is a sitemap index - download each sub-sitemap
                self.log(f'Found sitemap index with {len(sub_sitemaps)} sub-sitemaps')

                for i, sitemap_elem in enumerate(sub_sitemaps, 1):
                    if self.stop_requested:
                        break

                    sub_sitemap_url = sitemap_elem.text
                    self.log(f'Downloading sub-sitemap {i}/{len(sub_sitemaps)}...')

                    try:
                        sub_response = self.session.get(sub_sitemap_url, timeout=30)
                        sub_response.raise_for_status()
                        sub_decompressed = gzip.decompress(sub_response.content)
                        sub_root = ET.fromstring(sub_decompressed)

                        # Extract URLs from sub-sitemap
                        for url_elem in sub_root.findall('.//ns:url/ns:loc', namespace):
                            url = url_elem.text
                            # Filter for clinic pages only (main clinic page, not individual doctor pages)
                            if '/medical-centres/' in url and '/doctors' in url and url.endswith('/doctors'):
                                all_urls.append(url)

                        self.log(f'Sub-sitemap {i}: Found {len(all_urls)} total clinic URLs so far')

                    except Exception as e:
                        self.log(f'Error fetching sub-sitemap {i}: {str(e)}', 'warning')
                        continue
            else:
                # Single sitemap - extract URLs directly
                for url_elem in root.findall('.//ns:url/ns:loc', namespace):
                    url = url_elem.text
                    if '/medical-centres/' in url and '/doctors' in url and url.endswith('/doctors'):
                        all_urls.append(url)

            self.log(f'Found {len(all_urls)} total clinic URLs')
            return all_urls

        except Exception as e:
            self.log(f'Error fetching sitemap: {str(e)}', 'error')
            return []

    def extract_clinic_data(self, url, fields):
        """Extract clinic information from a single page using Selenium"""
        try:
            # Load page with Selenium
            self.driver.get(url)

            # Wait for page to load - wait for practice name to appear
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

            # Give extra time for dynamic content
            time.sleep(2)

            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'lxml')

            data = {'url': url}

            # Extract name
            if 'name' in fields:
                name = None
                # Try h1 first, then fall back to other selectors
                h1 = soup.find('h1')
                if h1:
                    name = h1.get_text(strip=True)
                    # If it's the generic HotDoc title, try other methods
                    if 'Find a Doctor' in name or 'HotDoc' in name:
                        # Try getting from URL slug as fallback
                        url_parts = url.split('/')
                        if len(url_parts) >= 5:
                            slug = url_parts[-2] if url_parts[-1] == 'doctors' else url_parts[-1]
                            name = slug.replace('_', ' ').replace('-', ' ').title()
                data['name'] = name or 'N/A'

            # Extract address
            if 'address' in fields:
                address = None
                # Look for address in various places
                address_elem = (
                    soup.find(attrs={'itemprop': 'address'}) or
                    soup.find('address') or
                    soup.find(class_=re.compile(r'address', re.I)) or
                    soup.find(attrs={'data-test-id': re.compile(r'address', re.I)})
                )
                if address_elem:
                    address = address_elem.get_text(strip=True)
                    address = ' '.join(address.split())
                data['address'] = address or 'N/A'

            # Extract phone
            if 'phone' in fields:
                phone = None
                # Try multiple selectors
                phone_elem = (
                    soup.find(attrs={'itemprop': 'telephone'}) or
                    soup.find('a', href=re.compile(r'tel:')) or
                    soup.find(class_=re.compile(r'phone', re.I)) or
                    soup.find(attrs={'data-test-id': re.compile(r'phone', re.I)})
                )
                if phone_elem:
                    if phone_elem.name == 'a' and phone_elem.get('href', '').startswith('tel:'):
                        phone = phone_elem.get('href').replace('tel:', '').strip()
                    else:
                        phone = phone_elem.get_text(strip=True)
                    # Clean phone number
                    phone = re.sub(r'[^\d\s\+\(\)-]', '', phone).strip()
                data['phone'] = phone or 'N/A'

            # Extract website
            if 'website' in fields:
                website = None

                # First try: Look for ClinicContactDetails-contact-link (most reliable)
                contact_links = soup.find_all('a', class_='ClinicContactDetails-contact-link')
                for link in contact_links:
                    href = link.get('href', '')
                    # Filter out maps, social media, and HotDoc links
                    if href and href.startswith('http') and \
                       'hotdoc.com' not in href and \
                       'google.com/maps' not in href and \
                       'facebook.com' not in href and \
                       'instagram.com' not in href and \
                       'linkedin.com' not in href and \
                       'twitter.com' not in href:
                        website = href
                        break

                # Second try: Look for any external links if first method failed
                if not website:
                    all_links = soup.find_all('a', href=True)
                    for link in all_links:
                        href = link.get('href', '')
                        # Check if it's a clinic website
                        if href and href.startswith('http') and \
                           'hotdoc.com' not in href and \
                           'google.com' not in href and \
                           'facebook.com' not in href and \
                           'instagram.com' not in href and \
                           'linkedin.com' not in href and \
                           'twitter.com' not in href:
                            # Additional check: likely to be clinic website
                            text = link.get_text(strip=True).lower()
                            if any(keyword in text for keyword in ['visit', 'website', 'clinic', '.com', '.au']):
                                website = href
                                break

                data['website'] = website or 'N/A'

            return data

        except TimeoutException:
            self.log(f'Timeout loading {url}', 'warning')
            return None
        except Exception as e:
            self.log(f'Error scraping {url}: {str(e)}', 'warning')
            return None

    def scrape(self, sitemap_url, start_range=1, end_range=10, fields=None, limit=None):
        """Main scraping function"""
        if fields is None:
            fields = ['name', 'address', 'phone', 'website']

        self.stop_requested = False
        results = []

        try:
            # Get URLs from sitemap
            urls = self.get_sitemap_urls(sitemap_url)

            if not urls:
                self.log('No clinic URLs found in sitemap', 'error')
                return results

            # Apply range (convert to 0-indexed)
            # If limit is provided (for backward compatibility), use it
            if limit and limit > 0:
                urls = urls[:limit]
                self.log(f'Limited to {limit} clinics')
            else:
                # Use range
                start_idx = max(0, start_range - 1)  # Convert to 0-indexed
                end_idx = min(len(urls), end_range)
                urls = urls[start_idx:end_idx]
                self.log(f'Scraping range {start_range}-{end_range} ({len(urls)} clinics)')

            total = len(urls)

            # Setup Selenium driver
            self.setup_driver()

            # Scrape each URL
            for i, url in enumerate(urls, 1):
                if self.stop_requested:
                    self.log('Scraping stopped by user', 'warning')
                    break

                self.log(f'Scraping {i}/{total}: {url}')
                self.update_progress(i, total, f'Scraping clinic {i}/{total}')

                data = self.extract_clinic_data(url, fields)

                if data:
                    results.append(data)
                    self.log(f"✓ Success: {data.get('name', 'Unknown')}", 'success')
                else:
                    self.log(f'✗ Failed to scrape {url}', 'error')

                # Rate limiting - be respectful to the server
                if i < total:
                    time.sleep(1)  # 1 second between requests

            self.log(f'Scraping complete! Collected {len(results)} clinics', 'success')

        finally:
            # Always close the driver
            self.close_driver()

        return results

    def save_to_csv(self, data, filename='clinics.csv'):
        """Save scraped data to CSV file"""
        if not data:
            self.log('No data to save', 'warning')
            return False

        try:
            # Get all unique fields from data
            fieldnames = set()
            for row in data:
                fieldnames.update(row.keys())
            fieldnames = sorted(list(fieldnames))

            # Move 'url' to the end if present
            if 'url' in fieldnames:
                fieldnames.remove('url')
                fieldnames.append('url')

            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)

            self.log(f'Data saved to {filename}', 'success')
            return True

        except Exception as e:
            self.log(f'Error saving CSV: {str(e)}', 'error')
            return False


if __name__ == '__main__':
    # Simple test run
    def print_callback(data):
        if data['type'] == 'log':
            print(f"[{data['level'].upper()}] {data['message']}")
        elif data['type'] == 'progress':
            print(f"Progress: {data['current']}/{data['total']} - {data['status']}")

    scraper = ClinicScraper(progress_callback=print_callback)
    results = scraper.scrape(
        'https://www.hotdoc.com.au/sitemap.xml.gz',
        limit=5,  # Test with just 5 clinics
        fields=['name', 'address', 'phone', 'website']
    )
    scraper.save_to_csv(results)
