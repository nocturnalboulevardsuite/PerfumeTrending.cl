"""
Verificación de Vistas Optimizadas y Función upsert_oferta en Supabase
"""
import toml
import requests
import json
import os

SECRETS_PATH = os.path.join(os.path.dirname(__file__), '..', 'APP', '.streamlit', 'secrets.toml')

def verificar_vistas():
    secrets = toml.load(SECRETS_PATH)
    url = secrets['SUPABASE_URL']
    key = secrets['SUPABASE_SERVICE_ROLE_KEY']
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    print("=" * 60)
    print("VERIFICACIÓN DE VISTAS OPTIMIZADAS Y RPC UPSERT_OFERTA")
    print("=" * 60)
    
    vistas = [
        'mejor_precio_por_variante',
        'ofertas_con_descuento',
        'historial_precio_variante',
        'perfumes_por_nota',
        'ranking_tendencias',
        'salud_scrapers'
    ]
    
    for v in vistas:
        r = requests.get(f"{url}/rest/v1/{v}?limit=1", headers=headers)
        if r.status_code == 200:
            print(f"[OK] Vista '{v}': Accesible (HTTP 200)")
        else:
            print(f"[ERROR] Vista '{v}': HTTP {r.status_code} - {r.text[:80]}")
            
    # Probar RPC upsert_oferta
    # Buscamos una variante viva
    r_var = requests.get(f"{url}/rest/v1/variantes_perfume?limit=1", headers=headers)
    if r_var.status_code == 200 and len(r_var.json()) > 0:
        var_id = r_var.json()[0]['id']
        r_rpc = requests.post(f"{url}/rest/v1/rpc/upsert_oferta", headers=headers, json={
            "p_variante_id": var_id,
            "p_tienda_id": 1,
            "p_precio_actual": 99990,
            "p_precio_normal": 119990,
            "p_en_stock": True,
            "p_url_producto": "https://test.verificacion.local/item-test"
        })
        if r_rpc.status_code == 200:
            print(f"[OK] RPC 'upsert_oferta': Funcionando (Retorno: {r_rpc.json()})")
        else:
            print(f"[ERROR] RPC 'upsert_oferta': HTTP {r_rpc.status_code} - {r_rpc.text[:80]}")
            
    print("=" * 60)

if __name__ == '__main__':
    verificar_vistas()
