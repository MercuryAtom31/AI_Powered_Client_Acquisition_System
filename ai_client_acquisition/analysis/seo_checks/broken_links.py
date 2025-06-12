from bs4 import BeautifulSoup
import requests
from typing import Dict, List, Optional, Set
import logging
from urllib.parse import urljoin, urlparse
import concurrent.futures
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

class BrokenLinksChecker:
    def __init__(self):
        self.timeout = 10
        self.max_workers = 10
        self.max_links = 100  # Limit number of links to check

    def check(self, html: str, base_url: str) -> Dict:
        """
        Check for broken links on a webpage.
        
        Args:
            html (str): The HTML content of the page
            base_url (str): The base URL of the page
            
        Returns:
            Dict containing:
            - broken_links_count (int): Number of broken links
            - broken_links (List[str]): List of broken link URLs
            - recommendations (List[str]): List of recommendations
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            base_domain = urlparse(base_url).netloc
            
            # Collect all links
            links = set()
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith(('javascript:', 'mailto:', 'tel:')):
                    continue
                
                full_url = urljoin(base_url, href)
                if base_domain in full_url:  # Only check internal links
                    links.add(full_url)
            
            # Limit number of links to check
            links = list(links)[:self.max_links]
            
            # Check links in parallel
            broken_links = self._check_links_parallel(links)
            
            recommendations = []
            if broken_links:
                recommendations.append(f'Fix {len(broken_links)} broken links')
            
            return {
                'broken_links_count': len(broken_links),
                'broken_links': list(broken_links),
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Error checking broken links: {str(e)}")
            return {
                'broken_links_count': 0,
                'broken_links': [],
                'recommendations': ['Error checking broken links']
            }

    def _check_links_parallel(self, links: List[str]) -> Set[str]:
        """
        Check multiple links in parallel.
        """
        broken_links = set()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self._check_single_link, url): url for url in links}
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    if not future.result():
                        broken_links.add(url)
                except Exception as e:
                    logger.error(f"Error checking link {url}: {str(e)}")
                    broken_links.add(url)
        
        return broken_links

    def _check_single_link(self, url: str) -> bool:
        """
        Check if a single link is working.
        """
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
            # Use requests.get instead of requests.head for more accurate broken link detection
            # Set stream=True and iter_content to immediately close connection for efficiency
            response = requests.get(url, timeout=self.timeout, allow_redirects=True, stream=True, headers=headers)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            # Consume content to release connection if not already released by stream=True
            for _ in response.iter_content(chunk_size=1024):
                pass
            return True
        except RequestException as e:
            logger.error(f"Link check failed for {url}: {e}") # Log the actual error
            return False 