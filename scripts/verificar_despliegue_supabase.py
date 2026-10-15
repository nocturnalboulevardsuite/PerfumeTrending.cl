"""
Script de Verificación Post-Migración en Supabase
Verifica la integridad de las tablas, catálogo de notas, funciones RPC y registros migrados.
"""
import toml
import requests
import json
import os

SECRETS_PATH = os.path.join(os.path.dirname(__file__), '..', 'APP', '.streamlit', 'secrets.toml')

def verificar_despliegue():
    if not os.path.exists(SECRETS_PATH):
        print(f"Error: No se encontró {SECRETS_PATH}")
        return False
        
    secrets = toml.load(SECRETS_PATH)
    url = secrets.get('SUPABASE_URL')
    key = secrets.get('SUPABASE_SERVICE_ROLE_KEY')
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    print("=" * 60)
    print("VERIFICACIÓN DE DESPLIEGUE TRANSACCIONAL EN SUPABASE")
    print(f"URL: {url}")
    print("=" * 60)
    
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
    
    for tabla, minimo_filas in tablas:
        r = requests.get(f"{url}/rest/v1/{tabla}?select=count", headers=headers)
        if r.status_code != 200:
            errores.append(f"Tabla '{tabla}' no accesible o no existe (HTTP {r.status_code}: {r.text[:80]})")
        else:
            # Obtener count del header content-range o select
            r_count = requests.get(f"{url}/rest/v1/{tabla}?select=id", headers={**headers, "Range": "0-0", "Prefer": "count=exact"})
            content_range = r_count.headers.get('content-range', '')
            total = content_range.split('/')[-1] if '/' in content_range else 'desconocido'
            print(f"[OK] Tabla '{tabla}': {total} registros (mínimo esperado: {minimo_filas})")
            if total != 'desconocido' and minimo_filas > 0 and int(total) < minimo_filas:
                errores.append(f"Tabla '{tabla}' tiene menos filas de las esperadas ({total} < {minimo_filas})")

    # 2. Verificar Vista
    r_vista = requests.get(f"{url}/rest/v1/vista_precios_actuales?limit=1", headers=headers)
    if r_vista.status_code == 200:
        print("[OK] Vista 'vista_precios_actuales' operativa.")
    else:
        errores.append(f"Vista 'vista_precios_actuales' falló (HTTP {r_vista.status_code})")
        
    # 3. Verificar RPCs transaccionales
    print("\n--- Verificando Funciones RPC ---")
    
    # Obtenemos una variante y tienda existente para la prueba
    r_var = requests.get(f"{url}/rest/v1/variantes_perfume?limit=1", headers=headers)
    if r_var.status_code == 200 and len(r_var.json()) > 0:
        var_id = r_var.json()[0]['id']
        
        # Test RPC registrar_fallo_scraping
        r_rpc_fallo = requests.post(f"{url}/rest/v1/rpc/registrar_fallo_scraping", headers=headers, json={
            "p_variante_id": var_id,
            "p_tienda_id": 1,
            "p_mensaje": "Ping de verificacion post-despliegue"
        })
        if r_rpc_fallo.status_code == 200:
            print(f"[OK] RPC 'registrar_fallo_scraping' responde correctamente: {r_rpc_fallo.json()}")
        else:
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
        if r_rpc_obs.status_code == 200:
            print(f"[OK] RPC 'registrar_observacion_oferta' responde correctamente: {r_rpc_obs.json()}")
        else:
            errores.append(f"RPC 'registrar_observacion_oferta' falló (HTTP {r_rpc_obs.status_code}: {r_rpc_obs.text[:100]})")
    else:
        errores.append("No se pudo obtener una variante para probar RPCs")
        
    print("\n" + "=" * 60)
    if not errores:
        print("RESULTADO: DESPLIEGUE 100% EXITOSO Y OPERATIVO EN SUPABASE")
        print("=" * 60)
        return True
    else:
        print("RESULTADO: PENDIENTE O CON ERRORES")
        for err in errores:
            print(f" - {err}")
        print("=" * 60)
        return False

if __name__ == '__main__':
    verificar_despliegue()
