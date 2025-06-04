import streamlit as st
import json
import pandas as pd
from collections import defaultdict, Counter
from urllib.parse import urlparse
import numpy as np
import sqlite3
import requests # Added requests for direct scraping
from bs4 import BeautifulSoup # Added BeautifulSoup for parsing HTML
from ollama_client import OllamaClient
from hubspot_client import HubSpotClient
import time
from ai_client_acquisition.analysis.seo_analyzer import SEOAnalyzer # Import your modules
from ai_client_acquisition.extraction.contact_extractor import ContactExtractor
# from ai_client_acquisition.discovery.crawler import WebsiteCrawler, run_crawler # Keep imports commented for now, as full crawler integration is complex in Streamlit

def init_db():
    """Initialize the SQLite database and create the table if it doesn't exist.
    """
    try:
        conn = sqlite3.connect('client_acquisition.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                url TEXT PRIMARY KEY,
                analysis_data TEXT,
                synced_to_hubspot BOOLEAN DEFAULT FALSE
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Erreur lors de l'initialisation de la base de données : {e}")

# Initialize the database
init_db()

st.set_page_config(page_title="Tableau de bord d'acquisition de clients par IA", layout="wide")
st.title("Tableau de bord d'acquisition de clients par IA")

# Initialize clients and analyzers
ollama_client = OllamaClient()
seo_analyzer = SEOAnalyzer()
contact_extractor = ContactExtractor()
try:
    hubspot_client = HubSpotClient()
    hubspot_available = True
except Exception as e:
    st.warning("L'intégration HubSpot n'est pas disponible. Veuillez vérifier votre clé API dans le fichier .env.")
    hubspot_available = False

# URL Input Section
st.header("Analyse d'URL")
urls_input = st.text_area(
    "Entrez les URLs à analyser (une par ligne)",
    height=150,
    help="Entrez une ou plusieurs URLs à analyser. Chaque URL doit être sur une nouvelle ligne."
)

if st.button("Analyser les URLs"):
    if not urls_input.strip():
        st.error("Veuillez entrer au moins une URL à analyser.")
    else:
        urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
        
        # Simple URL validation (can be enhanced)
        valid_urls = []
        for url in urls:
            if urlparse(url).scheme in ['http', 'https']:
                valid_urls.append(url)
            else:
                st.warning(f"URL invalide ignorée : {url} (schéma manquant ou incorrect)")
                
        if not valid_urls:
            st.error("Aucune URL valide à analyser.")
            st.stop()

        st.info(f"Analyse de {len(valid_urls)} URL(s) en cours...")
        progress_bar = st.progress(0)
        analyzed_count = 0

        for i, url in enumerate(valid_urls):
            try:
                # --- Integrated Analysis Pipeline ---
                st.write(f"Analyse de : {url}")
                
                # 1. Fetch HTML
                try:
                    response = requests.get(url, timeout=15) # Added timeout
                    response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                    html_content = response.text
                except requests.exceptions.RequestException as e:
                    st.error(f"Erreur de requête pour {url}: {str(e)}")
                    progress_bar.progress((i + 1) / len(valid_urls))
                    continue # Skip to the next URL

                # 2. Extract Contact Info
                contact_info = contact_extractor.extract_from_html(html_content, url)

                # 3. Perform SEO Analysis
                seo_analysis = seo_analyzer.analyze_html(html_content, url)
                
                # 4. Combine data for LLM (including basic extracted info)
                # Prepare content for LLM - adjust based on what analyze_html and extract_from_html return
                llm_content = {
                    "url": url,
                    "contact_info": contact_info,
                    "seo_analysis": seo_analysis,
                    # You might add more specific text content extraction here if needed for LLM
                    # For now, passing the structured analysis results
                }
                
                # 5. Generate AI Analysis using Ollama
                # Note: The generate_seo_analysis prompt in ollama_client.py might need adjustment
                # to better utilize the structured seo_analysis and contact_info data
                ai_analysis = ollama_client.generate_seo_analysis(url, llm_content)

                # 6. Prepare full analysis result to save
                full_analysis_result = {
                    "url": url,
                    "contact_info": contact_info,
                    "seo_analysis": seo_analysis,
                    "ai_analysis": ai_analysis,
                    "recommendations": ai_analysis.get('response', '').split('\n') if isinstance(ai_analysis, dict) and ai_analysis.get('response') else [] # Simple split for display
                }

                # 7. Store in SQLite
                conn = sqlite3.connect('client_acquisition.db')
                cursor = conn.cursor()
                # Check if URL already exists to avoid duplicate primary key error
                cursor.execute('SELECT url FROM analysis_results WHERE url = ?', (url,))
                existing_url = cursor.fetchone()
                
                if existing_url:
                    # Update existing record
                    cursor.execute('''
                        UPDATE analysis_results
                        SET analysis_data = ?, synced_to_hubspot = ?
                        WHERE url = ?
                    ''', (json.dumps(full_analysis_result), False, url))
                    st.info(f"Mise à jour de l'analyse pour : {url}")
                else:
                    # Insert new record
                    cursor.execute('''
                        INSERT INTO analysis_results (url, analysis_data, synced_to_hubspot)
                        VALUES (?, ?, ?)
                    ''', (url, json.dumps(full_analysis_result), False))
                    st.info(f"Nouvelle analyse enregistrée pour : {url}")

                conn.commit()
                conn.close()

                analyzed_count += 1

                # --- End Integrated Analysis Pipeline ---
                
                # Update progress
                progress_bar.progress((i + 1) / len(valid_urls))
                
            except Exception as e:
                st.error(f"Erreur lors de l'analyse de {url}: {str(e)}")
                progress_bar.progress((i + 1) / len(valid_urls))

        st.success(f"Analyse terminée pour {analyzed_count} URL(s) !")

# Load and display results
def load_data():
    try:
        conn = sqlite3.connect('client_acquisition.db')
        cursor = conn.cursor()
        # Only select analysis_data column as before
        cursor.execute('SELECT analysis_data FROM analysis_results')
        results = [json.loads(row[0]) for row in cursor.fetchall()]
        conn.close()
        return results
    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return []

data = load_data()

if data:
    # Summary statistics
    st.header("Résumé de l'analyse")
    col1, col2, col3, col4 = st.columns(4)
    
    unique_domains = len(set(urlparse(r['url']).netloc for r in data if 'url' in r))
    total_emails = sum(len(r.get('contact_info', {}).get('emails', [])) for r in data if 'contact_info' in r)
    sites_with_email = sum(1 for r in data if r.get('contact_info', {}).get('emails'))
    sites_with_phone = sum(1 for r in data if r.get('contact_info', {}).get('phones'))
    
    col1.metric("Total Entreprises", unique_domains)
    col2.metric("Total Contacts", total_emails)
    col3.metric("Sites avec Email", sites_with_email)
    col4.metric("Sites avec Téléphone", sites_with_phone)
    
    # Detailed Results
    st.header("Analyse détaillée")
    for result in data:
        # Added checks for keys in result dictionary
        url = result.get('url', 'URL inconnue')
        with st.expander(f"Analyse pour {url}"):
            # Contact Information
            st.subheader("Coordonnées")
            contact_info = result.get('contact_info', {})
            st.write("Emails:", ", ".join(contact_info.get('emails', [])))
            st.write("Téléphones:", ", ".join(contact_info.get('phones', [])))
            
            # SEO Analysis
            st.subheader("Analyse SEO")
            seo = result.get('seo_analysis', {})
            st.write("Titre:", seo.get('title', {}).get('text', 'N/A'))
            st.write("Meta Description:", seo.get('meta_description', {}).get('text', 'N/A'))
            st.write("Nombre de mots:", seo.get('content_analysis', {}).get('word_count', 'N/A'))
            
            # AI Analysis
            st.subheader("Analyse IA")
            ai_analysis = result.get('ai_analysis', {})
            if isinstance(ai_analysis, dict):
                st.write(ai_analysis.get('response', 'Aucune analyse IA disponible'))
            
            # Recommendations from AI Analysis
            st.subheader("Recommandations")
            recommendations = result.get('recommendations', [])
            if recommendations:
                for rec in recommendations:
                    st.write(f"- {rec}")
            else:
                st.write("Aucune recommandation disponible.")

            # HubSpot Integration Button
            if hubspot_available:
                # Use url in key to ensure uniqueness if URLs are identical after parsing (unlikely but safe)
                if st.button(f"Pousser vers HubSpot", key=f"hubspot_{url}"):
                    with st.spinner("Envoi vers HubSpot..."):
                        # Prepare contact_info for HubSpot (adjust field names as needed by HubSpotClient)
                        hubspot_contact_info = {
                            "email": contact_info.get('emails', [''])[0], # Take the first email
                            "website": url,
                            # Pass SEO and AI analysis as strings (or map to specific HubSpot properties)
                            "seo_analysis": json.dumps(seo), # Convert dict to JSON string
                            "recommendations": json.dumps(ai_analysis) # Convert dict to JSON string
                        }
                        
                        contact_id = hubspot_client.create_or_update_contact(hubspot_contact_info)
                        if contact_id:
                            # Optional: Update DB to mark as synced (requires adding synced_to_hubspot to schema)
                            # For now, just show success message
                            # update_synced_status(url, True)
                            st.success(f"Envoyé avec succès vers HubSpot pour {url} !")
                        else:
                            st.error(f"Échec de l'envoi vers HubSpot pour {url}")

# Download option
if data:
    st.download_button(
        label="Télécharger les résultats d'analyse (CSV)",
        data=pd.DataFrame(data).to_csv(index=False),
        file_name="analysis_results.csv",
        mime="text/csv"
    )