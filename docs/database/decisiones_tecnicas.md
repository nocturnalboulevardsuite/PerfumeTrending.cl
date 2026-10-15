# PerfumeTrending.cl — Registro de Decisiones de Arquitectura (ADR)

---

## ADR 001: Persistencia Transaccional Atómica (Oferta + Historial)
- **Contexto:** Anteriormente, los scrapers insertaban registros independientes en `precios_registro` sin garantizar atomicidad ni deduplicación. Si ocurría un fallo de red o error de inserción a mitad de proceso, la base de datos quedaba en estado inconsistente.
- **Decisión:** Toda actualización de precio/stock debe realizarse de forma atómica en una sola transacción:
  1. Adquirir lock exclusivo de la fila en `ofertas_actuales` (`FOR UPDATE`).
  2. Comparar campos (`precio_actual`, `precio_normal`, `en_stock`, `url_producto`).
  3. Si no hay cambios, solo actualizar timestamp de verificación (`sin_cambios`).
  4. Si hay cambios confirmados o es una observación inicial, actualizar `ofertas_actuales` e insertar simultáneamente el evento en `precios_registro`.
  5. Si el insert en `precios_registro` falla, la transacción completa se revierte.
- **Consecuencias:** Se eliminan carreras de concurrencia, duplicados de ofertas e inconsistencias entre la oferta viva y el historial.

---

## ADR 002: Prohibición de Precios o Stock Sintéticos ante Fallos de Scraping
- **Contexto:** En la versión anterior de `scraper_periodico.py`, cuando una tienda retornaba 403, 429, 404 o timeout, el código ejecutaba un bloque `else:` que re-insertaba el último precio conocido con `en_stock=True`, haciendo pasar un fallo técnico como una confirmación en vivo.
- **Decisión:** Los fallos técnicos (errores de red, bloqueos, CAPTCHA, selectores desactualizados) son tratados como anomalías de extracción:
  - Nunca actualizan `precio_actual`, `en_stock` ni `url_producto`.
  - Incrementan el contador `fallos_consecutivos` en `ofertas_actuales`.
  - Se audita el mensaje de error en `ultimo_error` y en `scraping_runs` / `scraping_logs`.
  - El stock se preserva en su último estado confirmado; jamás se declara agotado ni disponible por una falla de conexión.
- **Consecuencias:** Integridad absoluta de las métricas de precios. Cero datos inventados.

---

## ADR 003: Tratamiento Semántico de Stock (`NULL` vs `FALSE` vs `TRUE`)
- **Contexto:** Confundir producto agotado con producto desconocido o no disponible para scraping causa pérdida de confianza en los compradores.
- **Decisión:**
  - `en_stock = TRUE`: La tienda confirma inventario disponible para compra inmediata.
  - `en_stock = FALSE`: La tienda confirma explícitamente que el producto está agotado / sin stock.
  - `en_stock = NULL`: La tienda no informa el estado de inventario o la ficha es ambigua. No se asume agotado ni disponible.
- **Consecuencias:** Transparencia con el usuario. Las ofertas con stock desconocido requieren verificación antes de recomendarse.

---

## ADR 004: Modelo Híbrido PostgreSQL (Supabase) + SQLite (Resiliencia Local)
- **Contexto:** PerfumeTrending opera como una aplicación de alta disponibilidad en Streamlit Cloud. Supabase es la fuente primaria en la nube, pero ante cortes de red o agotamiento de cuotas, la plataforma no debe caerse.
- **Decisión:** Mantener una capa DAO dual en `APP/backend/database.py`:
  - Cada método intenta ejecutar la operación en Supabase vía cliente oficial o RPC.
  - Si Supabase no está disponible, conmuta limpiamente a SQLite local en modo WAL con integridad transaccional idéntica.
- **Consecuencias:** Zero-downtime para lectura y visualización en la interfaz de usuario.

---

## ADR 005: Catálogo de Notas Idempotente con Slugs Estables
- **Contexto:** La migración de notas olfativas debe ser reproducible y tolerante a re-ejecuciones sin generar duplicados.
- **Decisión:** Usar `slug` en kebab-case como clave unívoca natural en `familias_notas` y `notas_olfativas`. Las inserciones usan cláusulas `ON CONFLICT (slug) DO UPDATE` fusionando sinónimos mediante `array_agg(DISTINCT)`.
- **Consecuencias:** Seeds 100% seguros de re-ejecutar sin corromper relaciones de perfumes.
