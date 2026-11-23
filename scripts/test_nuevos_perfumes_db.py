"""
Script de prueba y verificación de extracción y persistencia para nuevos perfumes.
Ejecuta el ciclo de scraping sobre los perfumes recién agregados y valida su inserción en la BD.
"""
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (time)
import time
# Importación de librería estándar o dependencia externa (logging)
import logging

# Ejecutamos instrucción: sys.path.insert(0, os.path.abspath(os.path.join(os.p...
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "APP")))

# Importación de componentes (get_supabase, is_supabase_disponible, registrar_observacion_oferta, get_connection) desde el módulo 'backend.database'
from backend.database import get_supabase, is_supabase_disponible, registrar_observacion_oferta, get_connection
# Importación de componentes (crear_sesion_robusta, extraer_variedades_shopify, extraer_variedades_falabella, extraer_variedades_paris, ...) desde el módulo 'backend.scraper_periodico'
from backend.scraper_periodico import (
    crear_sesion_robusta,
    extraer_variedades_shopify,
    extraer_variedades_falabella,
    extraer_variedades_paris,
    extraer_variedades_ripley,
    TIENDAS_SHOPIFY,
    tienda_comercializa_marca
)

# Ejecutamos instrucción: logging.basicConfig(level=logging.INFO, format='%(as...
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
# Asignamos 'logger' con logging.getLogger('TestNuevosPerfumes')
logger = logging.getLogger("TestNuevosPerfumes")

# Asignamos 'PERFUMES_TEST_IDS' con [135, 136, 137, 138, 139, 140]
PERFUMES_TEST_IDS = [135, 136, 137, 138, 139, 140]


# Definición de función 'probar_y_persistir_perfumes' sin parámetros externos
def probar_y_persistir_perfumes():
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (not sb or not is_supabase_disponible()) para controlar el flujo
    if not sb or not is_supabase_disponible():
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        logger.error("Supabase no disponible para la prueba")
        # Finalizamos la ejecución de la función retornando None
        return

    # 1. Obtener datos de los perfumes a probar
    res_p = sb.table("perfumes").select("id, nombre, marca, precio_referencia").in_("id", PERFUMES_TEST_IDS).execute()
    # Asignamos 'perfumes' con res_p.data or []
    perfumes = res_p.data or []
    
    # 2. Obtener tiendas activas
    res_t = sb.table("tiendas").select("id, nombre, url_base, trust_score").execute()
    # Asignamos 'tiendas' con res_t.data or []
    tiendas = res_t.data or []
    # Asignamos 'tiendas_map' con {t['nombre']: t['id'] for t in tiendas}
    tiendas_map = {t["nombre"]: t["id"] for t in tiendas}

    # Asignamos 'session' con crear_sesion_robusta()
    session = crear_sesion_robusta()
    # Asignamos 'total_ofertas_registradas' con 0
    total_ofertas_registradas = 0

    # Ejecutamos instrucción: print('=============================================...
    print("================================================================================")
    # Ejecutamos instrucción: print('INICIANDO EXTRACCIÓN Y PERSISTENCIA DE NUEVOS...
    print("INICIANDO EXTRACCIÓN Y PERSISTENCIA DE NUEVOS PERFUMES EN LA BASE DE DATOS")
    # Ejecutamos instrucción: print('=============================================...
    print("================================================================================")

    # Recorremos iterativamente cada 'p' en perfumes
    for p in perfumes:
        # Asignamos 'p_id' con p['id']
        p_id = p["id"]
        # Asignamos 'p_nom' con p['nombre']
        p_nom = p["nombre"]
        # Asignamos 'p_marca' con p['marca']
        p_marca = p["marca"]

        # Ejecutamos instrucción: print(f'\n>>> AUDITANDO: {p_nom} ({p_marca}) [ID: {p...
        print(f"\n>>> AUDITANDO: {p_nom} ({p_marca}) [ID: {p_id}]")

        # Recorremos iterativamente cada 'tienda' en tiendas
        for tienda in tiendas:
            # Asignamos 't_id' con tienda['id']
            t_id = tienda["id"]
            # Asignamos 't_nom' con tienda['nombre']
            t_nom = tienda["nombre"]

            # Evaluamos la condición lógica (not tienda_comercializa_marca(t_nom, p_marca)) para controlar el flujo
            if not tienda_comercializa_marca(t_nom, p_marca):
                # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                continue

            # Ejecutamos instrucción: time.sleep(0.3)
            time.sleep(0.3)
            # Asignamos 'variedades' con []
            variedades = []

            # Bloque try/except para manejo seguro de errores y resiliencia operativa
            try:
                # Evaluamos la condición lógica (t_nom in TIENDAS_SHOPIFY) para controlar el flujo
                if t_nom in TIENDAS_SHOPIFY:
                    # Asignamos 'variedades' con extraer_variedades_shopify(session=session...
                    variedades = extraer_variedades_shopify(
                        session=session,
                        dominio=TIENDAS_SHOPIFY[t_nom],
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=100
                    )
                # Evaluamos la condición lógica ('falabella' in t_nom.lower()) para controlar el flujo
                elif "falabella" in t_nom.lower():
                    # Asignamos 'variedades' con extraer_variedades_falabella(session=sessi...
                    variedades = extraer_variedades_falabella(
                        session=session,
                        url_directa=None,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=100
                    )
                # Evaluamos la condición lógica ('paris' in t_nom.lower()) para controlar el flujo
                elif "paris" in t_nom.lower():
                    # Asignamos 'variedades' con extraer_variedades_paris(session=session, ...
                    variedades = extraer_variedades_paris(
                        session=session,
                        url_directa=None,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=100
                    )
                # Evaluamos la condición lógica ('ripley' in t_nom.lower()) para controlar el flujo
                elif "ripley" in t_nom.lower():
                    # Asignamos 'variedades' con extraer_variedades_ripley(session=session,...
                    variedades = extraer_variedades_ripley(
                        session=session,
                        url_directa=None,
                        perfume_nombre=p_nom,
                        marca=p_marca,
                        volumen_ml_defecto=100
                    )

                # Evaluamos la condición lógica (variedades) para controlar el flujo
                if variedades:
                    # Recorremos iterativamente cada 'v' en variedades
                    for v in variedades:
                        # Evaluamos la condición lógica (not v.get('exito')) para controlar el flujo
                        if not v.get("exito"):
                            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
                            continue
                        
                        # Asignamos 'p_act' con v['precio_actual']
                        p_act = v["precio_actual"]
                        # Asignamos 'p_norm' con v['precio_normal']
                        p_norm = v["precio_normal"]
                        # Asignamos 'vol' con v['volumen_ml']
                        vol = v["volumen_ml"]
                        # Asignamos 'url' con v['url']
                        url = v["url"]
                        # Asignamos 'en_stock' con v.get('en_stock', True)
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

                        # Evaluamos la condición lógica (res_reg) para controlar el flujo
                        if res_reg:
                            # Actualizamos acumulativamente el valor de 'total_ofertas_registradas'
                            total_ofertas_registradas += 1
                            # Ejecutamos instrucción: print(f" [GUARDADO] {t_nom:16} | {vol}ml | ${p_act:,...
                            print(f"  [GUARDADO] {t_nom:16} | {vol}ml | ${p_act:,} (Normal: ${p_norm:,}) | {v.get('metodo')}")

            except Exception as e:
                # Registro de evento diagnóstico en la bitácora (logger) del sistema
                logger.warning(f"Error procesando {p_nom} en {t_nom}: {e}")

    # Ejecutamos instrucción: print('\n===========================================...
    print("\n================================================================================")
    # Ejecutamos instrucción: print(f'RESUMEN: Total de ofertas y variedades guard...
    print(f"RESUMEN: Total de ofertas y variedades guardadas exitosamente: {total_ofertas_registradas}")
    # Ejecutamos instrucción: print('=============================================...
    print("================================================================================")

    # 3. Consultar y verificar la vista de precios actuales en Supabase
    print("\n--- AUDITORÍA DE VERIFICACIÓN EN VISTA_PRECIOS_ACTUALES (SUPABASE) ---")
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    res_vista = sb.table("vista_precios_actuales")\
        .select("perfume_id, tienda_nombre, volumen_ml, precio_actual, precio_normal, precio_por_ml, en_stock, url_producto")\
        .in_("perfume_id", PERFUMES_TEST_IDS)\
        .order("perfume_id")\
        .order("volumen_ml")\
        .execute()

    # Asignamos 'filas' con res_vista.data or []
    filas = res_vista.data or []
    # Ejecutamos instrucción: print(f'Total registros encontrados en vista_precios...
    print(f"Total registros encontrados en vista_precios_actuales: {len(filas)}")
    
    # Agrupar por perfume
    perfumes_dict = {p["id"]: p["nombre"] for p in perfumes}
    # Asignamos 'current_pid' con None
    current_pid = None
    # Recorremos iterativamente cada 'f' en filas
    for f in filas:
        # Asignamos 'pid' con f['perfume_id']
        pid = f["perfume_id"]
        # Evaluamos la condición lógica (pid != current_pid) para controlar el flujo
        if pid != current_pid:
            # Asignamos 'current_pid' con pid
            current_pid = pid
            # Ejecutamos instrucción: print(f"\nFragancia: {perfumes_dict.get(pid, f'ID {p...
            print(f"\nFragancia: {perfumes_dict.get(pid, f'ID {pid}')}")
            # Ejecutamos instrucción: print(f"{'Tienda':<18} | {'Volumen':<8} | {'Precio':...
            print(f"{'Tienda':<18} | {'Volumen':<8} | {'Precio':<10} | {'$/ml':<10} | {'Stock':<6}")
            # Ejecutamos instrucción: print('-' * 65)
            print("-" * 65)
        # Ejecutamos instrucción: print(f"{f['tienda_nombre']:<18} | {str(f['volumen_m...
        print(f"{f['tienda_nombre']:<18} | {str(f['volumen_ml'])+'ml':<8} | ${f['precio_actual']:<9,}| ${f['precio_por_ml']:<9,}| {'SÍ' if f['en_stock'] else 'NO'}")


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: probar_y_persistir_perfumes()
    probar_y_persistir_perfumes()
