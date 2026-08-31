import streamlit as st
import pandas as pd
import json
from pypdf import PdfReader
from jobspy import scrape_jobs
from google import genai

st.set_page_config(page_title="Buscador Multi-Portal con Gemini", layout="wide")

st.title("Buscador Inteligente de Empleo Multi-Portal")
st.caption("LinkedIn | Indeed | Glassdoor | ZipRecruiter — Analizado con Gemini 3.6 Flash")

# Clave predeterminada si existe en Secrets, o entrada manual
default_key = st.secrets.get("GEMINI_API_KEY", "")

# --- Barra lateral: Filtros de Búsqueda ---
with st.sidebar:
    st.header("Configuracion")
    
    api_key = st.text_input(
        "Gemini API Key:",
        value=default_key,
        type="password",
        help="Obtenla gratis en Google AI Studio"
    )
    st.markdown("---")
    
    selected_sites = st.multiselect(
        "Portales a rastrear:",
        options=["linkedin", "indeed", "glassdoor", "zip_recruiter"],
        default=["linkedin", "indeed"],
        help="Puedes combinar varios portales simultaneamente"
    )
    
    keywords = st.text_input("Puesto o Palabras Clave:", value="Analista Financiero")
    location = st.text_input("Ubicacion:", value="Buenos Aires, Argentina")
    
    time_options = {
        "Ultimas 24 horas": 24,
        "Ultimos 3 dias": 72,
        "Ultima semana": 168,
        "Ultimo mes": 720
    }
    selected_time_label = st.selectbox(
        "Antiguedad de las ofertas:",
        options=list(time_options.keys()),
        index=0
    )
    hours_filter = time_options[selected_time_label]
    
    only_remote = st.checkbox("Solo puestos 100% Remotos", value=False)
    
    max_results = st.slider(
        "Cantidad maxima de ofertas a recopilar:",
        min_value=10,
        max_value=150,
        value=30,
        step=10
    )

# --- Area Principal: Perfil y Criterios ---
st.subheader("Perfil del Candidato")

uploaded_cv = st.file_uploader(
    "Subir CV en formato PDF (opcional):", 
    type=["pdf"], 
    help="El texto se procesa de forma local sin costo de tokens adicional."
)

cv_extracted_text = ""
if uploaded_cv is not None:
    try:
        reader = PdfReader(uploaded_cv)
        extracted_pages = [page.extract_text() for page in reader.pages if page.extract_text()]
        cv_extracted_text = "\n".join(extracted_pages)
        st.info("CV cargado y procesado correctamente.")
    except Exception as e:
        st.error(f"Error al leer el archivo PDF: {e}")

user_criteria = st.text_area(
    "Criterios de busqueda, intereses o condiciones especificas:",
    value="Busco posiciones junior o pasantias orientadas a finanzas corporativas, control de gestion o analisis de datos. Modalidad hibrida o remota. Valora empresas con plan de carrera y descarta puestos senior o de ventas comisionadas.",
    height=90
)

# Integrar perfil de CV con criterios adicionales
if cv_extracted_text:
    candidate_profile = f"INFORMACION DEL CV:\n{cv_extracted_text}\n\nPREFERENCIAS Y CONDICIONES ADICIONALES:\n{user_criteria}"
else:
    candidate_profile = user_criteria

def fetch_multisite_jobs(sites: list, query: str, loc: str, limit: int, hours: int, is_remote: bool):
    try:
        jobs_df = scrape_jobs(
            site_name=sites,
            search_term=query,
            location=loc,
            results_wanted=limit,
            hours_old=hours,
            is_remote=is_remote,
            country_indeed="argentina"
        )
        
        if jobs_df is None or jobs_df.empty:
            return []
        
        standardized_jobs = []
        for _, row in jobs_df.iterrows():
            standardized_jobs.append({
                "portal": str(row.get("site", "N/A")).upper(),
                "titulo": str(row.get("title", "Sin titulo")),
                "empresa": str(row.get("company", "No especificada")),
                "ubicacion": str(row.get("location", loc)),
                "enlace": str(row.get("job_url", "#"))
            })
        return standardized_jobs
        
    except Exception as e:
        st.error(f"Error durante el rastreo de ofertas: {e}")
        return []

def analyze_jobs_with_gemini(jobs: list, criteria: str, key: str):
    client = genai.Client(api_key=key)
    
    prompt = f"""
    Eres un consultor senior de seleccion de talento.
    
    Lista de {len(jobs)} ofertas laborales:
    {json.dumps(jobs, indent=2, ensure_ascii=False)}
    
    Perfil y criterios del candidato:
    "{criteria}"
    
    Tu tarea:
    1. Evalua cada vacante contra el perfil y criterios del candidato.
    2. Asigna un porcentaje de afinidad ("match_score") del 0 al 100%.
    3. Escribe un resumen de 2 lineas ("motivo_match") explicando por que encaja o que condiciones cumple segun su formacion/experiencia.
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
    Devuelve UNICAMENTE el bloque JSON valido sin texto adicional.
    """
    
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt,
        config={'response_mime_type': 'application/json'}
    )
    return json.loads(response.text)

def generate_cover_message(job_title: str, company: str, criteria: str, key: str):
    client = genai.Client(api_key=key)
    prompt = f"""
    Redacta un mensaje de contacto directo para LinkedIn (maximo 70 palabras), formal y conciso, dirigido al reclutador de la vacante "{job_title}" en la empresa "{company}".
    
    Contexto del candidato:
    "{criteria}"
    
    El mensaje debe expresar interes concreto, destacar afinidad directa y dejar abierta la posibilidad de una conversacion.
    """
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt
    )
    return response.text

# --- Ejecucion ---
if st.button("Buscar y Clasificar Ofertas", type="primary"):
    if not api_key:
        st.error("Ingresa tu clave de API de Gemini en la barra lateral.")
    elif not selected_sites:
        st.warning("Selecciona al menos un portal en la barra lateral.")
    else:
        with st.spinner(f"Fase 1/2: Rastreando ofertas ({selected_time_label.lower()}) en {', '.join(selected_sites).upper()}..."):
            raw_jobs = fetch_multisite_jobs(selected_sites, keywords, location, max_results, hours_filter, only_remote)

        if not raw_jobs:
            st.warning("No se encontraron ofertas con esos filtros temporales. Prueba ampliando el rango de tiempo o los terminos.")
        else:
            st.info(f"Se recopilaron {len(raw_jobs)} vacantes. Enviando a Gemini para evaluacion...")
            
            with st.spinner("Fase 2/2: Gemini esta evaluando y ordenando las vacantes segun tu perfil..."):
                try:
                    analyzed_jobs = analyze_jobs_with_gemini(raw_jobs, candidate_profile, api_key)
                    analyzed_jobs = sorted(analyzed_jobs, key=lambda x: x.get('match_score', 0), reverse=True)
                    
                    st.success(f"Evaluacion completada. Se analizaron {len(analyzed_jobs)} ofertas.")
                    st.session_state['analyzed_jobs'] = analyzed_jobs
                    
                except Exception as e:
                    st.error(f"Error durante el procesamiento con Gemini: {e}")

# --- Renderizado de Resultados ---
if 'analyzed_jobs' in st.session_state and st.session_state['analyzed_jobs']:
    jobs_list = st.session_state['analyzed_jobs']
    
    df_export = pd.DataFrame(jobs_list)
    csv_data = df_export.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Descargar resultados (CSV / Excel)",
        data=csv_data,
        file_name="ofertas_recomendadas.csv",
        mime="text/csv"
    )
    
    st.markdown("---")
    
    for i, job in enumerate(jobs_list):
        score = job.get('match_score', 0)
        portal = job.get('portal', 'WEB')
        
        with st.expander(f"[{score}% Match] [{portal}] {job.get('titulo')} — {job.get('empresa')}"):
            st.write(f"**Ubicacion:** {job.get('ubicacion')}")
            st.write(f"**Analisis de compatibilidad:** {job.get('motivo_match')}")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.link_button(f"Abrir postulacion en {portal}", job.get('enlace'))
            
            with col2:
                if st.button(f"Generar mensaje de contacto", key=f"msg_{i}"):
                    with st.spinner("Redactando mensaje..."):
                        cover_letter = generate_cover_message(job.get('titulo'), job.get('empresa'), candidate_profile, api_key)
                        st.text_area("Mensaje listo para enviar al reclutador:", value=cover_letter, height=120)