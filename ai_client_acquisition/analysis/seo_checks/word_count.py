from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging
from nltk.tokenize import word_tokenize
import re

logger = logging.getLogger(__name__)

class WordCountChecker:
    def __init__(self):
        self.min_words = 300
        self.max_words = 2000

    def check(self, html: str) -> Dict:
        """
        Check word count of a webpage.
        
        Args:
            html (str): The HTML content of the page
            
        Returns:
            Dict containing:
            - word_count (int): Number of words
            - is_optimal_length (bool): Whether word count is optimal
            - recommendations (List[str]): List of recommendations
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean text
            text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
            text = text.strip()
            
            # Count words
            words = word_tokenize(text)
            word_count = len(words)
            
            recommendations = []
            if word_count < self.min_words:
                recommendations.append(f'Content is too short ({word_count} words). Aim for at least {self.min_words} words')
            elif word_count > self.max_words:
                recommendations.append(f'Content is too long ({word_count} words). Consider splitting into multiple pages')
            
            return {
                'word_count': word_count,
                'is_optimal_length': self.min_words <= word_count <= self.max_words,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Error checking word count: {str(e)}")
            return {
                'word_count': 0,
                'is_optimal_length': False,
                'recommendations': ['Error analyzing word count']
            } 