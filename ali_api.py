import os
from dotenv import load_dotenv
import requests

load_dotenv()

APP_KEY = os.getenv("ALI_APP_KEY")
APP_SECRET = os.getenv("ALI_APP_SECRET")

print(f"DEBUG LOCAL: Mi App Key es -> {APP_KEY}")

def obtener_detalles_producto(product_id):
    # Endpoint para México/Global
    url = "https://gw.api.alibaba.com/openapi/param2/2/portals.open/api.getPromotionProductDetail/" + APP_KEY
    
    params = {
        "fields": "productTitle,salePrice,imageUrl,originalPrice",
        "productIds": product_id
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        # Esto nos ayudará a ver qué dice AliExpress exactamente
        print(f"DEBUG API: {data}") 
        
        if "result" in data and data["result"]["products"]:
            prod = data["result"]["products"][0]
            return {
                "titulo": prod["productTitle"],
                "precio_promo": prod["salePrice"],
                "precio_original": prod.get("originalPrice", prod["salePrice"]),
                "foto": prod["imageUrl"]
            }
        else:
            print(f"⚠️ AliExpress dice: {data.get('error_msg', 'Producto no encontrado o API en espera')}")
            
    except Exception as e:
        print(f"❌ Error técnico: {e}")
    
    return None