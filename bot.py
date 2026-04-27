import telebot
import os
from dotenv import load_dotenv
from ali_api import obtener_detalles_producto # Importamos tu nuevo lector

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
ID_CANAL = '@RadarPromoMX_Oficial'

def publicar_automaticamente(url_aliexpress):
    # 1. Extraer el ID del producto del link
    # Ejemplo: .../item/12345.html -> 12345
    try:
        product_id = url_aliexpress.split("/item/")[1].split(".html")[0]
    except:
        print("❌ URL no válida")
        return

    # 2. Obtener datos reales de la API
    datos = obtener_detalles_producto(product_id)
    
    if datos:
        descuento = int(100 - (float(datos['precio_promo']) * 100 / float(datos['precio_original'])))
        
        mensaje = (
            f"🔥 <b>{datos['titulo'].upper()}</b>\n\n"
            f"💰 <b>Precio Especial:</b> ${datos['precio_promo']} MXN\n"
            f"❌ <b>Antes:</b> <s>${datos['precio_original']} MXN</s> ({descuento}% OFF)\n\n"
            f"🕵️ <i>Curaduría técnica por RadarPromo-MX</i>\n\n"
            f"🛒 <a href='{url_aliexpress}'>¡VER OFERTA AQUÍ!</a>"
        )
        
        bot.send_photo(ID_CANAL, datos['foto'], caption=mensaje, parse_mode='HTML')
        print(f"✅ ¡Oferta de {product_id} publicada automáticamente!")
    else:
        print("⚠️ No se pudo obtener info de la API.")

if __name__ == "__main__":
    # ¡PRUEBA FINAL! Solo pon el link, la API hará el resto
    link = "https://es.aliexpress.com/item/1005010050151907.html"
    publicar_automaticamente(link)