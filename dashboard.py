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
    except Exception:
        return None


def clean(df):
    if df is None:
        return None
    d = df.copy()

    for old, new in [("datemut", "date_mut"), ("valeurfonc", "prix"),
                     ("sbati", "surf"), ("libtypbien", "type"),
                     ("l_codinsee", "cinsee"), ("geompar_x", "xl"),
                     ("geompar_y", "yl"), ("l_codepost", "cpost"),
                     ("nbpieceprin", "nbp")]:
        if old in d.columns:
            d.rename(columns={old: new}, inplace=True)

    if "prix" not in d.columns or "surf" not in d.columns:
        return None

    d["prix"] = pd.to_numeric(d["prix"], errors="coerce")
    d["surf"] = pd.to_numeric(d["surf"], errors="coerce")
    if "date_mut" in d.columns:
        d["date_mut"] = pd.to_datetime(d["date_mut"], errors="coerce")
    if "nbp" in d.columns:
        d["nbp"] = pd.to_numeric(d["nbp"], errors="coerce")

    if "type" in d.columns:
        d = d[d["type"].isin(["Maison", "Appartement"])]

    d = d.dropna(subset=["prix", "surf"])
    d = d[d["prix"].between(20000, 3000000)]
    d = d[d["surf"].between(9, 400)]
    d["pm2"] = d["prix"] / d["surf"]
    d = d[d["pm2"].between(500, 12000)]

    if "cinsee" in d.columns:
        d["cinsee"] = d["cinsee"].str.zfill(5)
        d["commune"] = d["cinsee"].map(COMMUNES)
        d = d.dropna(subset=["commune"])

    if "xl" in d.columns and "yl" in d.columns:
        d["xl"] = pd.to_numeric(d["xl"], errors="coerce")
        d["yl"] = pd.to_numeric(d["yl"], errors="coerce")
        if HAS_PYPROJ:
            try:
                t = pyproj.Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
                m = d["xl"].notna() & d["yl"].notna()
                if m.any():
                    d.loc[m, "lon"], d.loc[m, "lat"] = t.transform(
                        d.loc[m, "xl"].values, d.loc[m, "yl"].values)
            except Exception:
                d["lon"], d["lat"] = d["xl"], d["yl"]
        else:
            d["lon"], d["lat"] = d["xl"], d["yl"]
        d.drop(columns=["xl", "yl"], errors="ignore", inplace=True)

    keep = [c for c in ["date_mut", "prix", "surf", "type", "cpost",
                         "nbp", "pm2", "commune", "lat", "lon"] if c in d.columns]
    return d[keep].copy() if keep else None


# === MAIN ===
st.title("🏘️ Dashboard Immobilier Gironde 2026")

raw = load()
if raw is None:
    st.error("Donnees indisponibles.")
    st.stop()

df = clean(raw)
if df is None or df.empty:
    st.error("Aucune transaction valide.")
    st.stop()

st.sidebar.success(f"{len(df):,} transactions")

coms = sorted(df["commune"].unique())
sel = st.sidebar.selectbox("Commune", coms,
                           index=coms.index("Bordeaux") if "Bordeaux" in coms else 0)
dc = df[df["commune"] == sel].copy()

if dc.empty:
    st.warning(f"Pas de donnees pour {sel}")
    st.stop()

st.sidebar.header("Filtres")
typ = st.sidebar.selectbox("Type", ["Tous", "Maison", "Appartement"])
pmin = st.sidebar.number_input("Prix min", 0, step=20000)
pmax = st.sidebar.number_input("Prix max", int(dc["prix"].max()), step=50000)
smin = st.sidebar.slider("Surface min", 0, int(dc["surf"].max()), 0)

f = dc.copy()
f = f[f["prix"].between(pmin, pmax) & (f["surf"] >= smin)]
if typ != "Tous" and "type" in f.columns:
    f = f[f["type"] == typ]

if f.empty:
    st.warning("Aucun resultat.")
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Prix/m2", f"{f['pm2'].mean():,.0f} €")
k2.metric("Median", f"{f['prix'].median():,.0f} €")
k3.metric("Transactions", f"{len(f):,}")
k4.metric("Surface moy", f"{f['surf'].mean():.0f} m²")

c1, c2 = st.columns(2)
clr = "type" if "type" in f.columns else None

with c1:
    fig = px.histogram(f, x="pm2", nbins=30, color=clr, title=f"Prix/m² - {sel}")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fig = px.scatter(f, x="surf", y="prix", color=clr, title="Surface vs Prix")
    st.plotly_chart(fig, use_container_width=True)

st.subheader(f"🗺️ Carte - {sel}")
if "lat" in f.columns and "lon" in f.columns:
    fm = f[["lat", "lon", "pm2", "surf"]].dropna().copy()
    fm["lat"] = pd.to_numeric(fm["lat"], errors="coerce")
    fm["lon"] = pd.to_numeric(fm["lon"], errors="coerce")
    fm = fm.dropna()
    ok = fm["lat"].between(-90, 90) & fm["lon"].between(-180, 180)
    if ok.any():
        st.map(fm[ok], latitude="lat", longitude="lon", size="surf", color="pm2")
    else:
        st.warning("Coordonnees invalides.")
else:
    st.info("Pas de coordonnees.")

if "date_mut" in f.columns:
    ft = f.dropna(subset=["date_mut"]).copy()
    if not ft.empty:
        ft["mois"] = ft["date_mut"].dt.strftime("%Y-%m")
        agg = ft.groupby("mois").agg(pm2=("pm2", "mean"), n=("prix", "count")).reset_index()
        c1, c2 = st.columns(2)
        with c1:
            fig = px.line(agg, x="mois", y="pm2", markers=True, title="Prix/m²")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.bar(agg, x="mois", y="n", title="Transactions")
            st.plotly_chart(fig, use_container_width=True)

st.subheader("💰 Top 5")
cols = [c for c in ["date_mut", "prix", "surf", "pm2", "type"] if c in f.columns]
if cols:
    st.dataframe(f.nlargest(5, "prix")[cols], hide_index=True, use_container_width=True)

st.subheader("📋 Dernieres")
st.dataframe(f.sort_values("date_mut", ascending=False).head(30)[cols],
             hide_index=True, use_container_width=True)

st.caption(f"MAJ: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
