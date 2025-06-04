import requests
from typing import Dict, List, Optional
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class RedirectChecker:
    def __init__(self):
        self.timeout = 10
        self.max_redirects = 5

    def check(self, url: str) -> Dict:
        """
        Check redirects for a URL.
        
        Args:
            url (str): The URL to check
            
        Returns:
            Dict containing:
            - has_redirects (bool): Whether URL has redirects
            - redirect_chain (List[str]): List of URLs in redirect chain
            - is_optimal (bool): Whether redirect chain is optimal
            - recommendations (List[str]): List of recommendations
        """
        try:
            # Start with HTTP if HTTPS is not specified
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            
            response = requests.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                stream=True  # Don't download the full response
            )
            
            # Get redirect chain
            redirect_chain = [r.url for r in response.history]
            final_url = response.url
            
            # Add final URL if it's different from the last redirect
            if redirect_chain and redirect_chain[-1] != final_url:
                redirect_chain.append(final_url)
            
            has_redirects = len(redirect_chain) > 0
            is_optimal = self._is_redirect_chain_optimal(redirect_chain)
            
            recommendations = []
            if has_redirects:
                if len(redirect_chain) > self.max_redirects:
                    recommendations.append(f'Too many redirects ({len(redirect_chain)}). Keep it under {self.max_redirects}')
                
                # Check for HTTP to HTTPS redirect
                if not any(url.startswith('https://') for url in redirect_chain):
                    recommendations.append('Redirect to HTTPS instead of HTTP')
                
                # Check for www to non-www redirect (or vice versa)
                if not self._is_www_redirect_consistent(redirect_chain):
                    recommendations.append('Make www/non-www redirects consistent')
            
            return {
                'has_redirects': has_redirects,
                'redirect_chain': redirect_chain,
                'is_optimal': is_optimal,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Error checking redirects for {url}: {str(e)}")
            return {
                'has_redirects': False,
                'redirect_chain': [],
                'is_optimal': False,
                'recommendations': ['Error checking redirects']
            }

    def _is_redirect_chain_optimal(self, redirect_chain: List[str]) -> bool:
        """
        Check if redirect chain is optimal.
        """
        if not redirect_chain:
            return True
        
        # Check number of redirects
        if len(redirect_chain) > self.max_redirects:
            return False
        
        # Check if final URL is HTTPS
        if not redirect_chain[-1].startswith('https://'):
            return False
        
        # Check if www/non-www is consistent
        if not self._is_www_redirect_consistent(redirect_chain):
            return False
        
        return True

    def _is_www_redirect_consistent(self, redirect_chain: List[str]) -> bool:
        """
        Check if www/non-www redirects are consistent.
        """
        if not redirect_chain:
            return True
        
        # Get domains from URLs
        domains = [urlparse(url).netloc for url in redirect_chain]
        
        # Check if all domains are either www or non-www
        has_www = any(domain.startswith('www.') for domain in domains)
        has_non_www = any(not domain.startswith('www.') for domain in domains)
        
        # Should be either all www or all non-www
        return not (has_www and has_non_www) 