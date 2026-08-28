# dashboard_gironde_2026.py – version avec diagnostic complet et fallback manuel
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from datetime import datetime

# ------------------------------------------------------------
# 🔗 Lien vers les données – MODIFIEZ‑LE ICI SI NÉCESSAIRE
# ------------------------------------------------------------
DATA_URL = "https://github.com/gunout/Dashboard-Immobilier-Gironde-2026/releases/download/DVF-33/dvf_plus_d33.csv"
# ------------------------------------------------------------

# Détection de pyproj pour la conversion Lambert 93
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

# ------------------------------------------------------------------
# SECTION DIAGNOSTIC - affichage en direct dans l'application
# ------------------------------------------------------------------
st.title("🔧 Diagnostic du chargement des données")

# Tentative de téléchargement
try:
    with st.spinner(f"📥 Téléchargement depuis {DATA_URL}..."):
        response = requests.get(DATA_URL, stream=True, timeout=60)
        status_code = response.status_code
        content_type = response.headers.get('content-type', 'inconnu')
        st.write(f"**Statut HTTP :** {status_code}")
        st.write(f"**Content-Type :** {content_type}")
        
        if status_code != 200:
            st.error(f"❌ Erreur HTTP {status_code}")
            st.stop()
        
        if 'text/html' in content_type:
            st.error("❌ Le serveur renvoie une page HTML (probablement une page d'erreur GitHub). Vérifiez que la release est publique.")
            st.write("**Aperçu du contenu :**")
            st.text(response.text[:500])
            st.stop()
        
        # Lire le contenu
        content = response.text
        st.write(f"**Taille du fichier :** {len(content):,} caractères")
        st.write("**Aperçu des 500 premiers caractères :**")
        st.text(content[:500])
        
        # Lire les premières lignes pour voir le séparateur
        lines = content.split('\n')
        st.write(f"**Nombre de lignes :** {len(lines)}")
        if lines:
            st.write("**Première ligne (en-tête) :**")
            st.text(lines[0])
            st.write("**Deuxième ligne (exemple) :**")
            if len(lines) > 1:
                st.text(lines[1])
        
        # Tenter de parser avec différents séparateurs
        st.subheader("🔬 Tentative de parsing")
        try:
            # Essayer avec séparateur '|'
            df_test = pd.read_csv(io.StringIO(content), sep='|', nrows=5, dtype=str, engine='python', on_bad_lines='skip')
            st.success(f"✅ Parsing avec séparateur '|' réussi. Colonnes : {list(df_test.columns)}")
            sep_ok = '|'
        except Exception as e:
            st.warning(f"Parsing avec '|' échoué : {e}")
            try:
                df_test = pd.read_csv(io.StringIO(content), sep=',', nrows=5, dtype=str, engine='python', on_bad_lines='skip')
                st.success(f"✅ Parsing avec ',' réussi. Colonnes : {list(df_test.columns)}")
                sep_ok = ','
            except Exception as e2:
                st.error(f"Parsing avec ',' échoué : {e2}")
                st.stop()
        
        # Maintenant, charger tout le fichier avec le bon séparateur
        with st.spinner("📊 Chargement complet du fichier..."):
            df = pd.read_csv(io.StringIO(content), sep=sep_ok, dtype=str, engine='python', on_bad_lines='skip')
        
        if df.empty:
            st.error("Le fichier est vide après parsing.")
            st.stop()
        
        st.success(f"✅ Fichier chargé : {len(df):,} lignes, {len(df.columns)} colonnes")
        st.write("**Colonnes :**", list(df.columns))

        # --- Renommage ---
        rename_dict = {
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
        for old, new in rename_dict.items():
            if old in df.columns:
                df = df.rename(columns={old: new})
        
        st.write("**Colonnes après renommage :**", list(df.columns))
        
        # Vérification des colonnes essentielles
        required = ['valeur_fonciere', 'surface_reelle_bati']
        missing = [col for col in required if col not in df.columns]
        if missing:
            st.error(f"❌ Colonnes manquantes : {missing}")
            st.write("**Colonnes disponibles :**", list(df.columns))
            # Fallback : chercher des colonnes similaires
            for req in missing:
                found = [col for col in df.columns if req.lower() in col.lower()]
                if found:
                    st.info(f"Renommage automatique de '{found[0]}' → '{req}'")
                    df = df.rename(columns={found[0]: req})
            missing2 = [col for col in required if col not in df.columns]
            if missing2:
                st.error("Échec du fallback. Arrêt.")
                st.stop()
            else:
                st.success("Fallback réussi.")
        
        # Conversion numérique
        df['valeur_fonciere'] = pd.to_numeric(df['valeur_fonciere'], errors='coerce')
        df['surface_reelle_bati'] = pd.to_numeric(df['surface_reelle_bati'], errors='coerce')
        
        # Conversion Lambert → WGS84
        if 'longitude_lambert' in df.columns and 'latitude_lambert' in df.columns and HAS_PYPROJ:
            try:
                lambert93 = pyproj.Proj('+proj=lcc +lat_1=49 +lat_2=44 +lat_0=46.5 +lon_0=3 +x_0=700000 +y_0=6600000 +ellps=GRS80 +units=m +no_defs')
                wgs84 = pyproj.Proj('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
                lon_vals = pd.to_numeric(df['longitude_lambert'], errors='coerce').values
                lat_vals = pd.to_numeric(df['latitude_lambert'], errors='coerce').values
                mask = ~(pd.isna(lon_vals) | pd.isna(lat_vals))
                if mask.any():
                    new_lon, new_lat = pyproj.transform(lambert93, wgs84, lon_vals[mask], lat_vals[mask])
                    df.loc[mask, 'longitude'] = new_lon
                    df.loc[mask, 'latitude'] = new_lat
                df = df.drop(columns=['longitude_lambert', 'latitude_lambert'], errors='ignore')
                st.success("Conversion Lambert → WGS84 effectuée.")
            except Exception as e:
                st.warning(f"Conversion échouée : {e}")
                df['longitude'] = pd.to_numeric(df['longitude_lambert'], errors='coerce')
                df['latitude'] = pd.to_numeric(df['latitude_lambert'], errors='coerce')
        elif 'longitude_lambert' in df.columns and 'latitude_lambert' in df.columns:
            df['longitude'] = pd.to_numeric(df['longitude_lambert'], errors='coerce')
            df['latitude'] = pd.to_numeric(df['latitude_lambert'], errors='coerce')
        
        # Garder les colonnes utiles
        keep_cols = ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati',
                     'type_local', 'code_commune', 'code_postal', 'latitude', 'longitude',
                     'nombre_pieces_principales']
        available = [c for c in keep_cols if c in df.columns]
        if available:
            df = df[available]
        else:
            st.error("Aucune colonne utile.")
            st.stop()
        
        mem = round(df.memory_usage(deep=True).sum() / 1024**2, 1)
        st.sidebar.success(f"✅ {len(df):,} transactions ({mem} Mo)")
        # On stocke dans session_state pour la suite
        st.session_state['df_brut'] = df
        
    except Exception as e:
        st.error(f"❌ Erreur : {e}")
        import traceback
        st.code(traceback.format_exc())
        st.stop()

# Si tout est ok, on passe au dashboard
if 'df_brut' in st.session_state:
    df_brut = st.session_state['df_brut']
    
    # Fonction de préparation
    def prepare_data(df):
        df_clean = df.copy()
        if 'date_mutation' in df_clean.columns:
            df_clean["date_mutation"] = pd.to_datetime(df_clean["date_mutation"], errors='coerce')
        if 'valeur_fonciere' in df_clean.columns:
            df_clean["valeur_fonciere"] = pd.to_numeric(df_clean["valeur_fonciere"], errors='coerce')
        if 'surface_reelle_bati' in df_clean.columns:
            df_clean["surface_reelle_bati"] = pd.to_numeric(df_clean["surface_reelle_bati"], errors='coerce')
        if 'type_local' in df_clean.columns:
            df_clean = df_clean[df_clean["type_local"].isin(['Maison', 'Appartement'])]
        df_clean = df_clean.dropna(subset=['valeur_fonciere', 'surface_reelle_bati'])
        df_clean = df_clean[(df_clean['valeur_fonciere'] > 20000) & (df_clean['valeur_fonciere'] < 3000000)]
        df_clean = df_clean[(df_clean['surface_reelle_bati'] > 9) & (df_clean['surface_reelle_bati'] < 400)]
        df_clean['prix_m2'] = df_clean['valeur_fonciere'] / df_clean['surface_reelle_bati']
        df_clean = df_clean[(df_clean['prix_m2'] > 500) & (df_clean['prix_m2'] < 12000)]
        if 'code_commune' in df_clean.columns:
            df_clean['code_commune'] = df_clean['code_commune'].astype(str).str.zfill(5)
            df_clean['nom_commune'] = df_clean['code_commune'].map(COMMUNES_GIRONDE)
            df_clean = df_clean.dropna(subset=['nom_commune'])
        return df_clean
    
    df = prepare_data(df_brut)
    if df.empty:
        st.warning("Aucune transaction valide après nettoyage.")
        st.stop()
    
    # --- Interface utilisateur (dashboard) ---
    st.title("🏘️ Dashboard Immobilier Gironde - 2026")
    st.markdown(f"Source : [{DATA_URL}]({DATA_URL})")
    
    communes = sorted(df['nom_commune'].unique())
    selected = st.sidebar.selectbox("Commune", communes, index=communes.index("Bordeaux") if "Bordeaux" in communes else 0)
    df_commune = df[df['nom_commune'] == selected].copy()
    if df_commune.empty:
        st.stop()
    
    # Filtres
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
    
    # KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Prix moyen / m²", f"{df_filtre['prix_m2'].mean():,.0f} €")
    c2.metric("Prix médian", f"{df_filtre['valeur_fonciere'].median():,.0f} €")
    c3.metric("Transactions", f"{len(df_filtre):,}")
    c4.metric("Surface moyenne", f"{df_filtre['surface_reelle_bati'].mean():.0f} m²")
    if 'nombre_pieces_principales' in df_filtre.columns:
        c5.metric("Pièces", f"{df_filtre['nombre_pieces_principales'].mean():.1f}")
    
    # Graphiques
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
    
    # Carte
    st.subheader(f"🗺️ Carte des transactions - {selected}")
    if 'latitude' in df_filtre.columns and 'longitude' in df_filtre.columns:
        df_carte = df_filtre.copy()
        df_carte['latitude'] = pd.to_numeric(df_carte['latitude'].astype(str).str.replace(',', '.'), errors='coerce')
        df_carte['longitude'] = pd.to_numeric(df_carte['longitude'].astype(str).str.replace(',', '.'), errors='coerce')
        df_carte = df_carte.dropna(subset=['latitude', 'longitude'])
        if not df_carte.empty:
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
    
    # Évolution temporelle
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
    
    # Top ventes
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

else:
    # Si le chargement a échoué, proposer un upload manuel
    st.subheader("📂 Téléchargement manuel")
    st.info("Si le téléchargement automatique échoue, vous pouvez uploader le fichier CSV localement.")
    uploaded_file = st.file_uploader("Choisissez le fichier dvf_plus_d33.csv", type=["csv"])
    if uploaded_file is not None:
        try:
            content = uploaded_file.read().decode('utf-8')
            # Tenter de parser
            df = pd.read_csv(io.StringIO(content), sep='|', dtype=str, engine='python', on_bad_lines='skip')
            st.success(f"Fichier uploadé : {len(df)} lignes")
            # On pourrait le traiter ici, mais pour simplifier on stocke dans session_state et on rerun
            st.session_state['df_brut'] = df
            st.rerun()
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier uploadé : {e}")
