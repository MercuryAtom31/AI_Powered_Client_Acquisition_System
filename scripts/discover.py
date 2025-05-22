import sys
import os
import argparse
from pathlib import Path
import logging
from typing import List
import json

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from ai_client_acquisition.discovery.crawler import run_crawler
from ai_client_acquisition.database.connection import get_db
from ai_client_acquisition.database.models import Company, PlatformType
from ai_client_acquisition.extraction.contact_extractor import ContactExtractor
from ai_client_acquisition.analysis.seo_analyzer import SEOAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_seed_urls(file_path: str) -> List[str]:
    """
    Load seed URLs from a file.
    """
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def save_discovery_results(results: List[dict], output_file: str):
    """
    Save discovery results to a JSON file.
    """
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

def process_discovered_website(url: str, db_session) -> dict:
    """
    Process a discovered website: extract contacts and analyze SEO.
    """
    try:
        # Initialize extractors
        contact_extractor = ContactExtractor()
        seo_analyzer = SEOAnalyzer()
        
        # Extract contact information
        contact_info = contact_extractor.extract_from_url(url)
        
        # Analyze SEO
        seo_analysis = seo_analyzer.analyze_url(url)
        
        # Determine platform type
        platform_type = PlatformType.UNKNOWN
        if seo_analysis.get('platform_indicators', {}).get('wordpress'):
            platform_type = PlatformType.WORDPRESS
        elif seo_analysis.get('platform_indicators', {}).get('shopify'):
            platform_type = PlatformType.SHOPIFY
        elif seo_analysis.get('platform_indicators', {}).get('custom'):
            platform_type = PlatformType.CUSTOM
        
        # Create company record
        company = Company(
            website_url=url,
            platform_type=platform_type
        )
        db_session.add(company)
        db_session.commit()
        
        return {
            'url': url,
            'platform_type': platform_type.value,
            'contact_info': contact_info,
            'seo_analysis': seo_analysis
        }
        
    except Exception as e:
        logger.error(f"Error processing website {url}: {str(e)}")
        return {
            'url': url,
            'error': str(e)
        }

def main():
    """
    Main function to run the website discovery process.
    """
    parser = argparse.ArgumentParser(description='Discover and analyze websites')
    parser.add_argument('--seed-urls', required=True, help='Path to file containing seed URLs')
    parser.add_argument('--output', default='discovery_results.json', help='Output file for results')
    parser.add_argument('--allowed-domains', help='Comma-separated list of allowed domains')
    args = parser.parse_args()
    
    try:
        # Load seed URLs
        seed_urls = load_seed_urls(args.seed_urls)
        logger.info(f"Loaded {len(seed_urls)} seed URLs")
        
        # Parse allowed domains
        allowed_domains = args.allowed_domains.split(',') if args.allowed_domains else None
        
        # Get database session
        db = next(get_db())
        
        # Process each seed URL
        results = []
        for url in seed_urls:
            logger.info(f"Processing {url}")
            result = process_discovered_website(url, db)
            results.append(result)
        
        # Save results
        save_discovery_results(results, args.output)
        logger.info(f"Results saved to {args.output}")
        
    except Exception as e:
        logger.error(f"Error in discovery process: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 