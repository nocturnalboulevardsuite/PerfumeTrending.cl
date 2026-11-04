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

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_DIR = REPO_ROOT / "APP"
for _p in (str(APP_DIR), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.database import get_supabase, limpiar_cache_catalogo
from backend.normalizador import (
    clave_identidad_perfume,
    generos_compatibles,
    inferir_genero_explicito_nombre,
    limpiar_nombre_perfume,
    normalizar_genero,
    normalizar_marca_canonica,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("FusionarPerfumes")


# - ¿Qué hace esta función?:
#   Descarga paginadamente (de a 1.000 filas) una tabla completa desde Supabase.
def fetch_all_sb(sb: Any, table: str, select: str = "*") -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    offset = 0
    while True:
        res = sb.table(table).select(select).order("id", desc=False).range(offset, offset + 999).execute()
        batch = res.data or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return rows


# - ¿Qué hace esta función?:
#   Evalúa si las etiquetas de género de un grupo son compatibles para fusión automática:
#   - `Unisex` + `Hombre`/`Mujer` -> `(True, 'Hombre'|'Mujer')`
#   - Mismo género -> `(True, genero_normalizado)`
#   - `Hombre` vs `Mujer` -> `(False, '')` (conflicto real Pour Homme vs Pour Femme).
def evaluar_compatibilidad_generos_grupo(generos_raw: List[Optional[str]]) -> Tuple[bool, str]:
    acumulado = "Unisex"
    for g in generos_raw:
        ok, res = generos_compatibles(acumulado, g)
        if not ok:
            return False, ""
        acumulado = res
    return True, acumulado


# - ¿Qué hace esta función?:
#   Comprueba mediante HEAD/GET ligero si una `imagen_url` responde HTTP 200 válido
#   y no corresponde al placeholder genérico de Unsplash.
def es_imagen_valida_http(url: Optional[str], cache_http: Dict[str, bool]) -> bool:
    u = str(url or "").strip()
    if not u.startswith("http") or "images.unsplash.com/photo-1522337360788" in u:
        return False
    if u in cache_http:
        return cache_http[u]
    ok = False
    try:
        r = requests.head(u, timeout=5, allow_redirects=True)
        if r.status_code == 200:
            ok = True
        elif r.status_code in (403, 405):
            rg = requests.get(u, timeout=6, stream=True)
            ok = rg.status_code == 200
            rg.close()
    except Exception:
        ok = False
    cache_http[u] = ok
    return ok


# - ¿Qué hace esta función?:
#   Determina si `oferta_cand` debe prevalecer sobre `oferta_actual` cuando ambas
#   colisionan en `UNIQUE(variante_id, tienda_id)`, priorizando stock activo y frescura.
def _es_mejor_oferta(oferta_cand: Dict[str, Any], oferta_actual: Dict[str, Any]) -> bool:
    key_cand = (
        1 if (oferta_cand.get("estado") == "activa" and oferta_cand.get("en_stock")) else 0,
        1 if oferta_cand.get("estado") == "activa" else 0,
        str(oferta_cand.get("ultima_verificacion_exitosa") or ""),
        -int(oferta_cand.get("precio_actual") or 999999999),
    )
    key_act = (
        1 if (oferta_actual.get("estado") == "activa" and oferta_actual.get("en_stock")) else 0,
        1 if oferta_actual.get("estado") == "activa" else 0,
        str(oferta_actual.get("ultima_verificacion_exitosa") or ""),
        -int(oferta_actual.get("precio_actual") or 999999999),
    )
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
    id_origen = int(p_origen["id"])
    id_destino = int(p_destino["id"])
    if id_origen == id_destino:
        raise ValueError(f"id_origen == id_destino ({id_origen})")

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
    if favs_orig:
        favs_dest = sb.table("favoritos_usuario").select("usuario_id").eq("perfume_id", id_destino).execute().data or []
        usuarios_ya_en_dest = {str(f["usuario_id"]) for f in favs_dest}
        for fv in favs_orig:
            uid = str(fv["usuario_id"])
            if uid in usuarios_ya_en_dest:
                sb.table("favoritos_usuario").delete().eq("id", fv["id"]).execute()
            else:
                sb.table("favoritos_usuario").update({"perfume_id": id_destino}).eq("id", fv["id"]).execute()
                usuarios_ya_en_dest.add(uid)
            resumen_par["favoritos_reasignados"] += 1

    # 1b. Reasignar tablas olfativas con FK `ON DELETE RESTRICT`
    # - `perfume_notas`: UNIQUE(perfume_id, nota_id, etapa)
    notas_orig = sb.table("perfume_notas").select("id, nota_id, etapa").eq("perfume_id", id_origen).execute().data or []
    if notas_orig:
        notas_dest = sb.table("perfume_notas").select("nota_id, etapa").eq("perfume_id", id_destino).execute().data or []
        claves_nota_dest = {(int(n["nota_id"]), str(n.get("etapa") or "desconocida")) for n in notas_dest}
        for nr in notas_orig:
            k_nota = (int(nr["nota_id"]), str(nr.get("etapa") or "desconocida"))
            if k_nota in claves_nota_dest:
                sb.table("perfume_notas").delete().eq("id", nr["id"]).execute()
            else:
                sb.table("perfume_notas").update({"perfume_id": id_destino, "updated_at": now_iso}).eq("id", nr["id"]).execute()
                claves_nota_dest.add(k_nota)
            resumen_par["notas_reasignadas"] += 1

    # - `perfume_familias_olfativas`: UNIQUE(perfume_id, familia_id) + partial unique (perfume_id) WHERE es_principal = true
    fams_orig = sb.table("perfume_familias_olfativas").select("id, familia_id, es_principal").eq("perfume_id", id_origen).execute().data or []
    if fams_orig:
        fams_dest = sb.table("perfume_familias_olfativas").select("familia_id, es_principal").eq("perfume_id", id_destino).execute().data or []
        fams_ya_dest = {int(f["familia_id"]) for f in fams_dest}
        tiene_principal_dest = any(bool(f.get("es_principal")) for f in fams_dest)
        for fr in fams_orig:
            fid = int(fr["familia_id"])
            if fid in fams_ya_dest:
                sb.table("perfume_familias_olfativas").delete().eq("id", fr["id"]).execute()
            else:
                es_princ_nuevo = False if tiene_principal_dest else bool(fr.get("es_principal"))
                sb.table("perfume_familias_olfativas").update({
                    "perfume_id": id_destino,
                    "es_principal": es_princ_nuevo,
                }).eq("id", fr["id"]).execute()
                fams_ya_dest.add(fid)
                if es_princ_nuevo:
                    tiene_principal_dest = True
            resumen_par["notas_reasignadas"] += 1

    # - `perfume_notas_importacion`: UNIQUE(perfume_id)
    imp_orig = sb.table("perfume_notas_importacion").select("id, perfume_id").eq("perfume_id", id_origen).execute().data or []
    if imp_orig:
        imp_dest = sb.table("perfume_notas_importacion").select("id").eq("perfume_id", id_destino).limit(1).execute().data or []
        ya_tiene_imp = bool(imp_dest)
        for ir in imp_orig:
            if ya_tiene_imp:
                sb.table("perfume_notas_importacion").delete().eq("id", ir["id"]).execute()
            else:
                sb.table("perfume_notas_importacion").update({
                    "perfume_id": id_destino,
                    "updated_at": now_iso,
                }).eq("id", ir["id"]).execute()
                ya_tiene_imp = True
            resumen_par["notas_reasignadas"] += 1

    # 2. Reasignar y consolidar `variantes_perfume`, `ofertas_actuales` y `precios_registro`
    vars_dest = sb.table("variantes_perfume").select("*").eq("perfume_id", id_destino).execute().data or []
    vars_orig = sb.table("variantes_perfume").select("*").eq("perfume_id", id_origen).execute().data or []

    for v_orig in vars_orig:
        vid_orig = int(v_orig["id"])
        vol_orig = float(v_orig.get("volumen_ml") or 100.0)
        fmt_orig = str(v_orig.get("formato") or "regular").lower()

        v_match = next(
            (
                vd for vd in vars_dest
                if abs(float(vd.get("volumen_ml") or 100.0) - vol_orig) <= 1.0
                and str(vd.get("formato") or "regular").lower() == fmt_orig
            ),
            None,
        )

        if v_match is None:
            # No existe esa talla/formato en el canónico: mover la variante entera
            sb.table("variantes_perfume").update({
                "perfume_id": id_destino,
                "updated_at": now_iso,
            }).eq("id", vid_orig).execute()
            sb.table("precios_registro").update({"perfume_id": id_destino}).eq("variante_id", vid_orig).execute()
            vars_dest.append(dict(v_orig, perfume_id=id_destino))
            resumen_par["variantes_movidas"] += 1
        else:
            # Ya existe la variante equivalente en el canónico: consolidar ofertas e historial y borrar v_orig
            vid_dest = int(v_match["id"])
            ofs_dest = sb.table("ofertas_actuales").select("*").eq("variante_id", vid_dest).execute().data or []
            ofs_por_tienda = {int(od["tienda_id"]): od for od in ofs_dest}
            ofs_orig = sb.table("ofertas_actuales").select("*").eq("variante_id", vid_orig).execute().data or []

            for oo in ofs_orig:
                tid = int(oo["tienda_id"])
                oid_orig = int(oo["id"])
                od_exist = ofs_por_tienda.get(tid)
                if od_exist is not None:
                    if _es_mejor_oferta(oo, od_exist):
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
                    sb.table("ofertas_actuales").delete().eq("id", oid_orig).execute()
                    resumen_par["ofertas_deduplicadas"] += 1
                else:
                    sb.table("ofertas_actuales").update({
                        "variante_id": vid_dest,
                        "updated_at": now_iso,
                    }).eq("id", oid_orig).execute()
                    ofs_por_tienda[tid] = dict(oo, variante_id=vid_dest)
                    resumen_par["ofertas_movidas"] += 1

            sb.table("precios_registro").update({
                "variante_id": vid_dest,
                "perfume_id": id_destino,
            }).eq("variante_id", vid_orig).execute()

            # Verificar 0 referencias antes de borrar la variante duplicada
            rem_vo = sb.table("ofertas_actuales").select("id").eq("variante_id", vid_orig).limit(1).execute().data or []
            rem_vp = sb.table("precios_registro").select("id").eq("variante_id", vid_orig).limit(1).execute().data or []
            if rem_vo or rem_vp:
                raise RuntimeError(
                    f"Abortando: variante #{vid_orig} aún mantiene referencias "
                    f"(ofertas={len(rem_vo)}, precios_registro={len(rem_vp)})"
                )
            sb.table("variantes_perfume").delete().eq("id", vid_orig).execute()
            resumen_par["variantes_consolidadas"] += 1

    # Reasignar cualquier fila residual de `precios_registro` con `perfume_id = id_origen`
    sb.table("precios_registro").update({"perfume_id": id_destino}).eq("perfume_id", id_origen).execute()

    # 3. Verificación explícita de CERO filas huérfanas antes del DELETE en `perfumes`
    chk_v = sb.table("variantes_perfume").select("id").eq("perfume_id", id_origen).limit(1).execute().data or []
    chk_pr = sb.table("precios_registro").select("id").eq("perfume_id", id_origen).limit(1).execute().data or []
    chk_fv = sb.table("favoritos_usuario").select("id").eq("perfume_id", id_origen).limit(1).execute().data or []
    chk_pn = sb.table("perfume_notas").select("id").eq("perfume_id", id_origen).limit(1).execute().data or []
    chk_pf = sb.table("perfume_familias_olfativas").select("id").eq("perfume_id", id_origen).limit(1).execute().data or []
    chk_pi = sb.table("perfume_notas_importacion").select("id").eq("perfume_id", id_origen).limit(1).execute().data or []
    if chk_v or chk_pr or chk_fv or chk_pn or chk_pf or chk_pi:
        raise RuntimeError(
            f"Abortando DELETE de perfume #{id_origen}: referencias activas "
            f"(variantes={len(chk_v)}, precios={len(chk_pr)}, favoritos={len(chk_fv)}, "
            f"notas={len(chk_pn)}, familias={len(chk_pf)}, notas_imp={len(chk_pi)})"
        )

    sb.table("perfumes").delete().eq("id", id_origen).execute()
    return resumen_par


# - ¿Qué hace esta función principal?:
#   Escanea `perfumes`, separa grupos seguros de conflictos `Hombre` vs `Mujer`,
#   exporta el CSV de revisión humana y ejecuta (en `--apply`) la fusión completa
#   dejando trazabilidad en `fusiones_perfumes` y `historial_fusiones.json`.
def ejecutar_fusion_perfumes(apply_changes: bool = False) -> Dict[str, Any]:
    sb = get_supabase(use_service_role=True)
    if not sb:
        raise RuntimeError("No se pudo obtener cliente Supabase con service_role.")

    perfumes = fetch_all_sb(sb, "perfumes", "*")
    variantes = fetch_all_sb(sb, "variantes_perfume", "id, perfume_id")
    ofertas = fetch_all_sb(sb, "ofertas_actuales", "id, variante_id, en_stock, estado")

    perf_por_var = {int(v["id"]): int(v["perfume_id"]) for v in variantes}
    stock_por_perf: Dict[int, int] = defaultdict(int)
    tot_por_perf: Dict[int, int] = defaultdict(int)
    for o in ofertas:
        pid = perf_por_var.get(int(o["variante_id"]))
        if not pid:
            continue
        tot_por_perf[pid] += 1
        if o.get("estado") == "activa" and o.get("en_stock"):
            stock_por_perf[pid] += 1

    grupos: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for p in perfumes:
        m_can = (normalizar_marca_canonica(p.get("marca") or "") or p.get("marca") or "").strip()
        tipo_raw = (p.get("tipo") or "").strip()
        k_sin_gen = clave_identidad_perfume(
            p.get("nombre") or "",
            p.get("marca") or m_can,
            tipo_raw,
            incluir_genero_nombre=False,
        )
        if not k_sin_gen:
            continue
        grupos[(m_can.lower(), k_sin_gen, tipo_raw.lower())].append(p)

    grupos_duplicados = {k: v for k, v in grupos.items() if len(v) > 1}
    grupos_seguros: List[Tuple[Tuple[str, str, str], List[Dict[str, Any]], str]] = []
    conflictos_manuales: List[Dict[str, Any]] = []

    for key, miembros in sorted(grupos_duplicados.items(), key=lambda x: x[0]):
        claves_con_gen = {
            clave_identidad_perfume(
                m.get("nombre") or "",
                m.get("marca") or "",
                m.get("tipo") or "",
                incluir_genero_nombre=True,
            )
            for m in miembros
        }
        generos_efectivos = [
            inferir_genero_explicito_nombre(m.get("nombre") or "", m.get("genero"))
            for m in miembros
        ]
        misma_clave_con_gen = len(claves_con_gen) == 1
        es_compatible, genero_resuelto = evaluar_compatibilidad_generos_grupo(generos_efectivos)

        if misma_clave_con_gen and es_compatible:
            grupos_seguros.append((key, miembros, genero_resuelto))
            continue

        por_gen_exp: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        unisex_por_subclave: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for m, g_ef in zip(miembros, generos_efectivos):
            if g_ef in ("Hombre", "Mujer"):
                por_gen_exp[g_ef].append(m)
            else:
                sk = clave_identidad_perfume(
                    m.get("nombre") or "",
                    m.get("marca") or "",
                    m.get("tipo") or "",
                    incluir_genero_nombre=True,
                )
                unisex_por_subclave[sk].append(m)

        if not ("Hombre" in por_gen_exp and "Mujer" in por_gen_exp):
            gen_unico = "Hombre" if "Hombre" in por_gen_exp else ("Mujer" if "Mujer" in por_gen_exp else None)
            if gen_unico:
                subclaves_exp = {
                    clave_identidad_perfume(
                        x.get("nombre") or "",
                        x.get("marca") or "",
                        x.get("tipo") or "",
                        incluir_genero_nombre=True,
                    )
                    for x in por_gen_exp[gen_unico]
                }
                for sk, u_list in list(unisex_por_subclave.items()):
                    if sk in subclaves_exp:
                        por_gen_exp[gen_unico].extend(u_list)
                        del unisex_por_subclave[sk]

        ids_donantes_subgrupo = set()
        for g_exp in ("Hombre", "Mujer"):
            sub = por_gen_exp.get(g_exp, [])
            if len(sub) > 1:
                grupos_seguros.append((key, sub, g_exp))
                sub_ord = sorted(
                    sub,
                    key=lambda p: (stock_por_perf[int(p["id"])], tot_por_perf[int(p["id"])], -int(p["id"])),
                    reverse=True,
                )
                for d_sub in sub_ord[1:]:
                    ids_donantes_subgrupo.add(int(d_sub["id"]))

        for _sk, u_sub in unisex_por_subclave.items():
            if len(u_sub) > 1:
                grupos_seguros.append((key, u_sub, "Unisex"))
                u_ord = sorted(
                    u_sub,
                    key=lambda p: (stock_por_perf[int(p["id"])], tot_por_perf[int(p["id"])], -int(p["id"])),
                    reverse=True,
                )
                for d_u in u_ord[1:]:
                    ids_donantes_subgrupo.add(int(d_u["id"]))

        for m in miembros:
            mid = int(m["id"])
            if mid in ids_donantes_subgrupo and apply_changes:
                continue
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
    manual_csv.parent.mkdir(parents=True, exist_ok=True)
    with manual_csv.open("w", encoding="utf-8", newline="") as f_man:
        campos = [
            "marca_canon", "nombre_limpio", "tipo", "perfume_id",
            "marca_bd", "nombre_bd", "genero_bd",
            "ofertas_en_stock", "ofertas_totales", "motivo",
        ]
        w = csv.DictWriter(f_man, fieldnames=campos)
        w.writeheader()
        w.writerows(conflictos_manuales)

    now_iso = datetime.now(timezone.utc).isoformat()
    cache_img: Dict[str, bool] = {}
    fusiones_ejecutadas: List[Dict[str, Any]] = []
    grupos_abortados = 0

    # Mapa opcional de favoritos en metadata de Auth
    usuarios_auth_favs: List[Any] = []
    if apply_changes:
        try:
            usuarios_auth_favs = [
                u for u in (sb.auth.admin.list_users() or [])
                if (getattr(u, "user_metadata", None) or {}).get("favoritos")
            ]
        except Exception as exc:
            logger.warning(f"No se pudo consultar auth.users metadata: {exc}")

    for key, miembros, genero_final in grupos_seguros:
        ordenados = sorted(
            miembros,
            key=lambda p: (
                stock_por_perf[int(p["id"])],
                tot_por_perf[int(p["id"])],
                -int(p["id"]),
            ),
            reverse=True,
        )
        p_canon = ordenados[0]
        donantes = ordenados[1:]
        id_canon = int(p_canon["id"])
        marca_canon = normalizar_marca_canonica(p_canon.get("marca") or "") or p_canon.get("marca") or ""
        cands_nombre = [
            limpiar_nombre_perfume(m.get("nombre") or "", m.get("marca") or marca_canon) or (m.get("nombre") or "").strip()
            for m in ordenados
        ]
        nombre_canon_limpio = cands_nombre[0]
        for cn in cands_nombre:
            if "\ufffd" in cn or not cn:
                continue
            tiene_amp = "&" in cn and "&" not in nombre_canon_limpio
            tiene_acento = any(ord(ch) > 127 for ch in cn) and not any(ord(ch) > 127 for ch in nombre_canon_limpio)
            es_mas_corto_limpio = len(cn) < len(nombre_canon_limpio) and len(cn) >= 3
            if tiene_amp or (tiene_acento and len(cn) <= len(nombre_canon_limpio) + 2) or ("\ufffd" in nombre_canon_limpio):
                nombre_canon_limpio = cn
            elif es_mas_corto_limpio and "&" not in nombre_canon_limpio and not any(ord(ch) > 127 for ch in nombre_canon_limpio):
                nombre_canon_limpio = cn

        if not apply_changes:
            for d in donantes:
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
            continue

        # Elegir mejor imagen HTTP 200 dentro del grupo
        mejor_img = p_canon.get("imagen_url") or ""
        if not es_imagen_valida_http(mejor_img, cache_img):
            for d in donantes:
                cand_img = d.get("imagen_url") or ""
                if es_imagen_valida_http(cand_img, cache_img):
                    mejor_img = cand_img
                    break

        try:
            detalles_donantes = []
            ids_donantes = {int(d["id"]) for d in donantes}

            # Actualizar metadata de auth.users si algún usuario tenía un id_origen en favoritos
            for u_obj in usuarios_auth_favs:
                meta = dict(getattr(u_obj, "user_metadata", None) or {})
                fav_list = meta.get("favoritos") or []
                if any(int(x) in ids_donantes for x in fav_list if str(x).isdigit()):
                    nueva_lista = []
                    vistos_f = set()
                    for x in fav_list:
                        x_int = id_canon if (str(x).isdigit() and int(x) in ids_donantes) else x
                        if x_int not in vistos_f:
                            vistos_f.add(x_int)
                            nueva_lista.append(x_int)
                    meta["favoritos"] = nueva_lista
                    sb.auth.admin.update_user_by_id(u_obj.id, {"user_metadata": meta})

            for d in donantes:
                det = fusionar_par_perfumes_sb(sb, d, p_canon, now_iso=now_iso)
                detalles_donantes.append((d, det))

            # Actualizar el perfume canónico DESPUÉS de borrar donantes (evita colisión en ux_perfumes_marca_nombre_tipo_genero)
            upd_canon: Dict[str, Any] = {
                "marca": marca_canon,
                "nombre": nombre_canon_limpio,
                "genero": genero_final,
            }
            if mejor_img and mejor_img != (p_canon.get("imagen_url") or ""):
                upd_canon["imagen_url"] = mejor_img
            sb.table("perfumes").update(upd_canon).eq("id", id_canon).execute()

            for d, det in detalles_donantes:
                registro_f = {
                    "id_origen": int(d["id"]),
                    "id_destino": id_canon,
                    "marca_origen": d.get("marca"),
                    "nombre_origen": d.get("nombre"),
                    "genero_origen": d.get("genero"),
                    "fecha_fusion": now_iso,
                    "detalle": det,
                }
                fusiones_ejecutadas.append(registro_f)
                try:
                    sb.table("fusiones_perfumes").insert(registro_f).execute()
                except Exception as exc_tbl:
                    logger.debug(f"Tabla fusiones_perfumes no disponible aún en remoto (guardado en JSON): {exc_tbl}")

        except Exception as exc_grp:
            grupos_abortados += 1
            logger.error(f"Grupo {key} ABORTADO por error: {exc_grp}")

    ts_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    modo_tag = "apply" if apply_changes else "dry_run"
    csv_backup_plan = REPO_ROOT / "scratch" / "backups" / f"fusion_perfumes_{modo_tag}_{ts_tag}.csv"
    csv_backup_plan.parent.mkdir(parents=True, exist_ok=True)
    if fusiones_ejecutadas:
        campos_f = sorted({k for r in fusiones_ejecutadas for k in r.keys()})
        with csv_backup_plan.open("w", encoding="utf-8", newline="") as f_csv:
            wf = csv.DictWriter(f_csv, fieldnames=campos_f)
            wf.writeheader()
            for r in fusiones_ejecutadas:
                wf.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in r.items()})

    if apply_changes:
        limpiar_cache_catalogo()
        hist_path = APP_DIR / "data" / "reportes" / "historial_fusiones.json"
        hist_path.parent.mkdir(parents=True, exist_ok=True)
        prev_hist = []
        if hist_path.exists():
            try:
                prev_hist = json.loads(hist_path.read_text(encoding="utf-8"))
            except Exception:
                prev_hist = []
        prev_hist.extend(fusiones_ejecutadas)
        hist_path.write_text(json.dumps(prev_hist, ensure_ascii=False, indent=2), encoding="utf-8")

    n_grupos_conflicto = len({(r["marca_canon"], r["nombre_limpio"], r["tipo"]) for r in conflictos_manuales})
    print("\n" + "=" * 76)
    print(f"REPORTE DE FUSIÓN SEGURA DE PERFUMES ({'APPLY' if apply_changes else 'DRY-RUN'})")
    print("=" * 76)
    print(f"Grupos duplicados totales detectados : {len(grupos_duplicados)}")
    print(f"Grupos/subgrupos seguros a fusionar  : {len(grupos_seguros)}")
    print(f"Grupos Hom/Muj enviados a revisión   : {n_grupos_conflicto} ({len(conflictos_manuales)} filas -> {manual_csv})")
    print(f"Perfumes duplicados a fusionar/fus.  : {len(fusiones_ejecutadas)}")
    if apply_changes:
        print(f"Grupos abortados por error           : {grupos_abortados}")
    print("=" * 76)

    return {
        "grupos_totales": len(grupos_duplicados),
        "grupos_seguros": len(grupos_seguros),
        "grupos_conflicto_genero": n_grupos_conflicto,
        "perfumes_fusionados": len(fusiones_ejecutadas),
        "grupos_abortados": grupos_abortados,
        "manual_csv": str(manual_csv),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fusión segura de perfumes duplicados.")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--dry-run", action="store_true", default=True, help="Simula fusiones sin escribir en BD (por defecto).")
    grp.add_argument("--apply", action="store_true", help="Ejecuta las fusiones seguras en Supabase.")
    args = parser.parse_args()

    ejecutar_fusion_perfumes(apply_changes=bool(args.apply))


if __name__ == "__main__":
    main()
