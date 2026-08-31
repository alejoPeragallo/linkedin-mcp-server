import streamlit as st
import pandas as pd
import json
from jobspy import scrape_jobs
from google import genai

st.set_page_config(page_title="Buscador Multi-Plataforma con Gemini", page_icon="💼", layout="wide")

st.title("Buscador Inteligente de Empleo Multi-Portal")
st.caption("Búsqueda simultánea en LinkedIn, Indeed y Glassdoor con análisis de Gemini 3.6 Flash")

# --- Barra lateral: Configuración ---
with st.sidebar:
    st.header("Configuración")
    api_key = st.text_input("Gemini API Key:", type="password", help="Obtenla gratis en Google AI Studio")
    st.markdown("---")
    
    # Selector de plataformas
    selected_sites = st.multiselect(
        "Portales a rastrear:",
        options=["linkedin", "indeed", "glassdoor", "zip_recruiter"],
        default=["linkedin", "indeed"],
        help="Puedes seleccionar varias plataformas al mismo tiempo"
    )
    
    keywords = st.text_input("Puesto o Palabras Clave:", value="Analista Financiero")
    location = st.text_input("Ubicación:", value="Buenos Aires, Argentina")
    
    # Slider ampliado de 10 a 150 ofertas
    max_results = st.slider(
        "Cantidad máxima de ofertas a recopilar:",
        min_value=10,
        max_value=150,
        value=50,
        step=10,
        help="La librería paginará automáticamente para alcanzar este número"
    )
    
# --- Formulario de Preferencias ---
st.subheader("Criterios de Selección y Filtro")
user_criteria = st.text_area(
    "Describe qué buscas y tus condiciones ideales:",
    value="Busco pasantías o posiciones junior orientadas a finanzas, planeamiento financiero o control de gestión. Modalidad híbrida o remota. Prioriza empresas donde haya posibilidades de crecimiento y descarta perfiles senior.",
    height=100
)

def fetch_multisite_jobs(sites: list, query: str, loc: str, limit: int):
    """Extrae ofertas simultáneamente de múltiples portales con paginación automática."""
    try:
        jobs_df = scrape_jobs(
            site_name=sites,
            search_term=query,
            location=loc,
            results_wanted=limit,
            country_indeed="argentina",
            hours_old=168 # Ofertas de los últimos 7 días
        )
        
        if jobs_df is None or jobs_df.empty:
            return []
        
        # Estandarizar resultados
        standardized_jobs = []
        for _, row in jobs_df.iterrows():
            standardized_jobs.append({
                "portal": str(row.get("site", "N/A")).upper(),
                "titulo": str(row.get("title", "Sin título")),
                "empresa": str(row.get("company", "No especificada")),
                "ubicacion": str(row.get("location", loc)),
                "enlace": str(row.get("job_url", "#"))
            })
        return standardized_jobs
        
    except Exception as e:
        st.error(f"Error durante el rastreo de ofertas: {e}")
        return []

def analyze_jobs_with_gemini(jobs: list, criteria: str, key: str):
    """Envía todo el lote a Gemini para ranking y análisis de compatibilidad."""
    client = genai.Client(api_key=key)
    
    prompt = f"""
    Eres un consultor senior de reclutamiento y selección de talento.
    
    Tienes una lista de {len(jobs)} vacantes de empleo extraídas de distintos portales:
    {json.dumps(jobs, indent=2, ensure_ascii=False)}
    
    Criterios y condiciones del candidato:
    "{criteria}"
    
    Tu tarea:
    1. Evalúa cada vacante contra los criterios del candidato.
    2. Asigna una puntuación de compatibilidad ("match_score") del 0 al 100%.
    3. Redacta un breve motivo ("motivo_match") explicando por qué encaja o qué condiciones cumple.
    4. Devuelve el resultado en formato JSON estructurado:
       [
         {{
           "portal": "...",
           "titulo": "...",
           "empresa": "...",
           "ubicacion": "...",
           "enlace": "...",
           "match_score": 90,
           "motivo_match": "..."
         }}
       ]
    Devuelve ÚNICAMENTE el bloque JSON válido sin texto adicional.
    """
    
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt,
        config={
            'response_mime_type': 'application/json'
        }
    )
    return json.loads(response.text)

# --- Botón de Ejecución ---
if st.button("Buscar y Clasificar con Gemini", type="primary"):
    if not api_key:
        st.error("Por favor, ingresa tu clave de API de Gemini en la barra lateral.")
    elif not selected_sites:
        st.warning("Debes seleccionar al menos un portal en la barra lateral.")
    else:
        with st.spinner(f"1/2 Extrayendo hasta {max_results} ofertas desde {', '.join(selected_sites).upper()}..."):
            raw_jobs = fetch_multisite_jobs(selected_sites, keywords, location, max_results)

        if not raw_jobs:
            st.warning("No se encontraron vacantes con esos filtros. Prueba cambiando los términos o la ubicación.")
        else:
            st.info(f"Se recopilaron **{len(raw_jobs)}** vacantes brutas. Enviando a Gemini para evaluación...")
            
            with st.spinner("2/2 Gemini está analizando, puntuando y ordenando las vacantes por relevancia..."):
                try:
                    analyzed_jobs = analyze_jobs_with_gemini(raw_jobs, user_criteria, api_key)
                    analyzed_jobs = sorted(analyzed_jobs, key=lambda x: x.get('match_score', 0), reverse=True)
                    
                    st.success(f"¡Evaluación terminada! Se analizaron {len(analyzed_jobs)} ofertas.")
                    
                    for job in analyzed_jobs:
                        score = job.get('match_score', 0)
                        score_icon = "🟢" if score >= 75 else "🟡" if score >= 50 else "🔴"
                        portal = job.get('portal', 'WEB')
                        
                        with st.expander(f"{score_icon} [{portal}] **{job.get('titulo')}** en **{job.get('empresa')}** — Coincidencia: {score}%"):
                            st.write(f"📍 **Ubicación:** {job.get('ubicacion')}")
                            st.write(f"💡 **Motivo de compatibilidad:** {job.get('motivo_match')}")
                            st.link_button(f"Abrir postulación en {portal} ↗", job.get('enlace'))
                            
                except Exception as e:
                    st.error(f"Error durante el procesamiento con Gemini: {e}")