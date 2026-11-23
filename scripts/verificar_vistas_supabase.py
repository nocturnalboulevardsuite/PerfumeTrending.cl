"""
Verificación de Vistas Optimizadas y Función upsert_oferta en Supabase
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

# Definición de función 'verificar_vistas' sin parámetros externos
def verificar_vistas():
    # Asignamos 'secrets' con toml.load(SECRETS_PATH)
    secrets = toml.load(SECRETS_PATH)
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    url = secrets['SUPABASE_URL']
    # Operación de lectura o persistencia sobre tablas/RPC de Supabase Cloud
    key = secrets['SUPABASE_SERVICE_ROLE_KEY']
    
    # Asignamos 'headers' con {'apikey': key, 'Authorization': f'Bearer ...
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    # Ejecutamos instrucción: print('=' * 60)
    print("=" * 60)
    # Ejecutamos instrucción: print('VERIFICACIÓN DE VISTAS OPTIMIZADAS Y RPC UPSE...
    print("VERIFICACIÓN DE VISTAS OPTIMIZADAS Y RPC UPSERT_OFERTA")
    # Ejecutamos instrucción: print('=' * 60)
    print("=" * 60)
    
    # Asignamos 'vistas' con ['mejor_precio_por_variante', 'ofertas_con...
    vistas = [
        'mejor_precio_por_variante',
        'ofertas_con_descuento',
        'historial_precio_variante',
        'perfumes_por_nota',
        'ranking_tendencias',
        'salud_scrapers'
    ]
    
    # Recorremos iterativamente cada 'v' en vistas
    for v in vistas:
        # Petición HTTP GET hacia el servidor externo con control de timeout y cabeceras
        r = requests.get(f"{url}/rest/v1/{v}?limit=1", headers=headers)
        # Evaluamos la condición lógica (r.status_code == 200) para controlar el flujo
        if r.status_code == 200:
            # Ejecutamos instrucción: print(f"[OK] Vista '{v}': Accesible (HTTP 200)")
            print(f"[OK] Vista '{v}': Accesible (HTTP 200)")
        else:
            # Ejecutamos instrucción: print(f"[ERROR] Vista '{v}': HTTP {r.status_code} - ...
            print(f"[ERROR] Vista '{v}': HTTP {r.status_code} - {r.text[:80]}")
            
    # Probar RPC upsert_oferta
    # Buscamos una variante viva
    r_var = requests.get(f"{url}/rest/v1/variantes_perfume?limit=1", headers=headers)
    # Evaluamos la condición lógica (r_var.status_code == 200 and len(r_var.json()) > 0) para controlar el flujo
    if r_var.status_code == 200 and len(r_var.json()) > 0:
        # Asignamos 'var_id' con r_var.json()[0]['id']
        var_id = r_var.json()[0]['id']
        # Asignamos 'r_rpc' con requests.post(f'{url}/rest/v1/rpc/upsert_o...
        r_rpc = requests.post(f"{url}/rest/v1/rpc/upsert_oferta", headers=headers, json={
            "p_variante_id": var_id,
            "p_tienda_id": 1,
            "p_precio_actual": 99990,
            "p_precio_normal": 119990,
            "p_en_stock": True,
            "p_url_producto": "https://test.verificacion.local/item-test"
        })
        # Evaluamos la condición lógica (r_rpc.status_code == 200) para controlar el flujo
        if r_rpc.status_code == 200:
            # Ejecutamos instrucción: print(f"[OK] RPC 'upsert_oferta': Funcionando (Retor...
            print(f"[OK] RPC 'upsert_oferta': Funcionando (Retorno: {r_rpc.json()})")
        else:
            # Ejecutamos instrucción: print(f"[ERROR] RPC 'upsert_oferta': HTTP {r_rpc.sta...
            print(f"[ERROR] RPC 'upsert_oferta': HTTP {r_rpc.status_code} - {r_rpc.text[:80]}")
            
    # Ejecutamos instrucción: print('=' * 60)
    print("=" * 60)

# Punto de entrada principal cuando el script se invoca directamente desde consola
if __name__ == '__main__':
    # Ejecutamos instrucción: verificar_vistas()
    verificar_vistas()
