import streamlit as st
import json
import pandas as pd
from collections import Counter

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

# Summary statistics
st.header("Statistiques Résumées")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Nombre total d'entreprises", len(df))
col2.metric("Nombre total de contacts", sum(df['contact_info.emails'].apply(lambda x: len(x) if isinstance(x, list) else 0)))
col3.metric("Sites web avec email", sum(df['contact_info.emails'].apply(lambda x: bool(x) and len(x) > 0)))
col4.metric("Sites web avec téléphone", sum(df['contact_info.phones'].apply(lambda x: bool(x) and len(x) > 0)))

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

# Detailed Website Analysis
st.subheader("Analyse détaillée du site web")
for idx, row in df.iterrows():
    with st.expander(f"{row['url']} ({row['platform_type']})"):
        st.markdown(f"**Emails de contact :** {', '.join(row['contact_info.emails']) if isinstance(row['contact_info.emails'], list) else row['contact_info.emails']}")
        st.markdown(f"**Téléphones de contact :** {', '.join(row['contact_info.phones']) if isinstance(row['contact_info.phones'], list) else row['contact_info.phones']}")
        st.markdown(f"**Titre SEO :** {row.get('seo_analysis.title.text', '')}")
        st.markdown(f"**Meta description :** {row.get('seo_analysis.meta_description.text', '')}")
        st.markdown(f"**Nombre de mots :** {row.get('seo_analysis.content_analysis.word_count', '')}")
        st.markdown(f"**Images sans texte alternatif :** {row.get('seo_analysis.images.images_without_alt', '')}")
        st.markdown(f"**Recommandations :**")
        recs = row['recommendations'] if isinstance(row['recommendations'], list) else []
        for rec in recs:
            st.write(f"- {rec}")
        # Show raw data if checkbox is checked
        if st.checkbox(f"Afficher les données brutes pour {row['url']}", key=f"raw_{idx}"):
            st.json(row.to_dict())

# Download option
st.download_button(
    label="Télécharger l'analyse complète en CSV",
    data=df.to_csv(index=False),
    file_name="resultats_analyse.csv",
    mime="text/csv"
) 