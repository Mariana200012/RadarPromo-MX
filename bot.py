import telebot
import os
from dotenv import load_dotenv
from ali_api import obtener_detalles_producto

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
ID_CANAL = '@RadarPromoMX_Oficial'

def publicar_oferta(url_aliexpress):
    try:
        # Extraer ID del link (ej: 10050012345)
        product_id = url_aliexpress.split("/item/")[1].split(".html")[0]
        print(f"🔎 Analizando producto ID: {product_id}")
        
        datos = obtener_detalles_producto(product_id)
        
        if datos:
            # Calcular descuento
            p_promo = float(datos['precio_promo'])
            p_orig = float(datos['precio_original'])
            desc = int(100 - (p_promo * 100 / p_orig)) if p_orig > 0 else 0
            
            mensaje = (
                f"🔥 <b>{datos['titulo'][:100]}...</b>\n\n"
                f"💰 <b>Precio:</b> ${p_promo} MXN\n"
                f"❌ <b>Antes:</b> <s>${p_orig} MXN</s> ({desc}% OFF)\n\n"
                f"🕵️ <i>Curaduría técnica por @RadarPromoMX</i>\n\n"
                f"🛒 <a href='{url_aliexpress}'>¡VER OFERTA AQUÍ!</a>"
            )
            
            bot.send_photo(ID_CANAL, datos['foto'], caption=mensaje, parse_mode='HTML')
            print("✅ Publicación exitosa en Telegram")
        else:
            print("⚠️ AliExpress aún no devuelve datos. Posible activación pendiente.")
            
    except Exception as e:
        print(f"❌ Error al procesar: {e}")

if __name__ == "__main__":
    # Link de prueba
    test_link = "https://es.aliexpress.com/item/1005010050151907.html"
    publicar_oferta(test_link)