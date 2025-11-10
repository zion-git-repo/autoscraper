# HotDoc Clinic Scraper

A web-based tool to automatically scrape clinic information from HotDoc's sitemap using Selenium for JavaScript rendering.

## Features

- Real-time web dashboard with live progress updates
- Configurable field extraction (name, address, phone, website)
- Limit control for number of clinics to scrape
- Live log feed showing scraping progress
- Results preview table
- CSV export functionality
- Selenium-based scraping for JavaScript-rendered pages
- Rate limiting to be respectful to servers
- **8,340+ clinic URLs** available in HotDoc sitemap

## Installation

### Prerequisites
- Python 3.12+
- Google Chrome browser (for Selenium)

### Install Dependencies

1. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

2. Chrome browser should be installed on your system (Selenium will use it in headless mode)

## Usage

1. Start the application:
```bash
python3 app.py
```

2. Open your browser to:
```
http://localhost:5000
```

3. Configure your scraping options:
   - Select which fields to extract (name, address, phone, website)
   - Set a limit (0 for no limit, or specify a number)
   - Click "Start Scraping"

4. Monitor progress in real-time:
   - Progress bar shows completion percentage
   - Live log displays current activity
   - Results preview shows first 10 clinics

5. Download results:
   - Click "Download CSV" when scraping is complete
   - File will be saved as `clinics.csv`

## Project Structure

```
autoscreape/
├── app.py              # Flask web server with SSE
├── scraper.py          # Scraping logic
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Dashboard UI
├── static/
│   ├── style.css       # Styling
│   └── script.js       # Real-time updates
└── clinics.csv         # Output file (generated)
```

## Features in Detail

### Scraper (scraper.py)
- Downloads and parses gzipped sitemap index (6 sub-sitemaps)
- Filters for clinic pages only (8,340+ clinic URLs)
- Uses **Selenium WebDriver** with headless Chrome for JavaScript rendering
- Extracts structured data from rendered pages using BeautifulSoup
- Progress callbacks for real-time updates
- Error handling with timeouts and retries
- Rate limiting (1 second between requests)
- Automatic browser cleanup

### Web Server (app.py)
- Flask server with SSE support
- Background threading for scraping
- REST API endpoints for control
- CSV download functionality

### Dashboard
- Modern, responsive UI
- Real-time progress tracking
- Configurable extraction options
- Live log feed
- Results preview table

## Notes

- Default rate limit: 1 second between requests
- Progress updates sent via Server-Sent Events (SSE)
- Results are saved incrementally
- Can stop scraping at any time
- Scraping is slower than traditional methods due to JavaScript rendering (headless browser)
- Some clinics may not have all fields available (will show "N/A")
- Chrome/Chromium must be installed for Selenium to work

## Sample Output

```csv
name,address,phone,website,url
Armadale Family Clinic,"Ground Floor 1002-1004 High St, Armadale VIC 3143",+61395091811,N/A,https://www.hotdoc.com.au/medical-centres/armadale-VIC-3143/armadale_family_clinic/doctors
East Bentleigh Medical Group,"873 Centre Rd, Bentleigh East VIC 3165",+61395792077,N/A,https://www.hotdoc.com.au/medical-centres/bentleigh-east-VIC-3165/ebmg/doctors
```

## Troubleshooting

**Browser not found error:**
- Make sure Google Chrome is installed
- On macOS: Install via `brew install --cask google-chrome`
- On Linux: Install chrome or chromium-browser

**Timeout errors:**
- Some pages may load slowly - this is normal
- Failed pages are logged and skipped automatically
