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
        """Extract listing ID from Airbnb URL"""
        try:
            # Handle different URL formats
            if '/rooms/' in url:
                listing_id = url.split('/rooms/')[1].split('?')[0].split('/')[0]
            elif '/listing/' in url:
                listing_id = url.split('/listing/')[1].split('?')[0].split('/')[0]
            else:
                # Try to find numeric ID in URL
                match = re.search(r'/(\d+)', url)
                if match:
                    listing_id = match.group(1)
                else:
                    return None
            return listing_id
        except Exception as e:
            logger.error(f"Error extracting listing ID: {e}")
            return None
    
    def scrape_listing(self, url: str) -> Dict:
        """Scrape a single Airbnb listing"""
        try:
            # Add random delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))
            
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract data from various sources in the page
            listing_data = {
                'url': url,
                'listing_id': self.extract_listing_id(url),
                'title': self._extract_title(soup),
                'description': self._extract_description(soup),
                'property_type': self._extract_property_type(soup),
                'room_type': self._extract_room_type(soup),
                'guest_capacity': self._extract_guest_capacity(soup),
                'bedrooms': self._extract_bedrooms(soup),
                'bathrooms': self._extract_bathrooms(soup),
                'price_per_night': self._extract_price(soup),
                'cleaning_fee': self._extract_cleaning_fee(soup),
                'review_count': self._extract_review_count(soup),
                'rating': self._extract_rating(soup),
                'amenities': self._extract_amenities(soup),
                'coordinates': self._extract_coordinates(soup),
                'neighborhood': self._extract_neighborhood(soup),
                'image_count': self._extract_image_count(soup),
                'availability_365': self._estimate_availability(soup),
                'host_info': self._extract_host_info(soup)
            }
            
            # Try to extract from JSON-LD or script tags
            json_data = self._extract_json_data(soup)
            if json_data:
                listing_data.update(json_data)
            
            return listing_data
            
        except Exception as e:
            logger.error(f"Error scraping listing {url}: {e}")
            return {'url': url, 'error': str(e)}
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract listing title"""
        selectors = [
            'h1[data-testid="listing-title"]',
            'h1._14i3z6h',
            'h1',
            '[data-section-id="TITLE_DEFAULT"] h1',
            'title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return "Unknown Title"
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract listing description"""
        selectors = [
            '[data-section-id="DESCRIPTION_DEFAULT"]',
            '[data-testid="listing-description"]',
            '.ll4r2nl',
            '[data-plugin-in-point-id="DESCRIPTION_DEFAULT"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)[:500]  # Limit description length
        return "No description available"
    
    def _extract_property_type(self, soup: BeautifulSoup) -> str:
        """Extract property type"""
        # Look for property type in various locations
        selectors = [
            '[data-testid="property-type"]',
            '._1qdp1ym',
            '.ll4r2nl div:first-child'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if any(prop_type in text.lower() for prop_type in ['apartment', 'house', 'condo', 'villa', 'cabin']):
                    return text
        
        # Fallback: look in title or description
        title = self._extract_title(soup).lower()
        if 'apartment' in title:
            return 'Apartment'
        elif 'house' in title:
            return 'House'
        elif 'condo' in title:
            return 'Condominium'
        
        return "Unknown"
    
    def _extract_room_type(self, soup: BeautifulSoup) -> str:
        """Extract room type (entire place, private room, etc.)"""
        selectors = [
            '[data-testid="room-type"]',
            '._1qdp1ym',
            '.ll4r2nl div'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True).lower()
                if 'entire' in text:
                    return 'Entire place'
                elif 'private room' in text:
                    return 'Private room'
                elif 'shared room' in text:
                    return 'Shared room'
        
        return "Entire place"  # Default assumption
    
    def _extract_guest_capacity(self, soup: BeautifulSoup) -> int:
        """Extract guest capacity"""
        # Look for guest count in various formats
        text = soup.get_text()
        
        patterns = [
            r'(\d+)\s*guests?',
            r'sleeps\s*(\d+)',
            r'accommodates\s*(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return 2  # Default assumption
    
    def _extract_bedrooms(self, soup: BeautifulSoup) -> int:
        """Extract number of bedrooms"""
        text = soup.get_text()
        
        patterns = [
            r'(\d+)\s*bedrooms?',
            r'(\d+)\s*bed\s*·',
            r'(\d+)\s*br\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        # Look for studio
        if re.search(r'studio', text, re.IGNORECASE):
            return 0
        
        return 1  # Default assumption
    
    def _extract_bathrooms(self, soup: BeautifulSoup) -> float:
        """Extract number of bathrooms"""
        text = soup.get_text()
        
        patterns = [
            r'(\d+(?:\.\d+)?)\s*bathrooms?',
            r'(\d+(?:\.\d+)?)\s*bath\s*·',
            r'(\d+(?:\.\d+)?)\s*ba\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        return 1.0  # Default assumption
    
    def _extract_price(self, soup: BeautifulSoup) -> float:
        """Extract price per night"""
        selectors = [
            '[data-testid="price-availability-row"]',
            '._1k4xcdh',
            '._tyxjp1',
            '._1p7iugi'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text()
                price_match = re.search(r'\$(\d+(?:,\d+)?)', text)
                if price_match:
                    return float(price_match.group(1).replace(',', ''))
        
        # Fallback: search entire page for price patterns
        text = soup.get_text()
        price_patterns = [
            r'\$(\d+(?:,\d+)?)\s*per\s*night',
            r'\$(\d+(?:,\d+)?)\s*/\s*night',
            r'\$(\d+(?:,\d+)?)\s*night'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(',', ''))
        
        return 100.0  # Default assumption
    
    def _extract_cleaning_fee(self, soup: BeautifulSoup) -> float:
        """Extract cleaning fee"""
        text = soup.get_text()
        
        patterns = [
            r'cleaning\s*fee[:\s]*\$(\d+(?:,\d+)?)',
            r'\$(\d+(?:,\d+)?)\s*cleaning',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(',', ''))
        
        return 0.0  # Default if not found
    
    def _extract_review_count(self, soup: BeautifulSoup) -> int:
        """Extract number of reviews"""
        selectors = [
            '[data-testid="review-count"]',
            '._1f1oir5',
            '._4oybiu'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text()
                match = re.search(r'(\d+(?:,\d+)?)', text)
                if match:
                    return int(match.group(1).replace(',', ''))
        
        # Fallback: search for review patterns
        text = soup.get_text()
        patterns = [
            r'(\d+(?:,\d+)?)\s*reviews?',
            r'reviews?\s*\((\d+(?:,\d+)?)\)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1).replace(',', ''))
        
        return 0
    
    def _extract_rating(self, soup: BeautifulSoup) -> float:
        """Extract rating"""
        selectors = [
            '[data-testid="rating"]',
            '._4oybiu',
            '._1f1oir5'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text()
                match = re.search(r'(\d+(?:\.\d+)?)', text)
                if match:
                    rating = float(match.group(1))
                    if 0 <= rating <= 5:
                        return rating
        
        return 0.0
    
    def _extract_amenities(self, soup: BeautifulSoup) -> List[str]:
        """Extract amenities list"""
        amenities = []
        
        # Look for amenities section
        selectors = [
            '[data-section-id="AMENITIES_DEFAULT"]',
            '[data-testid="amenities-section"]',
            '._1byskwn'
        ]
        
        for selector in selectors:
            section = soup.select_one(selector)
            if section:
                amenity_elements = section.find_all(['div', 'span', 'li'])
                for element in amenity_elements:
                    text = element.get_text(strip=True)
                    if text and len(text) < 50:  # Reasonable amenity length
                        amenities.append(text)
        
        # Remove duplicates and return first 20
        return list(dict.fromkeys(amenities))[:20]
    
    def _extract_coordinates(self, soup: BeautifulSoup) -> Optional[Tuple[float, float]]:
        """Extract coordinates if available"""
        # Look for coordinates in script tags or data attributes
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Look for lat/lng patterns
                lat_match = re.search(r'"lat":\s*(-?\d+\.\d+)', script.string)
                lng_match = re.search(r'"lng":\s*(-?\d+\.\d+)', script.string)
                
                if lat_match and lng_match:
                    return (float(lat_match.group(1)), float(lng_match.group(1)))
        
        return None
    
    def _extract_neighborhood(self, soup: BeautifulSoup) -> str:
        """Extract neighborhood information"""
        selectors = [
            '[data-testid="neighborhood"]',
            '._1qdp1ym',
            '.ll4r2nl'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if len(text) < 100:  # Reasonable neighborhood name length
                    return text
        
        return "Unknown"
    
    def _extract_image_count(self, soup: BeautifulSoup) -> int:
        """Count images in the listing"""
        img_elements = soup.find_all('img')
        # Filter out small images (likely icons)
        large_images = [img for img in img_elements if img.get('src') and 'airbnb' in img.get('src', '')]
        return len(large_images)
    
    def _estimate_availability(self, soup: BeautifulSoup) -> int:
        """Estimate availability based on review frequency"""
        review_count = self._extract_review_count(soup)
        
        # Rough estimation: more reviews = higher occupancy = lower availability
        if review_count > 100:
            return 200  # High occupancy property
        elif review_count > 50:
            return 250
        elif review_count > 20:
            return 300
        else:
            return 350  # Lower occupancy, higher availability
    
    def _extract_host_info(self, soup: BeautifulSoup) -> Dict:
        """Extract host information"""
        host_info = {
            'name': 'Unknown',
            'is_superhost': False,
            'response_rate': 0,
            'response_time': 'Unknown'
        }
        
        # Look for host section
        text = soup.get_text()
        
        # Check for superhost
        if 'superhost' in text.lower():
            host_info['is_superhost'] = True
        
        # Look for response rate
        response_match = re.search(r'(\d+)%\s*response\s*rate', text, re.IGNORECASE)
        if response_match:
            host_info['response_rate'] = int(response_match.group(1))
        
        return host_info
    
    def _extract_json_data(self, soup: BeautifulSoup) -> Dict:
        """Extract data from JSON-LD or script tags"""
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'name' in data:
                    return {
                        'title': data.get('name', ''),
                        'description': data.get('description', ''),
                        'price_per_night': self._parse_price_from_json(data)
                    }
            except json.JSONDecodeError:
                continue
        
        return {}
    
    def _parse_price_from_json(self, data: Dict) -> float:
        """Parse price from JSON data"""
        if 'offers' in data and isinstance(data['offers'], dict):
            price = data['offers'].get('price')
            if price:
                try:
                    return float(price)
                except (ValueError, TypeError):
                    pass
        return 0.0
    
    def find_comparable_listings(self, base_listing: Dict, max_comps: int = 10) -> List[Dict]:
        """Find comparable listings (simplified version)"""
        # This is a simplified implementation
        # In a real-world scenario, you would use Airbnb's search API or more sophisticated scraping
        
        comps = []
        
        # Generate some mock comparable data based on the base listing
        base_price = base_listing.get('price_per_night', 100)
        base_bedrooms = base_listing.get('bedrooms', 1)
        base_bathrooms = base_listing.get('bathrooms', 1)
        
        for i in range(min(max_comps, 8)):  # Generate 8 mock comps
            price_variation = random.uniform(0.8, 1.2)  # ±20% price variation
            comp = {
                'url': f"https://www.airbnb.com/rooms/mock_{i+1}",
                'listing_id': f"mock_{i+1}",
                'title': f"Comparable Property {i+1}",
                'property_type': base_listing.get('property_type', 'Apartment'),
                'room_type': base_listing.get('room_type', 'Entire place'),
                'bedrooms': base_bedrooms + random.choice([-1, 0, 1]) if base_bedrooms > 0 else base_bedrooms,
                'bathrooms': base_bathrooms + random.choice([-0.5, 0, 0.5]),
                'price_per_night': round(base_price * price_variation, 2),
                'cleaning_fee': random.uniform(20, 80),
                'review_count': random.randint(10, 200),
                'rating': round(random.uniform(4.0, 5.0), 1),
                'availability_365': random.randint(200, 350),
                'estimated_occupancy': random.uniform(0.6, 0.85)
            }
            comps.append(comp)
        
        logger.info(f"Generated {len(comps)} comparable listings")
        return comps

def scrape_airbnb_listing(url: str) -> Dict:
    """Main function to scrape an Airbnb listing and find comparables"""
    scraper = AirbnbScraper()
    
    # Scrape the main listing
    listing = scraper.scrape_listing(url)
    
    if 'error' in listing:
        return listing
    
    # Find comparable listings
    comps = scraper.find_comparable_listings(listing)
    
    return {
        'subject_property': listing,
        'comparable_properties': comps,
        'scrape_timestamp': time.time()
    }

