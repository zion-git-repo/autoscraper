# AWS Lightsail Deployment Guide

## Server Specs (Your Plan)
- 2 GB Memory ✅
- 2 vCPUs ✅
- 60 GB SSD Storage ✅
- 1.5 TB Transfer ✅

**Status:** Perfect for scraping 9000 clinics!

---

## Initial Server Setup

### 1. Connect to Lightsail Instance
```bash
# From Lightsail console, click "Connect using SSH"
# Or use your SSH client:
ssh -i YourKey.pem ubuntu@YOUR_LIGHTSAIL_IP
```

### 2. Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 3. Install Python & Dependencies
```bash
# Install Python 3.11
sudo apt install -y python3 python3-pip python3-venv

# Install Chrome & ChromeDriver
sudo apt install -y chromium-browser chromium-chromedriver

# Install other dependencies
sudo apt install -y git
```

### 4. Clone Your Repository
```bash
cd /home/ubuntu
git clone YOUR_GITHUB_REPO_URL autoscreape
cd autoscreape
```

### 5. Setup Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-deploy.txt
```

### 6. Configure Chrome Path for Ubuntu
The scraper should auto-detect, but verify Chrome is installed:
```bash
which chromium-browser
# Should output: /usr/bin/chromium-browser
```

---

## Running the Scraper

### Option A: Quick Test (Foreground)
```bash
source venv/bin/activate
python app.py
```

Then open your browser to: `http://YOUR_LIGHTSAIL_IP:5005`

### Option B: Production (Background with systemd)
**Recommended for long scraping jobs!**

Create systemd service file:
```bash
sudo nano /etc/systemd/system/hotdoc-scraper.service
```

Paste this configuration:
```ini
[Unit]
Description=HotDoc Clinic Scraper
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/autoscreape
Environment="PATH=/home/ubuntu/autoscreape/venv/bin"
ExecStart=/home/ubuntu/autoscreape/venv/bin/python app.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable hotdoc-scraper
sudo systemctl start hotdoc-scraper
sudo systemctl status hotdoc-scraper
```

View logs:
```bash
sudo journalctl -u hotdoc-scraper -f
```

### Option C: Using Screen (Keep Running After Disconnect)
```bash
# Install screen
sudo apt install -y screen

# Start a screen session
screen -S scraper

# Run your app
source venv/bin/activate
python app.py

# Detach: Press Ctrl+A then D
# Reattach later: screen -r scraper
```

---

## Configure Firewall

Open port 5005 in Lightsail console:
1. Go to your instance → "Networking" tab
2. Click "Add rule"
3. Application: Custom, Protocol: TCP, Port: 5005
4. Save

Or change to port 80:
```python
# In app.py, change port to 80
port = int(os.environ.get('PORT', 80))
```
Then run with sudo: `sudo venv/bin/python app.py`

---

## For 9000 Clinics - Important Configuration

### Increase Timeout Settings

Edit `app.py`, add after line 1:
```python
import os
os.environ['TIMEOUT'] = '36000'  # 10 hours
```

Change gunicorn timeout if using it:
```bash
gunicorn app:app --timeout 36000 --workers 1 --bind 0.0.0.0:5005
```

### Monitor Progress
The app already has real-time SSE updates, but you can also:
```bash
# Watch CSV file grow
watch -n 5 'wc -l clinics.csv'

# Monitor memory usage
watch -n 5 'free -h'

# Monitor Chrome processes
watch -n 5 'ps aux | grep chrome'
```

---

## Expected Performance for 9000 Clinics

| Metric | Estimate |
|--------|----------|
| **Time** | 8-10 hours |
| **Memory Usage** | 500-800 MB |
| **CPU Usage** | 20-40% avg |
| **Network Usage** | ~5-10 GB |
| **CSV Size** | ~5-10 MB |

---

## Optimization Tips

### 1. Reduce Delay (Faster Scraping)
In `scraper.py` line 310, reduce delay:
```python
time.sleep(0.5)  # Instead of 1 second (2x faster)
```
**Caution:** May get rate limited

### 2. Resume on Failure
Add this to track progress:
```python
# Before scraping, check existing CSV and skip scraped URLs
```

### 3. Run Overnight
Start the scraping job before bed:
```bash
screen -S scraper
source venv/bin/activate
python app.py
# Detach: Ctrl+A then D
# Disconnect from SSH - it keeps running!
```

---

## Troubleshooting

### Chrome Crashes
If you see Chrome crashes with 2GB RAM:
```bash
# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Out of Memory
Monitor memory:
```bash
free -h
```
If Chrome uses too much, restart the scraper periodically.

### Timeout Issues
The Flask app may timeout on Lightsail. Use systemd or screen to keep it running.

---

## Cost Estimate

Your Lightsail plan costs ~$10-20/month. Running for 10 hours:
- **Compute:** Included in monthly cost
- **Transfer:** ~5-10 GB out of 1.5 TB (negligible)
- **Total extra cost:** $0

---

## Quick Start Commands

```bash
# 1. SSH into Lightsail
ssh -i key.pem ubuntu@YOUR_IP

# 2. Setup (first time only)
sudo apt update && sudo apt install -y python3 python3-pip chromium-browser chromium-chromedriver git screen
git clone YOUR_REPO_URL autoscreape
cd autoscreape
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-deploy.txt

# 3. Run in screen session
screen -S scraper
python app.py
# Press Ctrl+A then D to detach

# 4. Access from browser
# Open: http://YOUR_LIGHTSAIL_IP:5005
# Start scraping with range 1-9000

# 5. Check back later
screen -r scraper  # Reattach to see progress
```

---

## Next Steps After Setup

1. Open `http://YOUR_LIGHTSAIL_IP:5005` in browser
2. Configure: Start=1, End=9000
3. Click "Start Scraping"
4. Leave it running for 8-10 hours
5. Download CSV when complete

Good luck with your scraping! 🚀
