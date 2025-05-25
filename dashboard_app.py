import streamlit as st
import json
import pandas as pd
from collections import defaultdict, Counter
from urllib.parse import urlparse
import numpy as np
import sqlite3
from ollama_client import OllamaClient
from hubspot_client import HubSpotClient
import time

st.set_page_config(page_title="AI-Powered Client Acquisition Dashboard", layout="wide")
st.title("AI-Powered Client Acquisition Dashboard")

# Initialize clients
ollama_client = OllamaClient()
try:
    hubspot_client = HubSpotClient()
    hubspot_available = True
except Exception as e:
    st.warning("HubSpot integration not available. Please check your API key in .env file.")
    hubspot_available = False

# URL Input Section
st.header("URL Analysis")
urls_input = st.text_area(
    "Enter URLs to analyze (one per line)",
    height=150,
    help="Enter one or more URLs to analyze. Each URL should be on a new line."
)

if st.button("Analyze URLs"):
    if not urls_input.strip():
        st.error("Please enter at least one URL to analyze.")
    else:
        urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
        
        with st.spinner("Analyzing URLs..."):
            progress_bar = st.progress(0)
            results = []
            
            for i, url in enumerate(urls):
                try:
                    # Here you would call your existing scraper/analyzer
                    # For now, we'll simulate the analysis
                    analysis_result = {
                        "url": url,
                        "contact_info": {
                            "emails": ["example@domain.com"],
                            "phones": ["+1234567890"]
                        },
                        "seo_analysis": {
                            "title": {"text": "Sample Title"},
                            "meta_description": {"text": "Sample Description"},
                            "headers": {"has_h1": True},
                            "images": {"images_without_alt": 0},
                            "content_analysis": {"word_count": 500}
                        }
                    }
                    
                    # Generate AI analysis using Ollama
                    ai_analysis = ollama_client.generate_seo_analysis(url, analysis_result)
                    analysis_result["ai_analysis"] = ai_analysis
                    
                    # Store in SQLite
                    conn = sqlite3.connect('client_acquisition.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO analysis_results (url, analysis_data, synced_to_hubspot)
                        VALUES (?, ?, ?)
                    ''', (url, json.dumps(analysis_result), False))
                    conn.commit()
                    conn.close()
                    
                    results.append(analysis_result)
                    
                    # Update progress
                    progress_bar.progress((i + 1) / len(urls))
                    
                except Exception as e:
                    st.error(f"Error analyzing {url}: {str(e)}")
            
            st.success(f"Analysis completed for {len(results)} URLs!")

# Load and display results
def load_data():
    try:
        conn = sqlite3.connect('client_acquisition.db')
        cursor = conn.cursor()
        cursor.execute('SELECT analysis_data FROM analysis_results')
        results = [json.loads(row[0]) for row in cursor.fetchall()]
        conn.close()
        return results
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return []

data = load_data()

if data:
    # Summary statistics
    st.header("Analysis Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    unique_domains = len(set(urlparse(r['url']).netloc for r in data))
    total_emails = sum(len(r.get('contact_info', {}).get('emails', [])) for r in data)
    sites_with_email = sum(1 for r in data if r.get('contact_info', {}).get('emails'))
    sites_with_phone = sum(1 for r in data if r.get('contact_info', {}).get('phones'))
    
    col1.metric("Total Companies", unique_domains)
    col2.metric("Total Contacts", total_emails)
    col3.metric("Sites with Email", sites_with_email)
    col4.metric("Sites with Phone", sites_with_phone)
    
    # Detailed Results
    st.header("Detailed Analysis")
    for result in data:
        with st.expander(f"Analysis for {result['url']}"):
            # Contact Information
            st.subheader("Contact Information")
            st.write("Emails:", ", ".join(result.get('contact_info', {}).get('emails', [])))
            st.write("Phones:", ", ".join(result.get('contact_info', {}).get('phones', [])))
            
            # SEO Analysis
            st.subheader("SEO Analysis")
            seo = result.get('seo_analysis', {})
            st.write("Title:", seo.get('title', {}).get('text', 'N/A'))
            st.write("Meta Description:", seo.get('meta_description', {}).get('text', 'N/A'))
            st.write("Word Count:", seo.get('content_analysis', {}).get('word_count', 'N/A'))
            
            # AI Analysis
            st.subheader("AI Analysis")
            ai_analysis = result.get('ai_analysis', {})
            if isinstance(ai_analysis, dict):
                st.write(ai_analysis.get('response', 'No AI analysis available'))
            
            # HubSpot Integration
            if hubspot_available:
                if st.button(f"Push to HubSpot", key=f"hubspot_{result['url']}"):
                    with st.spinner("Pushing to HubSpot..."):
                        contact_info = {
                            "email": result.get('contact_info', {}).get('emails', [''])[0],
                            "website": result['url'],
                            "seo_analysis": json.dumps(result.get('seo_analysis', {})),
                            "recommendations": json.dumps(result.get('ai_analysis', {}))
                        }
                        
                        contact_id = hubspot_client.create_or_update_contact(contact_info)
                        if contact_id:
                            st.success("Successfully pushed to HubSpot!")
                        else:
                            st.error("Failed to push to HubSpot")

# Download option
if data:
    st.download_button(
        label="Download Analysis Results (CSV)",
        data=pd.DataFrame(data).to_csv(index=False),
        file_name="analysis_results.csv",
        mime="text/csv"
    ) 