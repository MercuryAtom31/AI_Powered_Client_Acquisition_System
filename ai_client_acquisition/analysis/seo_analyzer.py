from bs4 import BeautifulSoup
import requests
from typing import Dict, List, Optional
import logging
from urllib.parse import urljoin, urlparse
from collections import Counter
import re
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SEOAnalyzer:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.title_max_length = 60
        self.meta_description_max_length = 160

    def analyze_url(self, url: str) -> Dict:
        """
        Analyze SEO elements of a given URL.
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return self.analyze_html(response.text, url)
        except Exception as e:
            logger.error(f"Error analyzing URL {url}: {str(e)}")
            return {}

    def analyze_html(self, html: str, base_url: str) -> Dict:
        """
        Analyze SEO elements from HTML content.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Initialize result dictionary
        result = {
            'title': self._analyze_title(soup),
            'meta_description': self._analyze_meta_description(soup),
            'headers': self._analyze_headers(soup),
            'keywords': self._extract_keywords(soup),
            'links': self._analyze_links(soup, base_url),
            'images': self._analyze_images(soup),
            'content_analysis': self._analyze_content(soup)
        }
        
        return result

    def _analyze_title(self, soup: BeautifulSoup) -> Dict:
        """
        Analyze the page title.
        """
        title_tag = soup.find('title')
        title = title_tag.get_text() if title_tag else ''
        
        return {
            'text': title,
            'length': len(title),
            'is_optimal_length': len(title) <= self.title_max_length,
            'has_keywords': bool(title),  # Basic check, can be enhanced
            'recommendations': self._get_title_recommendations(title)
        }

    def _analyze_meta_description(self, soup: BeautifulSoup) -> Dict:
        """
        Analyze the meta description.
        """
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '') if meta_desc else ''
        
        return {
            'text': description,
            'length': len(description),
            'is_optimal_length': len(description) <= self.meta_description_max_length,
            'has_keywords': bool(description),  # Basic check, can be enhanced
            'recommendations': self._get_meta_description_recommendations(description)
        }

    def _analyze_headers(self, soup: BeautifulSoup) -> Dict:
        """
        Analyze header structure and hierarchy.
        """
        headers = {
            'h1': [],
            'h2': [],
            'h3': [],
            'h4': [],
            'h5': [],
            'h6': []
        }
        
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            headers[tag] = [h.get_text().strip() for h in soup.find_all(tag)]
        
        return {
            'structure': headers,
            'has_h1': len(headers['h1']) > 0,
            'multiple_h1': len(headers['h1']) > 1,
            'recommendations': self._get_header_recommendations(headers)
        }

    def _extract_keywords(self, soup: BeautifulSoup) -> Dict:
        """
        Extract and analyze keywords from the page.
        """
        # Get all text content
        text = ' '.join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])])
        
        # Tokenize and clean
        words = word_tokenize(text.lower())
        words = [word for word in words if word.isalnum() and word not in self.stop_words]
        
        # Count word frequencies
        word_freq = Counter(words)
        
        # Get top keywords
        top_keywords = word_freq.most_common(10)
        
        return {
            'primary_keywords': [kw for kw, _ in top_keywords[:5]],
            'secondary_keywords': [kw for kw, _ in top_keywords[5:]],
            'keyword_density': self._calculate_keyword_density(word_freq, len(words))
        }

    def _analyze_links(self, soup: BeautifulSoup, base_url: str) -> Dict:
        """
        Analyze internal and external links.
        """
        internal_links = []
        external_links = []
        broken_links = []
        
        base_domain = urlparse(base_url).netloc
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Skip javascript: and mailto: links
            if href.startswith(('javascript:', 'mailto:')):
                continue
            
            try:
                if base_domain in full_url:
                    internal_links.append(full_url)
                else:
                    external_links.append(full_url)
            except Exception:
                broken_links.append(full_url)
        
        return {
            'internal_links': len(internal_links),
            'external_links': len(external_links),
            'broken_links': len(broken_links),
            'recommendations': self._get_link_recommendations(internal_links, external_links, broken_links)
        }

    def _analyze_images(self, soup: BeautifulSoup) -> Dict:
        """
        Analyze images and their alt text.
        """
        images = soup.find_all('img')
        total_images = len(images)
        images_with_alt = len([img for img in images if img.get('alt')])
        images_without_alt = total_images - images_with_alt
        
        return {
            'total_images': total_images,
            'images_with_alt': images_with_alt,
            'images_without_alt': images_without_alt,
            'recommendations': self._get_image_recommendations(total_images, images_with_alt)
        }

    def _analyze_content(self, soup: BeautifulSoup) -> Dict:
        """
        Analyze page content.
        """
        # Get all text content
        text = ' '.join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])])
        words = word_tokenize(text)
        
        return {
            'word_count': len(words),
            'is_optimal_length': 300 <= len(words) <= 2000,  # Basic content length check
            'recommendations': self._get_content_recommendations(len(words))
        }

    def _calculate_keyword_density(self, word_freq: Counter, total_words: int) -> Dict:
        """
        Calculate keyword density for top keywords.
        """
        if total_words == 0:
            return {}
        
        density = {}
        for word, count in word_freq.most_common(10):
            density[word] = (count / total_words) * 100
        
        return density

    def _get_title_recommendations(self, title: str) -> List[str]:
        """
        Generate recommendations for the title.
        """
        recommendations = []
        
        if not title:
            recommendations.append("Add a title tag")
        elif len(title) > self.title_max_length:
            recommendations.append(f"Title is too long ({len(title)} characters). Keep it under {self.title_max_length} characters")
        
        return recommendations

    def _get_meta_description_recommendations(self, description: str) -> List[str]:
        """
        Generate recommendations for the meta description.
        """
        recommendations = []
        
        if not description:
            recommendations.append("Add a meta description")
        elif len(description) > self.meta_description_max_length:
            recommendations.append(f"Meta description is too long ({len(description)} characters). Keep it under {self.meta_description_max_length} characters")
        
        return recommendations

    def _get_header_recommendations(self, headers: Dict) -> List[str]:
        """
        Generate recommendations for header structure.
        """
        recommendations = []
        
        if not headers['h1']:
            recommendations.append("Add an H1 tag")
        elif len(headers['h1']) > 1:
            recommendations.append("Use only one H1 tag per page")
        
        return recommendations

    def _get_link_recommendations(self, internal_links: List[str], external_links: List[str], broken_links: List[str]) -> List[str]:
        """
        Generate recommendations for links.
        """
        recommendations = []
        
        if not internal_links:
            recommendations.append("Add internal links to improve site structure")
        if not external_links:
            recommendations.append("Consider adding relevant external links")
        if broken_links:
            recommendations.append(f"Fix {len(broken_links)} broken links")
        
        return recommendations

    def _get_image_recommendations(self, total_images: int, images_with_alt: int) -> List[str]:
        """
        Generate recommendations for images.
        """
        recommendations = []
        
        if total_images == 0:
            recommendations.append("Consider adding relevant images to improve engagement")
        elif images_with_alt < total_images:
            recommendations.append(f"Add alt text to {total_images - images_with_alt} images")
        
        return recommendations

    def _get_content_recommendations(self, word_count: int) -> List[str]:
        """
        Generate recommendations for content.
        """
        recommendations = []
        
        if word_count < 300:
            recommendations.append("Add more content (aim for at least 300 words)")
        elif word_count > 2000:
            recommendations.append("Consider breaking up the content into multiple pages")
        
        return recommendations 