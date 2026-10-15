# PerfumeTrending.cl — Checklist de Validación en Staging

Antes de aplicar cualquier cambio o migración en el entorno de producción de Supabase, el equipo de ingeniería debe verificar y completar los siguientes puntos en una base de datos de desarrollo/staging aislada:

- [ ] **1. Respaldo Previsto:**
  - [ ] Ejecutar volcado completo (`pg_dump` o backup nativo de Supabase) antes de aplicar las migraciones.
  - [ ] Verificar que el archivo de respaldo no esté corrupto y pueda restaurarse localmente.

- [ ] **2. Ejecución Secuencial de Migraciones:**
  - [ ] `20261015000002_tablas_variantes_ofertas_auditoria.sql` ejecutado sin errores.
  - [ ] `20261015000003_catalogo_notas_familias_olfativas.sql` ejecutado sin errores.
  - [ ] `20261015000004_seed_familias_y_notas.sql` ejecutado sin errores.
  - [ ] `20261015000005_staging_notas_migracion.sql` ejecutado sin errores.
  - [ ] `20261015000006_funciones_persistencia_transaccional.sql` ejecutado sin errores.
  - [ ] `20261015000007_seguridad_rls_politicas.sql` ejecutado sin errores.
  - [ ] `20261015000008_migracion_datos_historicos.sql` ejecutado sin errores.

- [ ] **3. Verificación de Integridad de Datos:**
  - [ ] Exactamente 12 familias de notas registradas en `familias_notas`.
  - [ ] Exactamente 107 notas registradas en `notas_olfativas`.
  - [ ] Cero duplicados en `ofertas_actuales` por `(variante_id, tienda_id)`.
  - [ ] Ningún perfume con más de una familia principal en `perfume_familias_olfativas`.
  - [ ] El conteo de filas en `precios_registro` coincide exactamente con el conteo previo a la migración (cero pérdida de historial).
  - [ ] El campo `perfumes.notas` se mantiene intacto y con el 100% de los datos originales.

- [ ] **4. Pruebas Transaccionales y de Funciones:**
  - [ ] `registrar_observacion_oferta` probado con inserción inicial (crea oferta e historial).
  - [ ] `registrar_observacion_oferta` probado con observación idéntica (no duplica historial).
  - [ ] `registrar_observacion_oferta` probado con cambio de precio y stock (registra evento y actualiza oferta).
  - [ ] `registrar_fallo_scraping` probado (no altera precio ni stock confirmados).
  - [ ] Prueba de rollback transaccional ante precio negativo o fallo de FK.

- [ ] **5. Pruebas de Aplicación y Frontend:**
  - [ ] La app Streamlit carga correctamente el catálogo con las vistas actualizadas.
  - [ ] El comparador de precios muestra ofertas activas ordenadas por menor precio.
  - [ ] La página de perfil y favoritos opera sin excepciones.
  - [ ] Los scrapers nocturnos se ejecutan en seco (`dry-run`) validando que no haya excepciones no controladas.
