# dashboard.py – version de diagnostic ultra-simplifiée
import streamlit as st
import pandas as pd
import requests
import io

st.set_page_config(page_title="Diagnostic 2026", layout="wide")

st.title("🔍 Diagnostic du fichier DVF+ 2026")

DATA_URL = "https://github.com/gunout/Dashboard-Immobilier-Gironde-2026/releases/download/DVF-33/dvf_plus_d33.csv"

try:
    with st.spinner("Téléchargement..."):
        response = requests.get(DATA_URL, timeout=60)
        response.raise_for_status()
    st.success(f"✅ Téléchargement réussi – {len(response.text)} caractères")
    
    # Afficher un aperçu du contenu
    st.subheader("📄 Aperçu des 500 premiers caractères")
    st.text(response.text[:500])
    
    # Essayer de parser avec le séparateur '|'
    try:
        df = pd.read_csv(io.StringIO(response.text), sep='|', nrows=5, dtype=str, engine='python', on_bad_lines='skip')
        st.success("✅ Parsing réussi avec séparateur '|'")
        st.write("**Colonnes trouvées :**", list(df.columns))
        st.write("**Aperçu des données :**", df)
    except Exception as e:
        st.error(f"Parsing échoué : {e}")
        
except Exception as e:
    st.error(f"Erreur : {e}")
    import traceback
    st.code(traceback.format_exc())
