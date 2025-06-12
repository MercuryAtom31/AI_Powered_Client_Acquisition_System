import streamlit as st
import json
import pandas as pd
from collections import defaultdict, Counter
from urllib.parse import urlparse, urljoin
import numpy as np
import sqlite3
import requests # Added requests for direct scraping
from bs4 import BeautifulSoup # Added BeautifulSoup for parsing HTML
from ollama_client import OllamaClient
from hubspot_client import HubSpotClient
import time
from ai_client_acquisition.analysis.seo_analyzer import SEOAnalyzer # Import your modules
from ai_client_acquisition.extraction.contact_extractor import ContactExtractor
from ai_client_acquisition.discovery.google_places_client import GooglePlacesClient # Import Google Places Client
from typing import List, Dict, Optional # Import necessary types
from datetime import datetime # Import datetime
import logging # Import logging

# from ai_client_acquisition.discovery.crawler import WebsiteCrawler, run_crawler # Keep imports commented for now, as full crawler integration is complex in Streamlit

# Configure logging (move to top if needed)
logger = logging.getLogger(__name__)

# Set Streamlit page config first
st.set_page_config(page_title="Tableau de bord d'acquisition de clients par IA", layout="wide")

def _extract_navigation_links(html: str, base_url: str) -> List[str]:
    """
    Extracts relevant internal navigation links from HTML.
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        base_domain = urlparse(base_url).netloc
        internal_links = set()
        
        # Find common navigation elements and links within them
        nav_tags = soup.find_all(['nav', 'header', 'footer'])
        
        for tag in nav_tags:
            for link in tag.find_all('a', href=True):
                href = link['href']
                # Ignore anchor links, mailto, tel, etc.
                if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                    continue
                
                full_url = urljoin(base_url, href)
                parsed_full_url = urlparse(full_url)
                
                # Only include internal links and avoid file paths or simple / links (unless it's the base)
                if parsed_full_url.netloc == base_domain and parsed_full_url.scheme in ['http', 'https']:
                     # Basic check to avoid very short or potentially irrelevant links
                    if len(parsed_full_url.path) > 1 or parsed_full_url.path == '/':
                         internal_links.add(full_url)
        
        # Prioritize certain keywords in URLs if needed (optional)
        # relevant_links = [link for link in internal_links if any(keyword in link for keyword in ['services', 'about', 'contact'])]
        # If we want to limit the number of links:
        # return relevant_links[:limit] if limit else relevant_links
        
        return list(internal_links)
        
    except Exception as e:
        logger.error(f"Error extracting navigation links from {base_url}: {str(e)}")
        return []

def init_db():
    """Initialize the SQLite database and create the table if it doesn't exist.
    This version includes tables for business search results.
    """
    try:
        conn = sqlite3.connect('client_acquisition.db')
        cursor = conn.cursor()
        
        # Drop existing tables for simplicity during development
        # In a production app, you would use ALTER TABLE or migration tools
        # cursor.execute('DROP TABLE IF EXISTS analysis_results')
        # cursor.execute('DROP TABLE IF EXISTS businesses')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_query TEXT,
                place_id TEXT UNIQUE,
                name TEXT,
                address TEXT,
                website TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER,
                url TEXT,
                analysis_data TEXT,
                synced_to_hubspot BOOLEAN DEFAULT FALSE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (business_id) REFERENCES businesses(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        st.success("Database initialized with business search schema.")
    except Exception as e:
        st.error(f"Erreur lors de l'initialisation de la base de données : {e}")

# Initialize the database
init_db()

# st.set_page_config(page_title="Tableau de bord d'acquisition de clients par IA", layout="wide") # Moved to top
st.title("Tableau de bord d'acquisition de clients par IA")

# Initialize clients and analyzers
ollama_client = OllamaClient()
seo_analyzer = SEOAnalyzer()
contact_extractor = ContactExtractor()
google_places_client = GooglePlacesClient() # Initialize Google Places Client

try:
    hubspot_client = HubSpotClient()
    hubspot_available = True
except Exception as e:
    st.warning("L'intégration HubSpot n'est pas disponible. Veuillez vérifier votre clé API dans le fichier .env.")
    hubspot_available = False


def run_analysis_pipeline(urls: List[str], force_reanalysis: bool):
    """
    Runs the full analysis pipeline for a list of URLs and stores results.
    This is for direct URL input.
    """
    if not urls:
        st.warning("No valid URLs provided for analysis.")
        return
        
    st.info(f"Analyse de {len(urls)} URL(s) en cours...")
    progress_bar = st.progress(0)
    analyzed_count = 0
    
    # Create a copy of the URLs to iterate over to prevent modifying the list during iteration
    urls_to_process_in_this_run = list(urls)

    for i, url in enumerate(urls_to_process_in_this_run):
        try:
            # Check if this URL (from direct input) already exists in analysis_results
            # This is a simplified check; ideally, you'd handle updates more granularly
            conn = sqlite3.connect('client_acquisition.db')
            cursor = conn.cursor()
            if force_reanalysis:
                # If force_reanalysis is true, delete existing analysis for this URL
                cursor.execute('DELETE FROM analysis_results WHERE url = ?', (url,))
                st.info(f"Forcing re-analysis for: {url}. Deleting old data.")
            
            cursor.execute('SELECT id FROM analysis_results WHERE url = ?', (url,))
            existing_analysis = cursor.fetchone()
            conn.close()
            
            if existing_analysis and not force_reanalysis:
                st.info(f"Skipping already analyzed URL (from direct input): {url}")
                progress_bar.progress((i + 1) / len(urls_to_process_in_this_run))
                continue # Skip if already analyzed

            # --- Integrated Analysis Pipeline ---
            st.write(f"Analyse de : {url}")
            
            # 1. Fetch HTML
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                response = requests.get(url, timeout=15, headers=headers) # Added headers
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                html_content = response.text
                
                # Extract navigation links for multi-page analysis (only for the initial direct URL)
                if i == 0: # Only extract links from the first URL provided directly by the user
                    nav_links = _extract_navigation_links(html_content, url)
                    st.info(f"Found {len(nav_links)} navigation links from {url}")
                    # Limit the number of navigation links to analyze for direct URL input
                    links_to_add = nav_links[:3] # Limit to top 3 navigation links
                    # Add newly found links to the overall urls list for future processing (not in current run)
                    # Note: These links are currently just being added to the overall list for future analysis
                    # if the user re-runs or if the business search processes them.
                    for link in links_to_add:
                        # This logic will add them to the global 'urls' list used by the UI, but not process them in this run.
                        # For a full crawler, this would be more sophisticated.
                        if link not in urls: # 'urls' is the original input list (or global if used) - ensuring it's not re-added
                            urls.append(link) # This appends to the original list, but the iteration is on urls_to_process_in_this_run

            except requests.exceptions.RequestException as e:
                st.error(f"Erreur de requête pour {url}: {str(e)}")
                progress_bar.progress((i + 1) / len(urls_to_process_in_this_run))
                continue # Skip to the next URL

            # 2. Extract Contact Info (This is done within SEOAnalyzer now, adjust if needed)
            # Assuming SEOAnalyzer handles contact extraction or we do it separately here if needed

            # 3. Perform SEO Analysis
            seo_analysis = seo_analyzer.analyze_html(html_content, url) # Use analyze_html with pre-fetched HTML
            
            # 4. Perform AI Analysis (using OllamaClient)
            ai_analysis_result = {} # Initialize with empty dict
            try:
                # Pass raw HTML content for AI analysis, or a structured summary if preferred
                ai_analysis_result = ollama_client.generate_seo_analysis(url, {"html_content_summary": html_content[:2000]}) # Limit content size
                if "response" in ai_analysis_result:
                    st.write("AI Analysis:", ai_analysis_result["response"][:200] + "...") # Show snippet
            except Exception as ai_e:
                logger.error(f"Error during AI analysis for {url}: {str(ai_e)}")
                ai_analysis_result = {"error": str(ai_e), "response": "Error during AI analysis."}

            # 5. Combine data and store
            # For direct URL input, we don't link to a specific business found via search
            # We'll store it directly in analysis_results with no business_id
            full_analysis_result = {
                "url": url,
                "seo_analysis": seo_analysis,
                "ai_analysis": ai_analysis_result # Add AI analysis result
                # Add other relevant data if SEOAnalyzer returns it directly or call other extractors
            }

            conn = sqlite3.connect('client_acquisition.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO analysis_results (url, analysis_data, synced_to_hubspot)
                VALUES (?, ?, ?)
            ''', (url, json.dumps(full_analysis_result), False))

            conn.commit()
            conn.close()

            analyzed_count += 1

            # --- End Integrated Analysis Pipeline ---
            
            # Update progress
            progress_bar.progress((i + 1) / len(urls_to_process_in_this_run))
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de {url}: {str(e)}")
            st.error(f"Erreur lors de l'analyse de {url}: {str(e)}")
            progress_bar.progress((i + 1) / len(urls_to_process_in_this_run))

    st.success(f"Analyse terminée pour {analyzed_count} URL(s) !")



# URL Input Section
st.header("Analyse d'URL")
urls_input = st.text_area(
    "Entrez les URLs à analyser (une par ligne)",
    height=150,
    help="Entrez une ou plusieurs URLs à analyser. Chaque URL doit être sur une nouvelle ligne."
)
force_reanalysis = st.checkbox("Forcer la ré-analyse des URLs existantes")

if st.button("Analyser les URLs"):
    if not urls_input.strip():
        st.error("Veuillez entrer au moins une URL à analyser.")
    else:
        urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
        
        # Simple URL validation (can be enhanced)
        valid_urls = []
        for url in urls:
            # Add http:// if not present for basic validation
            if not urlparse(url).scheme in ['http', 'https']:
                 url = 'http://' + url
            if urlparse(url).scheme in ['http', 'https']:
                valid_urls.append(url)
            else:
                st.warning(f"URL invalide ignorée : {url} (schéma manquant ou incorrect)")
                
        run_analysis_pipeline(valid_urls, force_reanalysis)


def run_business_search_analysis(city: str, industry: str, batch_size: int = 5):
    """
    Performs business search, finds unanalyzed websites for this query,
    analyzes them (homepage + nav links), and stores results.
    """
    search_query = f"{industry} in {city}"
    st.info(f"Searching for {search_query}...")
    
    if not google_places_client.api_key:
        st.error("Google Places API key not found. Please add GOOGLE_PLACES_API_KEY to your .env file.")
        return
        
    conn = sqlite3.connect('client_acquisition.db')
    cursor = conn.cursor()
    
    # Find businesses for this search query that haven't been analyzed yet
    # This requires fetching more places than needed initially to find unanalyzed ones
    # For simplicity, let's fetch a reasonable number (e.g., 50) and filter locally
    all_places = google_places_client.search_places(keyword=industry, location=city, radius=50000)
    
    if not all_places:
        st.warning(f"No businesses found for {search_query}.")
        conn.close()
        return
    
    st.info(f"Found {len(all_places)} potential businesses via Google Places. Checking analysis status...")
    
    unanalyzed_businesses = []
    for place in all_places:
        place_id = place.get('place_id')
        if not place_id:
            continue
            
        # Check if this business (by place_id) has been analyzed for this specific search_query
        cursor.execute('''
            SELECT b.id FROM businesses b
            JOIN analysis_results ar ON b.id = ar.business_id
            WHERE b.place_id = ? AND b.search_query = ?
            LIMIT 1
        ''', (place_id, search_query))
        already_analyzed = cursor.fetchone()
        
        if not already_analyzed:
            # Get place details to ensure we have the website
            details = google_places_client.get_place_details(place_id)
            if details and 'website' in details:
                unanalyzed_businesses.append({
                    'place_id': place_id,
                    'name': details.get('name'),
                    'address': details.get('formatted_address'),
                    'website': details['website']
                })
        
        if len(unanalyzed_businesses) >= batch_size:
            break # Found enough unanalyzed businesses for this batch

    conn.close()

    if not unanalyzed_businesses:
        st.warning(f"No new unanalyzed businesses found for {search_query}.")
        return

    st.info(f"Analyzing {len(unanalyzed_businesses)} new businesses...")
    business_analysis_progress = st.progress(0, text="Analyzing businesses...")

    for i, business in enumerate(unanalyzed_businesses):
        business_url = business['website']
        st.write(f"Analyzing business: {business.get('name', 'N/A')} ({business_url})")
        
        try:
            conn = sqlite3.connect('client_acquisition.db')
            cursor = conn.cursor()
            
            # Insert the business into the database if it doesn't exist for this query
            cursor.execute('''
                INSERT OR IGNORE INTO businesses (search_query, place_id, name, address, website)
                VALUES (?, ?, ?, ?, ?)
            ''', (search_query, business['place_id'], business['name'], business['address'], business['website']))
            
            # Get the business_id
            cursor.execute('SELECT id FROM businesses WHERE place_id = ? LIMIT 1', (business['place_id'],))
            business_id = cursor.fetchone()[0]
            
            conn.commit()
            conn.close()

            # --- Analysis for Homepage ---
            st.write(f"- Analyzing homepage: {business_url}")
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                response = requests.get(business_url, timeout=15, headers=headers) # Fetch homepage HTML
                response.raise_for_status()
                homepage_html = response.text
                
                homepage_analysis = seo_analyzer.analyze_html(homepage_html, business_url) # Analyze homepage HTML
                
                # Perform AI Analysis for homepage
                homepage_ai_analysis = {} # Initialize
                try:
                    homepage_ai_analysis = ollama_client.generate_seo_analysis(business_url, {"html_content_summary": homepage_html[:2000]})
                except Exception as ai_e:
                    logger.error(f"Error during AI analysis for homepage {business_url}: {str(ai_e)}")
                    homepage_ai_analysis = {"error": str(ai_e), "response": "Error during AI analysis for homepage."}

                if homepage_analysis:
                     conn = sqlite3.connect('client_acquisition.db')
                     cursor = conn.cursor()
                     cursor.execute('''
                         INSERT INTO analysis_results (business_id, url, analysis_data, synced_to_hubspot)
                         VALUES (?, ?, ?, ?)
                     ''', (business_id, business_url, json.dumps({"seo_analysis": homepage_analysis, "ai_analysis": homepage_ai_analysis}), False))
                     conn.commit()
                     conn.close()
                     st.success("  Homepage analysis complete and saved.")
                
                # --- Analysis for Navigation Links (Limited) ---
                st.write("- Extracting and analyzing navigation links...")
                nav_links = _extract_navigation_links(homepage_html, business_url)
                st.write(f"  Found {len(nav_links)} potential navigation links.")
                
                # Limit the number of navigation links to analyze (e.g., max 3)
                links_to_analyze = nav_links[:3]
                
                for link_url in links_to_analyze:
                    st.write(f"  - Analyzing navigation link: {link_url}")
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                        link_response = requests.get(link_url, timeout=15, headers=headers)
                        link_response.raise_for_status()
                        link_html_content = link_response.text

                        link_seo_analysis = seo_analyzer.analyze_html(link_html_content, link_url) # Analyze navigation link HTML

                        # Perform AI Analysis for navigation link
                        link_ai_analysis = {} # Initialize
                        try:
                            link_ai_analysis = ollama_client.generate_seo_analysis(link_url, {"html_content_summary": link_html_content[:2000]})
                        except Exception as ai_e:
                            logger.error(f"Error during AI analysis for link {link_url}: {str(ai_e)}")
                            link_ai_analysis = {"error": str(ai_e), "response": "Error during AI analysis for link."}

                        if link_seo_analysis:
                             conn = sqlite3.connect('client_acquisition.db')
                             cursor = conn.cursor()
                             cursor.execute('''
                                 INSERT INTO analysis_results (business_id, url, analysis_data, synced_to_hubspot)
                                 VALUES (?, ?, ?, ?)
                             ''', (business_id, link_url, json.dumps({"seo_analysis": link_seo_analysis, "ai_analysis": link_ai_analysis}), False))
                             conn.commit()
                             conn.close()
                             st.success(f"    Analysis complete and saved for {link_url}.")
                    except requests.exceptions.RequestException as e:
                        st.error(f"  Error fetching or analyzing navigation link {link_url}: {str(e)}")
            
            except requests.exceptions.RequestException as e:
                 st.error(f"  Error fetching or analyzing homepage {business_url}: {str(e)}")

            business_analysis_progress.progress((i + 1) / len(unanalyzed_businesses), text=f"Analyzing businesses... {i+1}/{len(unanalyzed_businesses)}")

        except Exception as e:
             logger.error(f"Error analyzing business {business.get('name')}: {str(e)}")
             st.error(f"Error analyzing business {business.get('name')}: {str(e)}")

    business_analysis_progress.empty()
    st.success(f"Analysis complete for {len(unanalyzed_businesses)} new businesses!")
    
    # After analysis, reload data to display new results
    st.experimental_rerun() # Rerun the app to show updated data

# Helper function to display a single analysis result dictionary.
def _display_analysis_result(analysis_result: Dict, hubspot_available: bool):
    """
    Helper function to display a single analysis result dictionary.
    """
    # Display Contact Information (if available and extracted)
    contact_info = analysis_result.get('contact_info', {})
    if contact_info:
         st.subheader("Coordonnées")
         emails = contact_info.get('emails', [])
         st.write("Emails:", ", ".join(emails) if isinstance(emails, list) else "N/A")
         phones = contact_info.get('phones', [])
         st.write("Téléphones:", ", ".join(phones) if isinstance(phones, list) else "N/A")
    
    # Display SEO Analysis
    st.subheader("Analyse SEO")
    seo = analysis_result.get('seo_analysis', {})
    
    if seo:
        st.write(f"**Overall Score:** {seo.get('overall_score', 'N/A')}/100")
        
        # Display results for each checker
        checks_results = seo.get('checks', {})
        if checks_results:
            st.subheader("Detailed Checks")
            for check_name, check_result in checks_results.items():
                st.write(f"**{check_name.replace('_', ' ').title()} Check:**")
                if 'error' in check_result:
                    st.error(f"Error running check: {check_result['error']}")
                else:
                    # Display key-value pairs from check results (excluding recommendations)
                    details_to_display = {k: v for k, v in check_result.items() if k != 'recommendations'}
                    if details_to_display:
                        for key, value in details_to_display.items():
                             # Format boolean values nicely
                            if isinstance(value, bool):
                                 st.write(f"  - {key.replace('_', ' ').title()}: {'Yes' if value else 'No'}")
                            elif isinstance(value, list):
                                 st.write(f"  - {key.replace('_', ' ').title()}: {value}") # Display list as is for now
                            elif isinstance(value, dict):
                                 st.write(f"  - {key.replace('_', ' ').title()}: {value}") # Display dict as is for now
                            else:
                                 st.write(f"  - {key.replace('_', ' ').title()}: {value}")
                    
                    # Display recommendations for this specific check
                    check_recommendations = check_result.get('recommendations', [])
                    if check_recommendations:
                        st.write("  **Recommendations for this check:**")
                        for rec in check_recommendations:
                            st.write(f"    - {rec}")
                    else:
                        st.write("  No specific details available.")
        
        # Display overall recommendations
        overall_recommendations = seo.get('recommendations', [])
        if overall_recommendations:
            st.subheader("Overall Recommendations")
            for rec in overall_recommendations:
                st.write(f"- {rec}")
        
        # Display critical issues
        critical_issues = seo.get('critical_issues', [])
        if critical_issues:
            st.subheader("Critical Issues")
            for issue in critical_issues:
                st.error(f"- {issue}")
    else:
        st.write("SEO analysis results not available.")
    
    # Display AI Analysis
    ai_analysis = analysis_result.get('ai_analysis', {})
    if isinstance(ai_analysis, dict):
        st.subheader("Analyse IA")
        # Display only the 'response' from AI analysis, if available.
        # If 'response' is not present, display the raw JSON for debugging.
        if "response" in ai_analysis:
            st.write(ai_analysis['response'])
        elif "error" in ai_analysis:
            st.error(f"Erreur lors de l'analyse IA : {ai_analysis['error']}")
        else:
            st.write('Aucune analyse IA disponible ou format inattendu.')
            st.json(ai_analysis) # Display raw JSON for debugging unexpected formats
    
    # Display Recommendations from AI Analysis
    ai_recommendations = analysis_result.get('recommendations', [])
    if ai_recommendations:
         st.subheader("Recommandations IA")
         for rec in ai_recommendations:
              st.write(f"- {rec}")

    # HubSpot Integration Button (adjust key for uniqueness)
    if hubspot_available:
        # Use a unique key based on the URL being displayed
        if st.button(f"Pousser vers HubSpot ({analysis_result.get('url', 'N/A')})", key=f"hubspot_{analysis_result.get('url')}"):
            with st.spinner("Envoi vers HubSpot..."):
                # Prepare data for HubSpot (adjust field names as needed)
                hubspot_contact_info = {
                    "email": contact_info.get('emails', [''])[0], # Take the first email
                    "website": analysis_result.get('url', ''), # Use the analyzed URL as the website
                    "seo_analysis": json.dumps(seo) if seo else '', # Convert dict to JSON string
                    "ai_analysis": json.dumps(ai_analysis) if isinstance(ai_analysis, dict) else '', # Convert dict to JSON string
                    # You might want to add business name/details here if available from business search
                }
                
                contact_id = hubspot_client.create_or_update_contact(hubspot_contact_info)
                if contact_id:
                    st.success(f"Envoyé avec succès vers HubSpot pour {analysis_result.get('url', 'N/A')} !")
                else:
                    st.error(f"Échec de l'envoi vers HubSpot pour {analysis_result.get('url', 'N/A')}")

# Load and display results
def load_data():
    """
    Loads all analysis results, organized by business or direct URL.
    """
    try:
        conn = sqlite3.connect('client_acquisition.db')
        cursor = conn.cursor()
        
        # Fetch businesses and their linked analysis results
        cursor.execute('''
            SELECT b.name, b.website, b.search_query, ar.url, ar.analysis_data
            FROM businesses b
            JOIN analysis_results ar ON b.id = ar.business_id
            ORDER BY b.search_query, b.name, ar.url
        ''')
        business_results = cursor.fetchall()
        
        # Fetch analysis results from direct URL input (where business_id is NULL)
        cursor.execute('''
            SELECT NULL, ar.url, NULL, ar.url, ar.analysis_data
            FROM analysis_results ar
            WHERE ar.business_id IS NULL
            ORDER BY ar.url
        ''')
        direct_url_results = cursor.fetchall()
        
        conn.close()
        
        # Organize results for display
        organized_results = defaultdict(lambda: defaultdict(list))
        
        # Add business search results
        for name, website, search_query, url, analysis_data_json in business_results:
            organized_results[f"Search: {search_query}"][f"Business: {name} ({website})"][url].append(json.loads(analysis_data_json))
            
        # Add direct URL results
        for _, url, _, _, analysis_data_json in direct_url_results:
             # Use a distinct key for direct URLs, e.g., based on the URL itself
             # Simpler structure for direct URLs: { url: analysis_dict }
             organized_results["Direct URLs"][url] = json.loads(analysis_data_json)
        
        return organized_results
        
    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return {}

# Display results
st.header("Résultats de l'analyse")

organized_data = load_data()

if organized_data:
    # Summary statistics (can be updated to reflect new data structure)
    # st.header("Résumé de l'analyse") # Already have this header
    col1, col2, col3, col4 = st.columns(4)
    
    # Simplified summary for now - count total analyzed URLs and businesses
    total_analyzed_urls = sum(len(analysis_list) for businesses_or_urls in organized_data.values() for pages in businesses_or_urls.values() for analysis_list in pages.values())
    total_businesses = sum(len(businesses) for key, businesses in organized_data.items() if key.startswith("Search:"))
    total_direct_urls = len(organized_data.get("Direct URLs", {}))
    
    col1.metric("Total URLs Analysées", total_analyzed_urls)
    col2.metric("Total Entreprises Trouvées", total_businesses)
    col3.metric("Total URLs Directes Analysées", total_direct_urls)
    # col4.metric("Sites avec Téléphone", "N/A") # Update or remove
    
    # Detailed Results
    # st.header("Analyse détaillée") # Already have this header

    for group_name, businesses_or_urls in organized_data.items():
        st.subheader(group_name)
        for business_or_url, pages in businesses_or_urls.items():
            # Check if it's a business search result group or direct URL input group
            if group_name.startswith("Search:"):
                # This is a business search result (grouped by business)
                with st.expander(business_or_url): # business_or_url is like "Business: Name (website)"
                     for page_url, analyses in pages.items(): # pages is like { page_url: [analysis_dict] }
                          st.write(f"**Page:** {page_url}")
                          for analysis_result in analyses:
                               _display_analysis_result(analysis_result, hubspot_available)
            else:
                # This is a direct URL input group
                url = business_or_url # business_or_url is the URL string directly
                analysis_result = pages # pages is the analysis dictionary directly
                with st.expander(url):
                    _display_analysis_result(analysis_result, hubspot_available)

    # Download option
    if organized_data:
        # Flatten the organized_data into a list of rows for export
        csv_rows = []

        for group_name, businesses_or_urls in organized_data.items():
            for business_or_url, pages in businesses_or_urls.items():
                if group_name.startswith("Search:"):
                    for page_url, analyses in pages.items():
                        for analysis_result in analyses:
                            # Extract contact info, SEO, and AI analysis for CSV
                            contact_info = analysis_result.get('contact_info', {})
                            seo = analysis_result.get('seo_analysis', {})
                            ai_analysis = analysis_result.get('ai_analysis', {})
                            
                            csv_rows.append({
                                "Group": group_name,
                                "Business": business_or_url, # This contains Name (Website)
                                "URL": page_url,
                                "SEO Score": seo.get("overall_score", "N/A"),
                                "Critical Issues": ", ".join(seo.get("critical_issues", [])),
                                "Emails": ", ".join(contact_info.get('emails', [])),
                                "Phones": ", ".join(contact_info.get('phones', [])),
                                "AI Analysis": ai_analysis.get('response', '') if isinstance(ai_analysis, dict) else '',
                                # Add other fields as needed
                            })
                else:  # Direct URL group
                    # For direct URLs, business_or_url is the URL itself
                    url = business_or_url
                    analysis_result = pages # pages is the analysis dictionary directly for direct URLs
                    
                    # Extract contact info, SEO, and AI analysis for CSV
                    contact_info = analysis_result.get('contact_info', {})
                    seo = analysis_result.get('seo_analysis', {})
                    ai_analysis = analysis_result.get('ai_analysis', {})
                    
                    csv_rows.append({
                        "Group": group_name,
                        "Business": "N/A", # No business info for direct URLs
                        "URL": url,
                        "SEO Score": seo.get("overall_score", "N/A"),
                        "Critical Issues": ", ".join(seo.get("critical_issues", [])),
                        "Emails": ", ".join(contact_info.get('emails', [])),
                        "Phones": ", ".join(contact_info.get('phones', [])),
                        "AI Analysis": ai_analysis.get('response', '') if isinstance(ai_analysis, dict) else '',
                        # Add other fields as needed
                    })

        # Only show the download button if we have data
        if csv_rows:
            df = pd.DataFrame(csv_rows)
            st.download_button(
                label="Télécharger les résultats d'analyse (CSV)",
                data=df.to_csv(index=False),
                file_name="analysis_results.csv",
                mime="text/csv"
            )


# Business Search Section (New)
st.header("Business Search by City and Industry")
st.write("Search for businesses based on location and category. This uses the Google Places API.")
st.warning("A Google Places API key is required for this feature. Add `GOOGLE_PLACES_API_KEY='YOUR_API_KEY'` to your `.env` file.")

city = st.text_input("City", help="Enter the city name (e.g., London)")
industry = st.text_input("Industry / Business Type", help="Enter the type of business (e.g., digital marketing agency)")

# Add a batch size input
batch_size = st.number_input("Number of businesses to analyze per search", min_value=1, value=5, step=1)

if st.button("Start Business Search"):
    if not city or not industry:
        st.error("Please enter both City and Industry.")
    else:
        run_business_search_analysis(city, industry, batch_size)

# Placeholder for displaying business search results (Now handled by the main display logic)
# st.subheader("Business Search Results")
# st.write("Search results will appear here after you run a search.")