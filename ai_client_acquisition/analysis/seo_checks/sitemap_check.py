import requests
from typing import Dict, List, Optional
import logging
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
from datetime import datetime

logger = logging.getLogger(__name__)

class SitemapChecker:
    def __init__(self):
        self.timeout = 10

    def check(self, url: str) -> Dict:
        """
        Check sitemap.xml for a website.
        
        Args:
            url (str): The URL to check
            
        Returns:
            Dict containing:
            - exists (bool): Whether sitemap exists
            - url (str): Sitemap URL
            - url_count (int): Number of URLs in sitemap
            - last_modified (str): Last modified date
            - recommendations (List[str]): List of recommendations
        """
        try:
            # Get base URL
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Try common sitemap locations
            sitemap_urls = [
                urljoin(base_url, 'sitemap.xml'),
                urljoin(base_url, 'sitemap_index.xml'),
                urljoin(base_url, 'sitemap/sitemap.xml')
            ]
            
            for sitemap_url in sitemap_urls:
                try:
                    response = requests.get(sitemap_url, timeout=self.timeout)
                    if response.status_code == 200:
                        return self._analyze_sitemap(sitemap_url, response.text)
                except requests.RequestException:
                    continue
            
            # If no sitemap found
            return {
                'exists': False,
                'url': None,
                'url_count': 0,
                'last_modified': None,
                'recommendations': ['Add a sitemap.xml file to your website']
            }
            
        except Exception as e:
            logger.error(f"Error checking sitemap for {url}: {str(e)}")
            return {
                'exists': False,
                'url': None,
                'url_count': 0,
                'last_modified': None,
                'recommendations': ['Error checking sitemap']
            }

    def _analyze_sitemap(self, sitemap_url: str, sitemap_content: str) -> Dict:
        """
        Analyze sitemap content.
        """
        try:
            root = ET.fromstring(sitemap_content)
            
            # Check if it's a sitemap index
            if 'sitemapindex' in root.tag:
                return self._analyze_sitemap_index(sitemap_url, root)
            
            # Regular sitemap
            urls = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url')
            url_count = len(urls)
            
            # Get last modified date
            last_modified = None
            for url in urls:
                lastmod = url.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
                if lastmod is not None and lastmod.text:
                    try:
                        date = datetime.strptime(lastmod.text, '%Y-%m-%d')
                        if last_modified is None or date > last_modified:
                            last_modified = date
                    except ValueError:
                        continue
            
            recommendations = []
            if url_count == 0:
                recommendations.append('Add URLs to your sitemap')
            elif url_count > 50000:
                recommendations.append('Consider splitting your sitemap (over 50,000 URLs)')
            
            if last_modified:
                days_since_update = (datetime.now() - last_modified).days
                if days_since_update > 30:
                    recommendations.append(f'Update your sitemap (last updated {days_since_update} days ago)')
            
            return {
                'exists': True,
                'url': sitemap_url,
                'url_count': url_count,
                'last_modified': last_modified.isoformat() if last_modified else None,
                'recommendations': recommendations
            }
            
        except ET.ParseError as e:
            logger.error(f"Error parsing sitemap: {str(e)}")
            return {
                'exists': True,
                'url': sitemap_url,
                'url_count': 0,
                'last_modified': None,
                'recommendations': ['Fix sitemap XML format']
            }

    def _analyze_sitemap_index(self, index_url: str, root: ET.Element) -> Dict:
        """
        Analyze sitemap index file.
        """
        sitemaps = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap')
        total_urls = 0
        last_modified = None
        
        for sitemap in sitemaps:
            loc = sitemap.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc is not None:
                try:
                    response = requests.get(loc.text, timeout=self.timeout)
                    if response.status_code == 200:
                        sitemap_analysis = self._analyze_sitemap(loc.text, response.text)
                        total_urls += sitemap_analysis['url_count']
                        
                        if sitemap_analysis['last_modified']:
                            date = datetime.fromisoformat(sitemap_analysis['last_modified'])
                            if last_modified is None or date > last_modified:
                                last_modified = date
                except requests.RequestException:
                    continue
        
        recommendations = []
        if total_urls == 0:
            recommendations.append('Add URLs to your sitemap index')
        elif total_urls > 50000:
            recommendations.append('Consider reducing the number of URLs in your sitemaps')
        
        if last_modified:
            days_since_update = (datetime.now() - last_modified).days
            if days_since_update > 30:
                recommendations.append(f'Update your sitemaps (last updated {days_since_update} days ago)')
        
        return {
            'exists': True,
            'url': index_url,
            'url_count': total_urls,
            'last_modified': last_modified.isoformat() if last_modified else None,
            'recommendations': recommendations
        } 