# PerfumeTrending.cl — Informe de Compatibilidad Python y Scrapers

---

## 1. Auditoría de Contratos de Python

Se analizaron todos los puntos de integración entre la capa de acceso a datos (`database.py`), los scrapers (`scraper_periodico.py`, `scraper_autonomo.py`, `sincronizar_precios_reales.py`) y la aplicación Streamlit (`app.py`, `pages/*.py`).

### 1.1. Contrato `registrar_observacion_oferta`
Firma implementada:
```python
def registrar_observacion_oferta(observacion: dict) -> dict:
    """
    Persistencia atómica de una observación de precio/stock:
    - Valida precio positivo, stock explícito y formato de URL.
    - Actualiza ofertas_actuales e inserta precios_registro en una sola transacción.
    - Soporta ejecución en Supabase (RPC) y fallback transaccional en SQLite.
    """
```
- **Campos esperados:** `variante_id`, `tienda_id`, `precio_actual`, `precio_normal`, `en_stock`, `url_producto`, `scraping_run_id` (opcional), `perfume_id` (para retrocompatibilidad).
- **Validaciones aplicadas antes de persistir:**
  - `precio_actual > 0`
  - `precio_normal is None or precio_normal > 0`
  - `en_stock is not None` (debe ser booleano estricto)
  - `url_producto` debe iniciar con `http://` o `https://` y pertenecer al dominio autorizado de la tienda.

### 1.2. Contrato `registrar_fallo_scraping`
Firma implementada:
```python
def registrar_fallo_scraping(
    tienda_id: int,
    mensaje: str,
    variante_id: Optional[int] = None,
    perfume_id: Optional[int] = None
) -> dict:
    """
    Registra el fallo de extracción sin alterar los precios, stock ni URLs confirmadas.
    """
```
- No modifica `precio_actual`, `precio_normal` ni `en_stock` de las ofertas confirmadas.
- Registra el intento fallido e incrementa `fallos_consecutivos`.

---

## 2. Ajustes Realizados en Scrapers

1. **`scraper_periodico.py`**:
   - Se eliminó el bloque de fallback que insertaba precios inventados/respaldados cuando la petición fallaba.
   - En su lugar, cuando `datos_extraccion.get("exito")` es `False`, se invoca `registrar_fallo_scraping`.
   - Se reemplazó el hardcoding de `"en_stock": True` en Falabella, Paris y Ripley por analizadores que detectan texto `"Agotado"`, `"Sin stock"`, disponibilidad en Schema.org (`OutOfStock` vs `InStock`), o marcan `en_stock = False` cuando corresponde.
2. **`scraper_autonomo.py`**:
   - Desacoplado para utilizar `registrar_observacion_oferta`.
   - Valida que los precios extraídos de Shopify (`price > 0`) correspondan a productos en stock real (`available`).
