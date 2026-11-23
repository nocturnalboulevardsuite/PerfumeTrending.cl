"""
Script de remediación y auditoría de flankers, stock y URLs rotas:
1. Actualiza ofertas agotadas de Falabella para Bleu de Chanel (en_stock = False, estado = 'agotada').
2. Corrige URLs de Paris obsoletas para que apunten al buscador oficial o fichas vivas.
3. Limpia ofertas contaminadas de flankers en Acqua Di Gio (ID 7) y re-audita tanto ID 7 (EDT) como ID 96 (Profondo).
"""
# Importación de librería estándar o dependencia externa (sys)
import sys
# Importación de librería estándar o dependencia externa (os)
import os
# Importación de librería estándar o dependencia externa (time)
import time

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


# Definición de función 'remediar_base_de_datos' sin parámetros externos
def remediar_base_de_datos():
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    sb = get_supabase(use_service_role=True)
    # Evaluamos la condición lógica (not sb or not is_supabase_disponible()) para controlar el flujo
    if not sb or not is_supabase_disponible():
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        print("Error: Supabase no disponible")
        # Finalizamos la ejecución de la función retornando None
        return

    # Ejecutamos instrucción: print('=== 1. REMEDIANDO FALABELLA Y PARIS EN BLEU D...
    print("=== 1. REMEDIANDO FALABELLA Y PARIS EN BLEU DE CHANEL (ID: 1) ===")
    # 1.1 Marcar Bleu de Chanel en Falabella como agotado
    res_fal_variantes = sb.table("variantes_perfume").select("id").eq("perfume_id", 1).execute().data or []
    # Asignamos 'fal_var_ids' con [v['id'] for v in res_fal_variantes]
    fal_var_ids = [v["id"] for v in res_fal_variantes]
    # Evaluamos la condición lógica (fal_var_ids) para controlar el flujo
    if fal_var_ids:
        # Falabella tiene tienda_id = 1
        upd = sb.table("ofertas_actuales").update({"en_stock": False, "estado": "agotada"}).in_("variante_id", fal_var_ids).eq("tienda_id", 1).execute()
        # Ejecutamos instrucción: print(f'Ofertas de Falabella marcadas como agotadas ...
        print(f"Ofertas de Falabella marcadas como agotadas para Bleu de Chanel: {len(upd.data or [])}")

    # 1.2 Corregir URL de Paris en Bleu de Chanel (reemplazar link 434948999 por búsqueda oficial de Chanel Bleu)
    clean_paris_url = "https://www.paris.cl/search?q=Chanel%20Bleu%20de%20Chanel"
    # Evaluamos la condición lógica (fal_var_ids) para controlar el flujo
    if fal_var_ids:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        upd_par = sb.table("ofertas_actuales").update({"url_producto": clean_paris_url}).in_("variante_id", fal_var_ids).eq("tienda_id", 2).execute()
        # Ejecutamos instrucción: print(f'URLs de Paris actualizadas a búsqueda oficia...
        print(f"URLs de Paris actualizadas a búsqueda oficial para Bleu de Chanel: {len(upd_par.data or [])}")

    # Ejecutamos instrucción: print('\n=== 2. REMEDIANDO ACQUA DI GIO (ID: 7) Y AC...
    print("\n=== 2. REMEDIANDO ACQUA DI GIO (ID: 7) Y ACQUA DI GIO PROFONDO (ID: 96) ===")
    # 2.1 Encontrar ofertas contaminadas en ID 7 que contengan 'profondo' o 'elixir' en su URL
    res_adg_variantes = sb.table("variantes_perfume").select("id").eq("perfume_id", 7).execute().data or []
    # Asignamos 'adg_var_ids' con [v['id'] for v in res_adg_variantes]
    adg_var_ids = [v["id"] for v in res_adg_variantes]
    # Evaluamos la condición lógica (adg_var_ids) para controlar el flujo
    if adg_var_ids:
        # Eliminar o desactivar ofertas de flankers en ID 7
        res_of = sb.table("ofertas_actuales").select("id, url_producto, variante_id").in_("variante_id", adg_var_ids).execute().data or []
        # Asignamos 'flanker_ids_to_del' con [o['id'] for o in res_of if any((w in (o.g...
        flanker_ids_to_del = [
            o["id"] for o in res_of 
            if any(w in (o.get("url_producto") or "").lower() for w in ["profondo", "elixir", "profumo", "gioia"])
        ]
        # Evaluamos la condición lógica (flanker_ids_to_del) para controlar el flujo
        if flanker_ids_to_del:
            # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
            sb.table("ofertas_actuales").delete().in_("id", flanker_ids_to_del).execute()
            # Ejecutamos instrucción: print(f'Eliminadas {len(flanker_ids_to_del)} ofertas...
            print(f"Eliminadas {len(flanker_ids_to_del)} ofertas contaminadas de flankers en Acqua Di Gio ID 7.")

    # 2.2 Re-auditar en vivo Acqua Di Gio (ID 7) y Acqua Di Gio Profondo (ID 96)
    session = crear_sesion_robusta()
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    res_tiendas = sb.table("tiendas").select("id, nombre, url_base").execute().data or []

    # Recorremos iterativamente cada 'target_id' en [7, 96]
    for target_id in [7, 96]:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        p_row = sb.table("perfumes").select("id, nombre, marca").eq("id", target_id).single().execute().data
        # Evaluamos la condición lógica (not p_row) para controlar el flujo
        if not p_row:
            # Saltamos a la siguiente iteración del ciclo descartando el elemento actual
            continue
        # Asignamos 'p_id' con p_row['id']
        p_id = p_row["id"]
        # Asignamos 'p_nom' con p_row['nombre']
        p_nom = p_row["nombre"]
        # Asignamos 'p_marca' con p_row['marca']
        p_marca = p_row["marca"]

        # Ejecutamos instrucción: print(f'\n--- AUDITANDO EN VIVO CON GUARDIA DE FLANK...
        print(f"\n--- AUDITANDO EN VIVO CON GUARDIA DE FLANKERS: {p_nom} ({p_marca}) [ID: {p_id}] ---")
        # Recorremos iterativamente cada 't' en res_tiendas
        for t in res_tiendas:
            # Asignamos 't_id' con t['id']
            t_id = t["id"]
            # Asignamos 't_nom' con t['nombre']
            t_nom = t["nombre"]
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
                    # Asignamos 'variedades' con extraer_variedades_shopify(session, TIENDA...
                    variedades = extraer_variedades_shopify(session, TIENDAS_SHOPIFY[t_nom], p_nom, p_marca, 100)
                # Evaluamos la condición lógica ('falabella' in t_nom.lower()) para controlar el flujo
                elif "falabella" in t_nom.lower():
                    # Asignamos 'variedades' con extraer_variedades_falabella(session, None...
                    variedades = extraer_variedades_falabella(session, None, p_nom, p_marca, 100)
                # Evaluamos la condición lógica ('paris' in t_nom.lower()) para controlar el flujo
                elif "paris" in t_nom.lower():
                    # Asignamos 'variedades' con extraer_variedades_paris(session, None, p_...
                    variedades = extraer_variedades_paris(session, None, p_nom, p_marca, 100)
                # Evaluamos la condición lógica ('ripley' in t_nom.lower()) para controlar el flujo
                elif "ripley" in t_nom.lower():
                    # Asignamos 'variedades' con extraer_variedades_ripley(session, None, p...
                    variedades = extraer_variedades_ripley(session, None, p_nom, p_marca, 100)

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

                    # Ejecutamos instrucción: registrar_observacion_oferta({'perfume_id': p_id, 't...
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
                    # Ejecutamos instrucción: print(f' [REGISTRADO] {t_nom:16} | {vol}ml | ${p_act...
                    print(f"  [REGISTRADO] {t_nom:16} | {vol}ml | ${p_act:,} | Stock: {en_stock} | {url[:55]}...")

            except Exception as e:
                # Ejecutamos instrucción: print(f'Error en {t_nom} para {p_nom}: {e}')
                print(f"Error en {t_nom} para {p_nom}: {e}")

    # Ejecutamos instrucción: print('\n=== VERIFICACIÓN FINAL EN VISTA_PRECIOS_ACT...
    print("\n=== VERIFICACIÓN FINAL EN VISTA_PRECIOS_ACTUALES ===")
    # Recorremos iterativamente cada '(pid, nombre)' en [(1, 'Bleu de Chanel'), (7, 'Acqua Di Gio ...
    for pid, nombre in [(1, "Bleu de Chanel"), (7, "Acqua Di Gio EDT"), (96, "Acqua Di Gio Profondo")]:
        # Ejecutamos instrucción: print(f'\nResultados vigentes para: {nombre} (ID: {p...
        print(f"\nResultados vigentes para: {nombre} (ID: {pid})")
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        res_v = sb.table("vista_precios_actuales").select("tienda_nombre, volumen_ml, precio_actual, precio_normal, precio_por_ml, url_producto").eq("perfume_id", pid).execute().data or []
        # Recorremos iterativamente cada 'r' en res_v
        for r in res_v:
            # Ejecutamos instrucción: print(f" {r['tienda_nombre']:<16} | {r['volumen_ml']...
            print(f"  {r['tienda_nombre']:<16} | {r['volumen_ml']}ml | ${r['precio_actual']:,} | $/ml: ${r['precio_por_ml']:,} | {r['url_producto'][:60]}...")


# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == "__main__":
    # Ejecutamos instrucción: remediar_base_de_datos()
    remediar_base_de_datos()
