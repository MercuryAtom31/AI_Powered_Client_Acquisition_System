import streamlit as st
import json
import pandas as pd
from collections import defaultdict, Counter
from urllib.parse import urlparse
import numpy as np

st.set_page_config(page_title="Tableau de bord d'acquisition de clients par IA", layout="wide")
st.title("Tableau de bord d'acquisition de clients par IA")

# Load analysis results
def load_data(file_path="analysis_results.json"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return []

data = load_data()

if not data:
    st.warning("Aucun résultat d'analyse trouvé. Veuillez d'abord exécuter le script d'analyse.")
    st.stop()

# Convert to DataFrame for easier manipulation
df = pd.json_normalize(data)
unique_domains = df['url'].apply(lambda x: urlparse(x).netloc).nunique()

def safe_len(x):
    if isinstance(x, list):
        return len(x)
    return 0

def has_email(x):
    if isinstance(x, list):
        return bool(x) and len(x) > 0
    return False

def has_phone(x):
    if isinstance(x, list):
        return bool(x) and len(x) > 0
    return False

# Summary statistics (robust)
st.header("Statistiques Résumées")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Nombre total d'entreprises", unique_domains)
col2.metric("Nombre total de contacts", sum(df['contact_info.emails'].apply(safe_len)))
col3.metric("Sites web avec email", sum(df['contact_info.emails'].apply(has_email)))
col4.metric("Sites web avec téléphone", sum(df['contact_info.phones'].apply(has_phone)))

# Platform distribution
st.subheader("Répartition des plateformes")
platform_counts = Counter(df['platform_type'])
platform_df = pd.DataFrame(platform_counts.items(), columns=["Plateforme", "Nombre"])
st.bar_chart(platform_df.set_index("Plateforme"))

# Top SEO Issues
st.subheader("Principaux problèmes SEO")
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
    {"Problème": "Meta description manquante", "Nombre": missing_meta},
    {"Problème": "Balises H1 manquantes", "Nombre": missing_h1},
    {"Problème": "Images sans texte alternatif", "Nombre": missing_alt},
])
st.dataframe(seo_issues, use_container_width=True)

# Group by domain for detailed analysis
domain_groups = defaultdict(list)
for row in data:
    domain = urlparse(row.get('url', '')).netloc
    domain_groups[domain].append(row)

# Optional: Add a search/filter box
search = st.text_input("Filtrer par domaine ou sous-page (optionnel)").lower()

st.header("Analyse détaillée par domaine et sous-page")
for domain, pages in sorted(domain_groups.items()):
    if not domain:
        continue  # Skip empty domain groups
    if search and search not in domain.lower() and not any(search in p['url'].lower() for p in pages):
        continue
    st.subheader(f"Domaine : {domain} (sous-pages analysées : {len(pages)})")
    for idx, row in enumerate(sorted(pages, key=lambda x: x['url'])):
        if search and search not in row['url'].lower():
            continue
        with st.expander(f"{row['url']}"):
            st.markdown(f"**Emails de contact :** {', '.join(row.get('contact_info', {}).get('emails', []))}")
            st.markdown(f"**Téléphones de contact :** {', '.join(row.get('contact_info', {}).get('phones', []))}")
            st.markdown(f"**Titre SEO :** {row.get('seo_analysis', {}).get('title', {}).get('text', '')}")
            st.markdown(f"**Meta description :** {row.get('seo_analysis', {}).get('meta_description', {}).get('text', '')}")
            st.markdown(f"**Nombre de mots :** {row.get('seo_analysis', {}).get('content_analysis', {}).get('word_count', '')}")
            st.markdown(f"**Images sans texte alternatif :** {row.get('seo_analysis', {}).get('images', {}).get('images_without_alt', '')}")
            st.markdown(f"**Recommandations :**")
            recs = row.get('recommendations', [])
            for rec in recs:
                st.write(f"- {rec}")
            if st.checkbox(f"Afficher les données brutes pour {row['url']}", key=f"raw_{domain}_{idx}"):
                st.json(row)

# Download option
st.download_button(
    label="Télécharger l'analyse complète en CSV",
    data=df.to_csv(index=False),
    file_name="resultats_analyse.csv",
    mime="text/csv"
) 