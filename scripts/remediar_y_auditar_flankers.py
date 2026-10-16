"""
Script de remediación y auditoría de flankers, stock y URLs rotas:
1. Actualiza ofertas agotadas de Falabella para Bleu de Chanel (en_stock = False, estado = 'agotada').
2. Corrige URLs de Paris obsoletas para que apunten al buscador oficial o fichas vivas.
3. Limpia ofertas contaminadas de flankers en Acqua Di Gio (ID 7) y re-audita tanto ID 7 (EDT) como ID 96 (Profondo).
"""
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "APP")))

from backend.database import get_supabase, is_supabase_disponible, registrar_observacion_oferta, get_connection
from backend.scraper_periodico import (
    crear_sesion_robusta,
    extraer_variedades_shopify,
    extraer_variedades_falabella,
    extraer_variedades_paris,
    extraer_variedades_ripley,
    TIENDAS_SHOPIFY,
    tienda_comercializa_marca
)


def remediar_base_de_datos():
    sb = get_supabase(use_service_role=True)
    if not sb or not is_supabase_disponible():
        print("Error: Supabase no disponible")
        return

    print("=== 1. REMEDIANDO FALABELLA Y PARIS EN BLEU DE CHANEL (ID: 1) ===")
    # 1.1 Marcar Bleu de Chanel en Falabella como agotado
    res_fal_variantes = sb.table("variantes_perfume").select("id").eq("perfume_id", 1).execute().data or []
    fal_var_ids = [v["id"] for v in res_fal_variantes]
    if fal_var_ids:
        # Falabella tiene tienda_id = 1
        upd = sb.table("ofertas_actuales").update({"en_stock": False, "estado": "agotada"}).in_("variante_id", fal_var_ids).eq("tienda_id", 1).execute()
        print(f"Ofertas de Falabella marcadas como agotadas para Bleu de Chanel: {len(upd.data or [])}")

    # 1.2 Corregir URL de Paris en Bleu de Chanel (reemplazar link 434948999 por búsqueda oficial de Chanel Bleu)
    clean_paris_url = "https://www.paris.cl/search?q=Chanel%20Bleu%20de%20Chanel"
    if fal_var_ids:
        upd_par = sb.table("ofertas_actuales").update({"url_producto": clean_paris_url}).in_("variante_id", fal_var_ids).eq("tienda_id", 2).execute()
        print(f"URLs de Paris actualizadas a búsqueda oficial para Bleu de Chanel: {len(upd_par.data or [])}")

    print("\n=== 2. REMEDIANDO ACQUA DI GIO (ID: 7) Y ACQUA DI GIO PROFONDO (ID: 96) ===")
    # 2.1 Encontrar ofertas contaminadas en ID 7 que contengan 'profondo' o 'elixir' en su URL
    res_adg_variantes = sb.table("variantes_perfume").select("id").eq("perfume_id", 7).execute().data or []
    adg_var_ids = [v["id"] for v in res_adg_variantes]
    if adg_var_ids:
        # Eliminar o desactivar ofertas de flankers en ID 7
        res_of = sb.table("ofertas_actuales").select("id, url_producto, variante_id").in_("variante_id", adg_var_ids).execute().data or []
        flanker_ids_to_del = [
            o["id"] for o in res_of 
            if any(w in (o.get("url_producto") or "").lower() for w in ["profondo", "elixir", "profumo", "gioia"])
        ]
        if flanker_ids_to_del:
            sb.table("ofertas_actuales").delete().in_("id", flanker_ids_to_del).execute()
            print(f"Eliminadas {len(flanker_ids_to_del)} ofertas contaminadas de flankers en Acqua Di Gio ID 7.")

    # 2.2 Re-auditar en vivo Acqua Di Gio (ID 7) y Acqua Di Gio Profondo (ID 96)
    session = crear_sesion_robusta()
    res_tiendas = sb.table("tiendas").select("id, nombre, url_base").execute().data or []

    for target_id in [7, 96]:
        p_row = sb.table("perfumes").select("id, nombre, marca").eq("id", target_id).single().execute().data
        if not p_row:
            continue
        p_id = p_row["id"]
        p_nom = p_row["nombre"]
        p_marca = p_row["marca"]

        print(f"\n--- AUDITANDO EN VIVO CON GUARDIA DE FLANKERS: {p_nom} ({p_marca}) [ID: {p_id}] ---")
        for t in res_tiendas:
            t_id = t["id"]
            t_nom = t["nombre"]
            if not tienda_comercializa_marca(t_nom, p_marca):
                continue

            time.sleep(0.3)
            variedades = []
            try:
                if t_nom in TIENDAS_SHOPIFY:
                    variedades = extraer_variedades_shopify(session, TIENDAS_SHOPIFY[t_nom], p_nom, p_marca, 100)
                elif "falabella" in t_nom.lower():
                    variedades = extraer_variedades_falabella(session, None, p_nom, p_marca, 100)
                elif "paris" in t_nom.lower():
                    variedades = extraer_variedades_paris(session, None, p_nom, p_marca, 100)
                elif "ripley" in t_nom.lower():
                    variedades = extraer_variedades_ripley(session, None, p_nom, p_marca, 100)

                for v in variedades:
                    if not v.get("exito"):
                        continue
                    p_act = v["precio_actual"]
                    p_norm = v["precio_normal"]
                    vol = v["volumen_ml"]
                    url = v["url"]
                    en_stock = v.get("en_stock", True)

                    registrar_observacion_oferta({
                        "perfume_id": p_id,
                        "tienda_id": t_id,
                        "precio_actual": p_act,
                        "precio_normal": p_norm,
                        "url_producto": url,
                        "en_stock": en_stock,
                        "volumen_ml": vol,
                        "metodo_extraccion": v.get("metodo", "Auto-Scraper")
                    })
                    print(f"  [REGISTRADO] {t_nom:16} | {vol}ml | ${p_act:,} | Stock: {en_stock} | {url[:55]}...")

            except Exception as e:
                print(f"Error en {t_nom} para {p_nom}: {e}")

    print("\n=== VERIFICACIÓN FINAL EN VISTA_PRECIOS_ACTUALES ===")
    for pid, nombre in [(1, "Bleu de Chanel"), (7, "Acqua Di Gio EDT"), (96, "Acqua Di Gio Profondo")]:
        print(f"\nResultados vigentes para: {nombre} (ID: {pid})")
        res_v = sb.table("vista_precios_actuales").select("tienda_nombre, volumen_ml, precio_actual, precio_normal, precio_por_ml, url_producto").eq("perfume_id", pid).execute().data or []
        for r in res_v:
            print(f"  {r['tienda_nombre']:<16} | {r['volumen_ml']}ml | ${r['precio_actual']:,} | $/ml: ${r['precio_por_ml']:,} | {r['url_producto'][:60]}...")


if __name__ == "__main__":
    remediar_base_de_datos()
