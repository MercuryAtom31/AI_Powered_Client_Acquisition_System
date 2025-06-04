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
from .seo_checks import (
    TitleTagChecker,
    MetaTagsChecker,
    H1Checker,
    WordCountChecker,
    SSLChecker,
    BrokenLinksChecker,
    ImageAltChecker,
    RedirectChecker,
    SitemapChecker,
    RobotsChecker
)

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
        self.title_checker = TitleTagChecker()
        self.meta_checker = MetaTagsChecker()
        self.h1_checker = H1Checker()
        self.word_count_checker = WordCountChecker()
        self.ssl_checker = SSLChecker()
        self.broken_links_checker = BrokenLinksChecker()
        self.image_alt_checker = ImageAltChecker()
        self.redirect_checker = RedirectChecker()
        self.sitemap_checker = SitemapChecker()
        self.robots_checker = RobotsChecker()

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
        try:
            # Run all SEO checks
            title_analysis = self.title_checker.check(html)
            meta_analysis = self.meta_checker.check(html)
            h1_analysis = self.h1_checker.check(html)
            word_count_analysis = self.word_count_checker.check(html)
            ssl_analysis = self.ssl_checker.check(base_url)
            broken_links_analysis = self.broken_links_checker.check(html, base_url)
            image_alt_analysis = self.image_alt_checker.check(html)
            redirect_analysis = self.redirect_checker.check(base_url)
            sitemap_analysis = self.sitemap_checker.check(base_url)
            robots_analysis = self.robots_checker.check(base_url)
            
            # Combine all analyses
            result = {
                'title': title_analysis,
                'meta_tags': meta_analysis,
                'h1': h1_analysis,
                'word_count': word_count_analysis,
                'ssl': ssl_analysis,
                'broken_links': broken_links_analysis,
                'images': image_alt_analysis,
                'redirects': redirect_analysis,
                'sitemap': sitemap_analysis,
                'robots': robots_analysis,
                'keywords': self._extract_keywords(html),
                'content_analysis': self._analyze_content(html)
            }
            
            # Add overall recommendations
            result['recommendations'] = self._get_overall_recommendations(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing HTML: {str(e)}")
            return {}

    def _extract_keywords(self, html: str) -> Dict:
        """
        Extract and analyze keywords from the page.
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            text = ' '.join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])])
            words = word_tokenize(text.lower())
            words = [word for word in words if word.isalnum() and word not in self.stop_words]
            word_freq = Counter(words)
            top_keywords = word_freq.most_common(10)
            
            return {
                'primary_keywords': [kw for kw, _ in top_keywords[:5]],
                'secondary_keywords': [kw for kw, _ in top_keywords[5:]],
                'keyword_density': self._calculate_keyword_density(word_freq, len(words))
            }
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return {
                'primary_keywords': [],
                'secondary_keywords': [],
                'keyword_density': {}
            }

    def _analyze_content(self, html: str) -> Dict:
        """
        Analyze page content.
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            text = ' '.join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])])
            words = word_tokenize(text)
            
            return {
                'word_count': len(words),
                'is_optimal_length': 300 <= len(words) <= 2000,
                'recommendations': self._get_content_recommendations(len(words))
            }
        except Exception as e:
            logger.error(f"Error analyzing content: {str(e)}")
            return {
                'word_count': 0,
                'is_optimal_length': False,
                'recommendations': ['Error analyzing content']
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

    def _get_content_recommendations(self, word_count: int) -> List[str]:
        """
        Generate recommendations for content.
        """
        recommendations = []
        
        if word_count < 300:
            recommendations.append('Add more content (at least 300 words)')
        elif word_count > 2000:
            recommendations.append('Consider splitting the content into multiple pages')
        
        return recommendations

    def _get_overall_recommendations(self, analysis: Dict) -> List[str]:
        """
        Generate overall recommendations based on all analyses.
        """
        recommendations = []
        
        # Title recommendations
        if not analysis['title']['exists']:
            recommendations.append('Add a title tag to your page')
        elif not analysis['title']['is_optimal_length']:
            recommendations.append(analysis['title']['recommendations'][0])
        
        # Meta description recommendations
        if not analysis['meta_tags']['has_meta_description']:
            recommendations.append('Add a meta description to your page')
        elif not analysis['meta_tags']['is_optimal_length']:
            recommendations.append(analysis['meta_tags']['recommendations'][0])
        
        # H1 recommendations
        if not analysis['h1']['has_h1']:
            recommendations.append('Add an H1 tag to your page')
        elif analysis['h1']['has_multiple_h1']:
            recommendations.append(analysis['h1']['recommendations'][0])
        
        # Content recommendations
        if not analysis['content_analysis']['is_optimal_length']:
            recommendations.append(analysis['content_analysis']['recommendations'][0])
        
        # SSL recommendations
        if not analysis['ssl']['is_secure']:
            recommendations.append('Enable HTTPS for your website')
        
        # Broken links recommendations
        if analysis['broken_links']['broken_links_count'] > 0:
            recommendations.append(f'Fix {analysis["broken_links"]["broken_links_count"]} broken links')
        
        # Image alt text recommendations
        if analysis['images']['images_without_alt'] > 0:
            recommendations.append(f'Add alt text to {analysis["images"]["images_without_alt"]} images')
        
        # Sitemap recommendations
        if not analysis['sitemap']['exists']:
            recommendations.append('Add a sitemap.xml file')
        
        # Robots.txt recommendations
        if not analysis['robots']['exists']:
            recommendations.append('Add a robots.txt file')
        
        return recommendations 