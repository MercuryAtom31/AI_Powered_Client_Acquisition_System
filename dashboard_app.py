import streamlit as st
import json
import pandas as pd
from collections import Counter

st.set_page_config(page_title="Client Acquisition Dashboard", layout="wide")
st.title("AI-Powered Client Acquisition Dashboard")

# Load analysis results
def load_data(file_path="analysis_results.json"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return []

data = load_data()

if not data:
    st.warning("No analysis results found. Please run the analysis script first.")
    st.stop()

# Convert to DataFrame for easier manipulation
df = pd.json_normalize(data)

# Summary statistics
st.header("Summary Statistics")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Companies", len(df))
col2.metric("Total Contacts", sum(df['contact_info.emails'].apply(lambda x: len(x) if isinstance(x, list) else 0)))
col3.metric("Websites with Email", sum(df['contact_info.emails'].apply(lambda x: bool(x) and len(x) > 0)))
col4.metric("Websites with Phone", sum(df['contact_info.phones'].apply(lambda x: bool(x) and len(x) > 0)))

# Platform distribution
st.subheader("Platform Distribution")
platform_counts = Counter(df['platform_type'])
platform_df = pd.DataFrame(platform_counts.items(), columns=["Platform", "Count"])
st.bar_chart(platform_df.set_index("Platform"))

# Top SEO Issues
st.subheader("Top SEO Issues")
missing_meta = sum(
    1 for r in data if not r.get('seo_analysis', {}).get('meta_description', {}).get('text')
)
missing_h1 = sum(
    1 for r in data if not r.get('seo_analysis', {}).get('headers', {}).get('has_h1')
)
missing_alt = sum(
    r.get('seo_analysis', {}).get('images', {}).get('images_without_alt', 0)
    for r in data
)
seo_issues = pd.DataFrame([
    {"Issue": "Missing Meta Description", "Count": missing_meta},
    {"Issue": "Missing H1 Tags", "Count": missing_h1},
    {"Issue": "Images Missing Alt Text", "Count": missing_alt},
])
st.dataframe(seo_issues, use_container_width=True)

# Detailed Website Analysis
st.subheader("Detailed Website Analysis")
for idx, row in df.iterrows():
    with st.expander(f"{row['url']} ({row['platform_type']})"):
        st.markdown(f"**Contact Emails:** {', '.join(row['contact_info.emails']) if isinstance(row['contact_info.emails'], list) else row['contact_info.emails']}")
        st.markdown(f"**Contact Phones:** {', '.join(row['contact_info.phones']) if isinstance(row['contact_info.phones'], list) else row['contact_info.phones']}")
        st.markdown(f"**SEO Title:** {row.get('seo_analysis.title.text', '')}")
        st.markdown(f"**Meta Description:** {row.get('seo_analysis.meta_description.text', '')}")
        st.markdown(f"**Word Count:** {row.get('seo_analysis.content_analysis.word_count', '')}")
        st.markdown(f"**Images Missing Alt Text:** {row.get('seo_analysis.images.images_without_alt', '')}")
        st.markdown(f"**Recommendations:**")
        recs = row['recommendations'] if isinstance(row['recommendations'], list) else []
        for rec in recs:
            st.write(f"- {rec}")
        # Show raw data if checkbox is checked
        if st.checkbox(f"Show raw data for {row['url']}", key=f"raw_{idx}"):
            st.json(row.to_dict())

# Download option
st.download_button(
    label="Download Full Analysis as CSV",
    data=df.to_csv(index=False),
    file_name="analysis_results.csv",
    mime="text/csv"
) 