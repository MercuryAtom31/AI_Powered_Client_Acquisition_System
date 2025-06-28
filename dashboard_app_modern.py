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
from typing import List, Dict, Optional
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Set Streamlit page config
st.set_page_config(
    page_title="🧠 AI SEO Analyzer & Business Finder", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- MODERN UI STYLING ---
st.markdown(
    """
    <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Global Styles */
        .main {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Modern Navbar */
        .main-navbar {
            position: fixed;
            top: 48px;
            left: 0;
            width: 100vw;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            z-index: 9999;
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
            padding-top: 120px !important;
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
        <a href="#url-analysis" class="nav-tab" id="nav-seo">🧠 AI SEO Analyzer</a>
        <a href="#business-search" class="nav-tab" id="nav-biz">🌍 Business Finder</a>
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
            🧠 AI SEO Analyzer & Business Finder
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
                    status_text.text(f"⏭️ Skipping {url} (already analyzed)")
                    continue
            
            status_text.text(f"🔍 Analyzing {url}...")
            
            try:
                # Run SEO analysis
                seo_result = seo_analyzer.analyze_url(url)
                
                # Extract contact information
                contact_result = contact_extractor.extract_contact_info(url)
                
                # Run AI analysis
                ai_result = ollama_client.analyze_website(url, seo_result, contact_result)
                
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
                status_text.text(f"✅ Completed analysis for {url}")
                
            except Exception as e:
                st.error(f"Error analyzing {url}: {str(e)}")
                analyzed_count += 1
                progress_bar.progress(analyzed_count / total_urls)
                continue
        
        conn.commit()
        conn.close()
        
        progress_bar.empty()
        status_text.empty()
        st.success(f"🎉 Analysis complete! Successfully analyzed {analyzed_count} URLs.")
        
    except Exception as e:
        st.error(f"Error during analysis pipeline: {str(e)}")
        conn.close()

def run_business_search_analysis(city: str, industry: str, batch_size: int = 5):
    """Runs business search and analysis pipeline."""
    try:
        # Search for businesses
        businesses = google_places_client.search_businesses(city, industry, batch_size)
        
        if not businesses:
            st.warning("No businesses found for the given criteria.")
            return
        
        # Create progress bar for business analysis
        business_analysis_progress = st.progress(0)
        business_status_text = st.empty()
        
        conn = sqlite3.connect('client_acquisition.db')
        cursor = conn.cursor()
        
        total_businesses = len(businesses)
        analyzed_businesses = 0
        
        for i, business in enumerate(businesses):
            business_status_text.text(f"🔍 Analyzing business: {business['name']}")
            
            # Store business in database
            cursor.execute('''
                INSERT OR IGNORE INTO businesses (search_query, place_id, name, address, website)
                VALUES (?, ?, ?, ?, ?)
            ''', (f"{city} {industry}", business['place_id'], business['name'], 
                  business.get('address', ''), business.get('website', '')))
            
            business_id = cursor.lastrowid
            
            # If business has a website, analyze it
            if business.get('website'):
                try:
                    # Run SEO analysis
                    seo_result = seo_analyzer.analyze_url(business['website'])
                    
                    # Extract contact information
                    contact_result = contact_extractor.extract_contact_info(business['website'])
                    
                    # Run AI analysis
                    ai_result = ollama_client.analyze_website(business['website'], seo_result, contact_result)
                    
                    # Combine results
                    analysis_result = {
                        'url': business['website'],
                        'seo_analysis': seo_result,
                        'contact_info': contact_result,
                        'ai_analysis': ai_result,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Store analysis result
                    cursor.execute('''
                        INSERT OR REPLACE INTO analysis_results (business_id, url, analysis_data)
                        VALUES (?, ?, ?)
                    ''', (business_id, business['website'], json.dumps(analysis_result)))
                    
                except Exception as e:
                    st.error(f"Error analyzing {business['website']}: {str(e)}")
            
            analyzed_businesses += 1
            business_analysis_progress.progress(analyzed_businesses / total_businesses)
        
        conn.commit()
        conn.close()
        
        business_analysis_progress.empty()
        business_status_text.empty()
        st.success(f"🎉 Business search and analysis complete for {len(businesses)} businesses!")
        
    except Exception as e:
        st.error(f"Error during business search analysis: {str(e)}")

def _display_analysis_result(analysis_result: Dict, hubspot_available: bool, unique_id: str = ""):
    """Display a single analysis result with modern card design."""
    url = analysis_result.get('url', 'N/A')
    seo = analysis_result.get('seo_analysis', {})
    contact_info = analysis_result.get('contact_info', {})
    ai_analysis = analysis_result.get('ai_analysis', {})
    key_suffix = f"{unique_id}_{url}"
    
    # Get SEO score and grade
    seo_score = seo.get('overall_score', 0)
    grade, grade_class = get_seo_grade(seo_score)
    
    # Create the analysis card
    st.markdown(
        f"""
        <div class="analysis-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3 style="margin: 0; color: #1e293b; font-size: 1.1rem;">🌐 {url}</h3>
                <div class="score-badge {grade_class}">
                    {grade} ({seo_score}/100)
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # SEO Analysis Section (no expander)
    if seo:
        st.markdown("#### 📊 SEO Analysis Details")
        checks_results = seo.get('checks', {})
        if checks_results:
            for check_name, check_result in checks_results.items():
                if 'error' not in check_result:
                    # Create issue display
                    issues = []
                    for key, value in check_result.items():
                        if key != 'recommendations':
                            if isinstance(value, bool) and not value:
                                issues.append(f"⚠️ {key.replace('_', ' ').title()}")
                            elif isinstance(value, list) and not value:
                                issues.append(f"⚠️ Missing {key.replace('_', ' ').title()}")
                    if issues:
                        for issue in issues:
                            st.markdown(f'<div class="issue-item issue-warning">{issue}</div>', unsafe_allow_html=True)
        # Critical issues
        critical_issues = seo.get('critical_issues', [])
        if critical_issues:
            st.markdown("**🔴 Critical Issues:**")
            for issue in critical_issues:
                st.markdown(f'<div class="issue-item issue-critical">🔴 {issue}</div>', unsafe_allow_html=True)
    
    # Contact Information (no expander)
    if contact_info:
        st.markdown("#### 📞 Contact Information")
        emails = contact_info.get('emails', [])
        phones = contact_info.get('phones', [])
        if emails:
            st.markdown(f"**📧 Emails:** {', '.join(emails)}")
        if phones:
            st.markdown(f"**📱 Phones:** {', '.join(phones)}")
    
    # AI Analysis (no expander)
    if isinstance(ai_analysis, dict) and "response" in ai_analysis:
        st.markdown("#### 🧠 AI Analysis")
        st.write(ai_analysis['response'])
    
    # Action Buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Re-analyze", key=f"reanalyze_{key_suffix}"):
            run_analysis_pipeline([url], True)
            st.rerun()
    with col2:
        if st.button("📊 View Details", key=f"details_{key_suffix}"):
            st.json(analysis_result)
    with col3:
        if hubspot_available:
            if st.button("📤 Push to HubSpot", key=f"hubspot_{key_suffix}"):
                with st.spinner("Sending to HubSpot..."):
                    hubspot_contact_info = {
                        "email": contact_info.get('emails', [''])[0],
                        "website": url,
                        "seo_analysis": json.dumps(seo) if seo else '',
                        "ai_analysis": json.dumps(ai_analysis) if isinstance(ai_analysis, dict) else '',
                    }
                    contact_id = hubspot_client.create_or_update_contact(hubspot_contact_info)
                    if contact_id:
                        st.success(f"✅ Successfully sent to HubSpot!")
                    else:
                        st.error(f"❌ Failed to send to HubSpot")

# URL Analysis Section
st.markdown('<h2 id="url-analysis">🧠 AI SEO Analyzer</h2>', unsafe_allow_html=True)

# URL Input Card
st.markdown(
    """
    <div class="metric-card">
        <h3 style="margin: 0 0 1rem 0; color: #1e293b;">📥 Enter URLs to Analyze</h3>
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
    force_reanalysis = st.checkbox("🔄 Re-analyze existing URLs", value=False)

with col2:
    if st.button("🚀 Analyze URLs", type="primary", use_container_width=True):
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
            SELECT id, url, analysis_data, timestamp
            FROM analysis_results ar
            WHERE ar.business_id IS NULL
            ORDER BY ar.url, ar.timestamp DESC
        ''')
        direct_url_results = cursor.fetchall()
        
        conn.close()
        
        # Organize results for display
        organized_results = defaultdict(lambda: defaultdict(list))
        
        # Add business search results
        for name, website, search_query, url, analysis_data_json in business_results:
            organized_results[f"Search: {search_query}"][f"Business: {name} ({website})"][url].append(json.loads(analysis_data_json))
            
        # Add direct URL results
        for analysis_id, url, analysis_data_json, timestamp in direct_url_results:
             analysis_dict = json.loads(analysis_data_json)
             analysis_dict['id'] = analysis_id
             analysis_dict['timestamp'] = timestamp
             organized_results["Direct URLs"][url].append(analysis_dict)
        
        return organized_results
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return {}

# Display Results Section
st.markdown('<h3>📊 Analysis Results</h3>', unsafe_allow_html=True)

organized_data = load_data()

if organized_data:
    # Summary Statistics
    total_analyzed_urls = 0
    for group_name, businesses_or_urls_dict in organized_data.items():
        if group_name == "Direct URLs":
            for analysis_list_for_url in businesses_or_urls_dict.values():
                total_analyzed_urls += len(analysis_list_for_url)
        else:
            for business_pages_dict in businesses_or_urls_dict.values():
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

    # Detailed Results
    for group_name, businesses_or_urls in organized_data.items():
        st.markdown(f'<h4 style="margin-top: 2rem; color: #1e293b;">{group_name}</h4>', unsafe_allow_html=True)
        
        for business_or_url, pages in businesses_or_urls.items():
            if group_name.startswith("Search:"):
                with st.expander(business_or_url):
                     for page_url, analyses in pages.items():
                          st.write(f"**Page:** {page_url}")
                          for idx, analysis_result in enumerate(analyses):
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
                label="🧾 Export Results (CSV)",
                data=df.to_csv(index=False),
                file_name="analysis_results.csv",
                mime="text/csv",
                use_container_width=True
            )

# Business Search Section
st.markdown('<h2 id="business-search">🌍 Business Finder</h2>', unsafe_allow_html=True)

# Business Search Card
st.markdown(
    """
    <div class="metric-card">
        <h3 style="margin: 0 0 1rem 0; color: #1e293b;">🔎 Search for Businesses</h3>
        <p style="color: #64748b; margin: 0;">Find and analyze businesses based on location and industry using Google Places API.</p>
    </div>
    """,
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns(3)

with col1:
    city = st.text_input(
        "📍 City",
        key="business_search_city",
        placeholder="e.g., Montreal",
        help="Enter the city name"
    )

with col2:
    industry = st.text_input(
        "🏢 Industry / Business Type",
        key="business_search_industry",
        placeholder="e.g., digital marketing agency",
        help="Enter the type of business"
    )

with col3:
    batch_size = st.number_input(
        "🔢 Max Results",
        min_value=1,
        value=5,
        step=1,
        key="business_search_batch_size",
        help="Number of businesses to analyze"
    )

if st.button("🚀 Start Business Search", type="primary", use_container_width=True):
    if not city or not industry:
        st.error("Please enter both City and Industry.")
    else:
        st.session_state['business_search_triggered'] = True
        st.rerun()

if st.session_state.get('business_search_triggered', False):
    st.session_state.pop('business_search_triggered')
    run_business_search_analysis(
        st.session_state.get('business_search_city', ''),
        st.session_state.get('business_search_industry', ''),
        st.session_state.get('business_search_batch_size', 5)
    )
    st.session_state['business_search_complete'] = True
    st.session_state['last_search_city'] = st.session_state.get('business_search_city', '')
    st.session_state['last_search_industry'] = st.session_state.get('business_search_industry', '')

if st.session_state.get('business_search_complete', False):
    st.success("🎉 Business search and analysis complete! See results above.")
    st.session_state['business_search_complete'] = False

if st.session_state.get('last_search_city') and st.session_state.get('last_search_industry'):
    st.info(f"📊 Showing results for {st.session_state['last_search_industry']} in {st.session_state['last_search_city']}")
