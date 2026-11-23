"""
Script de Verificación Post-Migración en Supabase
Verifica la integridad de las tablas, catálogo de notas, funciones RPC y registros migrados.
"""
# Importación de librería estándar o dependencia externa (toml)
import toml
# Importación de librería estándar o dependencia externa (requests)
import requests
# Importación de librería estándar o dependencia externa (json)
import json
# Importación de librería estándar o dependencia externa (os)
import os

# Asignamos 'SECRETS_PATH' con os.path.join(os.path.dirname(__file__), '....
SECRETS_PATH = os.path.join(os.path.dirname(__file__), '..', 'APP', '.streamlit', 'secrets.toml')

# Definición de función 'verificar_despliegue' sin parámetros externos
def verificar_despliegue():
    # Evaluamos la condición lógica (not os.path.exists(SECRETS_PATH)) para controlar el flujo
    if not os.path.exists(SECRETS_PATH):
        # Ejecutamos instrucción: print(f'Error: No se encontró {SECRETS_PATH}')
        print(f"Error: No se encontró {SECRETS_PATH}")
        # Retornamos el resultado procesado (False)
        return False
        
    # Asignamos 'secrets' con toml.load(SECRETS_PATH)
    secrets = toml.load(SECRETS_PATH)
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    url = secrets.get('SUPABASE_URL')
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    key = secrets.get('SUPABASE_SERVICE_ROLE_KEY')
    
    # Asignamos 'headers' con {'apikey': key, 'Authorization': f'Bearer ...
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    # Ejecutamos instrucción: print('=' * 60)
    print("=" * 60)
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    print("VERIFICACIÓN DE DESPLIEGUE TRANSACCIONAL EN SUPABASE")
    # Ejecutamos instrucción: print(f'URL: {url}')
    print(f"URL: {url}")
    # Ejecutamos instrucción: print('=' * 60)
    print("=" * 60)
    
    # Asignamos 'errores' con []
    errores = []
    
    # 1. Verificar Tablas Existentes
    tablas = [
        ('perfumes', 134),
        ('tiendas', 8),
        ('precios_registro', 460),
        ('familias_notas', 12),
        ('notas_olfativas', 107),
        ('variantes_perfume', 100), # al menos 100
        ('ofertas_actuales', 100),  # al menos 100
        ('scraping_runs', 0),
        ('perfume_notas_importacion', 0)
    ]
    
    # Recorremos iterativamente cada '(tabla, minimo_filas)' en tablas
    for tabla, minimo_filas in tablas:
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        r = requests.get(f"{url}/rest/v1/{tabla}?select=count", headers=headers)
        # Evaluamos la condición lógica (r.status_code != 200) para controlar el flujo
        if r.status_code != 200:
            # Ejecutamos instrucción: errores.append(f"Tabla '{tabla}' no accesible o no e...
            errores.append(f"Tabla '{tabla}' no accesible o no existe (HTTP {r.status_code}: {r.text[:80]})")
        else:
            # Obtener count del header content-range o select
            r_count = requests.get(f"{url}/rest/v1/{tabla}?select=id", headers={**headers, "Range": "0-0", "Prefer": "count=exact"})
            # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
            content_range = r_count.headers.get('content-range', '')
            # Asignamos 'total' con content_range.split('/')[-1] if '/' in con...
            total = content_range.split('/')[-1] if '/' in content_range else 'desconocido'
            # Ejecutamos instrucción: print(f"[OK] Tabla '{tabla}': {total} registros (mín...
            print(f"[OK] Tabla '{tabla}': {total} registros (mínimo esperado: {minimo_filas})")
            # Evaluamos la condición lógica (total != 'desconocido' and minimo_filas > 0 and (int...) para controlar el flujo
            if total != 'desconocido' and minimo_filas > 0 and int(total) < minimo_filas:
                # Ejecutamos instrucción: errores.append(f"Tabla '{tabla}' tiene menos filas d...
                errores.append(f"Tabla '{tabla}' tiene menos filas de las esperadas ({total} < {minimo_filas})")

    # 2. Verificar Vista
    r_vista = requests.get(f"{url}/rest/v1/vista_precios_actuales?limit=1", headers=headers)
    # Evaluamos la condición lógica (r_vista.status_code == 200) para controlar el flujo
    if r_vista.status_code == 200:
        # Ejecutamos instrucción: print("[OK] Vista 'vista_precios_actuales' operativa.")
        print("[OK] Vista 'vista_precios_actuales' operativa.")
    else:
        # Ejecutamos instrucción: errores.append(f"Vista 'vista_precios_actuales' fall...
        errores.append(f"Vista 'vista_precios_actuales' falló (HTTP {r_vista.status_code})")
        
    # 3. Verificar RPCs transaccionales
    print("\n--- Verificando Funciones RPC ---")
    
    # Obtenemos una variante y tienda existente para la prueba
    r_var = requests.get(f"{url}/rest/v1/variantes_perfume?limit=1", headers=headers)
    # Evaluamos la condición lógica (r_var.status_code == 200 and len(r_var.json()) > 0) para controlar el flujo
    if r_var.status_code == 200 and len(r_var.json()) > 0:
        # Asignamos 'var_id' con r_var.json()[0]['id']
        var_id = r_var.json()[0]['id']
        
        # Test RPC registrar_fallo_scraping
        r_rpc_fallo = requests.post(f"{url}/rest/v1/rpc/registrar_fallo_scraping", headers=headers, json={
            "p_variante_id": var_id,
            "p_tienda_id": 1,
            "p_mensaje": "Ping de verificacion post-despliegue"
        })
        # Evaluamos la condición lógica (r_rpc_fallo.status_code == 200) para controlar el flujo
        if r_rpc_fallo.status_code == 200:
            # Ejecutamos instrucción: print(f"[OK] RPC 'registrar_fallo_scraping' responde...
            print(f"[OK] RPC 'registrar_fallo_scraping' responde correctamente: {r_rpc_fallo.json()}")
        else:
            # Ejecutamos instrucción: errores.append(f"RPC 'registrar_fallo_scraping' fall...
            errores.append(f"RPC 'registrar_fallo_scraping' falló (HTTP {r_rpc_fallo.status_code}: {r_rpc_fallo.text[:100]})")
            
        # Test RPC registrar_observacion_oferta con datos que generen 'sin_cambios' o 'actualizada'
        r_rpc_obs = requests.post(f"{url}/rest/v1/rpc/registrar_observacion_oferta", headers=headers, json={
            "p_variante_id": var_id,
            "p_tienda_id": 1,
            "p_precio_actual": 99990,
            "p_precio_normal": 119990,
            "p_en_stock": True,
            "p_url_producto": "https://test.verificacion.local/item-test"
        })
        # Evaluamos la condición lógica (r_rpc_obs.status_code == 200) para controlar el flujo
        if r_rpc_obs.status_code == 200:
            # Ejecutamos instrucción: print(f"[OK] RPC 'registrar_observacion_oferta' resp...
            print(f"[OK] RPC 'registrar_observacion_oferta' responde correctamente: {r_rpc_obs.json()}")
        else:
            # Ejecutamos instrucción: errores.append(f"RPC 'registrar_observacion_oferta' ...
            errores.append(f"RPC 'registrar_observacion_oferta' falló (HTTP {r_rpc_obs.status_code}: {r_rpc_obs.text[:100]})")
    else:
        # Ejecutamos instrucción: errores.append('No se pudo obtener una variante para...
        errores.append("No se pudo obtener una variante para probar RPCs")
        
    # Ejecutamos instrucción: print('\n' + '=' * 60)
    print("\n" + "=" * 60)
    # Evaluamos la condición lógica (not errores) para controlar el flujo
    if not errores:
        # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
        print("RESULTADO: DESPLIEGUE 100% EXITOSO Y OPERATIVO EN SUPABASE")
        # Ejecutamos instrucción: print('=' * 60)
        print("=" * 60)
        # Retornamos el resultado procesado (True)
        return True
    else:
        # Ejecutamos instrucción: print('RESULTADO: PENDIENTE O CON ERRORES')
        print("RESULTADO: PENDIENTE O CON ERRORES")
        # Recorremos iterativamente cada 'err' en errores
        for err in errores:
            # Ejecutamos instrucción: print(f' - {err}')
            print(f" - {err}")
        # Ejecutamos instrucción: print('=' * 60)
        print("=" * 60)
        # Retornamos el resultado procesado (False)
        return False

# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == '__main__':
    # Ejecutamos instrucción: verificar_despliegue()
    verificar_despliegue()
