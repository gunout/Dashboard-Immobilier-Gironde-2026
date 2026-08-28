# dashboard.py – Version définitive pour DVF+ 2026
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from datetime import datetime

# Détection de pyproj pour la conversion Lambert 93
try:
    import pyproj
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False

st.set_page_config(page_title="Dashboard Immobilier Gironde 2026", page_icon="🏘️", layout="wide")

# --- Dictionnaire des communes ---
COMMUNES_GIRONDE = {
    "33063": "Bordeaux", "33069": "Bruges", "33075": "Cenon", "33119": "Eysines",
    "33192": "Gradignan", "33200": "Gujan-Mestras", "33249": "Lormont", "33273": "Mérignac",
    "33281": "Pessac", "33312": "Saint-Médard-en-Jalles", "33318": "Talence", "33434": "Le Bouscat",
    "33449": "Villenave-d'Ornon", "33039": "Bègles", "33056": "Blanquefort", "33162": "Floirac",
    "33243": "Libourne", "33522": "Arcachon", "33529": "La Teste-de-Buch", "33550": "Cestas",
}

# --- URL du fichier GitHub Release ---
DATA_URL = "https://github.com/gunout/Dashboard-Immobilier-Gironde-2026/releases/download/DVF-33/dvf_plus_d33.csv"

@st.cache_data(ttl=3600)
def load_data():
    """Télécharge et lit le fichier DVF+ (séparateur |) depuis GitHub Release."""
    try:
        with st.spinner("📥 Téléchargement des données 2026..."):
            response = requests.get(DATA_URL, timeout=60)
            response.raise_for_status()

        # Vérifier qu'on n'a pas une page HTML (erreur GitHub)
        content_type = response.headers.get('content-type', '')
        if 'text/html' in content_type:
            st.error("❌ Le lien renvoie une page HTML. Vérifiez que la release est publique.")
            return None

        # Lecture directe avec séparateur '|'
        df = pd.read_csv(
            io.StringIO(response.text),
            sep='|',
            dtype=str,
            engine='python',
            on_bad_lines='skip'
        )

        if df.empty:
            st.warning("Le fichier est vide.")
            return None

        # Affichage des colonnes dans la barre latérale (diagnostic)
        st.sidebar.write("**Colonnes trouvées :**", list(df.columns))
        st.sidebar.write(f"**Nombre de lignes :** {len(df):,}")

        return df

    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        return None

def prepare_data(df):
    """Prépare et nettoie les données DVF+."""
    if df is None or df.empty:
        return None

    d = df.copy()

    # --- Renommage des colonnes DVF+ vers les noms standards ---
    rename_map = {
        'datemut': 'date_mutation',
        'valeurfonc': 'valeur_fonciere',
        'sbati': 'surface_reelle_bati',
        'libtypbien': 'type_local',
        'l_codinsee': 'code_commune',
        'geompar_x': 'longitude_lambert',
        'geompar_y': 'latitude_lambert',
        'l_codepost': 'code_postal',
        'nbpieceprin': 'nombre_pieces_principales'
    }
    for old, new in rename_map.items():
        if old in d.columns:
            d = d.rename(columns={old: new})

    # --- Vérification des colonnes essentielles ---
    required = ['valeur_fonciere', 'surface_reelle_bati']
    missing = [col for col in required if col not in d.columns]
    if missing:
        st.error(f"❌ Colonnes manquantes : {missing}")
        st.error(f"Colonnes disponibles : {list(d.columns)}")
        return None

    # --- Conversion numérique ---
    d['valeur_fonciere'] = pd.to_numeric(d['valeur_fonciere'], errors='coerce')
    d['surface_reelle_bati'] = pd.to_numeric(d['surface_reelle_bati'], errors='coerce')

    # --- Filtrage des types de biens ---
    if 'type_local' in d.columns:
        d = d[d['type_local'].isin(['Maison', 'Appartement'])]

    # --- Suppression des NA ---
    d = d.dropna(subset=['valeur_fonciere', 'surface_reelle_bati'])

    # --- Filtres de cohérence ---
    d = d[(d['valeur_fonciere'] > 20000) & (d['valeur_fonciere'] < 3000000)]
    d = d[(d['surface_reelle_bati'] > 9) & (d['surface_reelle_bati'] < 400)]

    # --- Calcul du prix au m² ---
    d['prix_m2'] = d['valeur_fonciere'] / d['surface_reelle_bati']
    d = d[(d['prix_m2'] > 500) & (d['prix_m2'] < 12000)]

    # --- Nom de commune ---
    if 'code_commune' in d.columns:
        d['code_commune'] = d['code_commune'].astype(str).str.zfill(5)
        d['nom_commune'] = d['code_commune'].map(COMMUNES_GIRONDE)
        d = d.dropna(subset=['nom_commune'])

    # --- Conversion Lambert → WGS84 ---
    if 'longitude_lambert' in d.columns and 'latitude_lambert' in d.columns:
        d['longitude_lambert'] = pd.to_numeric(d['longitude_lambert'], errors='coerce')
        d['latitude_lambert'] = pd.to_numeric(d['latitude_lambert'], errors='coerce')

        if HAS_PYPROJ:
            try:
                lambert93 = pyproj.Proj('+proj=lcc +lat_1=49 +lat_2=44 +lat_0=46.5 +lon_0=3 +x_0=700000 +y_0=6600000 +ellps=GRS80 +units=m +no_defs')
                wgs84 = pyproj.Proj('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
                lon_vals = d['longitude_lambert'].values
                lat_vals = d['latitude_lambert'].values
                mask = ~(pd.isna(lon_vals) | pd.isna(lat_vals))
                if mask.any():
                    new_lon, new_lat = pyproj.transform(lambert93, wgs84, lon_vals[mask], lat_vals[mask])
                    d.loc[mask, 'longitude'] = new_lon
                    d.loc[mask, 'latitude'] = new_lat
                # Nettoyer les colonnes Lambert
                d = d.drop(columns=['longitude_lambert', 'latitude_lambert'], errors='ignore')
                st.sidebar.success("✅ Conversion Lambert → WGS84 effectuée")
            except Exception as e:
                st.sidebar.warning(f"⚠️ Conversion échouée : {e}")
                d['longitude'] = d['longitude_lambert']
                d['latitude'] = d['latitude_lambert']
        else:
            d['longitude'] = d['longitude_lambert']
            d['latitude'] = d['latitude_lambert']

    # --- Garder uniquement les colonnes utiles ---
    keep_cols = ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati',
                 'type_local', 'code_commune', 'code_postal',
                 'latitude', 'longitude', 'nombre_pieces_principales',
                 'prix_m2', 'nom_commune']
    keep_cols = [c for c in keep_cols if c in d.columns]
    if keep_cols:
        d = d[keep_cols]

    # --- Affichage des statistiques ---
    st.sidebar.success(f"✅ {len(d):,} transactions après nettoyage")
    return d

# --- Interface utilisateur ---
st.title("🏘️ Dashboard Immobilier Gironde - 2026")
st.markdown(f"Source : [dvf_plus_d33.csv]({DATA_URL})")

df = load_data()
if df is None or df.empty:
    st.error("❌ Impossible de charger les données. Vérifiez le lien et la release GitHub.")
    if st.button("🔄 Réessayer"):
        st.rerun()
    st.stop()

df = prepare_data(df)
if df is None or df.empty:
    st.warning("Aucune transaction valide après nettoyage.")
    st.stop()

# --- Sélection de la commune ---
communes = sorted(df['nom_commune'].unique())
selected = st.sidebar.selectbox(
    "Choisissez une commune",
    communes,
    index=communes.index("Bordeaux") if "Bordeaux" in communes else 0
)
df_commune = df[df['nom_commune'] == selected].copy()
if df_commune.empty:
    st.warning(f"Aucune donnée pour {selected}")
    st.stop()

# --- Filtres ---
st.sidebar.header("🔧 Filtres")
if 'code_postal' in df_commune.columns and not df_commune['code_postal'].isna().all():
    cp_options = sorted(df_commune['code_postal'].astype(str).unique())
    cp_selection = st.sidebar.multiselect("Code postal", cp_options, default=cp_options)
else:
    cp_selection = []

type_local = st.sidebar.selectbox("Type de bien", ['Tous', 'Maison', 'Appartement'])
prix_min = st.sidebar.number_input("Prix minimum (€)", 0, step=20000)
prix_max = st.sidebar.number_input(
    "Prix maximum (€)",
    int(df_commune['valeur_fonciere'].max()),
    step=50000,
    min_value=0
)
surface_min = st.sidebar.slider(
    "Surface minimum (m²)",
    min_value=0,
    max_value=int(df_commune['surface_reelle_bati'].max()),
    value=0
)

df_filtre = df_commune.copy()
if cp_selection and 'code_postal' in df_filtre.columns:
    df_filtre = df_filtre[df_filtre['code_postal'].astype(str).isin(cp_selection)]
df_filtre = df_filtre[
    (df_filtre['valeur_fonciere'] >= prix_min) &
    (df_filtre['valeur_fonciere'] <= prix_max) &
    (df_filtre['surface_reelle_bati'] >= surface_min)
]
if type_local != 'Tous' and 'type_local' in df_filtre.columns:
    df_filtre = df_filtre[df_filtre['type_local'] == type_local]
if df_filtre.empty:
    st.warning("Aucune transaction ne correspond aux filtres.")
    st.stop()

# --- KPIs ---
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Prix moyen / m²", f"{df_filtre['prix_m2'].mean():,.0f} €")
c2.metric("Prix médian", f"{df_filtre['valeur_fonciere'].median():,.0f} €")
c3.metric("Transactions", f"{len(df_filtre):,}")
c4.metric("Surface moyenne", f"{df_filtre['surface_reelle_bati'].mean():.0f} m²")
if 'nombre_pieces_principales' in df_filtre.columns:
    c5.metric("Pièces principales", f"{df_filtre['nombre_pieces_principales'].mean():.1f}")

# --- Graphiques ---
col1, col2 = st.columns(2)
with col1:
    fig = px.histogram(
        df_filtre,
        x='prix_m2',
        nbins=40,
        color='type_local' if 'type_local' in df_filtre.columns else None,
        marginal="box",
        title=f"Distribution des prix au m² – {selected}"
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.scatter(
        df_filtre,
        x='surface_reelle_bati',
        y='valeur_fonciere',
        color='type_local' if 'type_local' in df_filtre.columns else None,
        hover_data=['code_postal'],
        title="Corrélation surface / prix"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Carte avec OpenStreetMap ---
st.subheader(f"🗺️ Carte des transactions – {selected} (2026)")

if 'latitude' in df_filtre.columns and 'longitude' in df_filtre.columns:
    df_carte = df_filtre.copy()
    df_carte['latitude'] = pd.to_numeric(df_carte['latitude'], errors='coerce')
    df_carte['longitude'] = pd.to_numeric(df_carte['longitude'], errors='coerce')
    df_carte = df_carte.dropna(subset=['latitude', 'longitude'])

    if not df_carte.empty:
        lat_min, lat_max = df_carte['latitude'].min(), df_carte['latitude'].max()
        lon_min, lon_max = df_carte['longitude'].min(), df_carte['longitude'].max()

        with st.expander("🔍 Diagnostic des coordonnées"):
            st.write(f"Latitude : {lat_min:.4f} – {lat_max:.4f}")
            st.write(f"Longitude : {lon_min:.4f} – {lon_max:.4f}")
            if lat_max > 90 or lat_min < -90 or lon_max > 180 or lon_min < -180:
                st.warning("⚠️ Les coordonnées semblent être en mètres (Lambert). Affichage approximatif.")

        if len(df_carte) > 500:
            df_carte = df_carte.sample(500)
            st.caption(f"Affichage de 500 transactions sur {len(df_filtre)} (échantillon aléatoire)")

        try:
            fig = px.scatter_map(
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
                color_continuous_scale="Viridis",
                size_max=15,
                zoom=13,
                map_style="open-street-map",
                title=f"Transactions à {selected} (2026)"
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ Erreur avec OpenStreetMap : {e}")
            st.info("🔄 Tentative avec le style Carto-Positron...")
            try:
                fig = px.scatter_map(
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
                    color_continuous_scale="Viridis",
                    size_max=15,
                    zoom=13,
                    map_style="carto-positron",
                    title=f"Transactions à {selected} (fallback)"
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e2:
                st.error(f"❌ Erreur définitive : {e2}")
    else:
        st.info("📍 Aucune coordonnée valide pour la carte.")
else:
    st.info("📍 Colonnes latitude/longitude non disponibles.")

# --- Évolution temporelle ---
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
            markers=True,
            title="Évolution du prix au m²"
        )
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(
            df_mensuel,
            x='mois',
            y='nb_transactions',
            title="Nombre de transactions par mois"
        )
        st.plotly_chart(fig, use_container_width=True)

# --- Top 5 des ventes ---
st.subheader("💰 Top 5 des ventes les plus élevées")
top_cols = ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'prix_m2', 'type_local', 'code_postal']
available_top = [c for c in top_cols if c in df_filtre.columns]
if available_top:
    top_ventes = df_filtre.nlargest(5, 'valeur_fonciere')[available_top]
    top_ventes['valeur_fonciere'] = top_ventes['valeur_fonciere'].apply(lambda x: f"{x:,.0f} €")
    top_ventes['prix_m2'] = top_ventes['prix_m2'].apply(lambda x: f"{x:,.0f} €/m²")
    st.dataframe(top_ventes, hide_index=True, use_container_width=True)

# --- Dernières transactions ---
st.subheader("📋 Dernières transactions")
display_cols = ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'prix_m2', 'type_local', 'code_postal']
available_display = [c for c in display_cols if c in df_filtre.columns]
if available_display:
    display = df_filtre.sort_values('date_mutation', ascending=False).head(50)
    for c in ['valeur_fonciere', 'prix_m2']:
        if c in display.columns:
            display[c] = display[c].apply(lambda x: f"{x:,.0f} €" + ("/m²" if c == 'prix_m2' else ""))
    st.dataframe(display[available_display], hide_index=True, use_container_width=True)

# --- Pied de page ---
st.markdown("---")
st.caption(f"Mise à jour : {datetime.now().strftime('%d/%m/%Y %H:%M')} – DVF+ 2026 Gironde (33)")
