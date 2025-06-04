import requests
from typing import Dict, List, Optional
import logging
from urllib.parse import urljoin, urlparse
import re

logger = logging.getLogger(__name__)

class RobotsChecker:
    def __init__(self):
        self.timeout = 10

    def check(self, url: str) -> Dict:
        """
        Check robots.txt for a website.
        
        Args:
            url (str): The URL to check
            
        Returns:
            Dict containing:
            - exists (bool): Whether robots.txt exists
            - url (str): Robots.txt URL
            - has_sitemap (bool): Whether sitemap is referenced
            - has_user_agent (bool): Whether User-agent is specified
            - has_disallow (bool): Whether Disallow rules exist
            - recommendations (List[str]): List of recommendations
        """
        try:
            # Get base URL
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            robots_url = urljoin(base_url, 'robots.txt')
            
            try:
                response = requests.get(robots_url, timeout=self.timeout)
                if response.status_code == 200:
                    return self._analyze_robots(robots_url, response.text)
            except requests.RequestException:
                pass
            
            # If robots.txt not found
            return {
                'exists': False,
                'url': None,
                'has_sitemap': False,
                'has_user_agent': False,
                'has_disallow': False,
                'recommendations': ['Add a robots.txt file to your website']
            }
            
        except Exception as e:
            logger.error(f"Error checking robots.txt for {url}: {str(e)}")
            return {
                'exists': False,
                'url': None,
                'has_sitemap': False,
                'has_user_agent': False,
                'has_disallow': False,
                'recommendations': ['Error checking robots.txt']
            }

    def _analyze_robots(self, robots_url: str, content: str) -> Dict:
        """
        Analyze robots.txt content.
        """
        try:
            # Check for sitemap reference
            has_sitemap = bool(re.search(r'Sitemap:\s*https?://', content, re.IGNORECASE))
            
            # Check for User-agent
            has_user_agent = bool(re.search(r'User-agent:', content, re.IGNORECASE))
            
            # Check for Disallow rules
            has_disallow = bool(re.search(r'Disallow:', content, re.IGNORECASE))
            
            recommendations = []
            if not has_sitemap:
                recommendations.append('Add Sitemap directive to robots.txt')
            if not has_user_agent:
                recommendations.append('Add User-agent directive to robots.txt')
            if not has_disallow:
                recommendations.append('Consider adding Disallow rules to robots.txt')
            
            # Check for common issues
            if re.search(r'Disallow:\s*$', content, re.MULTILINE):
                recommendations.append('Fix empty Disallow rules')
            
            if re.search(r'Allow:\s*$', content, re.MULTILINE):
                recommendations.append('Fix empty Allow rules')
            
            # Check for wildcard in User-agent
            if not re.search(r'User-agent:\s*\*', content, re.IGNORECASE):
                recommendations.append('Add wildcard User-agent rule')
            
            return {
                'exists': True,
                'url': robots_url,
                'has_sitemap': has_sitemap,
                'has_user_agent': has_user_agent,
                'has_disallow': has_disallow,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Error analyzing robots.txt: {str(e)}")
            return {
                'exists': True,
                'url': robots_url,
                'has_sitemap': False,
                'has_user_agent': False,
                'has_disallow': False,
                'recommendations': ['Error analyzing robots.txt content']
            } 