from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class MetaTagsChecker:
    def __init__(self):
        self.meta_description_max_length = 160
        self.meta_description_min_length = 120

    def check(self, html: str) -> Dict:
        """
        Check meta tags of a webpage.
        
        Args:
            html (str): The HTML content of the page
            
        Returns:
            Dict containing:
            - has_meta_description (bool): Whether meta description exists
            - meta_description (str): The meta description text
            - meta_description_length (int): Length of meta description
            - is_optimal_length (bool): Whether length is optimal
            - has_duplicate_meta (bool): Whether duplicate meta tags exist
            - recommendations (List[str]): List of recommendations
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Check meta description
            meta_descriptions = soup.find_all('meta', attrs={'name': 'description'})
            has_duplicate_meta = len(meta_descriptions) > 1
            
            if not meta_descriptions:
                return {
                    'has_meta_description': False,
                    'meta_description': '',
                    'meta_description_length': 0,
                    'is_optimal_length': False,
                    'has_duplicate_meta': False,
                    'recommendations': ['Add a meta description to your page']
                }
            
            # Use the first meta description if multiple exist
            meta_description = meta_descriptions[0].get('content', '').strip()
            meta_length = len(meta_description)
            
            recommendations = []
            if has_duplicate_meta:
                recommendations.append('Remove duplicate meta description tags')
            
            if meta_length < self.meta_description_min_length:
                recommendations.append(f'Meta description is too short ({meta_length} chars). Aim for {self.meta_description_min_length}-{self.meta_description_max_length} characters')
            elif meta_length > self.meta_description_max_length:
                recommendations.append(f'Meta description is too long ({meta_length} chars). Keep it under {self.meta_description_max_length} characters')
            
            return {
                'has_meta_description': True,
                'meta_description': meta_description,
                'meta_description_length': meta_length,
                'is_optimal_length': self.meta_description_min_length <= meta_length <= self.meta_description_max_length,
                'has_duplicate_meta': has_duplicate_meta,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Error checking meta tags: {str(e)}")
            return {
                'has_meta_description': False,
                'meta_description': '',
                'meta_description_length': 0,
                'is_optimal_length': False,
                'has_duplicate_meta': False,
                'recommendations': ['Error analyzing meta tags']
            } 