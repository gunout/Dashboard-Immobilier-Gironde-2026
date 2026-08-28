# dashboard_gironde_2026.py – mapping dynamique des colonnes
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from datetime import datetime

try:
    import pyproj
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False

st.set_page_config(page_title="Dashboard Immobilier Gironde 2026", page_icon="🏘️", layout="wide")

COMMUNES_GIRONDE = {
    "33063": "Bordeaux", "33069": "Bruges", "33075": "Cenon", "33119": "Eysines",
    "33192": "Gradignan", "33200": "Gujan-Mestras", "33249": "Lormont", "33273": "Mérignac",
    "33281": "Pessac", "33312": "Saint-Médard-en-Jalles", "33318": "Talence", "33434": "Le Bouscat",
    "33449": "Villenave-d'Ornon", "33039": "Bègles", "33056": "Blanquefort", "33162": "Floirac",
    "33243": "Libourne", "33522": "Arcachon", "33529": "La Teste-de-Buch", "33550": "Cestas",
}

GITHUB_CSV_URL = "https://github.com/gunout/Dashboard-Immobilier-Gironde-2026/releases/download/DVF-33/dvf_plus_d33.csv"

@st.cache_data(ttl=3600)
def load_gironde_2026_data():
    try:
        with st.spinner("📥 Téléchargement depuis GitHub Release..."):
            response = requests.get(GITHUB_CSV_URL, stream=True, timeout=60)
            response.raise_for_status()
        
        if 'text/html' in response.headers.get('content-type', ''):
            st.error("Le lien renvoie une page HTML. Vérifiez que la release est publique.")
            return pd.DataFrame()

        with st.spinner("🔄 Lecture du CSV..."):
            df = pd.read_csv(
                io.StringIO(response.text),
                sep='|',
                quotechar='"',
                engine='python',
                on_bad_lines='skip',
                dtype=str
            )
        
        if df.empty:
            st.warning("Le fichier est vide.")
            return pd.DataFrame()
        
        # On garde les noms de colonnes originaux dans un attribut pour diagnostic
        st.session_state['original_columns'] = list(df.columns)
        
        # Affichage des colonnes dans la barre latérale pour debug
        st.sidebar.write("**Colonnes originales :**", st.session_state['original_columns'])
        
        return df

    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        return pd.DataFrame()

def find_column(df, target, candidates):
    """
    Cherche une colonne dont le nom normalisé (minuscule, sans espaces/underscores)
    correspond à l'un des candidats.
    """
    df_cols_norm = {col: col.strip().lower().replace(' ', '').replace('_', '') for col in df.columns}
    target_norm = target.strip().lower().replace(' ', '').replace('_', '')
    for col, norm in df_cols_norm.items():
        if norm == target_norm:
            return col
    for cand in candidates:
        cand_norm = cand.strip().lower().replace(' ', '').replace('_', '')
        for col, norm in df_cols_norm.items():
            if norm == cand_norm:
                return col
    return None

def prepare_data(df):
    if df.empty:
        return df

    # Définir les colonnes standard et leurs synonymes possibles
    column_mapping = {
        'valeur_fonciere': ['valeurfonc', 'valeur_fonciere', 'valeurfonc_brut'],
        'surface_reelle_bati': ['sbati', 'surface_reelle_bati', 'surfbati'],
        'date_mutation': ['datemut', 'date_mutation', 'datemutation'],
        'type_local': ['libtypbien', 'type_local', 'typbien'],
        'code_commune': ['l_codinsee', 'code_commune', 'codinsee'],
        'code_postal': ['l_codepost', 'code_postal', 'codepostal'],
        'longitude_lambert': ['geompar_x', 'longitude_lambert', 'x_lambert'],
        'latitude_lambert': ['geompar_y', 'latitude_lambert', 'y_lambert'],
        'nombre_pieces_principales': ['nbpieceprin', 'nombre_pieces_principales', 'pieces']
    }

    # Créer un mapping réel colonne_originale -> colonne_standard
    real_mapping = {}
    for std_col, candidates in column_mapping.items():
        found = find_column(df, std_col, candidates)
        if found:
            real_mapping[found] = std_col

    # Appliquer le renommage
    df_renamed = df.rename(columns=real_mapping)

    # Vérifier les colonnes essentielles
    required = ['valeur_fonciere', 'surface_reelle_bati']
    missing = [col for col in required if col not in df_renamed.columns]
    if missing:
        st.error(f"Colonnes essentielles manquantes : {missing}. Colonnes disponibles : {list(df_renamed.columns)}")
        return pd.DataFrame()

    # Maintenant, on applique le nettoyage avec les colonnes standard
    df_clean = df_renamed.copy()
    
    # Conversion dates
    if 'date_mutation' in df_clean.columns:
        df_clean["date_mutation"] = pd.to_datetime(df_clean["date_mutation"], errors='coerce')
    
    # Conversion numériques
    for col in ['valeur_fonciere', 'surface_reelle_bati']:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    # Filtre type_local
    if 'type_local' in df_clean.columns:
        df_clean = df_clean[df_clean["type_local"].isin(['Maison', 'Appartement'])]
    
    # Supprimer les NA
    subset_cols = [c for c in ['valeur_fonciere', 'surface_reelle_bati'] if c in df_clean.columns]
    if subset_cols:
        df_clean = df_clean.dropna(subset=subset_cols)
    else:
        st.error("Impossible de trouver les colonnes de valeur et surface.")
        return pd.DataFrame()
    
    # Filtres de cohérence
    if 'valeur_fonciere' in df_clean.columns:
        df_clean = df_clean[(df_clean['valeur_fonciere'] > 20000) & (df_clean['valeur_fonciere'] < 3000000)]
    if 'surface_reelle_bati' in df_clean.columns:
        df_clean = df_clean[(df_clean['surface_reelle_bati'] > 9) & (df_clean['surface_reelle_bati'] < 400)]
    
    # Prix m²
    if 'valeur_fonciere' in df_clean.columns and 'surface_reelle_bati' in df_clean.columns:
        df_clean['prix_m2'] = df_clean['valeur_fonciere'] / df_clean['surface_reelle_bati']
        df_clean = df_clean[(df_clean['prix_m2'] > 500) & (df_clean['prix_m2'] < 12000)]
    
    # Code commune -> nom
    if 'code_commune' in df_clean.columns:
        df_clean['code_commune'] = df_clean['code_commune'].astype(str).str.zfill(5)
        df_clean['nom_commune'] = df_clean['code_commune'].map(COMMUNES_GIRONDE)
        df_clean = df_clean.dropna(subset=['nom_commune'])
    
    # Gestion des coordonnées : on convertit Lambert -> WGS84 si possible
    if 'longitude_lambert' in df_clean.columns and 'latitude_lambert' in df_clean.columns and HAS_PYPROJ:
        try:
            lambert93 = pyproj.Proj('+proj=lcc +lat_1=49 +lat_2=44 +lat_0=46.5 +lon_0=3 +x_0=700000 +y_0=6600000 +ellps=GRS80 +units=m +no_defs')
            wgs84 = pyproj.Proj('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
            lon_vals = pd.to_numeric(df_clean['longitude_lambert'], errors='coerce').values
            lat_vals = pd.to_numeric(df_clean['latitude_lambert'], errors='coerce').values
            mask = ~(pd.isna(lon_vals) | pd.isna(lat_vals))
            if mask.any():
                new_lon, new_lat = pyproj.transform(lambert93, wgs84, lon_vals[mask], lat_vals[mask])
                df_clean.loc[mask, 'longitude'] = new_lon
                df_clean.loc[mask, 'latitude'] = new_lat
            df_clean = df_clean.drop(columns=['longitude_lambert', 'latitude_lambert'], errors='ignore')
        except Exception as e:
            st.warning(f"Conversion Lambert échouée : {e}")
            # On garde les coordonnées brutes (affichage approximatif)
            df_clean['longitude'] = pd.to_numeric(df_clean['longitude_lambert'], errors='coerce')
            df_clean['latitude'] = pd.to_numeric(df_clean['latitude_lambert'], errors='coerce')
    elif 'longitude_lambert' in df_clean.columns and 'latitude_lambert' in df_clean.columns:
        df_clean['longitude'] = pd.to_numeric(df_clean['longitude_lambert'], errors='coerce')
        df_clean['latitude'] = pd.to_numeric(df_clean['latitude_lambert'], errors='coerce')
    
    return df_clean

# --- Interface ---
st.title("🏘️ Dashboard Immobilier Gironde - 2026 (DVF+ format pipe)")
st.markdown(f"Source : [dvf_plus_d33.csv]({GITHUB_CSV_URL})")

df_brut = load_gironde_2026_data()
if df_brut.empty:
    st.info("Impossible de charger les données. Vérifiez le lien et les colonnes affichées dans la barre latérale.")
    if st.button("🔄 Réessayer"):
        st.rerun()
    st.stop()

df = prepare_data(df_brut)
if df.empty:
    st.warning("Aucune transaction valide après nettoyage.")
    st.stop()

# --- Sélection commune ---
communes = sorted(df['nom_commune'].unique())
selected = st.sidebar.selectbox("Commune", communes, index=communes.index("Bordeaux") if "Bordeaux" in communes else 0)
df_commune = df[df['nom_commune'] == selected].copy()
if df_commune.empty:
    st.stop()

# --- Filtres ---
st.sidebar.header("🔧 Filtres")
if 'code_postal' in df_commune.columns and not df_commune['code_postal'].isna().all():
    cp_options = sorted(df_commune['code_postal'].astype(str).unique())
    cp_selection = st.sidebar.multiselect("Code postal", cp_options, default=cp_options)
else:
    cp_selection = []
type_local = st.sidebar.selectbox("Type de bien", ['Tous', 'Maison', 'Appartement'])
prix_min = st.sidebar.number_input("Prix min (€)", 0, step=20000)
prix_max = st.sidebar.number_input("Prix max (€)", int(df_commune['valeur_fonciere'].max()), step=50000)
surface_min = st.sidebar.slider("Surface min (m²)", 0, int(df_commune['surface_reelle_bati'].max()), 0)

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
    st.warning("Aucun résultat.")
    st.stop()

# --- KPIs ---
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Prix moyen / m²", f"{df_filtre['prix_m2'].mean():,.0f} €")
c2.metric("Prix médian", f"{df_filtre['valeur_fonciere'].median():,.0f} €")
c3.metric("Transactions", f"{len(df_filtre):,}")
c4.metric("Surface moyenne", f"{df_filtre['surface_reelle_bati'].mean():.0f} m²")
if 'nombre_pieces_principales' in df_filtre.columns:
    c5.metric("Pièces", f"{df_filtre['nombre_pieces_principales'].mean():.1f}")

# --- Graphiques ---
col1, col2 = st.columns(2)
with col1:
    fig = px.histogram(df_filtre, x='prix_m2', nbins=40,
                       color='type_local' if 'type_local' in df_filtre.columns else None,
                       marginal='box')
    st.plotly_chart(fig, use_container_width=True)
with col2:
    fig = px.scatter(df_filtre, x='surface_reelle_bati', y='valeur_fonciere',
                     color='type_local' if 'type_local' in df_filtre.columns else None,
                     hover_data=['code_postal'])
    st.plotly_chart(fig, use_container_width=True)

# --- Carte ---
st.subheader(f"🗺️ Carte des transactions - {selected} (2026)")

if 'latitude' in df_filtre.columns and 'longitude' in df_filtre.columns:
    df_carte = df_filtre.copy()
    df_carte['latitude'] = pd.to_numeric(df_carte['latitude'], errors='coerce')
    df_carte['longitude'] = pd.to_numeric(df_carte['longitude'], errors='coerce')
    df_carte = df_carte.dropna(subset=['latitude', 'longitude'])

    if not df_carte.empty:
        lat_min, lat_max = df_carte['latitude'].min(), df_carte['latitude'].max()
        lon_min, lon_max = df_carte['longitude'].min(), df_carte['longitude'].max()
        with st.expander("🔍 Diagnostic des coordonnées", expanded=False):
            st.write(f"Latitude : min {lat_min:.4f}, max {lat_max:.4f}")
            st.write(f"Longitude : min {lon_min:.4f}, max {lon_max:.4f}")
            if lat_max > 90 or lat_min < -90 or lon_max > 180 or lon_min < -180:
                st.warning("⚠️ Coordonnées en mètres (Lambert) – affichage décalé possible.")

        if len(df_carte) > 500:
            df_carte = df_carte.sample(500)
            st.caption(f"Affichage de 500 transactions sur {len(df_filtre)} (échantillon)")

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
            st.error(f"Erreur avec open-street-map : {e}")
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
                st.error(f"Erreur définitive : {e2}")
    else:
        st.info("📍 Aucune coordonnée valide.")
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
        fig = px.line(df_mensuel, x='mois', y='prix_m2_moyen', markers=True)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(df_mensuel, x='mois', y='nb_transactions')
        st.plotly_chart(fig, use_container_width=True)

# --- Top ventes ---
st.subheader("💰 Top 5 des ventes")
top = df_filtre.nlargest(5, 'valeur_fonciere')[['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'prix_m2', 'type_local', 'code_postal']]
if not top.empty:
    top['valeur_fonciere'] = top['valeur_fonciere'].apply(lambda x: f"{x:,.0f} €")
    top['prix_m2'] = top['prix_m2'].apply(lambda x: f"{x:,.0f} €/m²")
    st.dataframe(top, hide_index=True, use_container_width=True)

st.subheader("📋 Dernières transactions")
display = df_filtre.sort_values('date_mutation', ascending=False).head(50)
display_cols = ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'prix_m2', 'type_local', 'code_postal']
available = [c for c in display_cols if c in display.columns]
for c in ['valeur_fonciere', 'prix_m2']:
    if c in display.columns:
        display[c] = display[c].apply(lambda x: f"{x:,.0f} €" + ("/m²" if c == 'prix_m2' else ""))
st.dataframe(display[available], hide_index=True, use_container_width=True)

st.markdown("---")
st.caption(f"Mise à jour : {datetime.now().strftime('%d/%m/%Y %H:%M')} – DVF+ 2026 Gironde (33) – GitHub Release")
