import requests
from bs4 import BeautifulSoup
import json
import re
import time
import random
from urllib.parse import urljoin, urlparse, parse_qs
from typing import Dict, List, Optional, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AirbnbScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def extract_listing_id(self, url: str) -> Optional[str]:
        try:
            if '/rooms/' in url:
                listing_id = url.split('/rooms/')[1].split('?')[0].split('/')[0]
            elif '/listing/' in url:
                listing_id = url.split('/listing/')[1].split('?')[0].split('/')[0]
            else:
                match = re.search(r'/rooms/(\d+)', url)
