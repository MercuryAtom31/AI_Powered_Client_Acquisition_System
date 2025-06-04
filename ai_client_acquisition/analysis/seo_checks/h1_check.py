from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class H1Checker:
    def __init__(self):
        self.max_h1_tags = 1

    def check(self, html: str) -> Dict:
        """
        Check H1 tags of a webpage.
        
        Args:
            html (str): The HTML content of the page
            
        Returns:
            Dict containing:
            - h1_count (int): Number of H1 tags
            - h1_texts (List[str]): List of H1 tag texts
            - has_h1 (bool): Whether H1 tag exists
            - has_multiple_h1 (bool): Whether multiple H1 tags exist
            - recommendations (List[str]): List of recommendations
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            h1_tags = soup.find_all('h1')
            h1_texts = [tag.get_text().strip() for tag in h1_tags]
            h1_count = len(h1_tags)
            
            recommendations = []
            if h1_count == 0:
                recommendations.append('Add an H1 tag to your page')
            elif h1_count > self.max_h1_tags:
                recommendations.append(f'Remove extra H1 tags. Only one H1 tag is recommended, found {h1_count}')
            
            return {
                'h1_count': h1_count,
                'h1_texts': h1_texts,
                'has_h1': h1_count > 0,
                'has_multiple_h1': h1_count > self.max_h1_tags,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Error checking H1 tags: {str(e)}")
            return {
                'h1_count': 0,
                'h1_texts': [],
                'has_h1': False,
                'has_multiple_h1': False,
                'recommendations': ['Error analyzing H1 tags']
            } 