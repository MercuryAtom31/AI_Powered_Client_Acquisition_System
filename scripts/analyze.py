import sys
import os
import argparse
from pathlib import Path
import logging
from typing import List, Dict
import json
from datetime import datetime

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
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
            logger.info(f"Successfully loaded {len(urls)} URLs from {file_path}")
            logger.debug(f"URLs loaded: {urls}")
            return urls
    except Exception as e:
        logger.error(f"Error loading seed URLs from {file_path}: {str(e)}")
        return []

def save_analysis_results(results: List[dict], output_file: str):
    """
    Save analysis results to a JSON file.
    """
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

def analyze_website(url: str, db_session) -> dict:
    """
    Analyze a website: extract contacts and analyze SEO.
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
        
        # Check if company already exists
        existing_company = db_session.query(Company).filter_by(website_url=url).first()
        
        if existing_company:
            # Update existing record
            existing_company.platform_type = platform_type
            existing_company.last_updated = datetime.utcnow()
            company = existing_company
        else:
            # Create new company record
            company = Company(
                website_url=url,
                platform_type=platform_type
            )
            db_session.add(company)
        
        db_session.commit()
        
        # Prepare detailed analysis
        analysis = {
            'url': url,
            'platform_type': platform_type.value,
            'contact_info': contact_info,
            'seo_analysis': seo_analysis,
            'analysis_date': datetime.utcnow().isoformat(),
            'recommendations': _generate_recommendations(seo_analysis)
        }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing website {url}: {str(e)}")
        return {
            'url': url,
            'error': str(e)
        }

def _generate_recommendations(seo_analysis: Dict) -> List[str]:
    """
    Générer des recommandations basées sur l'analyse SEO (en français).
    """
    recommendations = []
    
    # Recommandations sur le titre
    if 'title' in seo_analysis:
        if not seo_analysis['title']['is_optimal_length']:
            recommendations.append("Optimisez la longueur du titre (doit être sous 60 caractères)")
        if not seo_analysis['title']['has_keywords']:
            recommendations.append("Ajoutez des mots-clés pertinents dans le titre")
    
    # Recommandations sur la meta description
    if 'meta_description' in seo_analysis:
        if not seo_analysis['meta_description']['is_optimal_length']:
            recommendations.append("Optimisez la longueur de la meta description (doit être sous 160 caractères)")
        if not seo_analysis['meta_description']['has_keywords']:
            recommendations.append("Ajoutez des mots-clés pertinents dans la meta description")
    
    # Recommandations sur les en-têtes
    if 'headers' in seo_analysis:
        if not seo_analysis['headers']['has_h1']:
            recommendations.append("Ajoutez une balise H1 à la page")
        if seo_analysis['headers']['multiple_h1']:
            recommendations.append("Utilisez une seule balise H1 par page")
    
    # Recommandations sur les images
    if 'images' in seo_analysis:
        if seo_analysis['images']['images_without_alt'] > 0:
            recommendations.append(f"Ajoutez un texte alternatif (alt) à {seo_analysis['images']['images_without_alt']} images")
    
    # Recommandations sur le contenu
    if 'content_analysis' in seo_analysis:
        if not seo_analysis['content_analysis']['is_optimal_length']:
            recommendations.append("Optimisez la longueur du contenu (objectif : 300 à 2000 mots)")
    
    return recommendations

def main():
    """
    Main function to run the website analysis process.
    """
    parser = argparse.ArgumentParser(description='Analyze websites and generate SEO recommendations')
    parser.add_argument('--seed-urls', required=True, help='Path to file containing seed URLs')
    parser.add_argument('--output', default='analysis_results.json', help='Output file for results')
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
            logger.info(f"Analyzing {url}")
            result = analyze_website(url, db)
            results.append(result)
            
            # Print summary for each website
            if 'error' not in result:
                print(f"\nAnalysis for {url}:")
                print(f"Platform: {result['platform_type']}")
                print(f"Contact Emails Found: {len(result['contact_info'].get('emails', []))}")
                print("Top Recommendations:")
                for rec in result['recommendations'][:3]:  # Show top 3 recommendations
                    print(f"- {rec}")
                print("-" * 50)
        
        # Save results
        save_analysis_results(results, args.output)
        logger.info(f"Results saved to {args.output}")
        
    except Exception as e:
        logger.error(f"Error in analysis process: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 