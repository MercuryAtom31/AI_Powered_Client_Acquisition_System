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
            logger.info(f"SSL Analysis Result: {ssl_analysis}")
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
                'content_analysis': self._analyze_content(html),
                'checks': {
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
                }
            }
            
            # Add overall recommendations
            result['recommendations'] = self._get_overall_recommendations(result)
            
            # Calculate and add overall score
            result['overall_score'] = self._calculate_overall_score(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing HTML: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}, Exception message: {e}") # Detailed logging
            # Return a simplified error response
            return {
                'overall_score': 0,
                'recommendations': [f'An error occurred during SEO analysis: {e}'],
                'checks': {
                    'title': {'error': f'Analysis failed: {e}'},
                    'meta_tags': {'error': f'Analysis failed: {e}'},
                    'h1': {'error': f'Analysis failed: {e}'},
                    'word_count': {'error': f'Analysis failed: {e}'},
                    'ssl': {'error': f'Analysis failed: {e}'},
                    'broken_links': {'error': f'Analysis failed: {e}'},
                    'images': {'error': f'Analysis failed: {e}', 'all_have_alt': False},
                    'redirects': {'error': f'Analysis failed: {e}'},
                    'sitemap': {'error': f'Analysis failed: {e}'},
                    'robots': {'error': f'Analysis failed: {e}'},
                }
            }

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
        if not analysis.get('title', {}).get('exists', False):
            recommendations.append('Add a title tag to your page')
        elif not analysis.get('title', {}).get('is_optimal_length', False):
            recommendations.append(analysis.get('title', {}).get('recommendations', ['Analysis error'])[0])
        
        # Meta description recommendations
        if not analysis.get('meta_tags', {}).get('has_meta_description', False):
            recommendations.append('Add a meta description to your page')
        elif not analysis.get('meta_tags', {}).get('is_optimal_length', False):
            recommendations.append(analysis.get('meta_tags', {}).get('recommendations', ['Analysis error'])[0])
        
        # H1 recommendations
        if not analysis.get('h1', {}).get('has_h1', False):
            recommendations.append('Add an H1 tag to your page')
        elif analysis.get('h1', {}).get('has_multiple_h1', False):
            recommendations.append('Remove extra H1 tags. Only one H1 tag is recommended.')
        
        # Content recommendations
        if not analysis.get('content_analysis', {}).get('is_optimal_length', False):
            recommendations.extend(analysis.get('content_analysis', {}).get('recommendations', []))
        
        # SSL recommendations
        if not analysis.get('ssl', {}).get('is_secure', False):
            recommendations.append('Enable HTTPS for your website')
        
        # Broken links recommendations
        if analysis.get('broken_links', {}).get('broken_links_count', 0) > 0:
            recommendations.append(f'Fix {analysis["broken_links"]["broken_links_count"]} broken links')
        
        # Image alt text recommendations
        if analysis.get('images', {}).get('images_without_alt', 0) > 0:
            # Safely access images_without_alt for the recommendation string
            images_without_alt_count = analysis.get('images', {}).get('images_without_alt', 0)
            recommendations.append(f'Add alt text to {images_without_alt_count} images')
        if analysis.get('images', {}).get('all_have_alt', True) is False:
            recommendations.append('Ensure all images have descriptive alt text')
        
        # Sitemap recommendations
        if not analysis.get('sitemap', {}).get('exists', False):
            recommendations.append('Add a sitemap.xml file')
        
        # Robots.txt recommendations
        if not analysis.get('robots', {}).get('exists', False):
            recommendations.append('Add a robots.txt file')
        
        return recommendations

    def _calculate_overall_score(self, analysis: Dict) -> int:
        """
        Calculate an overall SEO score based on analysis results.
        Score out of 100.
        """
        score = 100 # Start with a perfect score
        
        # Deduct points for critical issues
        if not analysis.get('ssl', {}).get('is_secure', False):
            score -= 20
        if not analysis.get('title', {}).get('exists', False):
            score -= 15
        if not analysis.get('meta_tags', {}).get('has_meta_description', False):
            score -= 10
        if not analysis.get('h1', {}).get('has_h1', False):
            score -= 10
        if analysis.get('h1', {}).get('has_multiple_h1', False):
            score -= 10
        
        # Deduct points for warnings/optimizations
        if not analysis.get('title', {}).get('is_optimal_length', False):
            score -= 5
        if not analysis.get('meta_tags', {}).get('is_optimal_length', False):
            score -= 5
        if not analysis.get('content_analysis', {}).get('is_optimal_length', False):
            score -= 5
        if analysis.get('broken_links', {}).get('broken_links_count', 0) > 0:
            score -= 10
        
        # Ensure score doesn't go below 0
        return max(0, score) 