from jobspy import scrape_jobs

print("Probando scraping en multiples sitios...")
try:
    jobs_df = scrape_jobs(
        site_name=["linkedin", "indeed", "google"],
        search_term="Pasantia Finanzas",
        location="Buenos Aires, Argentina",
        results_wanted=15,
        hours_old=48, # Ampliamos a 48 horas por las dudas
        country_indeed="argentina"
    )
    
    if jobs_df is not None and not jobs_df.empty:
        print("\nResultados obtenidos por sitio:")
        print(jobs_df['site'].value_counts())
        print("\nPrimeras ofertas encontradas:")
        print(jobs_df[['site', 'title', 'company']].head(5))
    else:
        print("El DataFrame devolvio vacio para todos los sitios.")
        
except Exception as e:
    print(f"Error durante el scraping: {e}")