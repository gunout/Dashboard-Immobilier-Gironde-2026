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

st.set_page_config(
    page_title="Dashboard Immobilier Gironde 2026",
    page_icon="🏘️",
    layout="wide"
)

COMMUNES_GIRONDE = {
    "33063": "Bordeaux", "33069": "Bruges", "33075": "Cenon",
    "33119": "Eysines", "33192": "Gradignan", "33200": "Gujan-Mestras",
    "33249": "Lormont", "33273": "Merignac", "33281": "Pessac",
    "33312": "Saint-Medard-en-Jalles", "33318": "Talence",
    "33434": "Le Bouscat", "33449": "Villenave-d'Ornon",
    "33039": "Begles", "33056": "Blanquefort", "33162": "Floirac",
    "33243": "Libourne", "33522": "Arcachon",
    "33529": "La Teste-de-Buch", "33550": "Cestas",
}

DATA_URL = "https://github.com/gunout/Dashboard-Immobilier-Gironde-2026/releases/download/DVF-33/dvf_plus_d33.csv"


@st.cache_data(ttl=3600)
def load_data():
    try:
        resp = requests.get(DATA_URL, timeout=60)
        resp.raise_for_status()
        if "text/html" in resp.headers.get("content-type", ""):
            return None
        df = pd.read_csv(io.StringIO(resp.text), sep="|", dtype=str,
                         engine="python", on_bad_lines="skip")
        return df if not df.empty else None
    except Exception:
        return None


def clean_data(df):
    if df is None:
        return None

    d = df.copy()

    # Renommage
    renames = {
        "datemut": "date_mutation", "valeurfonc": "valeur_fonciere",
        "sbati": "surface_bati", "libtypbien": "type_local",
        "l_codinsee": "code_commune", "geompar_x": "lon_lambert",
        "geompar_y": "lat_lambert", "l_codepost": "code_postal",
        "nbpieceprin": "nb_pieces",
    }
    for old, new in renames.items():
        if old in d.columns:
            d.rename(columns={old: new}, inplace=True)

    # Colonnes requises
    for col in ["valeur_fonciere", "surface_bati"]:
        if col not in d.columns:
            return None

    # Conversions
    d["valeur_fonciere"] = pd.to_numeric(d["valeur_fonciere"], errors="coerce")
    d["surface_bati"] = pd.to_numeric(d["surface_bati"], errors="coerce")
    if "date_mutation" in d.columns:
        d["date_mutation"] = pd.to_datetime(d["date_mutation"], errors="coerce")
    if "nb_pieces" in d.columns:
        d["nb_pieces"] = pd.to_numeric(d["nb_pieces"], errors="coerce")

    # Filtres
    if "type_local" in d.columns:
        d = d[d["type_local"].isin(["Maison", "Appartement"])]
    d = d.dropna(subset=["valeur_fonciere", "surface_bati"])
    d = d[d["valeur_fonciere"].between(20000, 3000000)]
    d = d[d["surface_bati"].between(9, 400)]
    d["prix_m2"] = d["valeur_fonciere"] / d["surface_bati"]
    d = d[d["prix_m2"].between(500, 12000)]

    # Commune
    if "code_commune" in d.columns:
        d["code_commune"] = d["code_commune"].str.zfill(5)
        d["commune"] = d["code_commune"].map(COMMUNES_GIRONDE)
        d = d.dropna(subset=["commune"])

    # Coordonnees
    if "lon_lambert" in d.columns and "lat_lambert" in d.columns:
        d["lon_lambert"] = pd.to_numeric(d["lon_lambert"], errors="coerce")
        d["lat_lambert"] = pd.to_numeric(d["lat_lambert"], errors="coerce")
        if HAS_PYPROJ:
            try:
                t = pyproj.Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
                mask = d["lon_lambert"].notna() & d["lat_lambert"].notna()
                if mask.any():
                    x, y = t.transform(d.loc[mask, "lon_lambert"].values,
                                       d.loc[mask, "lat_lambert"].values)
                    d.loc[mask, "lon"] = x
                    d.loc[mask, "lat"] = y
            except Exception:
                d["lon"] = d["lon_lambert"]
                d["lat"] = d["lat_lambert"]
        else:
            d["lon"] = d["lon_lambert"]
            d["lat"] = d["lat_lambert"]
        d.drop(columns=["lon_lambert", "lat_lambert"], errors="ignore", inplace=True)

    # Colonnes finales
    cols = [c for c in ["date_mutation", "valeur_fonciere", "surface_bati",
                         "type_local", "code_postal", "nb_pieces",
                         "prix_m2", "commune", "lat", "lon"] if c in d.columns]
    return d[cols].copy() if cols else None


# === MAIN ===
st.title("Dashboard Immobilier Gironde 2026")

raw = load_data()
if raw is None:
    st.error("Donnees indisponibles. Verifiez le lien GitHub Release.")
    st.stop()

df = clean_data(raw)
if df is None or df.empty:
    st.error("Aucune transaction valide apres nettoyage.")
    st.stop()

st.sidebar.success(f"{len(df):,} transactions chargees")

# Select commune
communes = sorted(df["commune"].unique())
sel = st.sidebar.selectbox("Commune", communes,
                           index=communes.index("Bordeaux") if "Bordeaux" in communes else 0)
dc = df[df["commune"] == sel].copy()

if dc.empty:
    st.warning(f"Pas de donnees pour {sel}")
    st.stop()

# Filters
st.sidebar.header("Filtres")
typ = st.sidebar.selectbox("Type", ["Tous", "Maison", "Appartement"])
pmin = st.sidebar.number_input("Prix min", 0, step=20000)
pmax = st.sidebar.number_input("Prix max", int(dc["valeur_fonciere"].max()), step=50000)
smin = st.sidebar.slider("Surface min", 0, int(dc["surface_bati"].max()), 0)

f = dc.copy()
f = f[f["valeur_fonciere"].between(pmin, pmax)]
f = f[f["surface_bati"] >= smin]
if typ != "Tous" and "type_local" in f.columns:
    f = f[f["type_local"] == typ]

if f.empty:
    st.warning("Aucun resultat.")
    st.stop()

# KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Prix/m2 moyen", f"{f['prix_m2'].mean():,.0f} EUR")
k2.metric("Prix median", f"{f['valeur_fonciere'].median():,.0f} EUR")
k3.metric("Transactions", f"{len(f):,}")
k4.metric("Surface moy.", f"{f['surface_bati'].mean():.0f} m2")

# Charts
c1, c2 = st.columns(2)
clr = "type_local" if "type_local" in f.columns else None

with c1:
    fig = px.histogram(f, x="prix_m2", nbins=30, color=clr,
                      title=f"Prix/m2 - {sel}")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fig = px.scatter(f, x="surface_bati", y="valeur_fonciere", color=clr,
                     title="Surface vs Prix")
    st.plotly_chart(fig, use_container_width=True)

# Map
st.subheader(f"Carte - {sel}")
if "lat" in f.columns and "lon" in f.columns:
    fm = f[["lat", "lon", "prix_m2", "surface_bati"]].dropna().copy()
    fm["lat"] = pd.to_numeric(fm["lat"], errors="coerce")
    fm["lon"] = pd.to_numeric(fm["lon"], errors="coerce")
    fm = fm.dropna()
    valid = fm["lat"].between(-90, 90) & fm["lon"].between(-180, 180)
    if valid.any():
        st.map(fm[valid], latitude="lat", longitude="lon",
               size="surface_bati", color="prix_m2")
    else:
        st.warning("Coordonnees hors limites.")
        st.dataframe(fm.describe())
else:
    st.info("Pas de coordonnees.")

# Time series
if "date_mutation" in f.columns:
    ft = f.dropna(subset=["date_mutation"]).copy()
    if not ft.empty:
        ft["mois"] = ft["date_mutation"].dt.strftime("%Y-%m")
        agg = ft.groupby("mois").agg(
            pm2=("prix_m2", "mean"),
            nb=("valeur_fonciere", "count")
        ).reset_index()

        c1, c2 = st.columns(2)
        with c1:
            fig = px.line(agg, x="mois", y="pm2", markers=True,
                         title="Prix/m2 dans le temps")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.bar(agg, x="mois", y="nb", title="Nb transactions")
            st.plotly_chart(fig, use_container_width=True)

# Top 5
st.subheader("Top 5 ventes")
cols_show = [c for c in ["date_mutation", "valeur_fonciere", "surface_bati",
                          "prix_m2", "type_local"] if c in f.columns]
if cols_show:
    top = f.nlargest(5, "valeur_fonciere")[cols_show].copy()
    st.dataframe(top, hide_index=True, use_container_width=True)

# Recent
st.subheader("Dernieres transactions")
rec = f.sort_values("date_mutation", ascending=False).head(30)[cols_show].copy()
st.dataframe(rec, hide_index=True, use_container_width=True)

st.caption(f"Mise a jour: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
