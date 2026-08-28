# dashboard.py – avec capture d'erreur
import streamlit as st
import sys
import traceback

try:
    import pandas as pd
    import plotly.express as px
    import requests
    import io
    from datetime import datetime

    # Détection de pyproj
    try:
        import pyproj
        HAS_PYPROJ = True
    except ImportError:
        HAS_PYPROJ = False

    st.set_page_config(page_title="Dashboard Immobilier Gironde 2026", page_icon="🏘️", layout="wide")

    DATA_URL = "https://github.com/gunout/Dashboard-Immobilier-Gironde-2026/releases/download/DVF-33/dvf_plus_d33.csv"

    COMMUNES = {
        "33063": "Bordeaux", "33069": "Bruges", "33075": "Cenon", "33119": "Eysines",
        "33192": "Gradignan", "33200": "Gujan-Mestras", "33249": "Lormont", "33273": "Mérignac",
        "33281": "Pessac", "33312": "Saint-Médard-en-Jalles", "33318": "Talence", "33434": "Le Bouscat",
        "33449": "Villenave-d'Ornon", "33039": "Bègles", "33056": "Blanquefort", "33162": "Floirac",
        "33243": "Libourne", "33522": "Arcachon", "33529": "La Teste-de-Buch", "33550": "Cestas",
    }

    @st.cache_data
    def load_data():
        try:
            response = requests.get(DATA_URL, timeout=60)
            response.raise_for_status()
            if 'text/html' in response.headers.get('content-type', ''):
                st.error("Le lien renvoie une page HTML – vérifiez la release GitHub.")
                return None
            df = pd.read_csv(io.StringIO(response.text), sep='|', dtype=str, engine='python', on_bad_lines='skip')
            if df.empty:
                return None
            st.sidebar.write("**Colonnes trouvées :**", list(df.columns))
            st.sidebar.write(f"**Lignes :** {len(df)}")
            return df
        except Exception as e:
            st.error(f"Erreur de chargement : {e}")
            return None

    def prepare(df):
        if df is None or df.empty:
            return df
        d = df.copy()
        # Conversion numérique
        for col in ['valeurfonc', 'sbati']:
            if col in d.columns:
                d[col] = pd.to_numeric(d[col], errors='coerce')
        # Filtre type
        if 'libtypbien' in d.columns:
            d = d[d['libtypbien'].isin(['Maison', 'Appartement'])]
        # Suppression NA
        if 'valeurfonc' in d.columns and 'sbati' in d.columns:
            d = d.dropna(subset=['valeurfonc', 'sbati'])
        else:
            st.error("Colonnes 'valeurfonc' ou 'sbati' manquantes.")
            return None
        # Filtres
        d = d[(d['valeurfonc'] > 20000) & (d['valeurfonc'] < 3000000)]
        d = d[(d['sbati'] > 9) & (d['sbati'] < 400)]
        d['prix_m2'] = d['valeurfonc'] / d['sbati']
        d = d[(d['prix_m2'] > 500) & (d['prix_m2'] < 12000)]
        # Commune
        if 'l_codinsee' in d.columns:
            d['l_codinsee'] = d['l_codinsee'].astype(str).str.zfill(5)
            d['nom_commune'] = d['l_codinsee'].map(COMMUNES)
            d = d.dropna(subset=['nom_commune'])
        # Coordonnées
        if 'geompar_x' in d.columns and 'geompar_y' in d.columns:
            d['geompar_x'] = pd.to_numeric(d['geompar_x'], errors='coerce')
            d['geompar_y'] = pd.to_numeric(d['geompar_y'], errors='coerce')
            if HAS_PYPROJ:
                try:
                    lambert93 = pyproj.Proj('+proj=lcc +lat_1=49 +lat_2=44 +lat_0=46.5 +lon_0=3 +x_0=700000 +y_0=6600000 +ellps=GRS80 +units=m +no_defs')
                    wgs84 = pyproj.Proj('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
                    lon_vals = d['geompar_x'].values
                    lat_vals = d['geompar_y'].values
                    mask = ~(pd.isna(lon_vals) | pd.isna(lat_vals))
                    if mask.any():
                        new_lon, new_lat = pyproj.transform(lambert93, wgs84, lon_vals[mask], lat_vals[mask])
                        d.loc[mask, 'longitude'] = new_lon
                        d.loc[mask, 'latitude'] = new_lat
                except Exception as e:
                    st.warning(f"Conversion Lambert échouée : {e}")
                    d['longitude'] = d['geompar_x']
                    d['latitude'] = d['geompar_y']
            else:
                d['longitude'] = d['geompar_x']
                d['latitude'] = d['geompar_y']
        # Renommage final
        rename = {
            'valeurfonc': 'valeur_fonciere',
            'sbati': 'surface_reelle_bati',
            'libtypbien': 'type_local',
            'l_codinsee': 'code_commune',
            'l_codepost': 'code_postal',
            'nbpieceprin': 'nombre_pieces_principales'
        }
        for old, new in rename.items():
            if old in d.columns:
                d = d.rename(columns={old: new})
        return d

    # --- Interface principale ---
    st.title("🏘️ Dashboard Immobilier Gironde - 2026")
    st.markdown(f"Source : [dvf_plus_d33.csv]({DATA_URL})")

    df_brut = load_data()
    if df_brut is None or df_brut.empty:
        st.info("Impossible de charger les données. Vérifiez le lien GitHub.")
        if st.button("🔄 Réessayer"):
            st.rerun()
        st.stop()

    df = prepare(df_brut)
    if df is None or df.empty:
        st.warning("Aucune transaction valide après nettoyage.")
        st.stop()

    communes = sorted(df['nom_commune'].unique())
    selected = st.sidebar.selectbox("Commune", communes, index=communes.index("Bordeaux") if "Bordeaux" in communes else 0)
    df_commune = df[df['nom_commune'] == selected].copy()
    if df_commune.empty:
        st.stop()

    # Filtres
    st.sidebar.header("🔧 Filtres")
    cp_options = sorted(df_commune['code_postal'].astype(str).unique()) if 'code_postal' in df_commune.columns else []
    cp_selection = st.sidebar.multiselect("Code postal", cp_options, default=cp_options) if cp_options else []
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
        df_carte['latitude'] = pd.to_numeric(df_carte['latitude'], errors='coerce')
        df_carte['longitude'] = pd.to_numeric(df_carte['longitude'], errors='coerce')
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
                st.error(f"Erreur open-street-map : {e}")
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

    # Évolution
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
    st.caption(f"Mise à jour : {datetime.now().strftime('%d/%m/%Y %H:%M')} – DVF+ 2026 Gironde (33)")

except Exception as e:
    st.error("❌ Une erreur s'est produite dans l'application.")
    st.code(f"{type(e).__name__}: {e}")
    st.code(traceback.format_exc())
    st.stop()
