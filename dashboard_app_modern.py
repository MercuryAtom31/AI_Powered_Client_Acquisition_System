import streamlit as st
import json
import pandas as pd
from collections import defaultdict, Counter
from urllib.parse import urlparse, urljoin
import numpy as np
import sqlite3
import requests
from bs4 import BeautifulSoup
from ollama_client import OllamaClient
from hubspot_client import HubSpotClient
import time
from ai_client_acquisition.analysis.seo_analyzer import SEOAnalyzer
from ai_client_acquisition.extraction.contact_extractor import ContactExtractor
from ai_client_acquisition.discovery.google_places_client import GooglePlacesClient
from hubspot.crm.contacts import SimplePublicObjectInputForCreate as ContactCreate
from typing import List, Dict, Optional
from datetime import datetime
import logging
import os

HUBSPOT_OWNER_ID = os.getenv("HUBSPOT_OWNER_ID")

# Configure logging
logger = logging.getLogger(__name__)

# Set Streamlit page config
st.set_page_config(
    page_title="AI SEO Analyzer & Business Finder", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- MODERN UI STYLING ---
st.markdown(
    """
    <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        @import url('https://fonts.googleapis.com/icon?family=Material+Icons');
        .material-icons {
            font-family: 'Material Icons';
            font-weight: normal;
            font-style: normal;
            font-size: 1.2em;
            display: inline-block;
            line-height: 1;
            text-transform: none;
            letter-spacing: normal;
            word-wrap: normal;
            direction: ltr;
            -webkit-font-feature-settings: 'liga';
            -webkit-font-smoothing: antialiased;
            vertical-align: middle;
        }
        
        /* Global Styles */
        .main {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Modern Navbar */
        .main-navbar {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            z-index: 10010;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 1rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
        }
        
        .nav-tab {
            color: #fff !important;
            text-shadow: 0 2px 8px rgba(60,30,90,0.18), 0 1px 0 #fff3;
            font-weight: 700;
            font-size: 1.18rem;
            letter-spacing: 0.5px;
            text-decoration: none;
            margin: 0 1.5rem;
            padding: 0.75rem 1.5rem;
            border-radius: 12px;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            cursor: pointer;
        }
        
        .nav-tab:hover {
            background: rgba(255,255,255,0.15);
            color: #fff;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .nav-tab.active {
            background: #fff;
            color: #764ba2 !important;
            box-shadow: 0 4px 12px rgba(118,75,162,0.15);
            font-weight: 800;
            text-shadow: none;
        }
        
        /* Card Styles */
        .metric-card {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 1.5rem;
            margin: 0.5rem 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        .analysis-card {
            background: #fff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        }
        
        .analysis-card:hover {
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        .score-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.875rem;
            margin: 0.5rem 0;
        }
        
        .score-excellent { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; }
        .score-good { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); color: white; }
        .score-average { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; }
        .score-poor { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; }
        
        /* Issue Icons */
        .issue-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem;
            border-radius: 8px;
            margin: 0.25rem 0;
            background: #f8fafc;
        }
        
        .issue-critical { border-left: 4px solid #ef4444; }
        .issue-warning { border-left: 4px solid #f59e0b; }
        .issue-info { border-left: 4px solid #3b82f6; }
        
        /* Button Styles */
        .stButton > button {
            border-radius: 12px;
            font-weight: 600;
            padding: 0.75rem 1.5rem;
            transition: all 0.3s ease;
            border: none;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        /* Input Styles */
        .stTextInput > div > div > input {
            border-radius: 12px;
            border: 2px solid #e2e8f0;
            padding: 0.75rem 1rem;
            transition: all 0.3s ease;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        /* Streamlit Overrides */
        .stApp {
            padding-top: 110px !important;
        }
        
        .main .block-container {
            max-width: 1200px;
            padding: 2rem 1rem;
        }
        
        /* Hide Streamlit elements */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        header { visibility: hidden; }
        
        .issue-item.issue-warning {
            border-left: 4px solid #f59e0b;
            background: #fffbe6;
            color: #b45309;
            font-weight: 500;
        }
    </style>
    
    <nav class="main-navbar">
        <a href="#url-analysis" class="nav-tab" id="nav-seo"><span class="material-icons">psychology</span> AI SEO Analyzer</a>
        <a href="#business-search" class="nav-tab" id="nav-biz"><span class="material-icons">public</span> Business Finder</a>
    </nav>
    
    <script>
        // Navbar active tab on scroll
        document.addEventListener('DOMContentLoaded', function() {
            const navTabs = document.querySelectorAll('.nav-tab');
            const sections = [
                {id: 'url-analysis', nav: document.getElementById('nav-seo')},
                {id: 'business-search', nav: document.getElementById('nav-biz')}
            ];
            function updateActiveTab() {
                let scrollPos = window.scrollY || window.pageYOffset;
                let found = false;
                for (let i = sections.length - 1; i >= 0; i--) {
                    const section = document.getElementById(sections[i].id);
                    if (section && section.offsetTop - 140 <= scrollPos) {
                        navTabs.forEach(t => t.classList.remove('active'));
                        sections[i].nav.classList.add('active');
                        found = true;
                        break;
                    }
                }
                if (!found) {
                    navTabs.forEach(t => t.classList.remove('active'));
                }
            }
            window.addEventListener('scroll', updateActiveTab);
            updateActiveTab();
            navTabs.forEach(tab => {
                tab.addEventListener('click', function(e) {
                    e.preventDefault();
                    const targetId = this.getAttribute('href').substring(1);
                    const targetElement = document.getElementById(targetId);
                    if (targetElement) {
                        window.scrollTo({
                            top: targetElement.offsetTop - 120,
                            behavior: 'smooth'
                        });
                    }
                });
            });
        });
    </script>
    """,
    unsafe_allow_html=True
)

def _extract_navigation_links(html: str, base_url: str) -> List[str]:
    """Extracts relevant internal navigation links from HTML."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        base_domain = urlparse(base_url).netloc
        internal_links = set()
        
        nav_tags = soup.find_all(['nav', 'header', 'footer'])
        
        for tag in nav_tags:
            for link in tag.find_all('a', href=True):
                href = link['href']
                if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                    continue
                
                full_url = urljoin(base_url, href)
                parsed_full_url = urlparse(full_url)
                
                if parsed_full_url.netloc == base_domain and parsed_full_url.scheme in ['http', 'https']:
                    if len(parsed_full_url.path) > 1 or parsed_full_url.path == '/':
                        internal_links.add(full_url)
        
        return list(internal_links)
        
    except Exception as e:
        logger.error(f"Error extracting navigation links from {base_url}: {str(e)}")
        return []

def init_db():
    """Initialize the SQLite database and create the table if it doesn't exist."""
    try:
        conn = sqlite3.connect('client_acquisition.db')
        cursor = conn.cursor()
        
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
    except Exception as e:
        st.error(f"Database initialization error: {e}")

# Initialize the database
init_db()

# Main App Header
st.markdown(
    """
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="font-size: 2.5rem; font-weight: 700; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem;">
            <span class="material-icons" style="font-size:2.2rem;vertical-align:middle;">psychology</span> AI SEO Analyzer & Business Finder
        </h1>
        <p style="font-size: 1.1rem; color: #64748b; margin: 0;">
            Professional SEO analysis and business discovery powered by AI
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# Initialize clients and analyzers
ollama_client = OllamaClient()
seo_analyzer = SEOAnalyzer()
contact_extractor = ContactExtractor()
google_places_client = GooglePlacesClient()

try:
    hubspot_client = HubSpotClient()
    hubspot_available = True
except Exception as e:
    st.warning("HubSpot integration is not available. Please check your API key in the .env file.")
    hubspot_available = False

def get_seo_grade(score):
    """Convert numeric score to letter grade with color coding."""
    if score >= 90:
        return "A+", "score-excellent"
    elif score >= 80:
        return "A", "score-excellent"
    elif score >= 70:
        return "B", "score-good"
    elif score >= 60:
        return "C", "score-average"
    else:
        return "D", "score-poor"

def run_analysis_pipeline(urls: List[str], force_reanalysis: bool):
    """Runs the full analysis pipeline for a list of URLs and stores results."""
    if not urls:
        st.warning("No valid URLs provided for analysis.")
        return
        
    # Create progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        conn = sqlite3.connect('client_acquisition.db')
        cursor = conn.cursor()
        
        total_urls = len(urls)
        analyzed_count = 0
        
        for i, url in enumerate(urls):
            url = url.strip()
            if not url:
                continue
                
            # Check if URL already exists and force_reanalysis is False
            if not force_reanalysis:
                cursor.execute('SELECT id FROM analysis_results WHERE url = ? AND business_id IS NULL', (url,))
                if cursor.fetchone():
                    analyzed_count += 1
                    progress_bar.progress(analyzed_count / total_urls)
                    status_text.text(f"[Skipped] {url} (already analyzed)")
                    continue
            
            status_text.text(f"[Analyzing] {url}...")
            
            try:
                # Run SEO analysis
                seo_result = seo_analyzer.analyze_url(url)
                
                # Extract contact information
                contact_result = contact_extractor.extract_from_url(url)
                
                # Run AI analysis
                ai_result = ollama_client.generate_seo_analysis(url, seo_result)
                
                # Combine results
                analysis_result = {
                    'url': url,
                    'seo_analysis': seo_result,
                    'contact_info': contact_result,
                    'ai_analysis': ai_result,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Store in database
                cursor.execute('''
                    INSERT OR REPLACE INTO analysis_results (url, analysis_data, business_id)
                    VALUES (?, ?, NULL)
                ''', (url, json.dumps(analysis_result)))
                
                analyzed_count += 1
                progress_bar.progress(analyzed_count / total_urls)
                status_text.text(f"[Done] Completed analysis for {url}")
                
            except Exception as e:
                st.error(f"Error analyzing {url}: {str(e)}")
                analyzed_count += 1
                progress_bar.progress(analyzed_count / total_urls)
                continue
        
        conn.commit()
        conn.close()
        
        progress_bar.empty()
        status_text.empty()
        st.success(f"Analysis complete! Successfully analyzed {analyzed_count} URLs.")
        
    except Exception as e:
        st.error(f"Error during analysis pipeline: {str(e)}")
        conn.close()

def run_business_search_analysis(city: str, industry: str, batch_size: int = 5, page: int = 1):
    """Runs business search and analysis pipeline."""
    try:
        # 1. Search for businesses (Nearby Search)
        businesses = google_places_client.search_places(industry, city, page=page)
        if batch_size is not None:
            businesses = businesses[:batch_size]

        if not businesses:
            st.warning("No businesses found for the given criteria.")
            return

        # 2. Set up Streamlit progress indicators
        progress_bar = st.progress(0)
        status_text  = st.empty()

        # 3. Open DB connection
        conn   = sqlite3.connect('client_acquisition.db')
        cursor = conn.cursor()

        # 3.1 Fetch all already-analyzed URLs
        cursor.execute('SELECT url FROM analysis_results')
        already_analyzed_urls = set(row[0] for row in cursor.fetchall())

        total = len(businesses)
        for i, biz in enumerate(businesses, start=1):
            name     = biz.get('name', 'N/A')
            place_id = biz.get('place_id')
            status_text.text(f"[Processing] {name}...")

            # 4. Fetch place-details (website, address, international_phone_number…)
            details = google_places_client.get_place_details(place_id) or {}
            website = details.get('website', '')
            address = details.get('formatted_address', '')

            # 5. Upsert into businesses table
            cursor.execute('''
                INSERT INTO businesses (search_query, place_id, name, address, website)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(place_id) DO UPDATE SET
                  address = excluded.address,
                  website = excluded.website
            ''', (
                f"{city} {industry}",
                place_id,
                name,
                address,
                website
            ))
            conn.commit()

            # 6. Grab the newly-inserted business ID
            cursor.execute('SELECT id FROM businesses WHERE place_id = ?', (place_id,))
            business_id = cursor.fetchone()[0]

            # 7. If we have a website, check if already analyzed
            if website:
                if website in already_analyzed_urls:
                    status_text.text(f"[Skipped] already analyzed: {website}")
                    progress_bar.progress(i / total)
                    continue
                try:
                    seo_result     = seo_analyzer.analyze_url(website)
                    contact_result = contact_extractor.extract_from_url(website)
                    ai_result      = ollama_client.generate_seo_analysis(website, seo_result)

                    analysis_payload = {
                        'url':          website,
                        'seo_analysis': seo_result,
                        'contact_info': contact_result,
                        'ai_analysis':  ai_result,
                        'timestamp':    datetime.now().isoformat()
                    }

                    cursor.execute('''
                        INSERT OR REPLACE INTO analysis_results
                          (business_id, url, analysis_data)
                        VALUES (?, ?, ?)
                    ''', (
                        business_id,
                        website,
                        json.dumps(analysis_payload, ensure_ascii=False)
                    ))
                    conn.commit()
                    already_analyzed_urls.add(website)
                except Exception as e:
                    st.error(f"Error analyzing {website}: {e}")

            # 8. Update progress bar
            progress_bar.progress(i / total)

        # 9. Clean up UI and DB
        progress_bar.empty()
        status_text.empty()
        conn.close()

    except Exception as e:
        st.error(f"Error during business search analysis: {e}")

def _display_analysis_result(analysis_result: Dict, hubspot_available: bool, unique_id: str = ""):
    """Display a single analysis result with modern card design."""
    url          = analysis_result.get('url', 'N/A')
    seo          = analysis_result.get('seo_analysis', {})
    contact_info = analysis_result.get('contact_info', {})
    ai_analysis  = analysis_result.get('ai_analysis', {})
    key_suffix   = f"{unique_id}_{url}"
    
    # Get SEO score and grade
    seo_score, grade, grade_class = seo.get('overall_score', 0), *get_seo_grade(seo.get('overall_score', 0))
    
    # Render the card
    st.markdown(f"""
        <div class="analysis-card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
            <h3 style="margin:0;color:#1e293b;font-size:1.1rem;"><span class="material-icons">public</span> {url}</h3>
            <div class="score-badge {grade_class}">{grade} ({seo_score}/100)</div>
          </div>
        </div>
    """, unsafe_allow_html=True)
    
    # SEO details
    if seo:
        st.markdown("#### <span class=\"material-icons\">bar_chart</span> SEO Analysis Details", unsafe_allow_html=True)
        for check_name, check_result in seo.get('checks', {}).items():
            if 'error' not in check_result:
                for k, v in check_result.items():
                    if k == 'recommendations': continue
                    if (isinstance(v, bool) and not v) or (isinstance(v, list) and not v):
                        label = k.replace('_',' ').title()
                        st.markdown(f'<div class="issue-item issue-warning"><span class="material-icons">warning</span> {label}</div>', unsafe_allow_html=True)
        for issue in seo.get('critical_issues', []):
            st.markdown(f'<div class="issue-item issue-critical"><span class="material-icons">error</span> {issue}</div>', unsafe_allow_html=True)
    
    # Contact info
    st.markdown("#### <span class=\"material-icons\">contact_mail</span> Contact Information", unsafe_allow_html=True)
    emails, phones = contact_info.get('emails', []), contact_info.get('phones', [])
    if emails:
        st.markdown(f"<span class=\"material-icons\">email</span> <b>Emails:</b> {', '.join(emails)}", unsafe_allow_html=True)
    if phones:
        st.markdown(f"<span class=\"material-icons\">phone_android</span> <b>Phones:</b> {', '.join(phones)}", unsafe_allow_html=True)
    
    # AI analysis
    if isinstance(ai_analysis, dict) and "response" in ai_analysis:
        st.markdown("#### <span class=\"material-icons\">psychology</span> AI Analysis", unsafe_allow_html=True)
        st.write(ai_analysis['response'])
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Re-analyze", key=f"reanalyze_{key_suffix}"):
            run_analysis_pipeline([url], True)
            st.rerun()
    with col2:
        details_key = f"details_open_{key_suffix}"
        if details_key not in st.session_state:
            st.session_state[details_key] = False
        if st.button("View Details", key=f"details_{key_suffix}"):
            st.session_state[details_key] = not st.session_state[details_key]
        if st.session_state[details_key]:
            st.json(analysis_result)
    with col3:
        if hubspot_available and st.button("Push to HubSpot", key=f"hubspot_{key_suffix}"):
            OWNER_ID = os.getenv("HUBSPOT_OWNER_ID")
            owner_prop = {"hubspot_owner_id": OWNER_ID} if OWNER_ID else {}

            # Path A: we have an email → upsert by email
            if emails:
                payload = {
                    "email":        emails[0],
                    "phone":        phones[0] if phones else "",
                    "website":      url,
                    "seo_analysis": json.dumps(seo, ensure_ascii=False),
                    **owner_prop
                }
                with st.spinner("Upserting contact by email…"):
                    contact_id = hubspot_client.create_or_update_contact(payload)
                    if not contact_id:
                        st.error("❌ Failed to upsert contact in HubSpot")
                        return

            # Path B: no email → create new contact named after domain
            else:
                hostname    = urlparse(url).netloc.replace("www.", "")
                domain_name = hostname.split(".")[0].capitalize()
                props = {
                    "firstname":    domain_name,
                    "phone":        phones[0] if phones else "",
                    "website":      url,
                    "seo_analysis": json.dumps(seo, ensure_ascii=False),
                    **owner_prop
                }
                with st.spinner("Creating contact by domain name…"):
                    new_ct = hubspot_client.client.crm.contacts.basic_api.create(
                        simple_public_object_input_for_create=ContactCreate(properties=props)
                    )
                    contact_id = new_ct.id

            # Attach the analysis note
            note_id = hubspot_client.create_analysis_note(contact_id, analysis_result)
            if note_id:
                st.success("✅ Analysis pushed as a Note on the contact!")
            else:
                st.error("❌ Contact upserted, but failed to add Note.")

# URL Analysis Section
st.markdown('<h2 id="url-analysis"><span class="material-icons">psychology</span> AI SEO Analyzer</h2>', unsafe_allow_html=True)

# URL Input Card
st.markdown(
    """
    <div class="metric-card">
        <h3 style="margin: 0 0 1rem 0; color: #1e293b;"><span class="material-icons">download</span> Enter URLs to Analyze</h3>
    </div>
    """,
    unsafe_allow_html=True
)

urls_input = st.text_area(
    "Enter URLs (one per line):",
    height=120,
    placeholder="https://example.com\nhttps://another-site.com",
    help="Enter the URLs you want to analyze, one per line"
)

col1, col2 = st.columns(2)

with col1:
    force_reanalysis = st.checkbox("Re-analyze existing URLs", value=False)

with col2:
    if st.button("Analyze URLs", type="primary", use_container_width=True, key="analyze_urls_btn"):
        if urls_input.strip():
            urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
            run_analysis_pipeline(urls, force_reanalysis)
            st.rerun()
        else:
            st.error("Please enter at least one URL to analyze.")

# Load and display results
def load_data():
    """Loads all analysis results, organized by business or direct URL."""
    try:
        conn = sqlite3.connect('client_acquisition.db')
        cursor = conn.cursor()

        # 1) Fetch all business‐linked analyses
        cursor.execute('''
            SELECT b.name, b.website, b.search_query, ar.url, ar.analysis_data
            FROM businesses b
            JOIN analysis_results ar ON b.id = ar.business_id
            ORDER BY b.search_query, b.name, ar.url
        ''')
        business_rows = cursor.fetchall()

        # 2) Fetch all direct‐URL analyses
        cursor.execute('''
            SELECT id, url, analysis_data, timestamp
            FROM analysis_results ar
            WHERE ar.business_id IS NULL
            ORDER BY url, timestamp DESC
        ''')
        direct_rows = cursor.fetchall()

        conn.close()

        organized = {}

        # 3) Build the "Search: ..." groups
        for name, website, search_query, page_url, analysis_json in business_rows:
            group_key     = f"Search: {search_query}"
            business_key  = f"Business: {name} ({website})"
            analysis_dict = json.loads(analysis_json)

            # Ensure all three nesting levels exist
            organized.setdefault(group_key, {})
            organized[group_key].setdefault(business_key, {})
            organized[group_key][business_key].setdefault(page_url, [])
            organized[group_key][business_key][page_url].append(analysis_dict)

        # 4) Build the "Direct URLs" group
        direct_key = "Direct URLs"
        organized[direct_key] = {}
        for analysis_id, page_url, analysis_json, ts in direct_rows:
            record = json.loads(analysis_json)
            record['id']        = analysis_id
            record['timestamp'] = ts
            organized[direct_key].setdefault(page_url, []).append(record)

        return organized

    except Exception as e:
        st.error(f"Error loading data: {e}")
        return {}

# Display Results Section
st.markdown('<h3><span class="material-icons">bar_chart</span> Analysis Results</h3>', unsafe_allow_html=True)

organized_data = load_data()

if organized_data:
    # Summary Statistics
    total_analyzed_urls = 0
    for group_name, businesses_or_urls in organized_data.items():
        if group_name == "Direct URLs":
            for analysis_list_for_url in businesses_or_urls.values():
                total_analyzed_urls += len(analysis_list_for_url)
        else:
            for business_pages_dict in businesses_or_urls.values():
                for analysis_list_for_page in business_pages_dict.values():
                    total_analyzed_urls += len(analysis_list_for_page)

    total_businesses = sum(len(businesses) for key, businesses in organized_data.items() if key.startswith("Search:"))
    total_direct_urls = len(organized_data.get("Direct URLs", {}))
    
    # Display metrics in cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="text-align: center;">
                    <div style="font-size: 2rem; font-weight: 700; color: #667eea;">{total_analyzed_urls}</div>
                    <div style="color: #64748b; font-size: 0.875rem;">Total URLs Analyzed</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="text-align: center;">
                    <div style="font-size: 2rem; font-weight: 700; color: #10b981;">{total_businesses}</div>
                    <div style="color: #64748b; font-size: 0.875rem;">Businesses Found</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="text-align: center;">
                    <div style="font-size: 2rem; font-weight: 700; color: #f59e0b;">{total_direct_urls}</div>
                    <div style="color: #64748b; font-size: 0.875rem;">Direct URLs</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col4:
        # Calculate average score
        total_score = 0
        score_count = 0
        for group_name, businesses_or_urls in organized_data.items():
            for business_or_url, pages in businesses_or_urls.items():
                if group_name.startswith("Search:"):
                    for page_url, analyses in pages.items():
                        for analysis_result in analyses:
                            seo = analysis_result.get('seo_analysis', {})
                            score = seo.get('overall_score', 0)
                            if score > 0:
                                total_score += score
                                score_count += 1
                else:
                    for analysis_result in pages:
                        seo = analysis_result.get('seo_analysis', {})
                        score = seo.get('overall_score', 0)
                        if score > 0:
                            total_score += score
                            score_count += 1
        
        avg_score = round(total_score / score_count, 1) if score_count > 0 else 0
        grade, _ = get_seo_grade(avg_score)
        
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="text-align: center;">
                    <div style="font-size: 2rem; font-weight: 700; color: #764ba2;">{avg_score}</div>
                    <div style="color: #64748b; font-size: 0.875rem;">Avg Score ({grade})</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Add a clear section header for Business Finder results
    business_finder_groups = [g for g in organized_data if g.startswith("Search:")]
    if business_finder_groups:
        st.markdown(
            '<h3 style="margin-top: 3rem; color: #7c3aed;">Business Finder Results</h3>'
            '<p style="color: #64748b; margin-bottom: 2rem;">Websites discovered and analyzed via the Business Finder search feature.</p>',
            unsafe_allow_html=True
        )
    for group_name, businesses_or_urls in organized_data.items():
        # Move the Direct URLs Results header and description here
        if group_name == "Direct URLs":
            st.markdown(
                '<h3 style="margin-top: 3rem; color: #2563eb;">Direct URLs Results</h3>'
                '<p style="color: #64748b; margin-bottom: 2rem;">Websites analyzed through the Enter URLs to Analyze section.</p>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(f'<h4 style="margin-top: 2rem; color: #1e293b;">{group_name}</h4>', unsafe_allow_html=True)
        
        for business_or_url, pages in businesses_or_urls.items():
            if group_name.startswith("Search:"):
                # Business Finder section: show number of analyses per website
                for page_url, analyses in pages.items():
                    expander_label = f"{page_url} ({len(analyses)} analyses)"
                    with st.expander(expander_label):
                        for idx, analysis_result in enumerate(analyses):
                            timestamp = analysis_result.get('timestamp', 'N/A')
                            st.markdown(f"**Analysis {idx + 1} (Date: {timestamp})**")
                            unique_id = str(analysis_result.get('id', idx))
                            _display_analysis_result(analysis_result, hubspot_available, unique_id=unique_id)
            else:
                url = business_or_url
                analyses = pages
                with st.expander(f"{url} ({len(analyses)} analyses)"):
                    for idx, analysis_result in enumerate(analyses):
                        st.markdown(f"**Analysis {idx + 1} (Date: {analysis_result.get('timestamp', 'N/A')})**")
                        unique_id = str(analysis_result.get('id', idx))
                        _display_analysis_result(analysis_result, hubspot_available, unique_id=unique_id)

    # Download option
    if organized_data:
        csv_rows = []
        for group_name, businesses_or_urls in organized_data.items():
            for business_or_url, pages in businesses_or_urls.items():
                if group_name.startswith("Search:"):
                    for page_url, analyses in pages.items():
                        for analysis_result in analyses:
                            contact_info = analysis_result.get('contact_info', {})
                            seo = analysis_result.get('seo_analysis', {})
                            ai_analysis = analysis_result.get('ai_analysis', {})
                            
                            csv_rows.append({
                                "Group": group_name,
                                "Business": business_or_url,
                                "URL": page_url,
                                "SEO Score": seo.get("overall_score", "N/A"),
                                "Critical Issues": ", ".join(seo.get("critical_issues", [])),
                                "Emails": ", ".join(contact_info.get('emails', [])),
                                "Phones": ", ".join(contact_info.get('phones', [])),
                                "AI Analysis": ai_analysis.get('response', '') if isinstance(ai_analysis, dict) else '',
                            })
                else:
                    url = business_or_url
                    analyses = pages
                    
                    for analysis_result in analyses:
                        contact_info = analysis_result.get('contact_info', {})
                        seo = analysis_result.get('seo_analysis', {})
                        ai_analysis = analysis_result.get('ai_analysis', {})
                        
                        csv_rows.append({
                            "Group": group_name,
                            "Business": "N/A",
                            "URL": url,
                            "SEO Score": seo.get("overall_score", "N/A"),
                            "Critical Issues": ", ".join(seo.get("critical_issues", [])),
                            "Emails": ", ".join(contact_info.get('emails', [])),
                            "Phones": ", ".join(contact_info.get('phones', [])),
                            "AI Analysis": ai_analysis.get('response', '') if isinstance(ai_analysis, dict) else '',
                        })

        if csv_rows:
            df = pd.DataFrame(csv_rows)
            st.download_button(
                label="⬇️ Export Results (CSV)",
                data=df.to_csv(index=False),
                file_name="analysis_results.csv",
                mime="text/csv",
                use_container_width=True
            )

# Business Search Section
st.markdown('<h2 id="business-search"><span class="material-icons">public</span> Business Finder</h2>', unsafe_allow_html=True)

# Business Search Card
st.markdown(
    """
    <div class="metric-card">
        <h3 style="margin: 0 0 1rem 0; color: #1e293b;"><span class="material-icons">search</span> Search for Businesses</h3>
        <p style="color: #64748b; margin: 0;">Find and analyze businesses based on location and industry using Google Places API.</p>
    </div>
    """,
    unsafe_allow_html=True
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    city = st.text_input(
        "City",
        key="business_search_city",
        placeholder="e.g., Montreal",
        help="Enter the city name"
    )

with col2:
    industry = st.text_input(
        "Industry / Business Type",
        key="business_search_industry",
        placeholder="e.g., digital marketing agency",
        help="Enter the type of business"
    )

with col3:
    batch_size = st.number_input(
        "Max Results",
        min_value=1,
        value=5,
        step=1,
        key="business_search_batch_size",
        help="Number of businesses to analyze"
    )

with col4:
    page = st.selectbox(
        "Page of Results",
        options=[1, 2, 3],
        index=0,
        key="business_search_page",
        help="Select which page of Google Places results to analyze",
        format_func=lambda x: f"Page {x}"
    )

if st.button("Start Business Search", type="primary", use_container_width=True, key="start_biz_search_btn"):
    if not city or not industry:
        st.error("Please enter both City and Industry.")
    else:
        st.session_state['business_search_triggered'] = True

if st.session_state.get('business_search_triggered', False):
    st.session_state.pop('business_search_triggered')
    run_business_search_analysis(
        st.session_state.get('business_search_city', ''),
        st.session_state.get('business_search_industry', ''),
        st.session_state.get('business_search_batch_size', 5),
        st.session_state.get('business_search_page', 1)
    )
    st.session_state['business_search_complete'] = True
    st.session_state['last_search_city'] = st.session_state.get('business_search_city', '')
    st.session_state['last_search_industry'] = st.session_state.get('business_search_industry', '')
    st.session_state['last_search_page'] = st.session_state.get('business_search_page', 1)
    st.rerun()

if st.session_state.get('business_search_complete', False):
    st.success("Business search and analysis complete! See results above.")

if st.session_state.get('last_search_city') and st.session_state.get('last_search_industry'):
    st.info(f"Showing results for {st.session_state['last_search_industry']} in {st.session_state['last_search_city']}")
