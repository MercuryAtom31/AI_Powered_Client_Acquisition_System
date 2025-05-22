import re
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse
import logging
from email_validator import validate_email, EmailNotValidError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContactExtractor:
    def __init__(self):
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        self.phone_pattern = re.compile(r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
        self.social_patterns = {
            'linkedin': re.compile(r'linkedin\.com/in/[\w-]+'),
            'twitter': re.compile(r'twitter\.com/[\w-]+'),
            'facebook': re.compile(r'facebook\.com/[\w-]+'),
            'instagram': re.compile(r'instagram\.com/[\w-]+')
        }

    def extract_from_url(self, url: str) -> Dict:
        """
        Extract contact information from a given URL.
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return self.extract_from_html(response.text, url)
        except Exception as e:
            logger.error(f"Error extracting from URL {url}: {str(e)}")
            return {}

    def extract_from_html(self, html: str, base_url: str) -> Dict:
        """
        Extract contact information from HTML content.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Initialize result dictionary
        result = {
            'emails': set(),
            'phones': set(),
            'social_media': {},
            'contact_page_url': None
        }
        
        # Find contact page
        contact_page = self._find_contact_page(soup, base_url)
        if contact_page:
            result['contact_page_url'] = contact_page
            # Extract from contact page if found
            try:
                contact_response = requests.get(contact_page, timeout=10)
                contact_response.raise_for_status()
                contact_soup = BeautifulSoup(contact_response.text, 'html.parser')
                self._extract_emails(contact_soup, result['emails'])
                self._extract_phones(contact_soup, result['phones'])
                self._extract_social_media(contact_soup, result['social_media'])
            except Exception as e:
                logger.error(f"Error extracting from contact page {contact_page}: {str(e)}")
        
        # Extract from main page as well
        self._extract_emails(soup, result['emails'])
        self._extract_phones(soup, result['phones'])
        self._extract_social_media(soup, result['social_media'])
        
        # Convert sets to lists for JSON serialization
        return {
            'emails': list(result['emails']),
            'phones': list(result['phones']),
            'social_media': result['social_media'],
            'contact_page_url': result['contact_page_url']
        }

    def _find_contact_page(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """
        Find the contact page URL from the main page.
        """
        contact_keywords = ['contact', 'about', 'team', 'reach', 'get in touch']
        
        # Look for links containing contact-related keywords
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().lower()
            
            # Check if the link text contains contact-related keywords
            if any(keyword in text for keyword in contact_keywords):
                return urljoin(base_url, href)
            
            # Check if the URL contains contact-related keywords
            if any(keyword in href.lower() for keyword in contact_keywords):
                return urljoin(base_url, href)
        
        return None

    def _extract_emails(self, soup: BeautifulSoup, emails: set) -> None:
        """
        Extract email addresses from the page.
        """
        # Find all text nodes
        for text in soup.stripped_strings:
            # Find all email matches
            for match in self.email_pattern.finditer(text):
                email = match.group()
                try:
                    # Validate email
                    validated = validate_email(email)
                    emails.add(validated.email)
                except EmailNotValidError:
                    continue

    def _extract_phones(self, soup: BeautifulSoup, phones: set) -> None:
        """
        Extract phone numbers from the page.
        """
        # Find all text nodes
        for text in soup.stripped_strings:
            # Find all phone matches
            for match in self.phone_pattern.finditer(text):
                phone = match.group()
                # Clean up the phone number
                phone = re.sub(r'[^\d+]', '', phone)
                if len(phone) >= 10:  # Basic validation
                    phones.add(phone)

    def _extract_social_media(self, soup: BeautifulSoup, social_media: Dict) -> None:
        """
        Extract social media links from the page.
        """
        for platform, pattern in self.social_patterns.items():
            # Look in href attributes
            for link in soup.find_all('a', href=True):
                href = link['href']
                if pattern.search(href):
                    social_media[platform] = href
                    break
            
            # Look in text content
            if platform not in social_media:
                for text in soup.stripped_strings:
                    match = pattern.search(text)
                    if match:
                        social_media[platform] = match.group()
                        break 