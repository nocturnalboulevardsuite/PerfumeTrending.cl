# BIBLIA TÉCNICA, COMERCIAL Y DE DEFENSA — PerfumeTrending.cl
**Documento Maestro Integral: La Verdad Completa del Código, Arquitectura, Scraper de 2 Velocidades, Normalizador de 12 Capas, Base de Datos Dual (Supabase vs. SQLite), Metodología en Cascada, Cifras de Mercado, Simulación Monte Carlo, Marco Legal y Glosario Oficial**

*Portafolio de Título 2026 (APT122 / Capstone) — Duoc UC Sede San Joaquín*  
*Equipo Desarrollador:*
* **Diego Medina:** Backend y Frontend (Motores de Scraping Periódico y Autónomo, Normalizador Determinista de 12 Capas, Persistencia Transaccional en Supabase/SQLite, Hype Radar con YouTube Data API).
* **Benjamín Espinoza:** Frontend y Backend (Arquitectura visual en Streamlit, experiencia de usuario UX/UI, vistas interactivas y maquetación).
* **Alonso Moreno:** Frontend, Documentación Técnica e Investigación (SRS, Diseño UML/DER/DFD, Plan de Pruebas, Manual Técnico, diseño del Trust Score y Simulación Financiera Monte Carlo).

---

## ÍNDICE GENERAL DEL DOCUMENTO
1. [Contexto Comercial y Problema Real en Chile (Las Cifras Oficiales de la Defensa)](#1-contexto-comercial-y-problema-real-en-chile-las-cifras-oficiales-de-la-defensa)
2. [Herramientas y Tecnologías Utilizadas (El Stack 100% Gratuito y Por Qué cada una)](#2-herramientas-y-tecnologías-utilizadas-el-stack-100-gratuito-y-por-qué-cada-una)
3. [La Verdad sobre SQLite vs. Supabase: ¿Por qué existen los dos y cómo interactúan?](#3-la-verdad-sobre-sqlite-vs-supabase-por-qué-existen-los-dos-y-cómo-interactúan)
4. [El Scraper por Dentro: ¿Es solo Actualizador o también es Buscador/Descubridor?](#4-el-scraper-por-dentro-es-solo-actualizador-o-también-es-buscadordescubridor)
5. [¿Cómo es posible auditar 3.364 perfumes en 16 tiendas sin tardar días? (Arquitectura de 2 Velocidades)](#5-cómo-es-posible-auditar-3364-perfumes-en-16-tiendas-sin-tardar-días-arquitectura-de-2-velocidades)
6. [El Cerebro del Sistema: El Normalizador Determinista de 12 Capas y la Guía Química Olfativa](#6-el-cerebro-del-sistema-el-normalizador-determinista-de-12-capas-y-la-guía-química-olfativa)
7. [Modelo de Datos Relacional en Supabase, Persistencia Transaccional y Outliers](#7-modelo-de-datos-relacional-en-supabase-persistencia-transaccional-y-outliers)
8. [Los 3 Pilares Funcionales: Comparador/Remates, Trust Score y Hype Radar](#8-los-3-pilares-funcionales-comparadorremates-trust-score-y-hype-radar)
9. [Gestión del Proyecto e Ingeniería de Software (Cascada, SRS, Carta Gantt, Ruta Crítica CPM/PERT)](#9-gestión-del-proyecto-e-ingeniería-de-software-cascada-srs-carta-gantt-ruta-crítica-cpmpert)
10. [Modelo de Negocio Freemium, Planes y Simulación Financiera Monte Carlo](#10-modelo-de-negocio-freemium-planes-y-simulación-financiera-monte-carlo)
11. [Marco Legal, Ético y Protección de Datos en Chile (Leyes 19.496, 21.398, 19.628 y 21.719)](#11-marco-legal-ético-y-protección-de-datos-en-chile-leyes-19496-21398-19628-y-21719)
12. [Estructura Completa del Código del Proyecto (Mapa Archivo por Archivo)](#12-estructura-completa-del-código-del-proyecto-mapa-archivo-por-archivo)
13. [Banco Completo de Preguntas del Jurado y Respuestas Ganadoras](#13-banco-completo-de-preguntas-del-jurado-y-respuestas-ganadoras)

---

## 1. Contexto Comercial y Problema Real en Chile (Las Cifras Oficiales de la Defensa)

### Los 3 Problemas del Consumidor Chileno
Comprar perfumes por internet en Chile presenta tres dolores concretos:
1. **Precios dispersos (Asimetría de precios de hasta +100%):** Un mismo perfume original sellado tiene precios radicalmente distintos según la tienda (por ejemplo, *Armaf Odyssey Spectra EDP 100 ml* cuesta **$19.990 CLP** en Chile Perfume, **$22.900 CLP** en Paris Marketplace y ComprarEnChile, **$27.990 CLP** en Ripley y **$29.890 CLP** en Falabella; mientras que en otros perfumes de diseñador la diferencia supera los **$45.000 CLP** por el mismo frasco).
2. **Tiendas dudosas y temor a falsificaciones (Asimetría de información):** Al comprador le cuesta distinguir qué perfumería online independiente es legítima y cuál vende réplicas o incumple entregas.
3. **Perfumes virales que cambian de precio o se agotan rápido:** Las tendencias en redes sociales (TikTok/YouTube) disparan la demanda de fragancias específicas (especialmente perfumería árabe), agotando el stock o inflando sus precios en pocos días.

### Las 6 Cifras Clave del Mercado Chileno (Para memorizar en la defensa)
*(Fuentes secundarias: 24 Horas, Canal 13, Meganoticias, La Tercera, SERNAC y Servicio Nacional de Aduanas)*
* **US$261 millones:** Tamaño del mercado de perfumería en Chile en 2024, creciendo desde **US$155 millones en 2020** (**+68% de crecimiento**).
* **US$2.128 millones:** Volumen de importaciones del sector cosmética y perfumería durante 2025.
* **250 tiendas:** Cantidad estimada de tiendas de perfumes solo en la Región Metropolitana (**+50%** de crecimiento desde 2019).
* **9 tiendas oficiadas por SERNAC:** Concentran cerca de **100 reclamos formales** por venta de perfumes presuntamente falsos, demoras extremas o incumplimiento de garantías.
* **+125% de aumento en incautaciones:** Incremento reportado por **Aduanas** en el decomiso de perfumes falsificados que intentaban ingresar al país.
* **37,5% de las ventas son Perfumes Árabes:** En perfumerías especializadas chilenas como *Silk Perfumes*, el **37,5%** de las ventas ya corresponde a **perfumería árabe** (marcas de Medio Oriente como *Lattafa, Armaf, Afnan, Al Haramain, Rasasi, Maison Alhambra*), que destacan por su alta concentración, duración y precios accesibles.

---

## 2. Herramientas y Tecnologías Utilizadas (El Stack 100% Gratuito y Por Qué cada una)

Una de las mayores fortalezas de factibilidad técnica y económica del proyecto es que **el 100% de las herramientas utilizadas son gratuitas o se ejecutan dentro de su capa gratuita (*Free Tier*)**:

| Herramienta / Tecnología | Rol en PerfumeTrending.cl | ¿POR QUÉ se eligió esta herramienta y no otra? |
| :--- | :--- | :--- |
| **Python 3.11+** | Lenguaje unificado de Backend, Scraping, Normalización y Frontend. | Permite escribir todo el proyecto en un solo lenguaje, con soporte nativo para expresiones regulares (`re`), multihilo (`ThreadPoolExecutor`) y ciencia de datos. |
| **Streamlit + CSS3/HTML5 Inyectado** | Frontend interactivo y servidor web (`APP/app.py`, `APP/pages/`). | Permite crear interfaces web modernas sin dividir el equipo en dos stacks distintos (React + Node). Se personalizó con CSS avanzado (*Tema Claro / Oscuro*). |
| **Streamlit Community Cloud** | Hosting / Despliegue en producción (`perfumetrending-cl.streamlit.app`). | Se conecta directamente a la rama `main` de GitHub: cada `git push` actualiza la página en vivo automáticamente (**CI/CD continuo sin costo de servidor**). |
| **Supabase Cloud (PostgreSQL 15+)** | Base de datos relacional principal en la nube y almacenamiento de imágenes (`IMG_perfumes`). | Entrega un motor PostgreSQL empresarial gratuito en la nube, accesible simultáneamente por los 3 integrantes del equipo, por la web y por GitHub Actions, con API REST (**PostgREST**), funciones transaccionales (**PL/pgSQL**) y seguridad **RLS**. |
| **SQLite 3 (Modo WAL)** | Base de datos local en un solo archivo (`perfumetrending.db`). | Se utilizó en la etapa inicial del proyecto, se mantiene como base de datos aislada para correr las **158 pruebas unitarias** sin ensuciar producción y actúa como respaldo (*failover*) si falla la conexión a la nube. |
| **`curl_cffi` (`chrome120` / `chrome124`)** | Cliente HTTP con impersonación criptográfica TLS. | Los firewalls anti-bot (**Cloudflare / Akamai WAF**) de tiendas como Ripley o Paris detectan el saludo TLS de Python normal y lo bloquean con `HTTP 403`. `curl_cffi` clona la huella TLS de un navegador Google Chrome real en milisegundos. |
| **`requests` + `urllib3.Retry` + `BeautifulSoup4`** | Descarga HTTP resiliente y parseo del árbol DOM HTML. | Mantiene un pool de conexiones reutilizables con reintentos exponenciales automáticos y extrae los bloques JSON ocultos (`__NEXT_DATA__` y `Schema.org JSON-LD`). |
| **GitHub + GitHub Actions** | Control de versiones (`Git`) y automatización de robots en la nube. | Ejecuta gratis los 4 workflows automáticos: `scraper_nocturno.yml` (diario en 4 Shards), `auditoria_enlaces.yml` (semanal), `keep_alive.yml` (cada 6h) y `probe_waf.yml`. |
| **YouTube Data API v3** | Fuente de datos sociales para el **Hype Radar** (`APP/hype_youtube.py`). | Es la única API oficial gratuita, pública y estable para medir videos, vistas, likes y comentarios de reseñas de perfumes en español (a diferencia de TikTok o Instagram, cuyas APIs son cerradas o de alto costo comercial). |
| **Docker / Docker Compose** | Contenedorización reproducible (`Dockerfile`, `docker-compose.yml`). | Opcional para desarrollo local: empaqueta Python 3.11 y todas las dependencias de `requirements.txt` en una imagen que funciona idéntico en cualquier computador en el puerto `8501`. |

---

## 3. La Verdad sobre SQLite vs. Supabase: ¿Por qué existen los dos y cómo interactúan?

Esta respuesta debe quedar clarísima para toda la comisión evaluadora:

1. **¿Por qué pasamos de SQLite a Supabase?**
   * Al inicio del proyecto (Fase 1), prototipamos con **SQLite** porque guarda todo en un solo archivo local y no requiere configuración de servidores.
   * Sin embargo, para trabajar en equipo entre los tres (Diego, Benjamín y Alonso), desplegar la aplicación en **Streamlit Community Cloud** y permitir que los robots de **GitHub Actions** actualizaran los precios desde la nube todos los días, necesitábamos una base de datos centralizada en línea.
   * Por eso migramos a **Supabase (PostgreSQL en la nube)** mediante el generador `APP/backend/generar_sql_supabase.py` y las migraciones de `supabase/migrations/`.
2. **¿Con cuál funciona la página web hoy?**
   * **La página web en producción y los GitHub Actions funcionan 100% con Supabase Cloud.**
3. **¿Por qué mantuvimos el código de SQLite dentro de `database.py` en vez de borrarlo?**
   * Por **dos razones de calidad de software**:
     * **Pruebas Unitarias Seguras:** Nuestra suite de **158 tests automatizados** (`tests/`) prueba inserciones, borrados, fusiones y fallos de scraping. Gracias al soporte SQLite, los tests se ejecutan con `SUPABASE_DISABLE=1` sobre una base SQLite temporal sin tocar ni alterar un solo dato real de Supabase.
     * **Tolerancia a Fallos (*Failover*):** Si algún día Supabase tiene una caída temporal o un desarrollador corre el proyecto sin internet, `database.py` detecta que Supabase no responde y cambia automáticamente a SQLite local en modo **WAL (`Write-Ahead Logging`)** para que el sistema nunca se caiga.

---

## 4. El Scraper por Dentro: ¿Es solo Actualizador o también es Buscador/Descubridor?

**El sistema hace AMBAS cosas.** No es una lista fija escrita a mano; es un ecosistema vivo compuesto por **dos motores de scraping** más un **auditor de enlaces**:

### Motor 1: El Buscador / Autodescubridor de Catálogo (`APP/backend/scraper_autonomo.py`)
* **¿Qué hace?** Explora automáticamente las tiendas chilenas para **descubrir perfumes nuevos** que aún no existen en nuestra base de datos.
* **¿Cómo funciona?**
  1. Recorre los endpoints públicos de catálogo completo de las **13 perfumerías especializadas**:
     * **10 Tiendas Shopify** (`/products.json?limit=250&page=N`): *Silk Perfumes, Elite Perfumes, Alisha Perfumes, Yauras Perfumes, Oferta Perfumes, L'Odoro, Mundo Aromas, Cosmetic, Fragante y ComprarEnChile*.
     * **3 Tiendas WooCommerce** (`/wp-json/wc/store/v1/products`): *Chile Perfume, Portal del Perfume y Aromata*.
  2. Por cada producto encontrado, aplica el **Normalizador (`normalizador.py`)**: descarta productos que no sean perfumes (cremas, desodorantes, decants, sets), unifica la marca canónica (`normalizar_marca_canonica`), limpia el nombre comercial (`limpiar_nombre_perfume`), extrae su género (`Hombre`, `Mujer`, `Unisex`), concentración (`EDP`, `EDT`, `Parfum`, `EDC`) y detecta automáticamente si es un **perfume árabe (`es_arabe=True`)**.
  3. Verifica si ese perfume ya existe en la tabla `perfumes`. Si es nuevo, **lo crea automáticamente en Supabase**, sube su foto al bucket CDN `IMG_perfumes` y registra sus variantes de volumen (`ml`) y su precio inicial.
* **¿Cómo se ejecuta?**
  * Se puede ejecutar bajo demanda (`python APP/backend/scraper_autonomo.py`) y además **corre integrado dentro de `scraper_periodico.py` (`--descubrir`)** reutilizando los ~38.670 productos ya descargados en memoria RAM.

### Motor 2: El Actualizador Periódico + Buscador Interno en Retail (`APP/backend/scraper_periodico.py`)
* **¿Qué hace?** Toma los **3.364 perfumes** del catálogo maestro y actualiza diariamente sus precios, variantes de volumen (`30 ml`, `50 ml`, `60 ml`, `100 ml`, `150 ml`, `200 ml`), formato (`regular` vs `tester`) y disponibilidad de stock en las **16 tiendas activas** (las 13 especializadas + **Falabella, Paris y Ripley**).
* **¿Cómo funciona su Buscador Interno de Auto-Sanación (*Self-Healing*) en Paris, Falabella y Ripley?**
  * Antes existía un filtro que asumía que el retail tradicional no vendía perfumes árabes. **Eliminamos esa restricción** porque hoy **Paris, Falabella y Ripley sí venden perfumería árabe** (tanto directo como a través de su Marketplace).
  * Para cada perfume (árabe o de diseñador) en Paris, Falabella y Ripley, el scraper aplica una estrategia de **2 pasos**:
    1. **Intento 1 (Verificación de URL Directa):** Si ya teníamos guardada la URL del producto en esa tienda, entra directo a verificar su precio y stock actual.
    2. **Intento 2 (Búsqueda Dinámica en Vivo):** Si no teníamos URL en esa tienda, o si la URL vieja murió (`HTTP 404`), o si esa publicación específica se quedó **sin stock (`en_stock=False`)**, el scraper **consulta automáticamente el buscador interno de la tienda** (`paris.cl/search?q=...`, `falabella.com/.../search?Ntt=...`, `simple.ripley.cl/search/...`).
    3. Revisa los productos encontrados, los pasa por las **12 capas del normalizador**, compara precios entre los distintos vendedores del Marketplace que tengan stock activo y **actualiza automáticamente la oferta con el nuevo enlace vivo y el precio más económico**.

---

## 5. ¿Cómo es posible auditar 3.364 perfumes en 16 tiendas sin tardar días? (Arquitectura de 2 Velocidades)

Cruzar **3.364 perfumes × 16 tiendas = 53.824 verificaciones**. Hacer 53.824 consultas web una por una tardaría más de 40 horas. Lo resolvimos con una **Arquitectura Híbrida de Dos Velocidades**:

### Velocidad 1: Precarga Masiva en Memoria RAM (*Bulk In-Memory*) — 13 Tiendas en ~22 Segundos
* Las 13 perfumerías especializadas usan **Shopify** o **WooCommerce**.
* En vez de consultarlas perfume por perfume, al inicio del ciclo la función `precargar_catalogos_bulk_tiendas()` descarga en paralelo los **38.670 productos** de las 13 tiendas en **~22 segundos** y los indexa en la memoria RAM (`CatalogoTiendaBulk`).
* Luego, buscar cada uno de los 3.364 perfumes en esas 13 tiendas se hace **100% en memoria RAM en menos de 0,5 milisegundos**, sin hacer peticiones HTTP individuales y sin saturar los servidores de las tiendas.

### Velocidad 2: Extracción Quirúrgica de JSON Oculto en Retail (Falabella, Paris y Ripley)
* Como Falabella, Paris y Ripley venden millones de artículos de todo tipo, no tienen un archivo único de perfumes.
* Para ellos usamos concurrencia (`ThreadPoolExecutor`) y **no leemos el diseño visual CSS** (que cambia constantemente), sino los **contratos de datos JSON ocultos dentro del HTML**:
  * **En Falabella (`extraer_variedades_falabella`):** Extrae la etiqueta `<script id="__NEXT_DATA__">` generada por Next.js. De ahí obtiene la lista de `variants`/`skus`, sus atributos de volumen (`size`), el precio oferta (`internetPrice`/`eventPrice`), el precio normal (`normalPrice`), el stock real y el vendedor (`sellerName`).
  * **En Paris (`extraer_variedades_paris`):** Extrae los bloques `<script type="application/ld+json">` (**Schema.org Product**). Lee la lista completa de `offers` (tomando `min(precios_validos)` como precio oferta vigente y `max(precios_validos)` como precio normal) y evalúa hasta 5 publicaciones del buscador de Paris para elegir siempre la oferta en stock más barata de cada tamaño (`ml`).
  * **En Ripley (`extraer_variedades_ripley`):** Utiliza `curl_cffi` con huella TLS de Chrome 124 para leer `<script id="__NEXT_DATA__">`, cruza los enlaces SEO reales del DOM HTML (`<a href="/...-mpm...">` y `...p`), verifica el nombre de la tienda en Marketplace (`shop.shopName`) y, si el sufijo de concentración (`EDP`/`EDT`) diluye la búsqueda en el motor de Ripley, reintenta automáticamente con el nombre limpio del perfume.

### Aceleradores Adicionales: Cola LRU, Sharding 4x y Circuit Breaker
* **Cola LRU (*Least Recently Used*):** Ordena los perfumes por `ultima_verificacion_exitosa ASC` para auditar primero los que llevan más tiempo sin actualizarse.
* **Horizontal Sharding (4 Shards en GitHub Actions):** El workflow `scraper_nocturno.yml` levanta **4 máquinas virtuales en paralelo** (`Shard 1/4, 2/4, 3/4 y 4/4`). Cada máquina procesa un cuarto exacto del catálogo (`idx % 4 == shard - 1`).
* **Circuit Breaker (`circuit_breaker_retail.json`):** Si un perfume sin URL previa no se encuentra en un retailer tras 3 intentos seguidos, entra en enfriamiento (*cooldown*) por 7 días antes de hacer un reintento (*Half-Open*).

---

## 6. El Cerebro del Sistema: El Normalizador Determinista de 12 Capas y la Guía Química Olfativa

### Guía Química Olfativa: ¿Por qué no es lo mismo un EDT, un EDP, una Colonia o un "Elixir"?
*(Contenido oficial de la Diapositiva 11 de la presentación)*
La diferencia real entre los tipos de perfume es el **porcentaje de esencia aromática disuelta en alcohol**:
* **EDC (*Eau de Cologne* / Colonia):** `2% a 5%` de esencia $\rightarrow$ Dura `1 a 2 horas`.
* **EDT (*Eau de Toilette*):** `5% a 15%` de esencia $\rightarrow$ Dura `3 a 5 horas`.
* **EDP (*Eau de Parfum*):** `15% a 20%` de esencia $\rightarrow$ Dura `5 a 8 horas`.
* **Parfum / Extrait de Parfum:** `20% a 40%` de esencia $\rightarrow$ Dura `8 horas o más`.
* **Mito vs. Realidad de *"Elixir"*, *"Intense"*, *"Absolu"* o *"Extreme"*:** **«Elixir» NO es una concentración química oficial**; es un nombre comercial (*Flanker*) que las marcas agregan para diferenciar una versión con distinta fórmula o notas. Por eso nuestro sistema jamás mezcla un *Sauvage EDT* con un *Sauvage Elixir*, ni un *Lattafa Yara* con un *Yara Candy*.

### Las 12 Capas Deterministas de `APP/backend/normalizador.py`
Antes de aceptar cualquier producto o precio, `normalizador.py` aplica una aduana estricta de **12 validaciones secuenciales**:

1. **Capa 1 — Validador de Rango Comercial de Precio (`es_precio_valido`):** Rechaza precios nulos, menores a **$5.000 CLP**, mayores o iguales a **$1.000.000 CLP** o placeholders de falta de stock (`$999.999` / `$9.999.999`).
2. **Capa 2 — Firewall Léxico Anti-Cosméticos y Accesorios (`es_producto_perfume_valido`):** Bloquea más de 90 palabras ajenas a un perfume: *limpiador facial, gel limpiador, crema, loción corporal, after shave, desodorante, body mist, bruma, hair mist, ambientador, vela, maquillaje, zapatillas, ropa, relojes* y productos medidos en gramos (`g` / `gr`). *(Esto evitó el caso real donde un Limpiador Facial Dior Sauvage de 125 ml a $47.800 CLP se infiltraba como perfume).*
3. **Capa 3 — Filtro Anti-Sets, Combos, Recargas y Decants (< 25 ml):** Bloquea estuches multipieza (`set`, `cofre`, `kit`, `estuche`, `100ml + 10ml`, `2x50ml`, `3 pcs`), botellas de recarga (`refill`, `recarga`) y muestras o decants menores a **25 ml**.
4. **Capa 4 — Detección de Formato (`Regular` vs. `Tester`):** Identifica si el producto es un probador (`tester` / `sin caja`) y lo separa en su propia variante (`formato='tester'`) para no distorsionar el precio del producto sellado (`formato='regular'`).
5. **Capa 5 — Canonización de Marcas (`CANONICAL_BRAND_MAP`):** Normaliza más de 110 variaciones ortográficas (ej. `"Maison Al Hambra"` / `"Alhambra"` $\rightarrow$ `"Maison Alhambra"`, `"Christian Dior"` $\rightarrow$ `"Dior"`).
6. **Capa 6 — Escudo Anti-Clones y Keyword Stuffing:** Bloquea títulos que contienen `"inspirado en"`, `"tipo"`, `"alternativo"`, `"homenaje"`, `"dupe"`, `"imitación"`, `"equivalencia"`, o que colocan otra marca antes de un guion y la marca famosa al final.
7. **Capa 7 — Filtro de Vendedores de Marketplace (`_es_vendedor_marketplace_no_verificado`):** En Marketplaces rechaza vendedores con palabras sospechosas (`imitacion`, `alternativ`, `decant`, `generico`) y autoriza retailers oficiales, tiendas verificadas y perfumería árabe.
8. **Capa 8 — Exigencia de Marca en Nombres Cortos o Genéricos:** Si el perfume tiene un nombre de una sola palabra común (*Terra*, *Adan*, *Romance*, *Pour Homme*), exige que la marca aparezca explícitamente en el título o en la URL.
9. **Capa 9 — Coincidencia de Tokens Nucleares:** Verifica que todas las palabras esenciales del nombre del perfume buscado existan como palabras completas (`\b...\b`) en el título de la tienda.
10. **Capa 10 — Guardia Bidireccional de Flankers Exclusivos (`FLANKERS_EXCLUSIVOS`):** Compara título y URL contra más de 70 términos de flankers (*elixir, intense, parfum, sport, absolu, extreme, prive, black, blue, red, gold, candy, moi, tous, qahwa, blush, spectra, mandarin, limoni, mega, urban*, etc.). Si sobra o falta un flanker, se rechaza.
11. **Capa 11 — Compatibilidad Estricta de Género y Concentración:**
    * **Género:** Impide cruzar perfumes de `Hombre` con `Mujer`.
    * **Concentración:** Impide cruzar `EDT` con `EDP`, `Parfum`, `Elixir` o `EDC/Colonia`.
12. **Capa 12 — Extracción Segura de Volumen (`resolver_volumen_oferta`) y Control de Outliers por Mediana:**
    * Convierte `fl oz` a `ml`, valida que el atributo `size` de Falabella sea un volumen real de perfumería (evitando que tallas de calzado `38` o `37.5` se conviertan en `38 ml` o `375 ml`) y prohíbe inventar `100 ml` cuando un producto tiene varias tallas sin especificar.
    * Al final de cada perfume, `detectar_precios_atipicos()` calcula la **mediana estadística** de los precios en stock del mismo volumen y envía a cuarentena (`estado='requiere_revision'`) cualquier precio atípico extremo.

---

## 7. Modelo de Datos Relacional en Supabase, Persistencia Transaccional y Outliers

### De las 8 Entidades Conceptuales del DER al Esquema de Producción en Supabase
En el Documento de Diseño definimos **8 entidades principales en el DER**: `Usuario`, `Perfume`, `Tienda`, `Precio`, `Trust_Score`, `Hype_Score`, `Alerta` y `Favorito`.
En producción en Supabase, normalizamos el modelo para soportar múltiples tamaños (`ml`), formatos (`regular`/`tester`), notas olfativas canónicas y trazabilidad completa:

1. **`perfumes`**: Catálogo maestro de las **3.364 fragancias únicas** (`id, nombre, marca, genero, tipo, notas, imagen_url, es_arabe, en_tendencia, en_remate, precio_referencia`).
2. **`variantes_perfume`**: Cada presentación física de un perfume (`id, perfume_id, volumen_ml, formato, concentracion, slug`). Desacopla el envase de `50 ml regular`, `100 ml regular`, `100 ml tester`, `200 ml regular`.
3. **`ofertas_actuales`**: Foto en tiempo real con restricción `UNIQUE (variante_id, tienda_id)`. Guarda `precio_actual, precio_normal, en_stock, url_producto, estado ('activa', 'agotada', 'requiere_revision'), ultima_verificacion_exitosa, fallos_consecutivos, ultimo_error`.
4. **`precios_registro`**: Historial de series de tiempo (*Time-Series*). Registra la primera observación y cada cambio confirmado de precio, stock o URL para dibujar la **curva histórica de precios**.
5. **`tiendas`**: Las 17 tiendas con su **Trust Score** y sus 4 pilares desglosados (`puntos_seguridad, puntos_legalidad, puntos_garantia, puntos_reputacion, ssl_seguro, anios_antiguedad, sello_ccs, reclamos_sernac, rut`).
6. **`tendencias_metricas`**: Datos del **Hype Radar** (`perfume_id, menciones_semanales, tasa_crecimiento, score_hype, plataforma='YouTube'`).
7. **`familias_notas` (12 familias), `notas_olfativas` (107 notas canónicas) y `perfume_notas`**: Taxonomía olfativa estructurada con índice GIN de sinónimos.
8. **`usuarios`, `sesiones_usuario`, `favoritos_usuario`, `alertas_precio`, `listas_usuario`**: Gestión segura de cuentas de usuario, favoritos y alertas de baja de precio.
9. **`scraping_runs` y `scraping_logs`**: Trazabilidad completa de cada ejecución automática.

### Persistencia Transaccional Atómica (`registrar_observacion_oferta`)
Cuando el scraper encuentra un precio válido, invoca la función RPC transaccional `registrar_observacion_oferta`:
* Actualiza `ofertas_actuales` e inserta el evento en `precios_registro` **dentro de una sola transacción PostgreSQL**.
* Si el precio no cambió respecto a la última vez, solo refresca `ultima_verificacion_exitosa = now()` y reinicia `fallos_consecutivos = 0`, sin llenar el historial de filas repetidas innecesarias.

---

## 8. Los 3 Pilares Funcionales: Comparador/Remates, Trust Score y Hype Radar

### Pilar 1: Comparador de Precios y Detector de Remates (`compararprecios.py` y `remates.py`)
* Muestra todas las tiendas que venden el perfume ordenadas de menor a mayor precio (primero las que tienen stock disponible).
* Permite filtrar por presentación exacta (`Todos`, `30 ML`, `50 ML`, `60 ML`, `100 ML`, `150 ML`, `200 ML`) y calcula el **Precio por Mililitro (`$/ml`)**.
* **Política de Frescura Honesta:** Si una oferta lleva entre **7 y 14 días** sin poder reverificarse (por ejemplo, por bloqueo WAF en la nube), muestra una advertencia visual y no puede ganar la medalla de *"Mejor Precio"*; si supera los **14 días**, se oculta automáticamente hasta que vuelva a verificarse.
* **Módulo de Remates:** Filtra ofertas activas en stock cuyo descuento real verificado sea **$\ge 15\%$** respecto a su precio normal y mediana de mercado.

### Pilar 2: Trust Score — Índice de Confianza de Tiendas de 0 a 100 (`trustpage.py`)
Combina indicadores públicos verificables en un puntaje de **0 a 100 puntos**:
* **Seguridad Técnica (hasta 25 pts):** Certificado HTTPS/SSL/TLS válido y pasarela de pago formal.
* **Legalidad Tributaria (hasta 25 pts):** RUT empresarial activo y razón social verificable en Chile.
* **Garantía y Postventa (hasta 25 pts):** Políticas públicas de devolución, despacho y canal formal.
* **Reputación y Antigüedad (hasta 25 pts):** Antigüedad del dominio (**WHOIS**), sello CCS y nivel de reclamos ante **SERNAC**.
* *Ejemplos reales de la presentación:* **Falabella: 96 pts**, **Paris: 95 pts**, **Silk Perfumes / L'Odoro: 92 pts**, **Alisha / Chile Perfume: 91 pts**; mientras que una **tienda no auditada o sospechosa obtiene ~38 pts** (etiquetada como *"Riesgo Alto"* con botón de compra bloqueado preventivamente).
* *Limitación declarada:* Es un indicador referencial basado en fuentes públicas, no una garantía legal absoluta.

### Pilar 3: Hype Radar y Hype Score (`hype_youtube.py` y `trendhype.py`)
* Conecta con **YouTube Data API v3** para monitorear cuántos videos, visitas, likes y comentarios reciben los perfumes en canales hispanos de reseñas.
* Calcula la **Tasa de Crecimiento** porcentual $\left(\frac{\text{valor nuevo} - \text{valor anterior}}{\text{valor anterior}} \times 100\right)$ y construye el **Hype Score (0 a 100)** para armar el ranking de fragancias en tendencia.
* *Limitación declarada en el alcance:* Detecta tendencias que ya están ocurriendo en YouTube (no predice el futuro) y utiliza exclusivamente YouTube porque las APIs de TikTok e Instagram son restringidas o de pago corporativo.

---

## 9. Gestión del Proyecto e Ingeniería de Software (Cascada, SRS, Carta Gantt, Ruta Crítica CPM/PERT)

*(Puntos clave del Glosario de Defensa y Diapositiva 5 para preguntas de metodología)*

* **¿Por qué elegimos Metodología en Cascada (*Waterfall*) y no Scrum (Ágil)?**
  * Porque el alcance del proyecto estaba completamente claro desde el inicio, el semestre académico tiene fechas de entrega fijas e inamovibles, y las responsabilidades del equipo estaban claramente divididas. La **Carta Gantt de 13 semanas se cumplió al 100% sin cambios ni atrasos**, demostrando que Cascada fue la elección correcta.
* **Los 4 Entregables Formales de nuestra Cascada:**
  1. **SRS (Especificación de Requisitos de Software):** Compuesto por **19 Requisitos Funcionales (RF)**, **12 Requisitos No Funcionales (RNF)** y **9 Casos de Uso (UC)** (destacando `UC1: Buscar y comparar precios` y `UC7: Actualización automática del catálogo`), con **3 Actores** (*Visitante*, *Usuario Registrado* y *Motor Automático de Scraping*).
  2. **Documento de Diseño:** Incluye arquitectura en 3 capas (*Presentación Frontend en Streamlit*, *Lógica de Negocio Backend en Python* y *Capa de Datos en Supabase/SQLite*), diagramas **UML** (Casos de Uso, Clases con herencia `UsuarioRegistrado` $\rightarrow$ `Usuario`, Objetos, Secuencia para `UC1` y `UC7`, Actividades del scraping, Componentes y Despliegue), **DER** y **DFD** (Nivel 0 y Nivel 1 con 5 procesos).
  3. **Plan y Resultados de Pruebas:** Documenta casos de prueba funcionales, pruebas unitarias (**158 tests automatizados**), pruebas de integración, sistema, aceptación, usabilidad, rendimiento y seguridad.
  4. **Manual Técnico:** Guía de instalación, entorno virtual (`venv`), variables de entorno (`.env` / `secrets.toml`), contenedor Docker opcional y despliegue continuo CI/CD.
* **EDT, Carta Gantt y Ruta Crítica (CPM / PERT):**
  * **EDT (Estructura de Desglose del Trabajo):** Dividida en **3 fases** y **15 paquetes de trabajo**.
  * **Carta Gantt:** Planificada a **13 semanas**.
  * **Ruta Crítica (CPM) y Red PERT:** El cálculo de fechas tempranas y tardías demostró que **13 de las 15 actividades eran críticas (holgura = 0)**. Solo **2 actividades tenían holgura (5 semanas)**: la configuración inicial del repositorio GitHub y la maqueta (*mockup*) del frontend.

---

## 10. Modelo de Negocio Freemium, Planes y Simulación Financiera Monte Carlo

*(Contenido oficial de las Diapositivas 9 y 10 y Glosario Financiero)*

### Propuesta de Valor y Modelo B2C / B2B
* **Propuesta de valor:** Comprar perfumes originales más barato, más seguro (gracias al Trust Score) y sabiendo qué está de moda (gracias al Hype Radar), todo en un solo lugar.
* **Modelo Agregador:** Reúne las ofertas y redirige al usuario al e-commerce de la tienda elegida (no procesamos pagos ni inventario, eliminando costos logísticos).

### Las 4 Vías de Monetización y los 3 Planes Freemium
1. **Publicidad (Ads):** Cobro por impresiones (CPM) o clics (CPC).
2. **Marketing de Afiliados:** Comisión por cada venta generada desde los enlaces de PerfumeTrending.
3. **Cupones Patrocinados (B2B):** Las tiendas verificadas pagan por destacar cupones de descuento para ganar conversión.
4. **Suscripción Mensual (Modelo Freemium en 3 niveles):**
   * **Plan Free ($0 / Gratis):** Acceso completo a la plataforma, comparador entre tiendas, Trust Score, Hype Radar y registro de favoritos.
   * **Plan Premium ($2.000 CLP / mes):** Todo lo del plan Free + **Alertas automáticas de baja de precio por correo**, detalle de tienda y nuevo precio, seguimiento avanzado de favoritos y cupones exclusivos.
   * **Plan Socios VIP (Próximamente):** Todo lo del plan Premium + experiencias presenciales/físicas: catas de fragancias y *Mystery Box* mensual de decants para probar perfumes antes de comprar la botella completa.

### Simulación Financiera Monte Carlo (2.000 Escenarios a 12 Meses)
Para evaluar la viabilidad económica sin inventar una única cifra fija, ejecutamos una **Simulación Monte Carlo con 2.000 escenarios de 1 año** usando **distribuciones triangulares** (valor mínimo, más probable y máximo) para variables aleatorias como tráfico mensual y tasa de conversión:
* **87% de Probabilidad de Ganancia:** El **87%** de los 2.000 escenarios simulados termina el primer año con utilidad neta positiva.
* **Punto de Equilibrio (*Break-Even*): Mes 8** (momento en que el resultado acumulado pasa a ser positivo y los ingresos acumulados igualan a los costos acumulados).
* **Ganancia Mediana Anual (`Percentil P50`): ~$469.000 CLP** en el primer año como MVP (usamos la **mediana P50** en lugar del promedio porque la mediana no se distorsiona por escenarios extremos optimistas `P90` o pesimistas `P10`).
* **Análisis de Sensibilidad:** Las variables que más mueven el resultado financiero son el **tráfico de visitas** y la **tasa de conversión**, mientras que los costos se mantienen ultra-bajos gracias al uso de capas gratuitas (*Free Tier*).

---

## 11. Marco Legal, Ético y Protección de Datos en Chile (Leyes 19.496, 21.398, 19.628 y 21.719)

* **Ley del Consumidor (Ley 19.496) y Reforma "Pro Consumidor" (Ley 21.398):** Protege los derechos en compras online (información veraz de precios, stock y **derecho a retracto**). Como PerfumeTrending es un comparador informativo y la compra se realiza en el sitio de la tienda, el derecho a retracto y la garantía legal se ejercen directamente ante la tienda vendedora.
* **Protección de Datos Personales (Ley 19.628 y nueva Ley 21.719 que entra en vigencia el 1 de diciembre de 2026):**
  * La nueva **Ley 21.719** crea la **Agencia de Protección de Datos Personales** y refuerza los derechos de acceso, rectificación, cancelación/eliminación y portabilidad, exigiendo consentimiento claro.
  * Nuestro sistema cumple con el principio de **minimización de datos**: el visitante puede usar el comparador sin entregar ningún dato personal; solo se guarda correo y contraseña (hasheada con **PBKDF2-HMAC-SHA256 y 600.000 iteraciones**) cuando el usuario se registra con consentimiento explícito para guardar favoritos o recibir alertas.
* **Propiedad Industrial: Diferencia entre *Dupe* Legal vs. *Falsificación / Réplica* Ilegal:**
  * Un **dupe** (como las fragancias de *Lattafa, Armaf o Maison Alhambra*) es un producto **100% legal**: tiene su propia marca registrada, su propio diseño de frasco y registro sanitario ISP, aunque su aroma pertenezca a una familia olfativa similar a un perfume de lujo.
  * Una **réplica o falsificación** copia ilegalmente el nombre, logo y envase de una marca protegida para engañar al comprador. Nuestro normalizador y el Trust Score bloquean las réplicas e imitaciones, pero incluyen orgullosamente la perfumería árabe original.
* **Scraping Responsable:** Extraemos únicamente datos públicos comerciales de productos (nombre, precio, stock y URL), nunca datos personales; no vulneramos muros de pago ni logins; usamos descarga bulk en tiendas Shopify para no saturar sus servidores; y presentamos el **Trust Score** como una estimación referencial basada en indicadores públicos.

---

## 12. Estructura Completa del Código del Proyecto (Mapa Archivo por Archivo)

Todos los archivos del proyecto se encuentran completamente comentados línea por línea y bloque por bloque:

* **`APP/app.py`**: Router principal de Streamlit, barra de navegación superior, buscador rápido, control de sesión y pie de página.
* **`APP/pages/compararprecios.py`**: Vista central del comparador de precios por variante (`ml`), cálculo de `$/ml`, separación `Regular` vs `Tester`, gráfico histórico de precios y redirección segura a las tiendas.
* **`APP/pages/remates.py`**: Módulo de oportunidades y descuentos reales verificados ($\ge 15\%$ bajo su precio normal).
* **`APP/pages/trendhype.py`**: Interfaz del **Hype Radar**, ranking por **Hype Score**, filtro de perfumería árabe y métricas de YouTube.
* **`APP/pages/trustpage.py`**: Portal de transparencia del **Trust Score** (puntaje de 0 a 100 por tienda, desglose de los 4 pilares y estado de salud de los scrapers).
* **`APP/pages/perfil.py` y `APP/pages/comprarplan.py`**: Gestión de cuenta del usuario, favoritos, alertas de precio y presentación de los planes *Free*, *Premium ($2.000/mes)* y *Socios VIP*.
* **`APP/ui/theme.py`, `APP/ui/security.py`, `APP/ui/auth_modal.py`**: Sistema de temas (Claro/Oscuro), sanitización anti-XSS y modales de login/registro.
* **`APP/auth_email.py`, `APP/hype_youtube.py`, `APP/perfume_actions.py`**: Envío de correos SMTP para alertas/recuperación, cliente de YouTube Data API v3 y lógica de favoritos/listas.
* **`APP/backend/database.py`**: Capa de acceso a datos dual (**Supabase Cloud + SQLite WAL**), hashing PBKDF2-HMAC-SHA256, filtro `tienda_comercializa_marca` (con perfumería árabe habilitada en todo el retail), persistencia transaccional y caché en memoria.
* **`APP/backend/normalizador.py`**: Motor determinista de resolución de entidades en **12 capas**, canonización de +110 marcas, detección de perfumes árabes (`MARCAS_ARABES_CONOCIDAS`), guardia de flankers y detector estadístico de outliers por mediana.
* **`APP/backend/scraper_periodico.py`**: Scraper híbrido de 2 velocidades (*Bulk In-Memory* para 13 tiendas especializadas + extracción concurrente de `__NEXT_DATA__` y `Schema.org JSON-LD` para **Falabella, Paris y Ripley**), cola LRU, Sharding y Circuit Breaker.
* **`APP/backend/scraper_autonomo.py`**: Buscador / Autodescubridor de nuevos perfumes desde feeds JSON y subida de imágenes a Supabase Storage (`IMG_perfumes`).
* **`APP/backend/auditoria_enlaces.py`**: Auditor semanal de enlaces activos con política de **Histéresis de 2 Strikes** e inmunidad ante bloqueos WAF.
* **`APP/backend/generar_sql_supabase.py`, `importar_curados.py`, `sincronizar_precios_reales.py`, `subir_imagenes_bucket.py`**: Scripts de aprovisionamiento SQL, ingesta curada y sincronización de activos.
* **`APP/backend/mantenimiento/`**: Herramientas de diagnóstico y mantenimiento (`probe_waf.py`, `resumen_salud_ci.py`, `sincronizar_retail_local.py`, `detectar_outliers_bd.py`, `fusionar_perfumes.py`, `reparar_volumenes.py`, `auditar_imagenes.py`).
* **`.github/workflows/`**: Los 4 pipelines automatizados de GitHub Actions (`scraper_nocturno.yml`, `auditoria_enlaces.yml`, `keep_alive.yml`, `probe_waf.yml`).
* **`tests/`**: Los 20 módulos de pruebas con las **158 pruebas unitarias y de integración**.

---

## 13. Banco Completo de Preguntas del Jurado y Respuestas Ganadoras

1. **¿Por qué usaron Metodología en Cascada y no Scrum?**
   > *"Porque el alcance y los módulos del sistema estaban claramente definidos desde el inicio, el semestre tiene plazos fijos y cada integrante tenía un área de responsabilidad clara. La Carta Gantt de 13 semanas se cumplió sin atrasos ni cambios de alcance, confirmando que Cascada fue la metodología adecuada."*
2. **¿Qué les mostró la Ruta Crítica (CPM / PERT)?**
   > *"Nos mostró que 13 de las 15 actividades de nuestra EDT eran críticas (sin margen de atraso) y que el proyecto duraba exactamente las 13 semanas disponibles. Solo la creación del repositorio y la maqueta del frontend tenían una holgura de 5 semanas."*
3. **¿Por qué cambiaron de SQLite a Supabase y por qué siguen ambos en el código?**
   > *"Cambiamos a Supabase porque SQLite guarda todo en un archivo local y necesitábamos una base de datos PostgreSQL compartida en la nube para trabajar los tres simultáneamente, conectar Streamlit Cloud y recibir las actualizaciones nocturnas de GitHub Actions. Mantuvimos SQLite en `database.py` para correr nuestras 158 pruebas unitarias en un entorno aislado sin tocar los datos reales de producción y como respaldo local (failover)."*
4. **¿El scraper solo actualiza precios o también busca perfumes nuevos?**
   > *"Hace las dos cosas: el **Autodescubridor (`scraper_autonomo.py`)** recorre los catálogos de 13 tiendas especializadas, limpia los títulos con el normalizador y crea automáticamente cualquier perfume nuevo en Supabase; y el **Scraper Periódico (`scraper_periodico.py`)** actualiza diariamente los precios, variantes de tamaño y stock de los 3.364 perfumes en las 16 tiendas, incluyendo un buscador interno que descubre nuevos enlaces vivos de perfumes de diseñador y árabes en Paris, Falabella y Ripley."*
5. **¿Cómo evitan mezclar un perfume de 100 ml con uno de 50 ml, un Tester, un Body Mist o un Flanker como Elixir?**
   > *"Con nuestro motor determinista de **12 capas en `normalizador.py`** y el modelo de base de datos en **3 niveles** (`perfumes` $\rightarrow$ `variantes_perfume` $\rightarrow$ `ofertas_actuales`). El normalizador bloquea cremas, body mists, sets y decants menores a 25 ml; separa los formatos `Tester` de los `Regular`; distingue concentraciones (`EDT`, `EDP`, `Parfum`, `Colonia`) y tiene una guardia de más de 70 flankers (`Elixir`, `Intense`, `Candy`, `Spectra`, `Qahwa`) para que cada variante se compare exclusivamente con su par exacto."*
6. **¿Por qué el Hype Radar usa solo YouTube y cómo se calcula el Trust Score?**
   > *"El **Hype Radar** usa YouTube Data API v3 porque es oficial, gratuita y entrega métricas públicas auditables de vistas, likes y comentarios en reseñas en español, mientras que TikTok e Instagram tienen APIs cerradas o de alto costo; dejamos esto declarado como alcance del proyecto. Por su parte, el **Trust Score (0 a 100)** combina 4 pilares públicos: seguridad SSL/HTTPS, antigüedad del dominio en WHOIS, formalidad legal/RUT y reputación/SERNAC, mostrándose como un indicador referencial para reducir la asimetría de información."*
7. **¿El proyecto es rentable económicamente?**
   > *"Sí. Opera con un modelo **Freemium** (plan gratuito + plan Premium de $2.000 CLP/mes por alertas de baja de precio + comisiones de afiliados, publicidad y cupones patrocinados) y costos operativos mínimos gracias al uso de capas gratuitas (Free Tier). En nuestra **Simulación Monte Carlo de 2.000 escenarios a 12 meses**, el proyecto obtuvo un **87% de probabilidad de ganancia**, alcanzando el punto de equilibrio en el **mes 8** y una ganancia mediana (P50) de **$469.000 CLP** en su primer año como MVP."*
