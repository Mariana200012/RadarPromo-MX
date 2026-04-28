import os
from dotenv import load_dotenv
import requests

load_dotenv()

APP_KEY = os.getenv("ALI_APP_KEY")
APP_SECRET = os.getenv("ALI_APP_SECRET")

def obtener_detalles_producto(product_id):
    # Cambiamos la URL a la base limpia sin el ID al final
    url = "https://gw.api.alibaba.com/openapi/param2/2/portals.open/api.getPromotionProductDetail"
    
    # Ponemos la app_key dentro de los parámetros, no en la URL
    params = {
        "app_key": APP_KEY,
        "fields": "productTitle,salePrice,imageUrl,originalPrice",
        "productIds": product_id
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        print(f"DEBUG API Status: {response.status_code}")
        print(f"RESPUESTA COMPLETA: {data}")
        
        if "result" in data and data["result"]["products"]:
            prod = data["result"]["products"][0]
            return {
                "titulo": prod["productTitle"],
                "precio_promo": prod["salePrice"],
                "precio_original": prod.get("originalPrice", prod["salePrice"]),
                "foto": prod["imageUrl"]
            }
        # Si el error persiste, AliExpress nos dirá exactamente qué falta aquí
    except Exception as e:
        print(f"❌ Error técnico en ali_api: {e}")
    
    return None