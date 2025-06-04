from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class ImageAltChecker:
    def __init__(self):
        self.min_alt_length = 3  # Minimum length for meaningful alt text

    def check(self, html: str) -> Dict:
        """
        Check images for alt text.
        
        Args:
            html (str): The HTML content of the page
            
        Returns:
            Dict containing:
            - total_images (int): Total number of images
            - images_with_alt (int): Number of images with alt text
            - images_without_alt (int): Number of images without alt text
            - images_with_empty_alt (int): Number of images with empty alt text
            - recommendations (List[str]): List of recommendations
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            images = soup.find_all('img')
            
            total_images = len(images)
            images_with_alt = 0
            images_without_alt = 0
            images_with_empty_alt = 0
            
            for img in images:
                alt = img.get('alt', '')
                if not alt:
                    images_without_alt += 1
                elif len(alt.strip()) < self.min_alt_length:
                    images_with_empty_alt += 1
                else:
                    images_with_alt += 1
            
            recommendations = []
            if total_images == 0:
                recommendations.append('Consider adding relevant images to improve engagement')
            elif images_without_alt > 0:
                recommendations.append(f'Add alt text to {images_without_alt} images')
            if images_with_empty_alt > 0:
                recommendations.append(f'Improve alt text for {images_with_empty_alt} images (current alt text is too short)')
            
            return {
                'total_images': total_images,
                'images_with_alt': images_with_alt,
                'images_without_alt': images_without_alt,
                'images_with_empty_alt': images_with_empty_alt,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Error checking image alt text: {str(e)}")
            return {
                'total_images': 0,
                'images_with_alt': 0,
                'images_without_alt': 0,
                'images_with_empty_alt': 0,
                'recommendations': ['Error analyzing image alt text']
            } 