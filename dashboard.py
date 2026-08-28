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

st.set_page_config(page_title="Dashboard Gironde 2026", page_icon="🏘️", layout="wide")

COMMUNES = {
    "33063": "Bordeaux", "33069": "Bruges", "33075": "Cenon",
    "33119": "Eysines", "33192": "Gradignan", "33200": "Gujan-Mestras",
    "33249": "Lormont", "33273": "Merignac", "33281": "Pessac",
    "33312": "Saint-Medard-en-Jalles", "33318": "Talence",
    "33434": "Le Bouscat", "33449": "Villenave-d'Ornon",
    "33039": "Begles", "33056": "Blanquefort", "33162": "Floirac",
    "33243": "Libourne", "33522": "Arcachon",
    "33529": "La Teste-de-Buch", "33550": "Cestas",
}

URL = "https://github.com/gunout/Dashboard-Immobilier-Gironde-2026/releases/download/DVF-33/dvf_plus_d33.csv"


@st.cache_data(ttl=3600)
def load():
    try:
        r = requests.get(URL, timeout=60)
        r.raise_for_status()
        if "html" in r.headers.get("content-type", ""):
            return None
        df = pd.read_csv(io.StringIO(r.text), sep="|", dtype=str,
                         engine="python", on_bad_lines="skip")
        return None if df.empty else df
    except Exception as e:
        st.error(f"Erreur chargement: {e}")
        return None


def clean(df):
    if df is None:
        return None
    d = df.copy()

    # Colonnes utiles selon VOTRE fichier
    cols_map = {
        "datemut": "date",
        "valeurfonc": "prix",
        "sbati": "surf",
        "libtypbien": "type",
        "l_codinsee": "cinsee",
        "geompar_x": "xl",
        "geompar_y": "yl",
    }
    for old, new in cols_map.items():
        if old in d.columns:
            d.rename(columns={old: new}, inplace=True)

    if "prix" not in d.columns or "surf" not in d.columns:
        st.error(f"Colonnes manquantes. Disponibles: {list(d.columns)[:10]}...")
        return None

    # Conversions
    d["prix"] = pd.to_numeric(d["prix"], errors="coerce")
    d["surf"] = pd.to_numeric(d["surf"], errors="coerce")
    if "date" in d.columns:
        d["date"] = pd.to_datetime(d["date"], errors="coerce")

    # ✅ CORRECTION : Filtrer sur les vraies valeurs du fichier
    if "type" in d.columns:
        d = d[d["type"].str.contains("MAISON|APPARTEMENT", case=False, na=False)]

    d = d.dropna(subset=["prix", "surf"])
    d = d[d["prix"].between(20000, 5000000)]
    d = d[d["surf"].between(9, 500)]

    # Prix m2
    d["pm2"] = d["prix"] / d["surf"]
    d = d[d["pm2"].between(300, 15000)]

    # Commune
    if "cinsee" in d.columns:
        d["cinsee"] = d["cinsee"].str.zfill(5)
        d["commune"] = d["cinsee"].map(COMMUNES)
        d = d.dropna(subset=["commune"])

    # Nettoyer le type pour l'affichage
    if "type" in d.columns:
        d["type"] = d["type"].str.extract(r"(MAISON|APPARTEMENT)", expand=False)
        d["type"] = d["type"].str.title()

    # Coordonnees Lambert -> WGS84
    if "xl" in d.columns and "yl" in d.columns:
        d["xl"] = pd.to_numeric(d["xl"], errors="coerce")
        d["yl"] = pd.to_numeric(d["yl"], errors="coerce")
        if HAS_PYPROJ:
            try:
                t = pyproj.Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
                m = d["xl"].notna() & d["yl"].notna()
                if m.any():
                    lon, lat = t.transform(d.loc[m, "xl"].values, d.loc[m, "yl"].values)
                    d.loc[m, "lon"] = lon
                    d.loc[m, "lat"] = lat
            except Exception as e:
                st.warning(f"Conversion coords: {e}")
                d["lon"] = d["xl"]
                d["lat"] = d["yl"]
        else:
            d["lon"] = d["xl"]
            d["lat"] = d["yl"]
        d.drop(columns=["xl", "yl"], errors="ignore", inplace=True)

    keep = [c for c in ["date", "prix", "surf", "type", "pm2", "commune", "lat", "lon"]
            if c in d.columns]
    return d[keep].copy() if keep else None


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════
st.title("🏘️ Dashboard Immobilier Gironde 2026")

with st.spinner("Chargement des donnees..."):
    raw = load()

if raw is None:
    st.error("Donnees indisponibles. Verifiez le lien GitHub Release.")
    st.stop()

with st.spinner("Nettoyage des donnees..."):
    df = clean(raw)

if df is None or df.empty:
    st.error("Aucune transaction valide apres nettoyage.")
    st.info("Verifiez que le fichier contient des Maisons ou Appartements.")
    st.stop()

st.sidebar.success(f"✅ {len(df):,} transactions chargees")

# Stats rapides dans sidebar
with st.sidebar.expander("Stats globales"):
    st.write(f"Prix/m2 moyen: {df['pm2'].mean():,.0f} €")
    st.write(f"Communes: {df['commune'].nunique()}")
    if "type" in df.columns:
        st.write(f"Types: {df['type'].value_counts().to_dict()}")

# Select commune
coms = sorted(df["commune"].unique())
sel = st.sidebar.selectbox("Commune", coms,
                           index=coms.index("Bordeaux") if "Bordeaux" in coms else 0)
dc = df[df["commune"] == sel].copy()

if dc.empty:
    st.warning(f"Pas de donnees pour {sel}")
    st.stop()

# Filtres
st.sidebar.header("🔧 Filtres")
types_dispo = ["Tous"]
if "type" in dc.columns:
    types_dispo.extend(sorted(dc["type"].dropna().unique()))
typ = st.sidebar.selectbox("Type", types_dispo)
pmin = st.sidebar.number_input("Prix min (€)", 0, step=20000)
pmax = st.sidebar.number_input("Prix max (€)", int(dc["prix"].max()), step=50000)
smin = st.sidebar.slider("Surface min (m²)", 0, int(dc["surf"].max()), 0)

f = dc.copy()
f = f[f["prix"].between(pmin, pmax) & (f["surf"] >= smin)]
if typ != "Tous" and "type" in f.columns:
    f = f[f["type"] == typ]

if f.empty:
    st.warning("Aucun resultat avec ces filtres.")
    st.stop()

# KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Prix/m² moyen", f"{f['pm2'].mean():,.0f} €")
k2.metric("Prix médian", f"{f['prix'].median():,.0f} €")
k3.metric("Transactions", f"{len(f):,}")
k4.metric("Surface moy.", f"{f['surf'].mean():.0f} m²")

# Graphiques
c1, c2 = st.columns(2)
clr = "type" if "type" in f.columns else None

with c1:
    fig = px.histogram(f, x="pm2", nbins=30, color=clr,
                      title=f"Distribution prix/m² – {sel}")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fig = px.scatter(f, x="surf", y="prix", color=clr,
                     title="Surface vs Prix", opacity=0.6)
    st.plotly_chart(fig, use_container_width=True)

# Carte
st.subheader(f"🗺️ Carte – {sel}")
if "lat" in f.columns and "lon" in f.columns:
    fm = f[["lat", "lon", "pm2", "surf"]].dropna().copy()
    fm["lat"] = pd.to_numeric(fm["lat"], errors="coerce")
    fm["lon"] = pd.to_numeric(fm["lon"], errors="coerce")
    fm = fm.dropna()

    # Verif coordonnees valides WGS84
    ok = fm["lat"].between(-90, 90) & fm["lon"].between(-180, 180)

    if ok.any():
        carte = fm[ok].copy()
        if len(carte) > 500:
            carte = carte.sample(500, random_state=42)
            st.caption(f"📍 500 points affichés sur {len(fm)}")
        st.map(carte, latitude="lat", longitude="lon", size="surf", color="pm2")
    else:
        st.warning("⚠️ Coordonnées en Lambert (non converties).")
        with st.expander("Diagnostic"):
            st.dataframe(fm.describe())
else:
    st.info("📍 Pas de coordonnées disponibles.")

# Evolution temporelle
if "date" in f.columns:
    ft = f.dropna(subset=["date"]).copy()
    if not ft.empty:
        ft["mois"] = ft["date"].dt.strftime("%Y-%m")
        agg = ft.groupby("mois").agg(
            pm2=("pm2", "mean"),
            nb=("prix", "count")
        ).reset_index()

        st.subheader("📊 Évolution dans le temps")
        c1, c2 = st.columns(2)
        with c1:
            fig = px.line(agg, x="mois", y="pm2", markers=True,
                         title="Prix/m² moyen")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.bar(agg, x="mois", y="nb", title="Nb transactions")
            st.plotly_chart(fig, use_container_width=True)

# Top 5
st.subheader("💰 Top 5 ventes")
cols = [c for c in ["date", "prix", "surf", "pm2", "type"] if c in f.columns]
if cols:
    top = f.nlargest(5, "prix")[cols].copy()
    top["prix"] = top["prix"].apply(lambda x: f"{x:,.0f} €")
    top["pm2"] = top["pm2"].apply(lambda x: f"{x:,.0f} €/m²")
    st.dataframe(top, hide_index=True, use_container_width=True)

# Dernieres transactions
st.subheader("📋 Dernières transactions")
if cols:
    rec = f.sort_values("date", ascending=False).head(30)[cols].copy()
    rec["prix"] = rec["prix"].apply(lambda x: f"{x:,.0f} €")
    rec["pm2"] = rec["pm2"].apply(lambda x: f"{x:,.0f} €/m²")
    st.dataframe(rec, hide_index=True, use_container_width=True)

st.markdown("---")
st.caption(f"📊 DVF+ Gironde – MAJ: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
