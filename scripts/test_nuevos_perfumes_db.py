"""
Script de prueba y verificación de extracción y persistencia para nuevos perfumes.
Ejecuta el ciclo de scraping sobre los perfumes recién agregados y valida su inserción en la BD.
"""
import sys
import os
import time
import logging

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestNuevosPerfumes")

PERFUMES_TEST_IDS = [135, 136, 137, 138, 139, 140]


def probar_y_persistir_perfumes():
    sb = get_supabase(use_service_role=True)
    if not sb or not is_supabase_disponible():
        logger.error("Supabase no disponible para la prueba")
        return

    # 1. Obtener datos de los perfumes a probar
    res_p = sb.table("perfumes").select("id, nombre, marca, precio_referencia").in_("id", PERFUMES_TEST_IDS).execute()
    perfumes = res_p.data or []
    
    # 2. Obtener tiendas activas
    res_t = sb.table("tiendas").select("id, nombre, url_base, trust_score").execute()
    tiendas = res_t.data or []
    tiendas_map = {t["nombre"]: t["id"] for t in tiendas}

    session = crear_sesion_robusta()
    total_ofertas_registradas = 0

    print("================================================================================")
    print("INICIANDO EXTRACCIÓN Y PERSISTENCIA DE NUEVOS PERFUMES EN LA BASE DE DATOS")
    print("================================================================================")

    for p in perfumes:
        p_id = p["id"]
        p_nom = p["nombre"]
        p_marca = p["marca"]

        print(f"\n>>> AUDITANDO: {p_nom} ({p_marca}) [ID: {p_id}]")

        for tienda in tiendas:
            t_id = tienda["id"]
            t_nom = tienda["nombre"]

            if not tienda_comercializa_marca(t_nom, p_marca):
                continue

            time.sleep(0.3)
            variedades = []

            try:
                if t_nom in TIENDAS_SHOPIFY:
                    variedades = extraer_variedades_shopify(
                        session=session,
                        dominio=TIENDAS_SHOPIFY[t_nom],
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=100
                    )
                elif "falabella" in t_nom.lower():
                    variedades = extraer_variedades_falabella(
                        session=session,
                        url_directa=None,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=100
                    )
                elif "paris" in t_nom.lower():
                    variedades = extraer_variedades_paris(
                        session=session,
                        url_directa=None,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=100
                    )
                elif "ripley" in t_nom.lower():
                    variedades = extraer_variedades_ripley(
                        session=session,
                        url_directa=None,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=100
                    )

                if variedades:
                    for v in variedades:
                        if not v.get("exito"):
                            continue
                        
                        p_act = v["precio_actual"]
                        p_norm = v["precio_normal"]
                        vol = v["volumen_ml"]
                        url = v["url"]
                        en_stock = v.get("en_stock", True)

                        # Persistir en la base de datos (Supabase y SQLite)
                        res_reg = registrar_observacion_oferta({
                            "perfume_id": p_id,
                            "tienda_id": t_id,
                            "precio_actual": p_act,
                            "precio_normal": p_norm,
                            "url_producto": url,
                            "en_stock": en_stock,
                            "volumen_ml": vol,
                            "metodo_extraccion": v.get("metodo", "Auto-Scraper")
                        })

                        if res_reg:
                            total_ofertas_registradas += 1
                            print(f"  [GUARDADO] {t_nom:16} | {vol}ml | ${p_act:,} (Normal: ${p_norm:,}) | {v.get('metodo')}")

            except Exception as e:
                logger.warning(f"Error procesando {p_nom} en {t_nom}: {e}")

    print("\n================================================================================")
    print(f"RESUMEN: Total de ofertas y variedades guardadas exitosamente: {total_ofertas_registradas}")
    print("================================================================================")

    # 3. Consultar y verificar la vista de precios actuales en Supabase
    print("\n--- AUDITORÍA DE VERIFICACIÓN EN VISTA_PRECIOS_ACTUALES (SUPABASE) ---")
    res_vista = sb.table("vista_precios_actuales")\
        .select("perfume_id, tienda_nombre, volumen_ml, precio_actual, precio_normal, precio_por_ml, en_stock, url_producto")\
        .in_("perfume_id", PERFUMES_TEST_IDS)\
        .order("perfume_id")\
        .order("volumen_ml")\
        .execute()

    filas = res_vista.data or []
    print(f"Total registros encontrados en vista_precios_actuales: {len(filas)}")
    
    # Agrupar por perfume
    perfumes_dict = {p["id"]: p["nombre"] for p in perfumes}
    current_pid = None
    for f in filas:
        pid = f["perfume_id"]
        if pid != current_pid:
            current_pid = pid
            print(f"\nFragancia: {perfumes_dict.get(pid, f'ID {pid}')}")
            print(f"{'Tienda':<18} | {'Volumen':<8} | {'Precio':<10} | {'$/ml':<10} | {'Stock':<6}")
            print("-" * 65)
        print(f"{f['tienda_nombre']:<18} | {str(f['volumen_ml'])+'ml':<8} | ${f['precio_actual']:<9,}| ${f['precio_por_ml']:<9,}| {'SÍ' if f['en_stock'] else 'NO'}")


if __name__ == "__main__":
    probar_y_persistir_perfumes()
