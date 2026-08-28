import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

st.set_page_config(
    page_title="Dashboard Immobilier Gironde 2026",
    page_icon="🏘️",
    layout="wide"
)

# Dictionnaire des communes (INSEE -> nom)
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

@st.cache_data
def load_all_data():
    file_path = "dvf_plus_d33.csv"  # Utilisation du fichier DVF 2026 pour la Gironde
    if not os.path.exists(file_path):
        st.error(f"Fichier {file_path} introuvable.")
        return pd.DataFrame()
    try:
        df = pd.read_csv(file_path, sep=',', low_memory=False)
        if df.empty:
            return pd.DataFrame()
        if "date_mutation" in df.columns:
            df["date_mutation"] = pd.to_datetime(df["date_mutation"], errors='coerce')
        if "valeur_fonciere" in df.columns:
            df["valeur_fonciere"] = pd.to_numeric(df["valeur_fonciere"], errors='coerce')
        if "surface_reelle_bati" in df.columns:
            df["surface_reelle_bati"] = pd.to_numeric(df["surface_reelle_bati"], errors='coerce')
        if "type_local" in df.columns:
            df = df[df["type_local"].isin(['Maison', 'Appartement'])]
        elif "libtypbien" in df.columns:
            df = df[df["libtypbien"].str.contains("MAISON|APPARTEMENT", case=False, na=False)]
        df = df.dropna(subset=["valeur_fonciere", "surface_reelle_bati", "date_mutation"])
        if df.empty:
            return pd.DataFrame()
        df['prix_m2'] = df['valeur_fonciere'] / df['surface_reelle_bati']
        df = df[(df['prix_m2'] > 200) & (df['prix_m2'] < 15000)]
        if df.empty:
            return pd.DataFrame()
        if "code_commune" in df.columns:
            df["code_commune"] = df["code_commune"].astype(str).str.zfill(5)
        elif "l_codinsee" in df.columns:
            df["code_commune"] = df["l_codinsee"].astype(str).str.zfill(5)
        else:
            st.error("Colonne code_commune manquante.")
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"Erreur : {e}")
        return pd.DataFrame()

st.title("Dashboard Immobilier Gironde 2026")

st.sidebar.header("Commune")
selected_commune_name = st.sidebar.selectbox("Choisissez :", sorted(NOMS_COMMUNES.keys()))
selected_insee_code = NOMS_COMMUNES[selected_commune_name]
st.info(f"Données pour **{selected_commune_name}** (INSEE {selected_insee_code})")

with st.spinner("Chargement..."):
    all_data = load_all_data()
if all_data.empty:
    st.warning("Aucune donnée disponible.")
    st.stop()

with st.sidebar.expander("Diagnostic"):
    st.write(f"Code recherché : {selected_insee_code}")
    st.write(f"Trouvé : {'OUI' if selected_insee_code in all_data['code_commune'].values else 'NON'}")

df = all_data[all_data['code_commune'] == selected_insee_code].copy()
if df.empty:
    st.warning(f"Aucune transaction pour {selected_commune_name}.")
    st.stop()

st.sidebar.header("Filtres")
if "code_postal" in df.columns and not df["code_postal"].isna().all():
    cp_disp = sorted(df['code_postal'].astype(str).unique())
    cp_sel = st.sidebar.multiselect("Code postal", cp_disp, default=cp_disp)
    df_filtre = df[df['code_postal'].astype(str).isin(cp_sel)].copy()
else:
    df_filtre = df.copy()

types_dispo = ["Tous"]
if "type_local" in df_filtre.columns:
    types_dispo.extend(sorted(df_filtre["type_local"].dropna().unique()))
type_local = st.sidebar.selectbox("Type", types_dispo)
prix_min = st.sidebar.number_input("Prix min", 0, step=10000, value=0)
prix_max = st.sidebar.number_input("Prix max", int(df['valeur_fonciere'].max()) if not df.empty else 1000000, step=10000)

df_filtre = df_filtre[(df_filtre['valeur_fonciere'] >= prix_min) & (df_filtre['valeur_fonciere'] <= prix_max)].copy()
if type_local != 'Tous' and "type_local" in df_filtre.columns:
    df_filtre = df_filtre[df_filtre['type_local'] == type_local]
if df_filtre.empty:
    st.warning("Aucun résultat.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Prix/m²", f"{df_filtre['prix_m2'].mean():.0f} €")
c2.metric("Médian", f"{df_filtre['valeur_fonciere'].median():.0f} €")
c3.metric("Transactions", f"{len(df_filtre):,}")
c4.metric("Surface moy", f"{df_filtre['surface_reelle_bati'].mean():.0f} m²")

col1, col2 = st.columns(2)
color_col = "type_local" if "type_local" in df_filtre.columns else None
with col1:
    fig = px.histogram(df_filtre, x='prix_m2', nbins=40, color=color_col, marginal="box")
    st.plotly_chart(fig, width='stretch')
with col2:
    if color_col:
        fig = px.pie(df_filtre, names='type_local')
        st.plotly_chart(fig, width='stretch')

# ------------------------------------------------------------
# CARTE avec st.map (remplace scatter_mapbox)
# ------------------------------------------------------------
st.subheader(f"Carte des transactions - {selected_commune_name}")
if 'latitude' in df_filtre.columns and 'longitude' in df_filtre.columns:
    map_data = df_filtre[['latitude', 'longitude', 'prix_m2', 'surface_reelle_bati']].copy()
    map_data['latitude'] = pd.to_numeric(map_data['latitude'], errors='coerce')
    map_data['longitude'] = pd.to_numeric(map_data['longitude'], errors='coerce')
    map_data = map_data.dropna()
    map_data = map_data[
        (map_data['latitude'].between(-90, 90)) &
        (map_data['longitude'].between(-180, 180))
    ]
    if not map_data.empty:
        sample_size = min(2000, len(map_data))
        if sample_size > 0:
            map_sample = map_data.sample(n=sample_size, random_state=42)
            st.map(map_sample, latitude="latitude", longitude="longitude",
                   size="surface_reelle_bati", color="prix_m2")
        else:
            st.warning("Aucune donnée à afficher.")
    else:
        st.warning("Coordonnées hors limites.")
else:
    st.info("Pas de coordonnées.")

# --- Dernières transactions ---
st.subheader("Dernières transactions")
cols = [c for c in ["date_mutation", "valeur_fonciere", "surface_reelle_bati", "prix_m2", "type_local", "code_postal"] if c in df_filtre.columns]
if cols:
    aff = df_filtre.sort_values('date_mutation', ascending=False).head(100).copy()
    if "valeur_fonciere" in aff.columns:
        aff["valeur_fonciere"] = aff["valeur_fonciere"].apply(lambda x: f"{x:,.0f} €")
    if "prix_m2" in aff.columns:
        aff["prix_m2"] = aff["prix_m2"].apply(lambda x: f"{x:,.0f} €/m²")
    if "date_mutation" in aff.columns:
        aff["date_mutation"] = aff["date_mutation"].dt.strftime("%d/%m/%Y")
    st.dataframe(aff[cols], hide_index=True, width='stretch')

st.caption(f"Dashboard Gironde 2026 - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
