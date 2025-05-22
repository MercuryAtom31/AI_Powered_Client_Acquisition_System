import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from urllib.parse import urlparse
import logging
from typing import List, Set, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebsiteCrawler(CrawlSpider):
    name = 'website_crawler'
    
    def __init__(self, start_urls: List[str], allowed_domains: Optional[List[str]] = None, *args, **kwargs):
        self.start_urls = start_urls
        self.allowed_domains = allowed_domains or [urlparse(url).netloc for url in start_urls]
        self.visited_urls: Set[str] = set()
        self.max_pages = int(os.getenv("MAX_PAGES_PER_SITE", "100"))
        self.request_delay = int(os.getenv("REQUEST_DELAY", "2"))
        
        # Define rules for following links
        self.rules = (
            Rule(
                LinkExtractor(
                    allow_domains=self.allowed_domains,
                    deny=(
                        r'\.(jpg|jpeg|png|gif|css|js|pdf|zip|tar|gz)$',
                        r'/wp-admin/',
                        r'/wp-login.php',
                        r'/feed/',
                        r'/tag/',
                        r'/category/',
                        r'/author/',
                        r'/page/',
                        r'/search/',
                        r'/cart/',
                        r'/checkout/',
                        r'/account/',
                    )
                ),
                callback='parse_page',
                follow=True
            ),
        )
        
        super().__init__(*args, **kwargs)

    def parse_page(self, response):
        """
        Parse each page and extract relevant information.
        """
        if len(self.visited_urls) >= self.max_pages:
            return
        
        url = response.url
        if url in self.visited_urls:
            return
        
        self.visited_urls.add(url)
        
        # Extract page information
        yield {
            'url': url,
            'title': response.css('title::text').get(),
            'meta_description': response.css('meta[name="description"]::attr(content)').get(),
            'h1_tags': response.css('h1::text').getall(),
            'h2_tags': response.css('h2::text').getall(),
            'internal_links': self._get_internal_links(response),
            'external_links': self._get_external_links(response),
            'images_without_alt': len(response.css('img:not([alt])').getall()),
            'platform_indicators': self._detect_platform(response),
        }

    def _get_internal_links(self, response) -> List[str]:
        """
        Extract internal links from the page.
        """
        domain = urlparse(response.url).netloc
        return [
            link for link in response.css('a::attr(href)').getall()
            if domain in link or link.startswith('/')
        ]

    def _get_external_links(self, response) -> List[str]:
        """
        Extract external links from the page.
        """
        domain = urlparse(response.url).netloc
        return [
            link for link in response.css('a::attr(href)').getall()
            if not (domain in link or link.startswith('/'))
        ]

    def _detect_platform(self, response) -> dict:
        """
        Detect the website platform based on various indicators.
        """
        indicators = {
            'wordpress': False,
            'shopify': False,
            'custom': False
        }
        
        # Check for WordPress indicators
        if any([
            '/wp-content/' in response.text,
            '/wp-includes/' in response.text,
            'wp-' in response.text,
            response.css('meta[name="generator"]::attr(content)').get() and 'WordPress' in response.css('meta[name="generator"]::attr(content)').get()
        ]):
            indicators['wordpress'] = True
        
        # Check for Shopify indicators
        if any([
            'myshopify.com' in response.text,
            'shopify.com' in response.text,
            response.css('script[src*="shopify"]').get(),
            response.css('link[href*="shopify"]').get()
        ]):
            indicators['shopify'] = True
        
        # If no specific platform is detected, mark as custom
        if not any(indicators.values()):
            indicators['custom'] = True
        
        return indicators

def run_crawler(start_urls: List[str], allowed_domains: Optional[List[str]] = None) -> None:
    """
    Run the crawler with the given start URLs and allowed domains.
    """
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/5.0 (compatible; ClientAcquisitionBot/1.0; +http://yourdomain.com)',
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': int(os.getenv("REQUEST_DELAY", "2")),
        'CONCURRENT_REQUESTS': int(os.getenv("MAX_CONCURRENT_REQUESTS", "5")),
        'COOKIES_ENABLED': False,
        'LOG_LEVEL': 'INFO'
    })
    
    process.crawl(WebsiteCrawler, start_urls=start_urls, allowed_domains=allowed_domains)
    process.start() 