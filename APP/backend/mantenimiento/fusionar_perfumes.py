# -*- coding: utf-8 -*-
"""
PerfumeTrending.cl — Herramienta de Fusión Segura de Perfumes Duplicados (Fase 4)
=================================================================================
Identifica grupos duplicados en `perfumes` bajo clave canónica sin género
`(marca_canonica, nombre_limpio, tipo)` y ejecuta fusiones transaccionalmente
seguras respetando todas las restricciones FK (`ON DELETE RESTRICT`) e índices
únicos (`UNIQUE(variante_id, tienda_id)`, `UNIQUE(usuario_id, perfume_id)`,
`perfume_notas`, `perfume_familias_olfativas`, `perfume_notas_importacion`,
`ux_perfumes_marca_nombre_tipo_genero`).

Reglas estrictas:
  - Por defecto opera en `--dry-run` (cero escrituras).
  - Pares en conflicto explícito `Hombre` vs `Mujer` JAMÁS se fusionan entre sí
    (ni se absorbe `Unisex` cuando coexisten ambos géneros en el mismo grupo):
    se exportan a `scratch/revision_manual_duplicados.csv`. Si dentro de un grupo
    mixto existen duplicados exactos del mismo género (`Mujer`+`Mujer` u
    `Hombre`+`Hombre`), únicamente esos subgrupos del mismo género se consolidan.
  - Reasigna `favoritos_usuario` (y `auth.users.user_metadata.favoritos`),
    `perfume_notas`, `perfume_familias_olfativas`, `perfume_notas_importacion`,
    `variantes_perfume`, `ofertas_actuales` y `precios_registro`.
  - Verifica explícitamente 0 referencias residuales antes de `DELETE FROM perfumes`.
  - Cualquier excepción aborta el grupo completo (sin `except: pass`) y queda auditada.

Uso:
  python APP/backend/mantenimiento/fusionar_perfumes.py --dry-run
  python APP/backend/mantenimiento/fusionar_perfumes.py --apply
"""

# Importación de librería estándar o dependencia externa (argparse)
import argparse
# Importación de componentes (defaultdict) desde el módulo 'collections'
from collections import defaultdict
# Importación de librería estándar o dependencia externa (csv)
import csv
# Importación de componentes (datetime, timezone) desde el módulo 'datetime'
from datetime import datetime, timezone
# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (logging)
import logging
# Importación de componentes (Path) desde el módulo 'pathlib'
from pathlib import Path
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de componentes (Any, Dict, List, Optional, ...) desde el módulo 'typing'
from typing import Any, Dict, List, Optional, Tuple

# Importación de librería estándar o dependencia externa (requests)
import requests

# Asignamos 'REPO_ROOT' con Path(__file__).resolve().parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]
# Asignamos 'APP_DIR' con REPO_ROOT / 'APP'
APP_DIR = REPO_ROOT / "APP"
# Recorremos iterativamente cada '_p' en (str(APP_DIR), str(REPO_ROOT))
for _p in (str(APP_DIR), str(REPO_ROOT)):
    # Evaluamos la condición lógica (_p not in sys.path) para controlar el flujo
    if _p not in sys.path:
        # Ejecutamos instrucción: sys.path.insert(0, _p)
        sys.path.insert(0, _p)

# Importación de componentes (get_supabase, limpiar_cache_catalogo) desde el módulo 'backend.database'
from backend.database import get_supabase, limpiar_cache_catalogo
# Importación de componentes (clave_identidad_perfume, generos_compatibles, inferir_genero_explicito_nombre, limpiar_nombre_perfume, ...) desde el módulo 'backend.normalizador'
from backend.normalizador import (
    clave_identidad_perfume,
    generos_compatibles,
    inferir_genero_explicito_nombre,
    limpiar_nombre_perfume,
    normalizar_genero,
    normalizar_marca_canonica,
)

# Ejecutamos instrucción: logging.basicConfig(level=logging.INFO, format='%(as...
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Asignamos 'logger' con logging.getLogger('FusionarPerfumes')
logger = logging.getLogger("FusionarPerfumes")


# - ¿Qué hace esta función?:
#   Descarga paginadamente (de a 1.000 filas) una tabla completa desde Supabase.
def fetch_all_sb(sb: Any, table: str, select: str = "*") -> List[Dict[str, Any]]:
    # Asignamos 'rows' con []
    rows: List[Dict[str, Any]] = []
    # Asignamos 'offset' con 0
    offset = 0
    # Ejecutamos el ciclo mientras se mantenga la condición: True
    while True:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        res = sb.table(table).select(select).order("id", desc=False).range(offset, offset + 999).execute()
        # Asignamos 'batch' con res.data or []
        batch = res.data or []
        # Evaluamos la condición lógica (not batch) para controlar el flujo
        if not batch:
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
        # Ejecutamos instrucción: rows.extend(batch)
        rows.extend(batch)
        # Evaluamos la condición lógica (len(batch) < 1000) para controlar el flujo
        if len(batch) < 1000:
            # Interrumpimos el ciclo actual al cumplirse la condición de salida
            break
        # Actualizamos acumulativamente el valor de 'offset'
        offset += 1000
    # Retornamos el resultado procesado (rows)
    return rows


# - ¿Qué hace esta función?:
#   Evalúa si las etiquetas de género de un grupo son compatibles para fusión automática:
#   - `Unisex` + `Hombre`/`Mujer` -> `(True, 'Hombre'|'Mujer')`
#   - Mismo género -> `(True, genero_normalizado)`
#   - `Hombre` vs `Mujer` -> `(False, '')` (conflicto real Pour Homme vs Pour Femme).
def evaluar_compatibilidad_generos_grupo(generos_raw: List[Optional[str]]) -> Tuple[bool, str]:
    # Asignamos 'acumulado' con 'Unisex'
    acumulado = "Unisex"
    # Recorremos iterativamente cada 'g' en generos_raw
    for g in generos_raw:
        # Asignamos '(ok, res)' con generos_compatibles(acumulado, g)
        ok, res = generos_compatibles(acumulado, g)
        # Evaluamos la condición lógica (not ok) para controlar el flujo
        if not ok:
            # Retornamos el resultado procesado ((False, ''))
            return False, ""
        # Asignamos 'acumulado' con res
        acumulado = res
    # Retornamos el resultado procesado ((True, acumulado))
    return True, acumulado


# - ¿Qué hace esta función?:
#   Comprueba mediante HEAD/GET ligero si una `imagen_url` responde HTTP 200 válido
#   y no corresponde al placeholder genérico de Unsplash.
def es_imagen_valida_http(url: Optional[str], cache_http: Dict[str, bool]) -> bool:
    # Asignamos 'u' con str(url or '').strip()
    u = str(url or "").strip()
    # Evaluamos la condición lógica (not u.startswith('http') or 'images.unsplash.com/pho...) para controlar el flujo
    if not u.startswith("http") or "images.unsplash.com/photo-1522337360788" in u:
        # Retornamos el resultado procesado (False)
        return False
    # Evaluamos la condición lógica (u in cache_http) para controlar el flujo
    if u in cache_http:
        # Retornamos el resultado procesado (cache_http[u])
        return cache_http[u]
    # Asignamos 'ok' con False
    ok = False
    # Bloque try/except para manejo seguro de errores y resiliencia operativa
    try:
        # Asignamos 'r' con requests.head(u, timeout=5, allow_redirect...
        r = requests.head(u, timeout=5, allow_redirects=True)
        # Evaluamos la condición lógica (r.status_code == 200) para controlar el flujo
        if r.status_code == 200:
            # Asignamos 'ok' con True
            ok = True
        # Evaluamos la condición lógica (r.status_code in (403, 405)) para controlar el flujo
        elif r.status_code in (403, 405):
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            rg = requests.get(u, timeout=6, stream=True)
            # Asignamos 'ok' con rg.status_code == 200
            ok = rg.status_code == 200
            # Ejecutamos instrucción: rg.close()
            rg.close()
    except Exception:
        # Asignamos 'ok' con False
        ok = False
    # Asignamos 'cache_http[u]' con ok
    cache_http[u] = ok
    # Retornamos el resultado procesado (ok)
    return ok


# - ¿Qué hace esta función?:
#   Determina si `oferta_cand` debe prevalecer sobre `oferta_actual` cuando ambas
#   colisionan en `UNIQUE(variante_id, tienda_id)`, priorizando stock activo y frescura.
def _es_mejor_oferta(oferta_cand: Dict[str, Any], oferta_actual: Dict[str, Any]) -> bool:
    # Asignamos 'key_cand' con (1 if oferta_cand.get('estado') == 'activa...
    key_cand = (
        1 if (oferta_cand.get("estado") == "activa" and oferta_cand.get("en_stock")) else 0,
        1 if oferta_cand.get("estado") == "activa" else 0,
        str(oferta_cand.get("ultima_verificacion_exitosa") or ""),
        -int(oferta_cand.get("precio_actual") or 999999999),
    )
    # Asignamos 'key_act' con (1 if oferta_actual.get('estado') == 'acti...
    key_act = (
        1 if (oferta_actual.get("estado") == "activa" and oferta_actual.get("en_stock")) else 0,
        1 if oferta_actual.get("estado") == "activa" else 0,
        str(oferta_actual.get("ultima_verificacion_exitosa") or ""),
        -int(oferta_actual.get("precio_actual") or 999999999),
    )
    # Retornamos el resultado procesado (key_cand > key_act)
    return key_cand > key_act


# - ¿Qué hace esta función?:
#   Ejecuta de forma atómica a nivel lógico la fusión de `p_origen` dentro de `p_destino`
#   sobre un cliente Supabase (o doble de prueba compatible), verificando 0 referencias
#   residuales en todas las tablas con FK `ON DELETE RESTRICT` antes de eliminar `p_origen`.
def fusionar_par_perfumes_sb(
    sb: Any,
    p_origen: Dict[str, Any],
    p_destino: Dict[str, Any],
    now_iso: str,
) -> Dict[str, Any]:
    # Asignamos 'id_origen' con int(p_origen['id'])
    id_origen = int(p_origen["id"])
    # Asignamos 'id_destino' con int(p_destino['id'])
    id_destino = int(p_destino["id"])
    # Evaluamos la condición lógica (id_origen == id_destino) para controlar el flujo
    if id_origen == id_destino:
        # Propagamos excepción explícita ante condición de error detectada
        raise ValueError(f"id_origen == id_destino ({id_origen})")

    # Asignamos 'resumen_par' con {'id_origen': id_origen, 'id_destino': id_...
    resumen_par = {
        "id_origen": id_origen,
        "id_destino": id_destino,
        "favoritos_reasignados": 0,
        "notas_reasignadas": 0,
        "variantes_movidas": 0,
        "variantes_consolidadas": 0,
        "ofertas_movidas": 0,
        "ofertas_deduplicadas": 0,
    }

    # 1. Reasignar `favoritos_usuario` resolviendo UNIQUE(usuario_id, perfume_id)
    favs_orig = sb.table("favoritos_usuario").select("id, usuario_id, perfume_id").eq("perfume_id", id_origen).execute().data or []
    # Evaluamos la condición lógica (favs_orig) para controlar el flujo
    if favs_orig:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        favs_dest = sb.table("favoritos_usuario").select("usuario_id").eq("perfume_id", id_destino).execute().data or []
        # Asignamos 'usuarios_ya_en_dest' con {str(f['usuario_id']) for f in favs_dest}
        usuarios_ya_en_dest = {str(f["usuario_id"]) for f in favs_dest}
        # Recorremos iterativamente cada 'fv' en favs_orig
        for fv in favs_orig:
            # Asignamos 'uid' con str(fv['usuario_id'])
            uid = str(fv["usuario_id"])
            # Evaluamos la condición lógica (uid in usuarios_ya_en_dest) para controlar el flujo
            if uid in usuarios_ya_en_dest:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                sb.table("favoritos_usuario").delete().eq("id", fv["id"]).execute()
            else:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                sb.table("favoritos_usuario").update({"perfume_id": id_destino}).eq("id", fv["id"]).execute()
                # Ejecutamos instrucción: usuarios_ya_en_dest.add(uid)
                usuarios_ya_en_dest.add(uid)
            # Actualizamos acumulativamente el valor de 'resumen_par['favoritos_reasignad...'
            resumen_par["favoritos_reasignados"] += 1

    # 1b. Reasignar tablas olfativas con FK `ON DELETE RESTRICT`
    # - `perfume_notas`: UNIQUE(perfume_id, nota_id, etapa)
    notas_orig = sb.table("perfume_notas").select("id, nota_id, etapa").eq("perfume_id", id_origen).execute().data or []
    # Evaluamos la condición lógica (notas_orig) para controlar el flujo
    if notas_orig:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        notas_dest = sb.table("perfume_notas").select("nota_id, etapa").eq("perfume_id", id_destino).execute().data or []
        # Asignamos 'claves_nota_dest' con {(int(n['nota_id']), str(n.get('etapa') or...
        claves_nota_dest = {(int(n["nota_id"]), str(n.get("etapa") or "desconocida")) for n in notas_dest}
        # Recorremos iterativamente cada 'nr' en notas_orig
        for nr in notas_orig:
            # Asignamos 'k_nota' con (int(nr['nota_id']), str(nr.get('etapa') o...
            k_nota = (int(nr["nota_id"]), str(nr.get("etapa") or "desconocida"))
            # Evaluamos la condición lógica (k_nota in claves_nota_dest) para controlar el flujo
            if k_nota in claves_nota_dest:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                sb.table("perfume_notas").delete().eq("id", nr["id"]).execute()
            else:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                sb.table("perfume_notas").update({"perfume_id": id_destino, "updated_at": now_iso}).eq("id", nr["id"]).execute()
                # Ejecutamos instrucción: claves_nota_dest.add(k_nota)
                claves_nota_dest.add(k_nota)
            # Actualizamos acumulativamente el valor de 'resumen_par['notas_reasignadas']'
            resumen_par["notas_reasignadas"] += 1

    # - `perfume_familias_olfativas`: UNIQUE(perfume_id, familia_id) + partial unique (perfume_id) WHERE es_principal = true
    fams_orig = sb.table("perfume_familias_olfativas").select("id, familia_id, es_principal").eq("perfume_id", id_origen).execute().data or []
    # Evaluamos la condición lógica (fams_orig) para controlar el flujo
    if fams_orig:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        fams_dest = sb.table("perfume_familias_olfativas").select("familia_id, es_principal").eq("perfume_id", id_destino).execute().data or []
        # Asignamos 'fams_ya_dest' con {int(f['familia_id']) for f in fams_dest}
        fams_ya_dest = {int(f["familia_id"]) for f in fams_dest}
        # Asignamos 'tiene_principal_dest' con any((bool(f.get('es_principal')) for f in ...
        tiene_principal_dest = any(bool(f.get("es_principal")) for f in fams_dest)
        # Recorremos iterativamente cada 'fr' en fams_orig
        for fr in fams_orig:
            # Asignamos 'fid' con int(fr['familia_id'])
            fid = int(fr["familia_id"])
            # Evaluamos la condición lógica (fid in fams_ya_dest) para controlar el flujo
            if fid in fams_ya_dest:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                sb.table("perfume_familias_olfativas").delete().eq("id", fr["id"]).execute()
            else:
                # Asignamos 'es_princ_nuevo' con False if tiene_principal_dest else bool(fr...
                es_princ_nuevo = False if tiene_principal_dest else bool(fr.get("es_principal"))
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                sb.table("perfume_familias_olfativas").update({
                    "perfume_id": id_destino,
                    "es_principal": es_princ_nuevo,
                }).eq("id", fr["id"]).execute()
                # Ejecutamos instrucción: fams_ya_dest.add(fid)
                fams_ya_dest.add(fid)
                # Evaluamos la condición lógica (es_princ_nuevo) para controlar el flujo
                if es_princ_nuevo:
                    # Asignamos 'tiene_principal_dest' con True
                    tiene_principal_dest = True
            # Actualizamos acumulativamente el valor de 'resumen_par['notas_reasignadas']'
            resumen_par["notas_reasignadas"] += 1

    # - `perfume_notas_importacion`: UNIQUE(perfume_id)
    imp_orig = sb.table("perfume_notas_importacion").select("id, perfume_id").eq("perfume_id", id_origen).execute().data or []
    # Evaluamos la condición lógica (imp_orig) para controlar el flujo
    if imp_orig:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        imp_dest = sb.table("perfume_notas_importacion").select("id").eq("perfume_id", id_destino).limit(1).execute().data or []
        # Asignamos 'ya_tiene_imp' con bool(imp_dest)
        ya_tiene_imp = bool(imp_dest)
        # Recorremos iterativamente cada 'ir' en imp_orig
        for ir in imp_orig:
            # Evaluamos la condición lógica (ya_tiene_imp) para controlar el flujo
            if ya_tiene_imp:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                sb.table("perfume_notas_importacion").delete().eq("id", ir["id"]).execute()
            else:
                # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                sb.table("perfume_notas_importacion").update({
                    "perfume_id": id_destino,
                    "updated_at": now_iso,
                }).eq("id", ir["id"]).execute()
                # Asignamos 'ya_tiene_imp' con True
                ya_tiene_imp = True
            # Actualizamos acumulativamente el valor de 'resumen_par['notas_reasignadas']'
            resumen_par["notas_reasignadas"] += 1

    # 2. Reasignar y consolidar `variantes_perfume`, `ofertas_actuales` y `precios_registro`
    vars_dest = sb.table("variantes_perfume").select("*").eq("perfume_id", id_destino).execute().data or []
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    vars_orig = sb.table("variantes_perfume").select("*").eq("perfume_id", id_origen).execute().data or []

    # Recorremos iterativamente cada 'v_orig' en vars_orig
    for v_orig in vars_orig:
        # Asignamos 'vid_orig' con int(v_orig['id'])
        vid_orig = int(v_orig["id"])
        # Asignamos 'vol_orig' con float(v_orig.get('volumen_ml') or 100.0)
        vol_orig = float(v_orig.get("volumen_ml") or 100.0)
        # Asignamos 'fmt_orig' con str(v_orig.get('formato') or 'regular').lo...
        fmt_orig = str(v_orig.get("formato") or "regular").lower()

        # Asignamos 'v_match' con next((vd for vd in vars_dest if abs(float(...
        v_match = next(
            (
                vd for vd in vars_dest
                if abs(float(vd.get("volumen_ml") or 100.0) - vol_orig) <= 1.0
                and str(vd.get("formato") or "regular").lower() == fmt_orig
            ),
            None,
        )

        # Evaluamos la condición lógica (v_match is None) para controlar el flujo
        if v_match is None:
            # No existe esa talla/formato en el canónico: mover la variante entera
            sb.table("variantes_perfume").update({
                "perfume_id": id_destino,
                "updated_at": now_iso,
            }).eq("id", vid_orig).execute()
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            sb.table("precios_registro").update({"perfume_id": id_destino}).eq("variante_id", vid_orig).execute()
            # Ejecutamos instrucción: vars_dest.append(dict(v_orig, perfume_id=id_destino))
            vars_dest.append(dict(v_orig, perfume_id=id_destino))
            # Actualizamos acumulativamente el valor de 'resumen_par['variantes_movidas']'
            resumen_par["variantes_movidas"] += 1
        else:
            # Ya existe la variante equivalente en el canónico: consolidar ofertas e historial y borrar v_orig
            vid_dest = int(v_match["id"])
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            ofs_dest = sb.table("ofertas_actuales").select("*").eq("variante_id", vid_dest).execute().data or []
            # Asignamos 'ofs_por_tienda' con {int(od['tienda_id']): od for od in ofs_dest}
            ofs_por_tienda = {int(od["tienda_id"]): od for od in ofs_dest}
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            ofs_orig = sb.table("ofertas_actuales").select("*").eq("variante_id", vid_orig).execute().data or []

            # Recorremos iterativamente cada 'oo' en ofs_orig
            for oo in ofs_orig:
                # Asignamos 'tid' con int(oo['tienda_id'])
                tid = int(oo["tienda_id"])
                # Asignamos 'oid_orig' con int(oo['id'])
                oid_orig = int(oo["id"])
                # Asignamos 'od_exist' con ofs_por_tienda.get(tid)
                od_exist = ofs_por_tienda.get(tid)
                # Evaluamos la condición lógica (od_exist is not None) para controlar el flujo
                if od_exist is not None:
                    # Evaluamos la condición lógica (_es_mejor_oferta(oo, od_exist)) para controlar el flujo
                    if _es_mejor_oferta(oo, od_exist):
                        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                        sb.table("ofertas_actuales").update({
                            "precio_actual": oo["precio_actual"],
                            "precio_normal": oo.get("precio_normal") or oo["precio_actual"],
                            "en_stock": oo.get("en_stock", False),
                            "estado": oo.get("estado", "activa"),
                            "ultima_verificacion_exitosa": oo.get("ultima_verificacion_exitosa"),
                            "ultimo_intento": oo.get("ultimo_intento"),
                            "fallos_consecutivos": oo.get("fallos_consecutivos", 0),
                            "ultimo_error": oo.get("ultimo_error"),
                            "updated_at": now_iso,
                        }).eq("id", int(od_exist["id"])).execute()
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    sb.table("ofertas_actuales").delete().eq("id", oid_orig).execute()
                    # Actualizamos acumulativamente el valor de 'resumen_par['ofertas_deduplicadas']'
                    resumen_par["ofertas_deduplicadas"] += 1
                else:
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    sb.table("ofertas_actuales").update({
                        "variante_id": vid_dest,
                        "updated_at": now_iso,
                    }).eq("id", oid_orig).execute()
                    # Asignamos 'ofs_por_tienda[tid]' con dict(oo, variante_id=vid_dest)
                    ofs_por_tienda[tid] = dict(oo, variante_id=vid_dest)
                    # Actualizamos acumulativamente el valor de 'resumen_par['ofertas_movidas']'
                    resumen_par["ofertas_movidas"] += 1

            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            sb.table("precios_registro").update({
                "variante_id": vid_dest,
                "perfume_id": id_destino,
            }).eq("variante_id", vid_orig).execute()

            # Verificar 0 referencias antes de borrar la variante duplicada
            rem_vo = sb.table("ofertas_actuales").select("id").eq("variante_id", vid_orig).limit(1).execute().data or []
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            rem_vp = sb.table("precios_registro").select("id").eq("variante_id", vid_orig).limit(1).execute().data or []
            # Evaluamos la condición lógica (rem_vo or rem_vp) para controlar el flujo
            if rem_vo or rem_vp:
                # Propagamos excepción explícita ante condición de error detectada
                raise RuntimeError(
                    f"Abortando: variante #{vid_orig} aún mantiene referencias "
                    f"(ofertas={len(rem_vo)}, precios_registro={len(rem_vp)})"
                )
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            sb.table("variantes_perfume").delete().eq("id", vid_orig).execute()
            # Actualizamos acumulativamente el valor de 'resumen_par['variantes_consolida...'
            resumen_par["variantes_consolidadas"] += 1

    # Reasignar cualquier fila residual de `precios_registro` con `perfume_id = id_origen`
    sb.table("precios_registro").update({"perfume_id": id_destino}).eq("perfume_id", id_origen).execute()

    # 3. Verificación explícita de CERO filas huérfanas antes del DELETE en `perfumes`
    chk_v = sb.table("variantes_perfume").select("id").eq("perfume_id", id_origen).limit(1).execute().data or []
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    chk_pr = sb.table("precios_registro").select("id").eq("perfume_id", id_origen).limit(1).execute().data or []
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    chk_fv = sb.table("favoritos_usuario").select("id").eq("perfume_id", id_origen).limit(1).execute().data or []
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    chk_pn = sb.table("perfume_notas").select("id").eq("perfume_id", id_origen).limit(1).execute().data or []
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    chk_pf = sb.table("perfume_familias_olfativas").select("id").eq("perfume_id", id_origen).limit(1).execute().data or []
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    chk_pi = sb.table("perfume_notas_importacion").select("id").eq("perfume_id", id_origen).limit(1).execute().data or []
    # Evaluamos la condición lógica (chk_v or chk_pr or chk_fv or chk_pn or chk_pf or chk_pi) para controlar el flujo
    if chk_v or chk_pr or chk_fv or chk_pn or chk_pf or chk_pi:
        # Propagamos excepción explícita ante condición de error detectada
        raise RuntimeError(
            f"Abortando DELETE de perfume #{id_origen}: referencias activas "
            f"(variantes={len(chk_v)}, precios={len(chk_pr)}, favoritos={len(chk_fv)}, "
            f"notas={len(chk_pn)}, familias={len(chk_pf)}, notas_imp={len(chk_pi)})"
        )

    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb.table("perfumes").delete().eq("id", id_origen).execute()
    # Retornamos el resultado procesado (resumen_par)
    return resumen_par


# - ¿Qué hace esta función principal?:
#   Escanea `perfumes`, separa grupos seguros de conflictos `Hombre` vs `Mujer`,
#   exporta el CSV de revisión humana y ejecuta (en `--apply`) la fusión completa
#   dejando trazabilidad en `fusiones_perfumes` y `historial_fusiones.json`.
def ejecutar_fusion_perfumes(apply_changes: bool = False) -> Dict[str, Any]:
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (not sb) para controlar el flujo
    if not sb:
        # Propagamos excepción explícita ante condición de error detectada
        raise RuntimeError("No se pudo obtener cliente Supabase con service_role.")

    # Asignamos 'perfumes' con fetch_all_sb(sb, 'perfumes', '*')
    perfumes = fetch_all_sb(sb, "perfumes", "*")
    # Asignamos 'variantes' con fetch_all_sb(sb, 'variantes_perfume', 'id,...
    variantes = fetch_all_sb(sb, "variantes_perfume", "id, perfume_id")
    # Asignamos 'ofertas' con fetch_all_sb(sb, 'ofertas_actuales', 'id, ...
    ofertas = fetch_all_sb(sb, "ofertas_actuales", "id, variante_id, en_stock, estado")

    # Asignamos 'perf_por_var' con {int(v['id']): int(v['perfume_id']) for v ...
    perf_por_var = {int(v["id"]): int(v["perfume_id"]) for v in variantes}
    # Asignamos 'stock_por_perf' con defaultdict(int)
    stock_por_perf: Dict[int, int] = defaultdict(int)
    # Asignamos 'tot_por_perf' con defaultdict(int)
    tot_por_perf: Dict[int, int] = defaultdict(int)
    # Recorremos iterativamente cada 'o' en ofertas
    for o in ofertas:
        # Asignamos 'pid' con perf_por_var.get(int(o['variante_id']))
        pid = perf_por_var.get(int(o["variante_id"]))
        # Evaluamos la condición lógica (not pid) para controlar el flujo
        if not pid:
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Actualizamos acumulativamente el valor de 'tot_por_perf[pid]'
        tot_por_perf[pid] += 1
        # Evaluamos la condición lógica (o.get('estado') == 'activa' and o.get('en_stock')) para controlar el flujo
        if o.get("estado") == "activa" and o.get("en_stock"):
            # Actualizamos acumulativamente el valor de 'stock_por_perf[pid]'
            stock_por_perf[pid] += 1

    # Asignamos 'grupos' con defaultdict(list)
    grupos: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    # Recorremos iterativamente cada 'p' en perfumes
    for p in perfumes:
        # Asignamos 'm_can' con (normalizar_marca_canonica(p.get('marca') ...
        m_can = (normalizar_marca_canonica(p.get("marca") or "") or p.get("marca") or "").strip()
        # Asignamos 'tipo_raw' con (p.get('tipo') or '').strip()
        tipo_raw = (p.get("tipo") or "").strip()
        # Asignamos 'k_sin_gen' con clave_identidad_perfume(p.get('nombre') or...
        k_sin_gen = clave_identidad_perfume(
            p.get("nombre") or "",
            p.get("marca") or m_can,
            tipo_raw,
            incluir_genero_nombre=False,
        )
        # Evaluamos la condición lógica (not k_sin_gen) para controlar el flujo
        if not k_sin_gen:
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Ejecutamos instrucción: grupos[m_can.lower(), k_sin_gen, tipo_raw.lower()].a...
        grupos[(m_can.lower(), k_sin_gen, tipo_raw.lower())].append(p)

    # Asignamos 'grupos_duplicados' con {k: v for k, v in grupos.items() if len(v)...
    grupos_duplicados = {k: v for k, v in grupos.items() if len(v) > 1}
    # Asignamos 'grupos_seguros' con []
    grupos_seguros: List[Tuple[Tuple[str, str, str], List[Dict[str, Any]], str]] = []
    # Asignamos 'conflictos_manuales' con []
    conflictos_manuales: List[Dict[str, Any]] = []

    # Recorremos iterativamente cada '(key, miembros)' en sorted(grupos_duplicados.items(), key=lamb...
    for key, miembros in sorted(grupos_duplicados.items(), key=lambda x: x[0]):
        # Asignamos 'claves_con_gen' con {clave_identidad_perfume(m.get('nombre') o...
        claves_con_gen = {
            clave_identidad_perfume(
                m.get("nombre") or "",
                m.get("marca") or "",
                m.get("tipo") or "",
                incluir_genero_nombre=True,
            )
            for m in miembros
        }
        # Asignamos 'generos_efectivos' con [inferir_genero_explicito_nombre(m.get('no...
        generos_efectivos = [
            inferir_genero_explicito_nombre(m.get("nombre") or "", m.get("genero"))
            for m in miembros
        ]
        # Asignamos 'misma_clave_con_gen' con len(claves_con_gen) == 1
        misma_clave_con_gen = len(claves_con_gen) == 1
        # Asignamos '(es_compatible, genero_resuelto)' con evaluar_compatibilidad_generos_grupo(gener...
        es_compatible, genero_resuelto = evaluar_compatibilidad_generos_grupo(generos_efectivos)

        # Evaluamos la condición lógica (misma_clave_con_gen and es_compatible) para controlar el flujo
        if misma_clave_con_gen and es_compatible:
            # Ejecutamos instrucción: grupos_seguros.append((key, miembros, genero_resuelto))
            grupos_seguros.append((key, miembros, genero_resuelto))
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue

        # Asignamos 'por_gen_exp' con defaultdict(list)
        por_gen_exp: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # Asignamos 'unisex_por_subclave' con defaultdict(list)
        unisex_por_subclave: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # Recorremos iterativamente cada '(m, g_ef)' en zip(miembros, generos_efectivos)
        for m, g_ef in zip(miembros, generos_efectivos):
            # Evaluamos la condición lógica (g_ef in ('Hombre', 'Mujer')) para controlar el flujo
            if g_ef in ("Hombre", "Mujer"):
                # Ejecutamos instrucción: por_gen_exp[g_ef].append(m)
                por_gen_exp[g_ef].append(m)
            else:
                # Asignamos 'sk' con clave_identidad_perfume(m.get('nombre') or...
                sk = clave_identidad_perfume(
                    m.get("nombre") or "",
                    m.get("marca") or "",
                    m.get("tipo") or "",
                    incluir_genero_nombre=True,
                )
                # Ejecutamos instrucción: unisex_por_subclave[sk].append(m)
                unisex_por_subclave[sk].append(m)

        # Evaluamos la condición lógica (not ('Hombre' in por_gen_exp and 'Mujer' in por_gen_...) para controlar el flujo
        if not ("Hombre" in por_gen_exp and "Mujer" in por_gen_exp):
            # Asignamos 'gen_unico' con 'Hombre' if 'Hombre' in por_gen_exp else '...
            gen_unico = "Hombre" if "Hombre" in por_gen_exp else ("Mujer" if "Mujer" in por_gen_exp else None)
            # Evaluamos la condición lógica (gen_unico) para controlar el flujo
            if gen_unico:
                # Asignamos 'subclaves_exp' con {clave_identidad_perfume(x.get('nombre') o...
                subclaves_exp = {
                    clave_identidad_perfume(
                        x.get("nombre") or "",
                        x.get("marca") or "",
                        x.get("tipo") or "",
                        incluir_genero_nombre=True,
                    )
                    for x in por_gen_exp[gen_unico]
                }
                # Recorremos iterativamente cada '(sk, u_list)' en list(unisex_por_subclave.items())
                for sk, u_list in list(unisex_por_subclave.items()):
                    # Evaluamos la condición lógica (sk in subclaves_exp) para controlar el flujo
                    if sk in subclaves_exp:
                        # Ejecutamos instrucción: por_gen_exp[gen_unico].extend(u_list)
                        por_gen_exp[gen_unico].extend(u_list)
                        # Ejecutamos instrucción: del unisex_por_subclave[sk]
                        del unisex_por_subclave[sk]

        # Asignamos 'ids_donantes_subgrupo' con set()
        ids_donantes_subgrupo = set()
        # Recorremos iterativamente cada 'g_exp' en ('Hombre', 'Mujer')
        for g_exp in ("Hombre", "Mujer"):
            # Asignamos 'sub' con por_gen_exp.get(g_exp, [])
            sub = por_gen_exp.get(g_exp, [])
            # Evaluamos la condición lógica (len(sub) > 1) para controlar el flujo
            if len(sub) > 1:
                # Ejecutamos instrucción: grupos_seguros.append((key, sub, g_exp))
                grupos_seguros.append((key, sub, g_exp))
                # Asignamos 'sub_ord' con sorted(sub, key=lambda p: (stock_por_perf[...
                sub_ord = sorted(
                    sub,
                    key=lambda p: (stock_por_perf[int(p["id"])], tot_por_perf[int(p["id"])], -int(p["id"])),
                    reverse=True,
                )
                # Recorremos iterativamente cada 'd_sub' en sub_ord[1:]
                for d_sub in sub_ord[1:]:
                    # Ejecutamos instrucción: ids_donantes_subgrupo.add(int(d_sub['id']))
                    ids_donantes_subgrupo.add(int(d_sub["id"]))

        # Recorremos iterativamente cada '(_sk, u_sub)' en unisex_por_subclave.items()
        for _sk, u_sub in unisex_por_subclave.items():
            # Evaluamos la condición lógica (len(u_sub) > 1) para controlar el flujo
            if len(u_sub) > 1:
                # Ejecutamos instrucción: grupos_seguros.append((key, u_sub, 'Unisex'))
                grupos_seguros.append((key, u_sub, "Unisex"))
                # Asignamos 'u_ord' con sorted(u_sub, key=lambda p: (stock_por_per...
                u_ord = sorted(
                    u_sub,
                    key=lambda p: (stock_por_perf[int(p["id"])], tot_por_perf[int(p["id"])], -int(p["id"])),
                    reverse=True,
                )
                # Recorremos iterativamente cada 'd_u' en u_ord[1:]
                for d_u in u_ord[1:]:
                    # Ejecutamos instrucción: ids_donantes_subgrupo.add(int(d_u['id']))
                    ids_donantes_subgrupo.add(int(d_u["id"]))

        # Recorremos iterativamente cada 'm' en miembros
        for m in miembros:
            # Asignamos 'mid' con int(m['id'])
            mid = int(m["id"])
            # Evaluamos la condición lógica (mid in ids_donantes_subgrupo and apply_changes) para controlar el flujo
            if mid in ids_donantes_subgrupo and apply_changes:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Ejecutamos instrucción: conflictos_manuales.append({'marca_canon': key[0], '...
            conflictos_manuales.append({
                "marca_canon": key[0],
                "nombre_limpio": key[1],
                "tipo": key[2],
                "perfume_id": mid,
                "marca_bd": m.get("marca", ""),
                "nombre_bd": m.get("nombre", ""),
                "genero_bd": m.get("genero", ""),
                "ofertas_en_stock": stock_por_perf[mid],
                "ofertas_totales": tot_por_perf[mid],
                "motivo": "conflicto_genero_o_unisex_ambiguo",
            })

    # Exportar siempre CSV de revisión manual para conflictos Hombre vs Mujer
    manual_csv = REPO_ROOT / "scratch" / "revision_manual_duplicados.csv"
    # Ejecutamos instrucción: manual_csv.parent.mkdir(parents=True, exist_ok=True)
    manual_csv.parent.mkdir(parents=True, exist_ok=True)
    # Gestión automática de contexto y recursos para: manual_csv.open('w', encoding='utf-8', newline='')
    with manual_csv.open("w", encoding="utf-8", newline="") as f_man:
        # Asignamos 'campos' con ['marca_canon', 'nombre_limpio', 'tipo', '...
        campos = [
            "marca_canon", "nombre_limpio", "tipo", "perfume_id",
            "marca_bd", "nombre_bd", "genero_bd",
            "ofertas_en_stock", "ofertas_totales", "motivo",
        ]
        # Asignamos 'w' con csv.DictWriter(f_man, fieldnames=campos)
        w = csv.DictWriter(f_man, fieldnames=campos)
        # Ejecutamos instrucción: w.writeheader()
        w.writeheader()
        # Ejecutamos instrucción: w.writerows(conflictos_manuales)
        w.writerows(conflictos_manuales)

    # Asignamos 'now_iso' con datetime.now(timezone.utc).isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()
    # Asignamos 'cache_img' con {}
    cache_img: Dict[str, bool] = {}
    # Asignamos 'fusiones_ejecutadas' con []
    fusiones_ejecutadas: List[Dict[str, Any]] = []
    # Asignamos 'grupos_abortados' con 0
    grupos_abortados = 0

    # Mapa opcional de favoritos en metadata de Auth
    usuarios_auth_favs: List[Any] = []
    # Evaluamos la condición lógica (apply_changes) para controlar el flujo
    if apply_changes:
        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'usuarios_auth_favs' con [u for u in sb.auth.admin.list_users() or ...
            usuarios_auth_favs = [
                u for u in (sb.auth.admin.list_users() or [])
                if (getattr(u, "user_metadata", None) or {}).get("favoritos")
            ]
        except Exception as exc:
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.warning(f"No se pudo consultar auth.users metadata: {exc}")

    # Recorremos iterativamente cada '(key, miembros, genero_final)' en grupos_seguros
    for key, miembros, genero_final in grupos_seguros:
        # Asignamos 'ordenados' con sorted(miembros, key=lambda p: (stock_por_...
        ordenados = sorted(
            miembros,
            key=lambda p: (
                stock_por_perf[int(p["id"])],
                tot_por_perf[int(p["id"])],
                -int(p["id"]),
            ),
            reverse=True,
        )
        # Asignamos 'p_canon' con ordenados[0]
        p_canon = ordenados[0]
        # Asignamos 'donantes' con ordenados[1:]
        donantes = ordenados[1:]
        # Asignamos 'id_canon' con int(p_canon['id'])
        id_canon = int(p_canon["id"])
        # Asignamos 'marca_canon' con normalizar_marca_canonica(p_canon.get('mar...
        marca_canon = normalizar_marca_canonica(p_canon.get("marca") or "") or p_canon.get("marca") or ""
        # Asignamos 'cands_nombre' con [limpiar_nombre_perfume(m.get('nombre') or...
        cands_nombre = [
            limpiar_nombre_perfume(m.get("nombre") or "", m.get("marca") or marca_canon) or (m.get("nombre") or "").strip()
            for m in ordenados
        ]
        # Asignamos 'nombre_canon_limpio' con cands_nombre[0]
        nombre_canon_limpio = cands_nombre[0]
        # Recorremos iterativamente cada 'cn' en cands_nombre
        for cn in cands_nombre:
            # Evaluamos la condición lógica ('�' in cn or not cn) para controlar el flujo
            if "\ufffd" in cn or not cn:
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue
            # Asignamos 'tiene_amp' con '&' in cn and '&' not in nombre_canon_limpio
            tiene_amp = "&" in cn and "&" not in nombre_canon_limpio
            # Asignamos 'tiene_acento' con any((ord(ch) > 127 for ch in cn)) and (not...
            tiene_acento = any(ord(ch) > 127 for ch in cn) and not any(ord(ch) > 127 for ch in nombre_canon_limpio)
            # Asignamos 'es_mas_corto_limpio' con len(cn) < len(nombre_canon_limpio) and len...
            es_mas_corto_limpio = len(cn) < len(nombre_canon_limpio) and len(cn) >= 3
            # Evaluamos la condición lógica (tiene_amp or (tiene_acento and len(cn) <= len(nombre...) para controlar el flujo
            if tiene_amp or (tiene_acento and len(cn) <= len(nombre_canon_limpio) + 2) or ("\ufffd" in nombre_canon_limpio):
                # Asignamos 'nombre_canon_limpio' con cn
                nombre_canon_limpio = cn
            # Evaluamos la condición lógica (es_mas_corto_limpio and '&' not in nombre_canon_limp...) para controlar el flujo
            elif es_mas_corto_limpio and "&" not in nombre_canon_limpio and not any(ord(ch) > 127 for ch in nombre_canon_limpio):
                # Asignamos 'nombre_canon_limpio' con cn
                nombre_canon_limpio = cn

        # Evaluamos la condición lógica (not apply_changes) para controlar el flujo
        if not apply_changes:
            # Recorremos iterativamente cada 'd' en donantes
            for d in donantes:
                # Ejecutamos instrucción: fusiones_ejecutadas.append({'id_origen': int(d['id']...
                fusiones_ejecutadas.append({
                    "id_origen": int(d["id"]),
                    "id_destino": id_canon,
                    "marca": marca_canon,
                    "nombre_origen": d.get("nombre"),
                    "nombre_destino": nombre_canon_limpio,
                    "genero_origen": d.get("genero"),
                    "genero_final": genero_final,
                    "modo": "dry_run",
                })
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue

        # Elegir mejor imagen HTTP 200 dentro del grupo
        mejor_img = p_canon.get("imagen_url") or ""
        # Evaluamos la condición lógica (not es_imagen_valida_http(mejor_img, cache_img)) para controlar el flujo
        if not es_imagen_valida_http(mejor_img, cache_img):
            # Recorremos iterativamente cada 'd' en donantes
            for d in donantes:
                # Asignamos 'cand_img' con d.get('imagen_url') or ''
                cand_img = d.get("imagen_url") or ""
                # Evaluamos la condición lógica (es_imagen_valida_http(cand_img, cache_img)) para controlar el flujo
                if es_imagen_valida_http(cand_img, cache_img):
                    # Asignamos 'mejor_img' con cand_img
                    mejor_img = cand_img
                    # Interrumpimos el ciclo actual al cumplirse la condición de salida
                    break

        # Bloque try/except para manejo seguro de errores y resiliencia operativa
        try:
            # Asignamos 'detalles_donantes' con []
            detalles_donantes = []
            # Asignamos 'ids_donantes' con {int(d['id']) for d in donantes}
            ids_donantes = {int(d["id"]) for d in donantes}

            # Actualizar metadata de auth.users si algún usuario tenía un id_origen en favoritos
            for u_obj in usuarios_auth_favs:
                # Asignamos 'meta' con dict(getattr(u_obj, 'user_metadata', None)...
                meta = dict(getattr(u_obj, "user_metadata", None) or {})
                # Asignamos 'fav_list' con meta.get('favoritos') or []
                fav_list = meta.get("favoritos") or []
                # Evaluamos la condición lógica (any((int(x) in ids_donantes for x in fav_list if str...) para controlar el flujo
                if any(int(x) in ids_donantes for x in fav_list if str(x).isdigit()):
                    # Asignamos 'nueva_lista' con []
                    nueva_lista = []
                    # Asignamos 'vistos_f' con set()
                    vistos_f = set()
                    # Recorremos iterativamente cada 'x' en fav_list
                    for x in fav_list:
                        # Asignamos 'x_int' con id_canon if str(x).isdigit() and int(x) in...
                        x_int = id_canon if (str(x).isdigit() and int(x) in ids_donantes) else x
                        # Evaluamos la condición lógica (x_int not in vistos_f) para controlar el flujo
                        if x_int not in vistos_f:
                            # Ejecutamos instrucción: vistos_f.add(x_int)
                            vistos_f.add(x_int)
                            # Ejecutamos instrucción: nueva_lista.append(x_int)
                            nueva_lista.append(x_int)
                    # Asignamos 'meta['favoritos']' con nueva_lista
                    meta["favoritos"] = nueva_lista
                    # Ejecutamos instrucción: sb.auth.admin.update_user_by_id(u_obj.id, {'user_met...
                    sb.auth.admin.update_user_by_id(u_obj.id, {"user_metadata": meta})

            # Recorremos iterativamente cada 'd' en donantes
            for d in donantes:
                # Asignamos 'det' con fusionar_par_perfumes_sb(sb, d, p_canon, n...
                det = fusionar_par_perfumes_sb(sb, d, p_canon, now_iso=now_iso)
                # Ejecutamos instrucción: detalles_donantes.append((d, det))
                detalles_donantes.append((d, det))

            # Actualizar el perfume canónico DESPUÉS de borrar donantes (evita colisión en ux_perfumes_marca_nombre_tipo_genero)
            upd_canon: Dict[str, Any] = {
                "marca": marca_canon,
                "nombre": nombre_canon_limpio,
                "genero": genero_final,
            }
            # Evaluamos la condición lógica (mejor_img and mejor_img != (p_canon.get('imagen_url'...) para controlar el flujo
            if mejor_img and mejor_img != (p_canon.get("imagen_url") or ""):
                # Asignamos 'upd_canon['imagen_url']' con mejor_img
                upd_canon["imagen_url"] = mejor_img
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            sb.table("perfumes").update(upd_canon).eq("id", id_canon).execute()

            # Recorremos iterativamente cada '(d, det)' en detalles_donantes
            for d, det in detalles_donantes:
                # Asignamos 'registro_f' con {'id_origen': int(d['id']), 'id_destino': ...
                registro_f = {
                    "id_origen": int(d["id"]),
                    "id_destino": id_canon,
                    "marca_origen": d.get("marca"),
                    "nombre_origen": d.get("nombre"),
                    "genero_origen": d.get("genero"),
                    "fecha_fusion": now_iso,
                    "detalle": det,
                }
                # Ejecutamos instrucción: fusiones_ejecutadas.append(registro_f)
                fusiones_ejecutadas.append(registro_f)
                # Bloque try/except para manejo seguro de errores y resiliencia operativa
                try:
                    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
                    sb.table("fusiones_perfumes").insert(registro_f).execute()
                except Exception as exc_tbl:
                    # Registro de evento diagnóstico en la bitácora (logger) del sistema
                    logger.debug(f"Tabla fusiones_perfumes no disponible aún en remoto (guardado en JSON): {exc_tbl}")

        except Exception as exc_grp:
            # Actualizamos acumulativamente el valor de 'grupos_abortados'
            grupos_abortados += 1
            # Registro de evento diagnóstico en la bitácora (logger) del sistema
            logger.error(f"Grupo {key} ABORTADO por error: {exc_grp}")

    # Asignamos 'ts_tag' con datetime.now().strftime('%Y%m%d_%H%M%S')
    ts_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Asignamos 'modo_tag' con 'apply' if apply_changes else 'dry_run'
    modo_tag = "apply" if apply_changes else "dry_run"
    # Asignamos 'csv_backup_plan' con REPO_ROOT / 'scratch' / 'backups' / f'fusi...
    csv_backup_plan = REPO_ROOT / "scratch" / "backups" / f"fusion_perfumes_{modo_tag}_{ts_tag}.csv"
    # Ejecutamos instrucción: csv_backup_plan.parent.mkdir(parents=True, exist_ok=...
    csv_backup_plan.parent.mkdir(parents=True, exist_ok=True)
    # Evaluamos la condición lógica (fusiones_ejecutadas) para controlar el flujo
    if fusiones_ejecutadas:
        # Asignamos 'campos_f' con sorted({k for r in fusiones_ejecutadas for...
        campos_f = sorted({k for r in fusiones_ejecutadas for k in r.keys()})
        # Gestión automática de contexto y recursos para: csv_backup_plan.open('w', encoding='utf-8', new...
        with csv_backup_plan.open("w", encoding="utf-8", newline="") as f_csv:
            # Asignamos 'wf' con csv.DictWriter(f_csv, fieldnames=campos_f)
            wf = csv.DictWriter(f_csv, fieldnames=campos_f)
            # Ejecutamos instrucción: wf.writeheader()
            wf.writeheader()
            # Recorremos iterativamente cada 'r' en fusiones_ejecutadas
            for r in fusiones_ejecutadas:
                # Procesamiento de serialización o deserialización de estructura JSON
                wf.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in r.items()})

    # Evaluamos la condición lógica (apply_changes) para controlar el flujo
    if apply_changes:
        # Ejecutamos instrucción: limpiar_cache_catalogo()
        limpiar_cache_catalogo()
        # Asignamos 'hist_path' con APP_DIR / 'data' / 'reportes' / 'historial...
        hist_path = APP_DIR / "data" / "reportes" / "historial_fusiones.json"
        # Ejecutamos instrucción: hist_path.parent.mkdir(parents=True, exist_ok=True)
        hist_path.parent.mkdir(parents=True, exist_ok=True)
        # Asignamos 'prev_hist' con []
        prev_hist = []
        # Evaluamos la condición lógica (hist_path.exists()) para controlar el flujo
        if hist_path.exists():
            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Procesamiento de serialización o deserialización de estructura JSON
                prev_hist = json.loads(hist_path.read_text(encoding="utf-8"))
            except Exception:
                # Asignamos 'prev_hist' con []
                prev_hist = []
        # Ejecutamos instrucción: prev_hist.extend(fusiones_ejecutadas)
        prev_hist.extend(fusiones_ejecutadas)
        # Procesamiento de serialización o deserialización de estructura JSON
        hist_path.write_text(json.dumps(prev_hist, ensure_ascii=False, indent=2), encoding="utf-8")

    # Asignamos 'n_grupos_conflicto' con len({(r['marca_canon'], r['nombre_limpio']...
    n_grupos_conflicto = len({(r["marca_canon"], r["nombre_limpio"], r["tipo"]) for r in conflictos_manuales})
    # Ejecutamos instrucción: print('\n' + '=' * 76)
    print("\n" + "=" * 76)
    # Ejecutamos instrucción: print(f"REPORTE DE FUSIÓN SEGURA DE PERFUMES ({('APP...
    print(f"REPORTE DE FUSIÓN SEGURA DE PERFUMES ({'APPLY' if apply_changes else 'DRY-RUN'})")
    # Ejecutamos instrucción: print('=' * 76)
    print("=" * 76)
    # Ejecutamos instrucción: print(f'Grupos duplicados totales detectados : {len(...
    print(f"Grupos duplicados totales detectados : {len(grupos_duplicados)}")
    # Ejecutamos instrucción: print(f'Grupos/subgrupos seguros a fusionar : {len(g...
    print(f"Grupos/subgrupos seguros a fusionar  : {len(grupos_seguros)}")
    # Ejecutamos instrucción: print(f'Grupos Hom/Muj enviados a revisión : {n_grup...
    print(f"Grupos Hom/Muj enviados a revisión   : {n_grupos_conflicto} ({len(conflictos_manuales)} filas -> {manual_csv})")
    # Ejecutamos instrucción: print(f'Perfumes duplicados a fusionar/fus. : {len(f...
    print(f"Perfumes duplicados a fusionar/fus.  : {len(fusiones_ejecutadas)}")
    # Evaluamos la condición lógica (apply_changes) para controlar el flujo
    if apply_changes:
        # Ejecutamos instrucción: print(f'Grupos abortados por error : {grupos_abortad...
        print(f"Grupos abortados por error           : {grupos_abortados}")
    # Ejecutamos instrucción: print('=' * 76)
    print("=" * 76)

    # Retornamos el resultado procesado ({'grupos_totales': len(grupos_duplicados), 'gru...)
    return {
        "grupos_totales": len(grupos_duplicados),
        "grupos_seguros": len(grupos_seguros),
        "grupos_conflicto_genero": n_grupos_conflicto,
        "perfumes_fusionados": len(fusiones_ejecutadas),
        "grupos_abortados": grupos_abortados,
        "manual_csv": str(manual_csv),
    }


# Definición de función 'main' sin parámetros externos
def main() -> None:
    # Definición de argumento de línea de comandos (CLI) para ejecución parametrizada
    parser = argparse.ArgumentParser(description="Fusión segura de perfumes duplicados.")
    # Asignamos 'grp' con parser.add_mutually_exclusive_group()
    grp = parser.add_mutually_exclusive_group()
    # Ejecutamos instrucción: grp.add_argument('--dry-run', action='store_true', d...
    grp.add_argument("--dry-run", action="store_true", default=True, help="Simula fusiones sin escribir en BD (por defecto).")
    # Ejecutamos instrucción: grp.add_argument('--apply', action='store_true', hel...
    grp.add_argument("--apply", action="store_true", help="Ejecuta las fusiones seguras en Supabase.")
    # Asignamos 'args' con parser.parse_args()
    args = parser.parse_args()

    # Ejecutamos instrucción: ejecutar_fusion_perfumes(apply_changes=bool(args.app...
    ejecutar_fusion_perfumes(apply_changes=bool(args.apply))


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: main()
    main()
