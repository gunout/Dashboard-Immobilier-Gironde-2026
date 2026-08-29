import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
from datetime import datetime

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Dashboard Immobilier Gironde 2026",
    page_icon="🏘️",
    layout="wide"
)

# ---------- DATA DOWNLOAD ----------
DATA_URL = "https://github.com/gunout/Dashboard-Immobilier-Gironde-2026/releases/download/DVF-33/dvf_plus_d33.csv"
DATA_FILE = "dvf_plus_d33.csv"

if not os.path.exists(DATA_FILE):
    with st.spinner(f"Téléchargement de {DATA_FILE}..."):
        try:
            r = requests.get(DATA_URL, stream=True)
            with open(DATA_FILE, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            st.success("Fichier téléchargé avec succès.")
        except Exception as e:
            st.error(f"Impossible de télécharger le fichier : {e}")
            st.stop()

# ---------- COMMUNES DICTIONARY ----------
COMMUNES_GIRONDE = {
    "33063": "Bordeaux",
    "33039": "Bègles",
    "33064": "Le Bouscat",
    "33075": "Cenon",
    "33069": "Bruges",
    "33119": "Eysines",
    "33192": "Gradignan",
    "33200": "Gujan-Mestras",
    "33249": "Lormont",
    "33273": "Mérignac",
    "33281": "Pessac",
    "33312": "Saint-Médard-en-Jalles",
    "33318": "Talence",
    "33449": "Villenave-d'Ornon",
    "33056": "Blanquefort",
    "33162": "Floirac",
    "33243": "Libourne",
    "33522": "Arcachon",
    "33529": "La Teste-de-Buch",
    "33550": "Cestas",
    "33001": "Aiguillon",
    "33002": "Ambès",
    "33009": "Arès",
    "33016": "Audenge",
    "33023": "Barsac",
    "33028": "Bégadan",
    "33034": "Biganos",
    "33040": "Bouliac",
    "33059": "Carbon-Blanc",
    "33091": "Martillac",
    "33097": "Pauillac",
    "33103": "Saint-Émilion",
    "33106": "Saint-Loubès",
    "33128": "Yvrac",
    "33003": "Arbanats",
    "33004": "Arcins",
    "33007": "Bassanne",
    "33011": "Artigues-près-Bordeaux",
    "33013": "Asques",
    "33018": "Auros",
    "33022": "Barie",
    "33031": "Béguey",
    "33032": "Beychac-et-Caillau",
    "33033": "Bieujac",
    "33036": "Blésignac",
    "33037": "Bommes",
    "33042": "Bourdelles",
    "33043": "Branne",
    "33044": "Brannens",
    "33045": "Braud-et-Saint-Louis",
    "33048": "Budos",
    "33052": "Cadarsac",
    "33053": "Cadillac",
    "33054": "Cadaujac",
    "33057": "Canéjan",
    "33058": "Capian",
    "33060": "Cardan",
    "33061": "Carignan-de-Bordeaux",
    "33065": "Castelnau-de-Médoc",
    "33066": "Castelviel",
    "33068": "Caudrot",
    "33070": "Cazats",
    "33071": "Cazaugitat",
    "33072": "Cérons",
    "33073": "Cestas",
    "33074": "Chadenac",
    "33076": "Chamadelle",
    "33081": "Les Billaux",
    "33083": "Lignan-de-Bordeaux",
    "33084": "Loupes",
    "33085": "Ludon-Médoc",
    "33086": "Lussac",
    "33087": "Macau",
    "33088": "Madirac",
    "33090": "Marmande",
    "33094": "Naujac-sur-Mer",
    "33095": "Neuillac",
    "33096": "Noaillac",
    "33099": "Peyrat-de-Bellegarde",
    "33100": "Pujols-sur-Ciron",
    "33101": "Queyrac",
    "33102": "Rions",
    "33104": "Saint-Genès-de-Lombaud",
    "33105": "Saint-Laurent-Médoc",
    "33108": "Saint-Pierre-de-Mons",
    "33109": "Saint-Quentin-de-Baron",
    "33110": "Saint-Selve",
    "33111": "Saint-Vincent-de-Paul",
    "33112": "Sallebœuf",
    "33113": "Saumos",
    "33114": "Savignac-de-l'Isle",
    "33115": "Tabanac",
    "33117": "Targon",
    "33120": "Teuillac",
    "33121": "Tizac-de-Lapouyade",
    "33122": "Torcy",
    "33123": "Le Tourne",
    "33124": "Le Tuzan",
    "33127": "Villeneuve-lès-Bordeaux",
}
NOMS_COMMUNES = {v: k for k, v in COMMUNES_GIRONDE.items()}

# ---------- DATA LOADING (cached) ----------
@st.cache_data
def load_all_data():
    if not os.path.exists(DATA_FILE):
        st.error(f"Fichier {DATA_FILE} introuvable.")
        return pd.DataFrame()
    
    try:
        # Lecture robuste du CSV
        try:
            df = pd.read_csv(
                DATA_FILE,
                sep=',',
                low_memory=False,
                on_bad_lines='skip',
                encoding='utf-8',
                quotechar='"'
            )
        except TypeError:
            df = pd.read_csv(
                DATA_FILE,
                sep=',',
                low_memory=False,
                error_bad_lines=False,
                warn_bad_lines=True,
                encoding='utf-8',
                quotechar='"'
            )
        except Exception:
            df = pd.read_csv(
                DATA_FILE,
                sep=',',
                low_memory=False,
                on_bad_lines='skip',
                encoding='latin1',
                quotechar='"'
            )
        
        if df.empty:
            st.warning("Le fichier est vide ou n'a pas pu être lu.")
            return pd.DataFrame()
        
        # --- MAPPING DES COLONNES (correspondance avec les noms réels) ---
        mapping = {
            'valeur_fonciere': ['valeur_fonciere', 'valeur_foncier', 'valeur', 'prix', 'montant', 'valeurfonc'],
            'surface_reelle_bati': ['surface_reelle_bati', 'surface', 'surface_bati', 'surface_habitable', 'sbati', 'sbatmai', 'sbatapt'],
            'date_mutation': ['date_mutation', 'date', 'date_acte', 'date_mut', 'datemut'],
            'code_commune': ['code_commune', 'l_codinsee', 'codgeo', 'commune_code'],
            'type_local': ['type_local', 'libtypbien', 'type', 'nature', 'codtypbien'],
            'code_postal': ['code_postal', 'cp', 'codepostal', 'l_dcnt'],
            'latitude': ['latitude', 'lat', 'y', 'geompar_y'],
            'longitude': ['longitude', 'long', 'x', 'geompar_x']
        }
        
        rename_dict = {}
        for standard, variants in mapping.items():
            for var in variants:
                if var in df.columns:
                    rename_dict[var] = standard
                    break
        
        if rename_dict:
            df.rename(columns=rename_dict, inplace=True)
        
        # Vérification des colonnes obligatoires après renommage
        required = ['valeur_fonciere', 'surface_reelle_bati', 'date_mutation', 'code_commune']
        missing = [col for col in required if col not in df.columns]
        if missing:
            # Affichage des colonnes disponibles pour diagnostic
            cols_dispo = list(df.columns)
            st.error(f"Colonnes manquantes : {missing}. Colonnes disponibles : {cols_dispo}")
            return pd.DataFrame()
        
        # --- NETTOYAGE ---
        # Dates
        df["date_mutation"] = pd.to_datetime(df["date_mutation"], errors='coerce')
        
        # Numériques
        df["valeur_fonciere"] = pd.to_numeric(df["valeur_fonciere"], errors='coerce')
        df["surface_reelle_bati"] = pd.to_numeric(df["surface_reelle_bati"], errors='coerce')
        
        # Suppression des lignes avec valeurs manquantes critiques
        df = df.dropna(subset=["valeur_fonciere", "surface_reelle_bati", "date_mutation"])
        if df.empty:
            st.warning("Aucune transaction valide après nettoyage (valeurs manquantes).")
            return pd.DataFrame()
        
        # Filtrage des types de biens (Maison / Appartement)
        if "type_local" in df.columns:
            # On garde seulement Maison et Appartement
            df = df[df["type_local"].isin(['Maison', 'Appartement'])]
        # Si la colonne n'existe pas, on ignore le filtrage (mais elle devrait exister via libtypbien)
        
        # Prix au m²
        df['prix_m2'] = df['valeur_fonciere'] / df['surface_reelle_bati']
        df = df[(df['prix_m2'] > 200) & (df['prix_m2'] < 15000)]
        if df.empty:
            st.warning("Aucune donnée dans les plages de prix au m² (200-15000).")
            return pd.DataFrame()
        
        # Code commune : s'assurer qu'il est en string et format 5 chiffres
        df["code_commune"] = df["code_commune"].astype(str).str.zfill(5)
        
        # Coordonnées
        for col in ["latitude", "longitude"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            else:
                df[col] = None  # colonne vide pour éviter les erreurs
        
        st.success(f"Données chargées : {len(df):,} transactions.")
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement : {e}")
        return pd.DataFrame()

# ---------- UI ----------
st.title("Dashboard Immobilier Gironde 2026")

st.sidebar.header("Commune")
selected_commune_name = st.sidebar.selectbox("Choisissez :", sorted(NOMS_COMMUNES.keys()))
selected_insee_code = NOMS_COMMUNES[selected_commune_name]
st.info(f"Données pour **{selected_commune_name}** (INSEE {selected_insee_code})")

# Chargement des données
with st.spinner("Chargement des données..."):
    all_data = load_all_data()

if all_data.empty:
    st.stop()

# Diagnostic : afficher les colonnes disponibles dans l'expander
with st.sidebar.expander("Diagnostic"):
    st.write(f"Code recherché : {selected_insee_code}")
    st.write(f"Trouvé : {'OUI' if selected_insee_code in all_data['code_commune'].values else 'NON'}")
    st.write("Colonnes disponibles :", list(all_data.columns))
    # Aperçu des 5 premières lignes
    st.dataframe(all_data.head(5))

# Filtrer par commune
df = all_data[all_data['code_commune'] == selected_insee_code].copy()
if df.empty:
    st.warning(f"Aucune transaction pour {selected_commune_name}.")
    st.stop()

# Sidebar : filtres supplémentaires
st.sidebar.header("Filtres")

# Code postal
if "code_postal" in df.columns and not df["code_postal"].isna().all():
    cp_disp = sorted(df['code_postal'].astype(str).unique())
    cp_sel = st.sidebar.multiselect("Code postal", cp_disp, default=cp_disp)
    df_filtre = df[df['code_postal'].astype(str).isin(cp_sel)].copy()
else:
    df_filtre = df.copy()

# Type de local
types_dispo = ["Tous"]
if "type_local" in df_filtre.columns:
    types_dispo.extend(sorted(df_filtre["type_local"].dropna().unique()))
type_local = st.sidebar.selectbox("Type", types_dispo)

# Prix min/max
prix_min = st.sidebar.number_input("Prix min (€)", 0, step=10000, value=0)
prix_max = st.sidebar.number_input("Prix max (€)", 
                                   int(df['valeur_fonciere'].max()) if not df.empty else 1000000, 
                                   step=10000)

# Période
if "date_mutation" in df_filtre.columns:
    min_date = df_filtre["date_mutation"].min().date()
    max_date = df_filtre["date_mutation"].max().date()
    date_range = st.sidebar.date_input("Période", [min_date, max_date], min_value=min_date, max_value=max_date)
    if len(date_range) == 2:
        start_date, end_date = date_range
        df_filtre = df_filtre[(df_filtre["date_mutation"].dt.date >= start_date) & 
                              (df_filtre["date_mutation"].dt.date <= end_date)]

# Application des filtres
df_filtre = df_filtre[(df_filtre['valeur_fonciere'] >= prix_min) & 
                       (df_filtre['valeur_fonciere'] <= prix_max)].copy()
if type_local != 'Tous' and "type_local" in df_filtre.columns:
    df_filtre = df_filtre[df_filtre['type_local'] == type_local]

if df_filtre.empty:
    st.warning("Aucun résultat avec ces filtres.")
    st.stop()

# ---------- INDICATEURS ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Prix/m² moyen", f"{df_filtre['prix_m2'].mean():.0f} €")
c2.metric("Prix médian", f"{df_filtre['valeur_fonciere'].median():.0f} €")
c3.metric("Nombre de transactions", f"{len(df_filtre):,}")
c4.metric("Surface moyenne", f"{df_filtre['surface_reelle_bati'].mean():.0f} m²")

# ---------- GRAPHIQUES ----------
col1, col2 = st.columns(2)

with col1:
    fig_hist = px.histogram(
        df_filtre, 
        x='prix_m2', 
        nbins=40,
        color="type_local" if "type_local" in df_filtre.columns else None,
        marginal="box",
        title="Distribution des prix au m²"
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with col2:
    if "type_local" in df_filtre.columns:
        fig_pie = px.pie(df_filtre, names='type_local', title="Répartition par type")
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Pas de données de type pour le graphique circulaire.")

# ---------- CARTE (scatter_mapbox) ----------
st.subheader(f"Carte des transactions - {selected_commune_name}")

if 'latitude' in df_filtre.columns and 'longitude' in df_filtre.columns:
    map_data = df_filtre[['latitude', 'longitude', 'prix_m2', 'surface_reelle_bati', 'valeur_fonciere', 'date_mutation']].copy()
    map_data['latitude'] = pd.to_numeric(map_data['latitude'], errors='coerce')
    map_data['longitude'] = pd.to_numeric(map_data['longitude'], errors='coerce')
    map_data = map_data.dropna(subset=['latitude', 'longitude'])
    map_data = map_data[
        (map_data['latitude'].between(-90, 90)) &
        (map_data['longitude'].between(-180, 180))
    ]
    
    if not map_data.empty:
        sample_size = min(2000, len(map_data))
        if sample_size > 0:
            map_sample = map_data.sample(n=sample_size, random_state=42)
            
            fig_map = px.scatter_mapbox(
                map_sample,
                lat="latitude",
                lon="longitude",
                color="prix_m2",
                size="surface_reelle_bati",
                hover_name=map_sample.index,
                hover_data={"prix_m2": ":.0f", "valeur_fonciere": ":.0f", "surface_reelle_bati": ":.0f", "date_mutation": True},
                color_continuous_scale="Viridis",
                size_max=15,
                zoom=12,
                title="Carte des transactions (prix/m² en couleur, taille = surface)"
            )
            fig_map.update_layout(mapbox_style="open-street-map")
            fig_map.update_layout(margin={"r":0,"t":30,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.warning("Aucune donnée à afficher sur la carte.")
    else:
        st.warning("Coordonnées hors limites ou absentes.")
else:
    st.info("Les colonnes latitude/longitude ne sont pas disponibles dans les données.")

# ---------- DERNIÈRES TRANSACTIONS ----------
st.subheader("Dernières transactions")

cols_to_show = [c for c in ["date_mutation", "valeur_fonciere", "surface_reelle_bati", "prix_m2", "type_local", "code_postal"] 
                if c in df_filtre.columns]

if cols_to_show:
    aff = df_filtre.sort_values('date_mutation', ascending=False).head(100).copy()
    
    # Formatage
    if "valeur_fonciere" in aff.columns:
        aff["valeur_fonciere"] = aff["valeur_fonciere"].apply(lambda x: f"{x:,.0f} €")
    if "prix_m2" in aff.columns:
        aff["prix_m2"] = aff["prix_m2"].apply(lambda x: f"{x:,.0f} €/m²")
    if "date_mutation" in aff.columns:
        aff["date_mutation"] = aff["date_mutation"].dt.strftime("%d/%m/%Y")
    
    st.dataframe(aff[cols_to_show], hide_index=True, use_container_width=True)
else:
    st.info("Aucune colonne à afficher.")

# ---------- FOOTER ----------
st.caption(f"Dashboard Gironde 2026 - Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
