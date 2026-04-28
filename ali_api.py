import os
from dotenv import load_dotenv
import requests

load_dotenv()

APP_KEY = os.getenv("ALI_APP_KEY")
APP_SECRET = os.getenv("ALI_APP_SECRET")

def obtener_detalles_producto(product_id):
    # La URL DEBE incluir la versión y el nombre de la API exactos
    # Estructura: /openapi/param2/[v]/[namespace]/[api_name]/[app_key]
    url = f"https://gw.api.alibaba.com/openapi/param2/2/portals.open/api.getPromotionProductDetail/{APP_KEY}"
    
    # IMPORTANTE: Para esta API, los parámetros deben ir como un diccionario simple
    params = {
        "fields": "productTitle,salePrice,imageUrl,originalPrice",
        "productIds": str(product_id) # Nos aseguramos que sea texto
    }
    
    try:
        # Quitamos los headers complejos, usemos una petición limpia
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        print(f"DEBUG API Status: {response.status_code}")
        print(f"RESPUESTA COMPLETA: {data}")
        
        # AliExpress a veces responde con 'result' o con 'error_response'
        if "result" in data and data["result"].get("products"):
            prod = data["result"]["products"][0]
            return {
                "titulo": prod["productTitle"],
                "precio_promo": prod["salePrice"],
                "precio_original": prod.get("originalPrice", prod["salePrice"]),
                "foto": prod["imageUrl"]
            }
            
    except Exception as e:
        print(f"❌ Error técnico en ali_api: {e}")
    
    return None