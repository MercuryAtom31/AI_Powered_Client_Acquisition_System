from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class TitleTagChecker:
    def __init__(self):
        self.optimal_length = 60
        self.min_length = 30
        self.max_length = 70

    def check(self, html: str) -> Dict:
        """
        Check the title tag of a webpage.
        
        Args:
            html (str): The HTML content of the page
            
        Returns:
            Dict containing:
            - exists (bool): Whether title tag exists
            - text (str): The title text
            - length (int): Length of the title
            - is_optimal_length (bool): Whether length is optimal
            - recommendations (List[str]): List of recommendations
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            title_tag = soup.find('title')
            
            if not title_tag:
                return {
                    'exists': False,
                    'text': '',
                    'length': 0,
                    'is_optimal_length': False,
                    'recommendations': ['Add a title tag to your page']
                }
            
            title_text = title_tag.get_text().strip()
            title_length = len(title_text)
            
            recommendations = []
            if title_length < self.min_length:
                recommendations.append(f'Title is too short ({title_length} chars). Aim for {self.min_length}-{self.max_length} characters')
            elif title_length > self.max_length:
                recommendations.append(f'Title is too long ({title_length} chars). Keep it under {self.max_length} characters')
            
            return {
                'exists': True,
                'text': title_text,
                'length': title_length,
                'is_optimal_length': self.min_length <= title_length <= self.max_length,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Error checking title tag: {str(e)}")
            return {
                'exists': False,
                'text': '',
                'length': 0,
                'is_optimal_length': False,
                'recommendations': ['Error analyzing title tag']
            } 