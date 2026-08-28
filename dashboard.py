# dashboard_gironde_2026.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import requests
import io
import gzip
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="Dashboard Immobilier Gironde 2026",
    page_icon="🏘️",
    layout="wide"
)

# --- Dictionnaire des principales communes de Gironde ---
COMMUNES_GIRONDE = {
    "33063": "Bordeaux",
    "33069": "Bruges",
    "33075": "Cenon",
    "33119": "Eysines",
    "33192": "Gradignan",
    "33200": "Gujan-Mestras",
    "33249": "Lormont",
    "33273": "Mérignac",
    "33281": "Pessac",
    "33312": "Saint-Médard-en-Jalles",
    "33318": "Talence",
    "33434": "Le Bouscat",
    "33449": "Villenave-d'Ornon",
    "33039": "Bègles",
    "33056": "Blanquefort",
    "33162": "Floirac",
    "33243": "Libourne",
    "33522": "Arcachon",
    "33529": "La Teste-de-Buch",
    "33550": "Cestas",
}
NOMS_COMMUNES_GIRONDE = {v: k for k, v in COMMUNES_GIRONDE.items()}

# --- Fonction de chargement des données 2026 (via le lien Box) ---
@st.cache_data(ttl=3600)
def load_gironde_2026_data():
    """
    Charge les données DVF 2026 pour la Gironde
    depuis le lien de téléchargement Box fourni par l'utilisateur
    """
    # Lien direct vers le fichier (edition 2026)
    url = "https://euc1.boxcloud.com/d/1/a1!cfdBY_D0VOPJc6gdrcA3QM9x5JInLYadsDZDG3-ipQGuygd9H19f7N5M3MG1z5kVkw0jqzR80QzTr1IxGjZSjCQkegbiu9dGDyZKDTjQ2BZStXlPcoH-3LNiNDFoLqUBL3jX62QPuJ2n9O1Pr3lq6j-YpgOzlzBKfditcuJc7CQ1KdW7zKX7cWmFCtegSyDyvmunQfuzDcfJn_bZPS8gwSfHpkg1uTRkbcfYkLeSMiwD909m2NBmTmNh5YLt5dIgTidX4SjKbwhRTu6G1a1VLtpU1rY9OsEcbk_Zv2ziB6SxfmpWb6u2knsJXmRr7v5vKFzeYUYtJytDur0wGZ5Hbny0rjotdpWdYuhkK0VqjTDV2yltS2hDzyKw5fCG8XofVQGB6Kf3TjpXmiv1idDvZNtwUNJQGscJo_SCHzstEgvat20qLM7y56fVamODjp4az8lvN8GdcgtZgLXsKQMTV3S9zdQNwKQUGpbSLhoFa8-32HEGpEX5Rboi1hpfYXqLfSfv7nRjswX-KDVv4PzNZAHfLjdk4XujPqhfsullFr6502sZ1z8Eu1WBNg5zlxs8q43x8Md9Vx7MbasDOLzcTjJ792jay4ax4J43hZhr196jv9LShNaaBAUlg5vFN_bpr77ZKssdGfNqFZGQDpLur4jiOG7WQ1qTdeI05Q78gGwKOvkx41UI09eE8kLl6tZ1rD90WzmMmPZaCd2aqrVIM5reH2rXr8In4OwwKawGbM76I5H8QxaZZ1mgA3ZXyMZb7Li5cnFSF1IWK4gwayeDWEZnZO3LrTZJ9WU3McwKEVxeBVLuePlxFIDwnMQuRZvcoxJ0EZElJvdQtBlfM38Z3QyHY-KZ03M-a72PUXOasS4cyevwCzSi6sFl1VOwm4wz6wI7zLbCbfF9nruqqqmY-G0bTuN9MEuQeINEt4rPG-0U9IeTHjWLG-2k-UzLBmNi0Id9ykZmcTkY6CTrQ6leHrnxWg1LUw5he7nTSjEu-4kwRsRHUOPuZHyHGEELKlxO8wfVG86i6GxY_qnx8iKf7yYYmbrJKYT6CQ6q_33JwjAyKYyoD2KeeS9uJ1oVOyIu0NFCL5VcEi__d94B5mO_Sz4alj1hOpHWFvvp5bglaM7rBIIbd-pKOLGBXDgWcvPqVH1bFisH51AJsjuhnNx4-rakRbAl9AT3TVZnpDo8OUeVnlfzXBhfo_-BWUGKayPYkefh9jAowbQhJsyFXhKhmFmpeURAoYfFKhKxBBGXRpTq6ovZfRffPkAX5ysHBld46FN1XKttas0TLnPtezzYj7IKZv3geaewejyxNPle5NOEztHWnvUbSyqhBL4qWgaSaOxMuLA2KM6F0UBbyEguJJG3-4n8CzVH2nyoNWmuB4B2vNxXTKN6NpAoEpiufRT2hjAj_UGHu9CDOFWM2tKFoRV2wcQ./download"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        with st.spinner("📥 Téléchargement des données DVF 2026 depuis le lien Box..."):
            response = requests.get(url, headers=headers, stream=True, timeout=120)
            response.raise_for_status()
        
        content = response.content
        
        # Tentative de lecture (gère automatiquement le gzip si présent)
        with st.spinner("🔄 Décompression et traitement des données..."):
            try:
                # Si le fichier est compressé en gzip
                with gzip.open(io.BytesIO(content), 'rt', encoding='utf-8') as f:
                    df = pd.read_csv(f, sep=',', low_memory=False)
            except gzip.BadGzipFile:
                # Si le fichier est un CSV brut
                df = pd.read_csv(io.BytesIO(content), sep=',', low_memory=False)
            except Exception as e:
                # Fallback : lecture avec pandas en mode texte
                df = pd.read_csv(io.StringIO(content.decode('utf-8')), sep=',', low_memory=False)

        if df.empty:
            st.warning("Le fichier téléchargé est vide.")
            return pd.DataFrame()
        
        st.sidebar.success(f"✅ {len(df):,} transactions brutes chargées (source Box 2026)")
        return df
        
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            st.error("🚫 Le lien de téléchargement Box est introuvable (404). Il a peut-être expiré.")
            st.info("📂 Vous pouvez télécharger manuellement le fichier depuis le dossier Box et l'importer via le bouton ci-dessous.")
        else:
            st.error(f"Erreur HTTP : {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur lors du chargement depuis Box : {e}")
        st.info("📂 Vous pouvez télécharger manuellement le fichier et l'importer ci-dessous.")
        return pd.DataFrame()

# --- Fonction de nettoyage et préparation (identique à la version 2025) ---
def prepare_data(df):
    if df.empty:
        return pd.DataFrame()
    
    df_clean = df.copy()
    
    if 'date_mutation' in df_clean.columns:
        df_clean["date_mutation"] = pd.to_datetime(df_clean["date_mutation"], 
                                                   format='%Y-%m-%d', 
                                                   errors='coerce')
    
    if 'valeur_fonciere' in df_clean.columns:
        df_clean["valeur_fonciere"] = pd.to_numeric(df_clean["valeur_fonciere"], 
                                                    errors='coerce')
    
    if 'surface_reelle_bati' in df_clean.columns:
        df_clean["surface_reelle_bati"] = pd.to_numeric(df_clean["surface_reelle_bati"], 
                                                       errors='coerce')
    
    if 'type_local' in df_clean.columns:
        df_clean = df_clean[df_clean["type_local"].isin(['Maison', 'Appartement'])]
    
    critical_cols = [col for col in ['valeur_fonciere', 'surface_reelle_bati'] 
                    if col in df_clean.columns]
    if critical_cols:
        df_clean = df_clean.dropna(subset=critical_cols)
    
    if 'valeur_fonciere' in df_clean.columns:
        df_clean = df_clean[df_clean['valeur_fonciere'] > 20000]
        df_clean = df_clean[df_clean['valeur_fonciere'] < 3000000]
    
    if 'surface_reelle_bati' in df_clean.columns:
        df_clean = df_clean[df_clean['surface_reelle_bati'] > 9]
        df_clean = df_clean[df_clean['surface_reelle_bati'] < 400]
    
    if 'valeur_fonciere' in df_clean.columns and 'surface_reelle_bati' in df_clean.columns:
        df_clean['prix_m2'] = df_clean['valeur_fonciere'] / df_clean['surface_reelle_bati']
        df_clean = df_clean[(df_clean['prix_m2'] > 500) & (df_clean['prix_m2'] < 12000)]
    
    if 'code_commune' in df_clean.columns:
        df_clean['code_commune'] = df_clean['code_commune'].astype(str).str.zfill(5)
        df_clean['nom_commune'] = df_clean['code_commune'].map(COMMUNES_GIRONDE)
        df_clean = df_clean.dropna(subset=['nom_commune'])
    
    return df_clean

# --- Interface Utilisateur ---
st.title("🏘️ Dashboard Immobilier Gironde - Données 2026")
st.markdown("*Source : DVF+ open-data (Cerema) via Box / data.gouv.fr*")
st.markdown("Département de la Gironde (33) - Édition 2026")

# Chargement des données
df_brut = load_gironde_2026_data()

# Fallback : si le chargement direct échoue, proposer l'upload manuel
if df_brut.empty:
    st.info("💡 Le chargement automatique a échoué ou le lien a expiré.")
    st.markdown("**Téléchargez le fichier CSV/CSV.gz depuis le dossier Box et importez-le manuellement :**")
    
    uploaded_file = st.file_uploader(
        "Choisissez le fichier de données (CSV ou CSV.gz)",
        type=['csv', 'gz']
    )
    
    if uploaded_file is not None:
        try:
            content = uploaded_file.read()
            # Tester si c'est du gzip
            try:
                with gzip.open(io.BytesIO(content), 'rt', encoding='utf-8') as f:
                    df_brut = pd.read_csv(f, sep=',', low_memory=False)
            except gzip.BadGzipFile:
                df_brut = pd.read_csv(io.BytesIO(content), sep=',', low_memory=False)
            
            st.sidebar.success(f"✅ {len(df_brut):,} transactions chargées manuellement")
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")
            st.stop()
    else:
        st.stop()
else:
    st.sidebar.success("✅ Données chargées depuis le lien Box")

if df_brut.empty:
    st.warning("Aucune donnée à traiter.")
    st.stop()

# Préparation des données
with st.spinner("🧹 Nettoyage et préparation des données..."):
    df = prepare_data(df_brut)

if df.empty:
    st.warning("⚠️ Aucune transaction valide pour la Gironde après nettoyage.")
    
    with st.expander("🔍 Voir les colonnes disponibles dans le fichier source"):
        st.write("Colonnes :", df_brut.columns.tolist())
        if 'code_commune' in df_brut.columns:
            st.write("Communes présentes dans les données brutes :")
            communes_presentes = df_brut['code_commune'].astype(str).str[:5].unique()
            st.write(sorted(communes_presentes)[:20])
    st.stop()

# --- Sélection de la commune ---
st.sidebar.header("📍 Sélection de la commune")
communes_disponibles = sorted(df['nom_commune'].unique())

if not communes_disponibles:
    st.error("Aucune commune trouvée.")
    st.stop()

selected_commune_name = st.sidebar.selectbox(
    "Choisissez une commune :",
    options=communes_disponibles,
    index=communes_disponibles.index("Bordeaux") if "Bordeaux" in communes_disponibles else 0
)

df_commune = df[df['nom_commune'] == selected_commune_name].copy()

if df_commune.empty:
    st.warning(f"Aucune donnée pour {selected_commune_name} en 2026")
    st.stop()

# --- Filtres avancés ---
st.sidebar.header("🔧 Filtres")

if 'code_postal' in df_commune.columns:
    codes_postaux = sorted(df_commune['code_postal'].astype(str).unique())
    code_postal_selection = st.sidebar.multiselect("Code postal", codes_postaux, default=codes_postaux)
else:
    code_postal_selection = []

if 'type_local' in df_commune.columns:
    type_local_options = ['Tous', 'Maison', 'Appartement']
    type_local = st.sidebar.selectbox("Type de bien", type_local_options)
else:
    type_local = 'Tous'

prix_min = st.sidebar.number_input("Prix minimum (€)", value=0, step=20000, min_value=0)
prix_max = st.sidebar.number_input("Prix maximum (€)", value=int(df_commune['valeur_fonciere'].max()), step=50000, min_value=0)
surface_min = st.sidebar.slider("Surface minimum (m²)", min_value=0, max_value=int(df_commune['surface_reelle_bati'].max()), value=0)

df_filtre = df_commune.copy()

if code_postal_selection and 'code_postal' in df_filtre.columns:
    df_filtre = df_filtre[df_filtre['code_postal'].astype(str).isin(code_postal_selection)]

df_filtre = df_filtre[
    (df_filtre['valeur_fonciere'] >= prix_min) & 
    (df_filtre['valeur_fonciere'] <= prix_max) &
    (df_filtre['surface_reelle_bati'] >= surface_min)
]

if type_local != 'Tous' and 'type_local' in df_filtre.columns:
    df_filtre = df_filtre[df_filtre['type_local'] == type_local]

if df_filtre.empty:
    st.warning("Aucune transaction ne correspond à vos filtres.")
    st.stop()

# --- KPIs ---
st.header(f"📊 Indicateurs Clés - {selected_commune_name} (2026)")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    prix_m2_moyen = df_filtre['prix_m2'].mean()
    st.metric("Prix moyen / m²", f"{prix_m2_moyen:,.0f} €")

with col2:
    prix_median = df_filtre['valeur_fonciere'].median()
    st.metric("Prix médian", f"{prix_median:,.0f} €")

with col3:
    nb_transactions = len(df_filtre)
    st.metric("Transactions", f"{nb_transactions:,}")

with col4:
    surface_moyenne = df_filtre['surface_reelle_bati'].mean()
    st.metric("Surface moyenne", f"{surface_moyenne:.0f} m²")

with col5:
    if 'nombre_pieces_principales' in df_filtre.columns:
        pieces_moyennes = df_filtre['nombre_pieces_principales'].mean()
        st.metric("Pièces principales", f"{pieces_moyennes:.1f}")

# --- Visualisations ---
st.header(f"📈 Analyses - {selected_commune_name}")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Distribution des prix au m²")
    fig = px.histogram(
        df_filtre, 
        x='prix_m2', 
        nbins=40,
        color='type_local' if 'type_local' in df_filtre.columns else None,
        marginal="box",
        title=f"Prix au m² - {selected_commune_name} (2026)",
        labels={'prix_m2': 'Prix au m² (€)', 'count': 'Nombre de transactions'}
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Prix selon la surface")
    fig = px.scatter(
        df_filtre,
        x='surface_reelle_bati',
        y='valeur_fonciere',
        color='type_local' if 'type_local' in df_filtre.columns else None,
        hover_data=['code_postal'],
        title="Corrélation surface / prix (2026)",
        labels={
            'surface_reelle_bati': 'Surface (m²)',
            'valeur_fonciere': 'Prix (€)'
        }
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Carte ---
st.subheader(f"🗺️ Carte des transactions - {selected_commune_name}")

if 'latitude' in df_filtre.columns and 'longitude' in df_filtre.columns:
    df_carte = df_filtre.dropna(subset=['latitude', 'longitude'])
    
    if not df_carte.empty:
        if len(df_carte) > 500:
            df_carte = df_carte.sample(500)
            st.caption(f"Affichage de 500 transactions sur {len(df_filtre)} (échantillon aléatoire)")
        
        fig = px.scatter_mapbox(
            df_carte,
            lat="latitude",
            lon="longitude",
            color="prix_m2",
            size="surface_reelle_bati",
            hover_data={
                "valeur_fonciere": ":.0f",
                "type_local": True,
                "surface_reelle_bati": ":.0f",
                "prix_m2": ":.0f"
            },
            color_continuous_scale="RdYlGn_r",
            size_max=15,
            zoom=12,
            mapbox_style="open-street-map",
            title=f"Transactions à {selected_commune_name} (2026)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📍 Données de géolocalisation non disponibles")

# --- Évolution temporelle ---
st.subheader(f"📅 Évolution des transactions - {selected_commune_name}")

if 'date_mutation' in df_filtre.columns and not df_filtre.empty:
    df_filtre['mois'] = df_filtre['date_mutation'].dt.to_period('M')
    df_mensuel = df_filtre.groupby('mois').agg({
        'prix_m2': 'mean',
        'valeur_fonciere': ['count', 'mean']
    }).round(0)
    
    df_mensuel.columns = ['prix_m2_moyen', 'nb_transactions', 'prix_moyen']
    df_mensuel = df_mensuel.reset_index()
    df_mensuel['mois'] = df_mensuel['mois'].astype(str)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.line(
            df_mensuel,
            x='mois',
            y='prix_m2_moyen',
            title="Évolution du prix au m² (2026)",
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.bar(
            df_mensuel,
            x='mois',
            y='nb_transactions',
            title="Nombre de transactions par mois (2026)"
        )
        st.plotly_chart(fig, use_container_width=True)

# --- Top des ventes ---
st.subheader("💰 Top 5 des ventes les plus élevées")
top_ventes = df_filtre.nlargest(5, 'valeur_fonciere')[
    ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'prix_m2', 'type_local', 'code_postal']
]
if not top_ventes.empty:
    top_ventes['valeur_fonciere'] = top_ventes['valeur_fonciere'].apply(lambda x: f"{x:,.0f} €")
    top_ventes['prix_m2'] = top_ventes['prix_m2'].apply(lambda x: f"{x:,.0f} €/m²")
    st.dataframe(top_ventes, use_container_width=True, hide_index=True)

st.subheader("📋 Dernières transactions")
df_display = df_filtre.sort_values('date_mutation', ascending=False).head(50)

display_cols = ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 
                'prix_m2', 'type_local', 'code_postal']
available_cols = [col for col in display_cols if col in df_display.columns]

if available_cols:
    for col in ['valeur_fonciere', 'prix_m2']:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(
                lambda x: f"{x:,.0f} €" + ("/m²" if col == 'prix_m2' else "")
            )
    
    st.dataframe(df_display[available_cols], use_container_width=True, hide_index=True)

# --- Pied de page ---
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: grey; padding: 10px;'>
        <b>Source :</b> DVF+ open-data (Cerema) / Box - Édition 2026 - Gironde (33)<br>
        <b>Données :</b> {len(df_filtre):,} transactions affichées sur {len(df_commune):,} pour {selected_commune_name}<br>
        <b>Mise à jour :</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}
    </div>
    """,
    unsafe_allow_html=True
)
