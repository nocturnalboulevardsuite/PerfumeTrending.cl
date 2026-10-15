# PerfumeTrending.cl — Informe de Historial No Mapeable y Auditoría de Datos

---

## 1. Diagnóstico de Registros en `precios_registro`

Durante la auditoría del esquema conectado en Supabase se analizaron los 460 registros históricos de `precios_registro`:

1. **Registros con `volumen_ml` ausente o inválido (`<= 0` o `NULL`):**
   - **Resultado:** 0 registros encontrados.
   - El 100% de las filas existentes posee un valor numérico válido en `volumen_ml` (predominantemente 100, 50, 75 o 200 ml).
2. **Registros con `precio_actual <= 0`:**
   - **Resultado:** 0 registros encontrados.
3. **Registros con `en_stock` nulo:**
   - **Resultado:** 0 registros encontrados.
4. **Pares huérfanos sin tienda o perfume asociado:**
   - **Resultado:** 0 registros huérfanos. Todas las claves foráneas apuntan a filas válidas en `perfumes` y `tiendas`.

---

## 2. Protocolo para Registros Ambiguos durante la Migración

Si durante futuras ingestas o migración masiva se detectan registros ambiguos:
1. **Regla de No Forzar Mapeo:**
   Si una observación histórica no cuenta con volumen o la URL no permite distinguir la presentación, el campo `variante_id` en `precios_registro` permanece como `NULL`.
2. **Preservación Obligatoria:**
   Bajo ninguna circunstancia se borran registros de `precios_registro` por falta de `variante_id`.
3. **Consulta de Monitoreo:**
   ```sql
   SELECT COUNT(*) AS pendientes_de_mapeo
   FROM public.precios_registro
   WHERE variante_id IS NULL;
   ```
4. **Resolución:**
   Los casos con `variante_id IS NULL` se reportan en el panel de auditoría ETL para revisión manual o asignación asistida por SKU de la tienda.
