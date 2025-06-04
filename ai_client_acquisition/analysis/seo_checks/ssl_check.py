import requests
from typing import Dict, List, Optional
import logging
from urllib.parse import urlparse
import ssl
import socket
from datetime import datetime

logger = logging.getLogger(__name__)

class SSLChecker:
    def __init__(self):
        self.timeout = 10

    def check(self, url: str) -> Dict:
        """
        Check SSL certificate of a website.
        
        Args:
            url (str): The URL to check
            
        Returns:
            Dict containing:
            - is_secure (bool): Whether site uses HTTPS
            - has_valid_cert (bool): Whether SSL certificate is valid
            - cert_expiry (str): Certificate expiry date
            - recommendations (List[str]): List of recommendations
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Check if URL uses HTTPS
            is_secure = parsed_url.scheme == 'https'
            
            if not is_secure:
                return {
                    'is_secure': False,
                    'has_valid_cert': False,
                    'cert_expiry': None,
                    'recommendations': ['Enable HTTPS for your website']
                }
            
            # Check SSL certificate
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Get certificate expiry date
                    expiry_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    days_remaining = (expiry_date - datetime.now()).days
                    
                    recommendations = []
                    if days_remaining < 30:
                        recommendations.append(f'SSL certificate expires in {days_remaining} days')
                    
                    return {
                        'is_secure': True,
                        'has_valid_cert': True,
                        'cert_expiry': expiry_date.isoformat(),
                        'recommendations': recommendations
                    }
            
        except ssl.SSLError as e:
            logger.error(f"SSL Error for {url}: {str(e)}")
            return {
                'is_secure': True,
                'has_valid_cert': False,
                'cert_expiry': None,
                'recommendations': ['Fix SSL certificate issues']
            }
        except Exception as e:
            logger.error(f"Error checking SSL for {url}: {str(e)}")
            return {
                'is_secure': False,
                'has_valid_cert': False,
                'cert_expiry': None,
                'recommendations': ['Error checking SSL certificate']
            } 