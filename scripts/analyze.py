import sys
import os
import argparse
from pathlib import Path
import logging
from typing import List, Dict
import json
from datetime import datetime
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from ai_client_acquisition.analysis.seo_analyzer import SEOAnalyzer
from ai_client_acquisition.extraction.contact_extractor import ContactExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_navbar_links(main_url):
    try:
        response = requests.get(main_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        nav = soup.find("nav")
        links = set()
        def is_valid_link(href):
            if href.startswith("http"):
                return urlparse(href).netloc == urlparse(main_url).netloc
            return href.startswith("/")
        if nav:
            for a in nav.find_all("a", href=True):
                href = a["href"]
                if is_valid_link(href):
                    full_url = urljoin(main_url, href)
                    links.add(full_url)
        else:
            header = soup.find("header")
            if header:
                for a in header.find_all("a", href=True):
                    href = a["href"]
                    if is_valid_link(href):
                        full_url = urljoin(main_url, href)
                        links.add(full_url)
        links.add(main_url)
        return list(links)
    except Exception as e:
        logger.error(f"Error extracting navbar links from {main_url}: {e}")
        return [main_url]

def generate_recommendations(seo_analysis):
    recommendations = []
    # Title recommendations
    if 'title' in seo_analysis:
        if not seo_analysis['title']['is_optimal_length']:
            recommendations.append("Optimisez la longueur du titre (doit être sous 60 caractères)")
        if not seo_analysis['title']['has_keywords']:
            recommendations.append("Ajoutez des mots-clés pertinents dans le titre")
    # Meta description recommendations
    if 'meta_description' in seo_analysis:
        if not seo_analysis['meta_description']['is_optimal_length']:
            recommendations.append("Optimisez la longueur de la meta description (doit être sous 160 caractères)")
        if not seo_analysis['meta_description']['has_keywords']:
            recommendations.append("Ajoutez des mots-clés pertinents dans la meta description")
    # Header recommendations
    if 'headers' in seo_analysis:
        if not seo_analysis['headers']['has_h1']:
            recommendations.append("Ajoutez une balise H1 à la page")
        if seo_analysis['headers']['multiple_h1']:
            recommendations.append("Utilisez une seule balise H1 par page")
    # Image recommendations
    if 'images' in seo_analysis:
        if seo_analysis['images']['images_without_alt'] > 0:
            recommendations.append(f"Ajoutez un texte alternatif (alt) à {seo_analysis['images']['images_without_alt']} images")
    # Content recommendations
    if 'content_analysis' in seo_analysis:
        if not seo_analysis['content_analysis']['is_optimal_length']:
            recommendations.append("Optimisez la longueur du contenu (objectif : 300 à 2000 mots)")
    return recommendations

def analyze_url(url):
    try:
        contact_extractor = ContactExtractor()
        seo_analyzer = SEOAnalyzer()
        contact_info = contact_extractor.extract_from_url(url)
        seo_analysis = seo_analyzer.analyze_url(url)
        platform_type = "unknown"
        if seo_analysis.get('platform_indicators', {}).get('wordpress'):
            platform_type = "wordpress"
        elif seo_analysis.get('platform_indicators', {}).get('shopify'):
            platform_type = "shopify"
        elif seo_analysis.get('platform_indicators', {}).get('custom'):
            platform_type = "custom"
        recommendations = generate_recommendations(seo_analysis)
        return {
            "url": url,
            "platform_type": platform_type,
            "contact_info": contact_info,
            "seo_analysis": seo_analysis,
            "recommendations": recommendations,
        }
    except Exception as e:
        logger.error(f"Error analyzing {url}: {e}")
        return {
            "url": url,
            "error": str(e)
        }

def load_seed_urls(file_path: str) -> List[str]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
            logger.info(f"Successfully loaded {len(urls)} URLs from {file_path}")
            return urls
    except Exception as e:
        logger.error(f"Error loading seed URLs from {file_path}: {str(e)}")
        return []

def save_analysis_results(results: List[dict], output_file: str):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description='Analyze only the main page and navbar subpages for each seed URL')
    parser.add_argument('--seed-urls', required=True, help='Path to file containing seed URLs')
    parser.add_argument('--output', default='analysis_results.json', help='Output file for results')
    args = parser.parse_args()

    seed_urls = load_seed_urls(args.seed_urls)
    all_results = []
    seen_urls = set()
    for seed_url in seed_urls:
        logger.info(f"Extracting navbar links from {seed_url}")
        subpages = get_navbar_links(seed_url)
        logger.info(f"  Found {len(subpages)} navbar pages (including main page)")
        for url in subpages:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            logger.info(f"    Analyzing: {url}")
            result = analyze_url(url)
            all_results.append(result)
            save_analysis_results(all_results, args.output)
    logger.info(f"Saved all results to {args.output}")

if __name__ == "__main__":
    main() 