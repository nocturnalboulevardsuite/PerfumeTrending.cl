# Arquitectura de Confiabilidad de Datos — PerfumeTrending.cl

Este documento describe las reglas deterministas de frescura, resolución de volúmenes, deduplicación de entidades, detección de precios atípicos y observabilidad continua del motor ETL de **PerfumeTrending.cl**.

---

## 1. Política de Frescura de Ofertas (Umbrales 3 / 7 / 14 días)

Ninguna oferta cuya verificación haya quedado rezagada se presenta como precio vigente sin advertencia. Los umbrales son parametrizables en [`APP/backend/database.py`](../APP/backend/database.py):

| Antigüedad (`now - ultima_verificacion_exitosa`) | Estado de Frescura | Comportamiento en UI y Ranking |
|---|---|---|
| **≤ 3 días** (`FRESCURA_FRESCO_DIAS = 3`) | `fresco` | Visualización normal; participa en **«Mejor precio»**, **«Mínimo histórico»** y **«Desde \$X»** del catálogo. |
| **3 – 7 días** (`FRESCURA_ADVERTENCIA_DIAS = 7`) | `reciente` | Muestra badge discreto *«Precio verificado hace N días»*. Participa en comparador con advertencia. |
| **7 – 14 días** (`FRESCURA_MAX_VISIBLE_DIAS = 14`) | `desactualizado` | Muestra badge ámbar *«Precio sin reverificar (hace N días)»* y queda **excluida** de **«Mejor precio»**, **«Mínimo histórico»** y del **«Desde \$X»** del catálogo. |
| **> 14 días** | `oculto` | Se oculta del comparador y del catálogo público hasta volver a verificarse en vivo. |

### Retiro por Ausencia Sostenida vs. Inmunidad WAF
En `registrar_fallo_scraping()`:
- Solo el código controlado `no_encontrado_en_feed` incrementa `fallos_consecutivos` hacia el retiro automático: al alcanzar **`MAX_FALLOS_AUSENCIA_FEED = 5`** corridas consecutivas ausente, la oferta pasa a `estado = 'agotada'` y `en_stock = False`.
- Los códigos transitorios (`waf`, `timeout`, `parse_error`) **nunca** incrementan `fallos_consecutivos` ni apagan stock.

---

## 2. Regla Estricta de Resolución de Volumen (Sin Default `100 ml` Inventado)

Implementada en `extraer_volumen_ml_opcional()` y `resolver_volumen_oferta()` ([`APP/backend/normalizador.py`](../APP/backend/normalizador.py)):

1. **Orden de precedencia único:**
   1. Título u opción explícita de la variante (`50 ml`, `3.4 oz`, etc.).
   2. Título comercial del producto.
   3. Cola del slug de la URL (decodificando `%20` previamente con `urllib.parse.unquote`).
   4. `volumen_ml_defecto` **únicamente si** el producto tiene **1 sola variante** (`n_variantes_producto <= 1`).
   5. `None` (descarte seguro; se contabiliza en `exclusiones_volumen_ambiguo` / `volumen_ambiguo`).
2. **Guardia de coherencia URL ↔ variante:** si el slug declara un volumen explícito (≥ 25 ml), la variante individual no declara otro tamaño propio y la diferencia supera 1 ml (en formato `regular`), la oferta se descarta antes de persistir.
3. **Reparación verificada en vivo:** [`APP/backend/mantenimiento/reparar_volumenes.py`](../APP/backend/mantenimiento/reparar_volumenes.py) contrasta ofertas sospechosas contra `/products/<handle>.js` o ficha viva exigiendo coincidencia de precio (±3 %) con una única variante antes de reasignar `variante_id` y `precios_registro`.

---

## 3. Estrategia Anti-WAF en Retailers (Falabella, Paris y Ripley)

El experimento empírico [`probe_waf.yml`](../.github/workflows/probe_waf.yml) (`APP/data/reportes/probe_waf.json`) sobre IPs datacenter de GitHub Actions (`ubuntu-latest`) demostró:
- **Falabella:** `requests.Session` obtiene **100 % HTTP 200 y payload `__NEXT_DATA__` válido** (mientras `curl_cffi` desde IP de Actions recibe 403). Por ello, `_peticion_retail_resiliente()` mantiene `requests` como cliente primario en Falabella.
- **Paris y Ripley:** desde IPs datacenter de GitHub Actions sufren bloqueo de borde por reputación de IP/ASN (HTTP 403 tanto en `requests` como en `curl_cffi`), mientras que desde IP residencial chilena con `curl_cffi(impersonate="chrome120")` alcanzan **100 % de extracción válida**.
- **Modos soportados sin cambio de código:**
  1. **Sincronización local desde IP residencial (gratis):** `python APP/backend/mantenimiento/sincronizar_retail_local.py --apply --stores Paris,Ripley --limit 300`.
  2. **Proxy residencial opcional:** definir `RETAIL_PROXY_URL` en variables de entorno / GitHub Secrets.
  3. **Cortocircuito limpio en Actions (`WAF_FAST_FAIL_THRESHOLD = 15`):** evita golpear innecesariamente el CDN tras confirmar bloqueo por IP en un lote, degradando con transparencia mediante los badges de frescura de Fase 1.

---

## 4. Deduplicación en Origen y Flujo de Fusión Segura

1. **Clave canónica sin género:** `(marca_canonica, nombre_limpio, concentracion)` junto con `ALIAS_MARCA` declarativo (`Giorgio Armani` ← `Emporio Armani`/`Armani`, `Yves Saint Laurent` ← `YSL`/`Saint Laurent`, `Lancôme` ← `Lancome`, etc.).
2. **Compatibilidad de géneros (`generos_compatibles`):**
   - `Unisex` + `Hombre` → `Hombre`; `Unisex` + `Mujer` → `Mujer`.
   - `Hombre` vs `Mujer` → **jamás se fusiona automáticamente** (protege pares legítimos *Pour Homme* vs *Pour Femme* como *Light Blue*, *Eros*, *Fakhar*, *Cool Water*, exportándolos a `scratch/revision_manual_duplicados.csv`).
3. **CLI de fusión transaccionalmente segura:** [`APP/backend/mantenimiento/fusionar_perfumes.py`](../APP/backend/mantenimiento/fusionar_perfumes.py) (`--dry-run` por defecto, `--apply` para ejecutar):
   - Reasigna y deduplica las 6 tablas dependientes de `perfumes(id)`: `favoritos_usuario` (`UNIQUE(usuario_id, perfume_id)`), `perfume_notas`, `perfume_familias_olfativas`, `perfume_notas_importacion`, `variantes_perfume` (junto con `ofertas_actuales` respetando `UNIQUE(variante_id, tienda_id)`) y `precios_registro`.
   - Consolida subgrupos del mismo género (`Hombre` + `Hombre`, `Mujer` + `Mujer`) incluso dentro de líneas que coexisten en ambas versiones, sin mezclar jamás `Hombre` con `Mujer`.
   - Verifica explícitamente **0 referencias residuales** antes de borrar el perfume donante y audita el historial en `fusiones_perfumes` y `APP/data/reportes/historial_fusiones.json`.

---

## 5. Taxonomía de Fallos, Outliers de Precio y Observabilidad CI

1. **Códigos de fallo controlados (`CODIGOS_FALLO_CONTROLADOS`):**
   `no_encontrado_en_feed`, `waf`, `timeout`, `parse_error`, `marca_excluida`, `volumen_ambiguo`, `entidad_no_coincide` — desglosados por tienda en `estadisticas_tiendas[tienda]["fallos_por_codigo"]`.
2. **Precios atípicos (`detectar_precios_atipicos` y `detectar_outliers_bd.py`):**
   - Con ≥ 4 ofertas activas en la misma variante: marca `estado = 'requiere_revision'` si `precio < 0,5 × mediana` o `precio > 2,2 × mediana`.
   - En cualquier tamaño: marca `estado = 'requiere_revision'` todo `tester` cuyo precio supere la mediana (o precio en la misma tienda) de la versión `regular` sellada.
3. **Cómo leer el Reporte de Salud en GitHub Actions:**
   - Al finalizar cada shard de [`scraper_nocturno.yml`](../.github/workflows/scraper_nocturno.yml), [`resumen_salud_ci.py`](../APP/backend/mantenimiento/resumen_salud_ci.py) publica en **`$GITHUB_STEP_SUMMARY`** la tabla por tienda con consultas, % de éxito en vivo (excluyendo ausentes del feed), % WAF, principales códigos de fallo y stock >3d / >7d.
   - Si una tienda cae bajo **20 % de éxito efectivo**, emite un `::warning::` visible en el resumen del run **sin hacer fallar el workflow**.
   - Todos los domingos (`08:30 UTC`), [`auditoria_enlaces.yml`](../.github/workflows/auditoria_enlaces.yml) audita 1.000 enlaces activos con histéresis de **2 strikes consecutivos** antes de desactivar cualquier 404/soft-404, ignorando siempre `403/429/timeout`.

---

## 6. Resumen de Indicadores de Calidad (Antes vs. Después)

| Indicador Operativo | Línea Base (Antes) | Resultado Verificado (Después) | Meta del Plan |
|---|---:|---:|---:|
| **Incoherencia URL ↔ Volumen en BD** | `14,3 %` (`2.269 / 15.821`) | **`0,1 %`** (`16 / 12.945`) | `< 0,5 %` |
| **Grupos de perfumes duplicados fusionables** | `129` grupos (`3.814` perfumes) | **`0` grupos** (`142` duplicados fusionados → `3.672` perfumes) | `0` grupos |
| **Enlaces activos válidos (excluyendo WAF)** | `98,05 %` | **`99,46 %`** (`913 / 918` HTTP 200 OK) | `≥ 99,0 %` |
| **Imágenes rotas o placeholders Unsplash en catálogo** | `20` (`6` HTTP 404 + `14` Unsplash) | **`0`** (`9` re-hospedadas en `IMG_perfumes` + `11` SVG limpio) | `0` |
| **Precios atípicos aislados (`requiere_revision`)** | Sin aislamiento (`0`) | **`402` ofertas aisladas** del ranking público | Activo |
| **Cobertura de tests automatizados** | `82` tests | **`155` tests (`100 % OK`)** | `100 % OK` |


