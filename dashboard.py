# dashboard.py – Version debug pour DVF+ 2026
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
import traceback
from datetime import datetime

# Détection de pyproj
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

DATA_URL = "https://github.com/gunout/Dashboard-Immobilier-Gironde-2026/releases/download/DVF-33/dvf_plus_d33.csv"

# ✅ Fonction de debug globale
def show_error(e, context=""):
    """Affiche l'erreur complète dans l'UI"""
    st.error(f"❌ Erreur {context}: {type(e).__name__}: {e}")
    with st.expander("📋 Détails techniques"):
        st.code(traceback.format_exc())

@st.cache_data(ttl=3600)
def load_data():
    try:
        with st.spinner("📥 Téléchargement des données 2026..."):
            response = requests.get(DATA_URL, timeout=60)
            response.raise_for_status()

        content_type = response.headers.get('content-type', '')
        if 'text/html' in content_type:
            st.error("❌ Le lien renvoie une page HTML.")
            return None

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

        with st.sidebar:
            st.write("**Colonnes :**", list(df.columns))
            st.write(f"**Lignes :** {len(df):,}")

        return df

    except Exception as e:
        show_error(e, "de chargement")
        return None

def prepare_data(df):
    try:
        if df is None or df.empty:
            return None

        d = df.copy()

        # Renommage
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

        # Vérification colonnes
        if 'valeur_fonciere' not in d.columns or 'surface_reelle_bati' not in d.columns:
            st.error(f"❌ Colonnes manquantes. Disponibles: {list(d.columns)}")
            return None

        # Conversion date
        if 'date_mutation' in d.columns:
            d['date_mutation'] = pd.to_datetime(d['date_mutation'], errors='coerce')

        # Conversion numérique
        d['valeur_fonciere'] = pd.to_numeric(d['valeur_fonciere'], errors='coerce')
        d['surface_reelle_bati'] = pd.to_numeric(d['surface_reelle_bati'], errors='coerce')

        # Filtre type
        if 'type_local' in d.columns:
            d = d[d['type_local'].isin(['Maison', 'Appartement'])]

        d = d.dropna(subset=['valeur_fonciere', 'surface_reelle_bati'])

        # Filtres cohérence
        d = d[(d['valeur_fonciere'] > 20000) & (d['valeur_fonciere'] < 3000000)]
        d = d[(d['surface_reelle_bati'] > 9) & (d['surface_reelle_bati'] < 400)]

        # Prix m²
        d['prix_m2'] = d['valeur_fonciere'] / d['surface_reelle_bati']
        d = d[(d['prix_m2'] > 500) & (d['prix_m2'] < 12000)]

        # Commune
        if 'code_commune' in d.columns:
            d['code_commune'] = d['code_commune'].astype(str).str.zfill(5)
            d['nom_commune'] = d['code_commune'].map(COMMUNES_GIRONDE)
            d = d.dropna(subset=['nom_commune'])

        # Conversion Lambert → WGS84
        if 'longitude_lambert' in d.columns and 'latitude_lambert' in d.columns:
            d['longitude_lambert'] = pd.to_numeric(d['longitude_lambert'], errors='coerce')
            d['latitude_lambert'] = pd.to_numeric(d['latitude_lambert'], errors='coerce')

            if HAS_PYPROJ:
                try:
                    transformer = pyproj.Transformer.from_crs(
                        "EPSG:2154",  # Lambert 93
                        "EPSG:4326",  # WGS84
                        always_xy=True
                    )
                    mask = d['longitude_lambert'].notna() & d['latitude_lambert'].notna()
                    if mask.any():
                        lon_wgs, lat_wgs = transformer.transform(
                            d.loc[mask, 'longitude_lambert'].values,
                            d.loc[mask, 'latitude_lambert'].values
                        )
                        d.loc[mask, 'longitude'] = lon_wgs
                        d.loc[mask, 'latitude'] = lat_wgs
                    d = d.drop(columns=['longitude_lambert', 'latitude_lambert'], errors='ignore')
                    st.sidebar.success("✅ Conversion Lambert → WGS84")
                except Exception as e:
                    st.sidebar.warning(f"⚠️ Conversion: {e}")
                    d['longitude'] = d['longitude_lambert']
                    d['latitude'] = d['latitude_lambert']
            else:
                d['longitude'] = d['longitude_lambert']
                d['latitude'] = d['latitude_lambert']

        # Colonnes finales
        keep_cols = ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati',
                     'type_local', 'code_commune', 'code_postal',
                     'latitude', 'longitude', 'nombre_pieces_principales',
                     'prix_m2', 'nom_commune']
        keep_cols = [c for c in keep_cols if c in d.columns]
        d = d[keep_cols].copy()

        st.sidebar.success(f"✅ {len(d):,} transactions nettoyées")
        return d

    except Exception as e:
        show_error(e, "de préparation")
        return None

# ═══════════════════════════════════════════════════════════
# PROGRAMME PRINCIPAL
# ═══════════════════════════════════════════════════════════

try:
    st.title("🏘️ Dashboard Immobilier Gironde - 2026")
    st.markdown(f"Source : [dvf_plus_d33.csv]({DATA_URL})")

    df = load_data()
    if df is None:
        st.error("❌ Données indisponibles.")
        if st.button("🔄 Réessayer"):
            st.cache_data.clear()
            st.rerun()
        st.stop()

    df = prepare_data(df)
    if df is None or df.empty:
        st.warning("Aucune transaction valide.")
        st.stop()

    # Sélection commune
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

    # Filtres
    st.sidebar.header("🔧 Filtres")
    
    cp_selection = []
    if 'code_postal' in df_commune.columns and not df_commune['code_postal'].isna().all():
        cp_options = sorted(df_commune['code_postal'].astype(str).unique())
        cp_selection = st.sidebar.multiselect("Code postal", cp_options, default=cp_options)

    type_local = st.sidebar.selectbox("Type de bien", ['Tous', 'Maison', 'Appartement'])
    prix_min = st.sidebar.number_input("Prix minimum (€)", 0, step=20000)
    prix_max = st.sidebar.number_input("Prix maximum (€)", int(df_commune['valeur_fonciere'].max()), step=50000, min_value=0)
    surface_min = st.sidebar.slider("Surface minimum (m²)", 0, int(df_commune['surface_reelle_bati'].max()), value=0)

    df_filtre = df_commune.copy()
    if cp_selection and 'code_postal' in df_filtre.columns:
        df_filtre = df_filtre[df_filtre['code_postal'].astype(str).isin(cp_selection)].copy()
    df_filtre = df_filtre[
        (df_filtre['valeur_fonciere'] >= prix_min) &
        (df_filtre['valeur_fonciere'] <= prix_max) &
        (df_filtre['surface_reelle_bati'] >= surface_min)
    ].copy()
    if type_local != 'Tous' and 'type_local' in df_filtre.columns:
        df_filtre = df_filtre[df_filtre['type_local'] == type_local].copy()

    if df_filtre.empty:
        st.warning("Aucune transaction ne correspond aux filtres.")
        st.stop()

    # KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Prix moyen / m²", f"{df_filtre['prix_m2'].mean():,.0f} €")
    c2.metric("Prix médian", f"{df_filtre['valeur_fonciere'].median():,.0f} €")
    c3.metric("Transactions", f"{len(df_filtre):,}")
    c4.metric("Surface moyenne", f"{df_filtre['surface_reelle_bati'].mean():.0f} m²")
    if 'nombre_pieces_principales' in df_filtre.columns:
        nb_pieces = df_filtre['nombre_pieces_principales']
        if pd.api.types.is_numeric_dtype(nb_pieces):
            c5.metric("Pièces moyennes", f"{nb_pieces.mean():.1f}")

    # Graphiques
    col1, col2 = st.columns(2)
    with col1:
        color_col = 'type_local' if 'type_local' in df_filtre.columns else None
        fig = px.histogram(df_filtre, x='prix_m2', nbins=40, color=color_col, marginal="box",
                          title=f"Distribution prix/m² – {selected}")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.scatter(df_filtre, x='surface_reelle_bati', y='valeur_fonciere',
                        color=color_col, hover_data=['code_postal'],
                        title="Surface / Prix")
        st.plotly_chart(fig, use_container_width=True)

    # Carte
    st.subheader(f"🗺️ Carte – {selected}")

    if 'latitude' in df_filtre.columns and 'longitude' in df_filtre.columns:
        df_carte = df_filtre[['latitude', 'longitude', 'prix_m2', 'surface_reelle_bati', 'valeur_fonciere', 'type_local']].copy()
        df_carte['latitude'] = pd.to_numeric(df_carte['latitude'], errors='coerce')
        df_carte['longitude'] = pd.to_numeric(df_carte['longitude'], errors='coerce')
        df_carte = df_carte.dropna(subset=['latitude', 'longitude'])

        if not df_carte.empty:
            # Vérification coordonnées valides
            valid_coords = (
                (df_carte['latitude'].between(-90, 90)) & 
                (df_carte['longitude'].between(-180, 180))
            )
            
            if valid_coords.any():
                df_map = df_carte[valid_coords].copy()
                if len(df_map) > 500:
                    df_map = df_map.sample(500, random_state=42)
                    st.caption(f"500 transactions affichées sur {len(df_carte)}")
                
                # ✅ st.map() sans paramètres problématiques
                st.map(df_map, latitude='latitude', longitude='longitude', 
                       size='surface_reelle_bati', color='prix_m2')
            else:
                st.warning("⚠️ Coordonnées hors limites (-90/90, -180/180). Vérifiez la conversion Lambert.")
                with st.expander("Diagnostic coordonnées"):
                    st.write(df_carte[['latitude', 'longitude']].describe())
        else:
            st.info("📍 Aucune coordonnée valide.")
    else:
        st.info("📍 Pas de coordonnées disponibles.")

    # Évolution temporelle
    st.subheader("📊 Évolution temporelle")
    
    if 'date_mutation' in df_filtre.columns:
        # ✅ Vérification robuste du type datetime
        try:
            df_temp = df_filtre.dropna(subset=['date_mutation']).copy()
            # Forcer la conversion si nécessaire
            if not pd.api.types.is_datetime64_any_dtype(df_temp['date_mutation']):
                df_temp['date_mutation'] = pd.to_datetime(df_temp['date_mutation'], errors='coerce')
                df_temp = df_temp.dropna(subset=['date_mutation'])
            
            if not df_temp.empty:
                # ✅ Utiliser dt.strftime au lieu de to_period pour éviter les problèmes
                df_temp['mois_str'] = df_temp['date_mutation'].dt.strftime('%Y-%m')
                df_mensuel = df_temp.groupby('mois_str').agg(
                    prix_m2_moyen=('prix_m2', 'mean'),
                    nb_transactions=('valeur_fonciere', 'count'),
                    prix_moyen=('valeur_fonciere', 'mean')
                ).round(0).reset_index()

                col1, col2 = st.columns(2)
                with col1:
                    fig = px.line(df_mensuel, x='mois_str', y='prix_m2_moyen',
                                 markers=True, title="Évolution prix/m²")
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    fig = px.bar(df_mensuel, x='mois_str', y='nb_transactions',
                                title="Transactions par mois")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📅 Aucune date valide.")
        except Exception as e:
            show_error(e, "graphique temporel")
    else:
        st.info("📅 Pas de colonne date.")

    # Top 5
    st.subheader("💰 Top 5 ventes")
    top_cols = ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'prix_m2', 'type_local']
    available_top = [c for c in top_cols if c in df_filtre.columns]
    if available_top:
        top = df_filtre.nlargest(5, 'valeur_fonciere')[available_top].copy()
        top['valeur_fonciere'] = top['valeur_fonciere'].apply(lambda x: f"{x:,.0f} €")
        if 'prix_m2' in top.columns:
            top['prix_m2'] = top['prix_m2'].apply(lambda x: f"{x:,.0f} €/m²")
        st.dataframe(top, hide_index=True, use_container_width=True)

    # Dernières transactions
    st.subheader("📋 Dernières transactions")
    display_cols = ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'prix_m2', 'type_local']
    available_disp = [c for c in display_cols if c in df_filtre.columns]
    if available_disp:
        disp = df_filtre.sort_values('date_mutation', ascending=False).head(50).copy()
        if 'valeur_fonciere' in disp.columns:
            disp['valeur_fonciere'] = disp['valeur_fonciere'].apply(lambda x: f"{x:,.0f} €")
        if 'prix_m2' in disp.columns:
            disp['prix_m2'] = disp['prix_m2'].apply(lambda x: f"{x:,.0f} €/m²")
        st.dataframe(disp[available_disp], hide_index=True, use_container_width=True)

    st.markdown("---")
    st.caption(f"Mise à jour : {datetime.now().strftime('%d/%m/%Y %H:%M')} – DVF+ 2026 Gironde")

except Exception as e:
    # ✅ CATCH-ALL : Affiche l'erreur dans l'UI
    st.error("# ❌ Erreur critique de l'application")
    show_error(e, "critique")
    st.info("💡 Copiez cette erreur pour le débogage.")
