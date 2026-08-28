# dashboard_gironde_2026.py – version robuste avec diagnostic des colonnes
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
            # On lit en mode texte avec le séparateur '|'
            df = pd.read_csv(
                io.StringIO(response.text),
                sep='|',
                quotechar='"',
                engine='python',
                on_bad_lines='skip',
                dtype=str  # tout en string pour éviter les erreurs de conversion
            )
        
        if df.empty:
            st.warning("Le fichier est vide.")
            return pd.DataFrame()
        
        # --- DIAGNOSTIC : Afficher les noms de colonnes réels ---
        st.sidebar.write("**Colonnes trouvées :**", list(df.columns))
        
        # --- RENOMMAGE ROBUSTE (insensible à la casse et aux espaces) ---
        # Créer un mapping normalisé
        rename_map = {
            'valeurfonc': 'valeur_fonciere',
            'sbati': 'surface_reelle_bati',
            'datemut': 'date_mutation',
            'libtypbien': 'type_local',
            'l_codinsee': 'code_commune',
            'geompar_x': 'longitude_lambert',
            'geompar_y': 'latitude_lambert',
            'l_codepost': 'code_postal',
            'nbpieceprin': 'nombre_pieces_principales'
        }
        # Nettoyer les noms de colonnes (trim, lower)
        df.columns = df.columns.str.strip()
        # Appliquer le renommage
        for old, new in rename_map.items():
            # Chercher une colonne qui correspond (sensible à la casse)
            matches = [col for col in df.columns if col.lower() == old.lower()]
            if matches:
                df = df.rename(columns={matches[0]: new})
        
        # --- VÉRIFICATION DES COLONNES ESSENTIELLES ---
        required = ['valeur_fonciere', 'surface_reelle_bati']
        missing = [col for col in required if col not in df.columns]
        if missing:
            st.error(f"Colonnes obligatoires manquantes : {missing}. Voici les colonnes existantes : {list(df.columns)}")
            return pd.DataFrame()
        
        # --- CONVERSION NUMÉRIQUE ---
        df['valeur_fonciere'] = pd.to_numeric(df['valeur_fonciere'], errors='coerce')
        df['surface_reelle_bati'] = pd.to_numeric(df['surface_reelle_bati'], errors='coerce')
        
        # --- COORDONNÉES ---
        # Convertir les colonnes Lambert en numérique (si présentes)
        if 'longitude_lambert' in df.columns and 'latitude_lambert' in df.columns:
            df['longitude_lambert'] = pd.to_numeric(df['longitude_lambert'], errors='coerce')
            df['latitude_lambert'] = pd.to_numeric(df['latitude_lambert'], errors='coerce')
            # Appliquer la conversion si pyproj est disponible
            if HAS_PYPROJ:
                try:
                    lambert93 = pyproj.Proj('+proj=lcc +lat_1=49 +lat_2=44 +lat_0=46.5 +lon_0=3 +x_0=700000 +y_0=6600000 +ellps=GRS80 +units=m +no_defs')
                    wgs84 = pyproj.Proj('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
                    lon_vals = df['longitude_lambert'].values
                    lat_vals = df['latitude_lambert'].values
                    # filtrer les valeurs valides
                    mask = ~(pd.isna(lon_vals) | pd.isna(lat_vals))
                    if mask.any():
                        new_lon, new_lat = pyproj.transform(lambert93, wgs84, lon_vals[mask], lat_vals[mask])
                        df.loc[mask, 'longitude'] = new_lon
                        df.loc[mask, 'latitude'] = new_lat
                    # on peut supprimer les colonnes Lambert
                    df = df.drop(columns=['longitude_lambert', 'latitude_lambert'], errors='ignore')
                except Exception as e:
                    st.warning(f"Conversion Lambert échouée : {e}. Affichage approximatif.")
                    # on garde les coordonnées en Lambert (affichage décalé)
                    df['longitude'] = df['longitude_lambert']
                    df['latitude'] = df['latitude_lambert']
            else:
                st.warning("pyproj non installé. Les coordonnées Lambert ne seront pas converties.")
                df['longitude'] = df['longitude_lambert']
                df['latitude'] = df['latitude_lambert']
        
        # --- GARDER UNIQUEMENT LES COLONNES UTILES ---
        keep_cols = ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati',
                     'type_local', 'code_commune', 'code_postal', 'latitude', 'longitude',
                     'nombre_pieces_principales']
        available = [c for c in keep_cols if c in df.columns]
        if available:
            df = df[available]
        
        mem = round(df.memory_usage(deep=True).sum() / 1024**2, 1)
        st.sidebar.success(f"✅ {len(df):,} transactions ({mem} Mo)")
        return df

    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        return pd.DataFrame()

def prepare_data(df):
    if df.empty:
        return df
    df_clean = df.copy()
    
    # Dates
    if 'date_mutation' in df_clean.columns:
        df_clean["date_mutation"] = pd.to_datetime(df_clean["date_mutation"], errors='coerce')
    
    # Numeriques – déjà fait, mais on s'assure
    for col in ['valeur_fonciere', 'surface_reelle_bati']:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    # Type local
    if 'type_local' in df_clean.columns:
        df_clean = df_clean[df_clean["type_local"].isin(['Maison', 'Appartement'])]
    
    # Supprimer les NA sur les colonnes essentielles
    subset_cols = [c for c in ['valeur_fonciere', 'surface_reelle_bati'] if c in df_clean.columns]
    if subset_cols:
        df_clean = df_clean.dropna(subset=subset_cols)
    else:
        st.error("Colonnes essentielles manquantes pour le nettoyage.")
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
    
    return df_clean

# --- Interface ---
st.title("🏘️ Dashboard Immobilier Gironde - 2026 (DVF+ format pipe)")
st.markdown(f"Source : [dvf_plus_d33.csv]({GITHUB_CSV_URL})")

df_brut = load_gironde_2026_data()
if df_brut.empty:
    st.info("Impossible de charger les données. Consultez le diagnostic des colonnes dans la barre latérale.")
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
