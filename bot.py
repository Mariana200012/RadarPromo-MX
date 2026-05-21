import os
import re
import sqlite3
import asyncio
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetHistoryRequest
from dotenv import load_dotenv

# 1. CONFIGURACIÓN E INICIALIZACIÓN
load_dotenv()
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_STR = os.getenv("TELEGRAM_SESSION")
ID_MI_CANAL = '@RadarPromoMX_Oficial'
CANALES_A_MONITOREAR = ['@ofertones', '@radar_deofertas2728'] 
AMAZON_TAG = "radarpmx-20"

def inicializar_db():
    conn = sqlite3.connect('radar_promo.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS ofertas_publicadas (source_id TEXT UNIQUE)')
    conn.commit()
    conn.close()

def ya_publicado(source_id):
    conn = sqlite3.connect('radar_promo.db')
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM ofertas_publicadas WHERE source_id = ?", (source_id,))
    existe = cursor.fetchone() is not None
    conn.close()
    return existe

def registrar_db(source_id):
    conn = sqlite3.connect('radar_promo.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO ofertas_publicadas (source_id) VALUES (?)", (source_id,))
        conn.commit()
    except: 
        pass
    conn.close()

def obtener_foto_amazon(asin):
    try:
        url = f"https://www.amazon.com.mx/dp/{asin}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        img_url = re.search(r'"large":"(https://m\.media-amazon\.com/images/I/[^"]+?\.jpg)"', response.text)
        if img_url:
            img_data = requests.get(img_url.group(1)).content
            path = f"temp_{asin}.jpg"
            with open(path, 'wb') as f:
                f.write(img_data)
            return path
    except:
        return None
    return None

def enviar_a_whatsapp_grupo(mensaje_wa, foto_path):
    """
    Envía las ofertas al Grupo de WhatsApp usando Green API.
    Soporta envío nativo de imágenes.
    """
    try:
        instance_id = os.getenv("GREEN_API_INSTANCE")
        api_token = os.getenv("GREEN_API_TOKEN")
        chat_id = os.getenv("WHATSAPP_CHANNEL_URL") 
        
        if not instance_id or not api_token or not chat_id:
            print("  ❌ GREEN API ERROR: Credenciales ausentes en la nube.")
            return False

        if foto_path and os.path.exists(foto_path):
            url = f"https://api.green-api.com/waInstance{instance_id}/sendFileByUpload/{api_token}"
            payload = {'chatId': chat_id, 'caption': mensaje_wa}
            files = {'file': open(foto_path, 'rb')}
            response = requests.post(url, data=payload, files=files, timeout=15)
        else:
            url = f"https://api.green-api.com/waInstance{instance_id}/sendMessage/{api_token}"
            payload = {"chatId": chat_id, "message": mensaje_wa, "linkPreview": True}
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            print("  ✅ GREEN API: ¡Oferta enviada al Grupo de WhatsApp!")
            return True
        else:
            print(f"  ❌ GREEN API ERROR: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ⚠️ Error en pasarela Green API: {e}")
        return False

async def procesar_canales():
    client = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)
    await client.start()
    
    print("🛰️ RadarPromoMX: Buscando ofertas en canales (Escaneando 40 publicaciones)...")
    ofertas_a_publicar = []

    for canal_user in CANALES_A_MONITOREAR:
        try:
            history = await client(GetHistoryRequest(
                peer=canal_user, limit=40, offset_date=None, offset_id=0,
                max_id=0, min_id=0, add_offset=0, hash=0
            ))
            
            for msg in history.messages:
                if msg.message:
                    urls = re.findall(r'(https?://[^\s]+)', msg.message)
                    if urls:
                        match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', urls[0])
                        if match:
                            asin = match.group(1)
                            if not ya_publicado(asin):
                                precios = re.findall(r'\$\s?[\d,.]+', msg.message)
                                p_ahora = precios[0] if len(precios) >= 1 else "Ver en tienda"
                                p_antes = precios[1] if len(precios) >= 2 else None
                                
                                dto_match = re.search(r'(-?\d{1,2}%)', msg.message)
                                descuento = dto_match.group(1) if dto_match else None
                                
                                foto_path = None
                                if msg.media:
                                    foto_path = await client.download_media(msg, file=f"temp_{asin}.jpg")
                                elif msg.web_preview and msg.web_preview.photo:
                                    foto_path = await client.download_media(msg.web_preview.photo, file=f"temp_{asin}.jpg")
                                
                                if not foto_path:
                                    foto_path = obtener_foto_amazon(asin)
                                
                                ofertas_a_publicar.append({
                                    'asin': asin,
                                    'url': f"https://www.amazon.com.mx/dp/{asin}?tag={AMAZON_TAG}",
                                    'texto_completo': msg.message,
                                    'p_ahora': p_ahora,
                                    'p_antes': p_antes,
                                    'descuento': descuento,
                                    'foto': foto_path
                                })
        except Exception as e:
            print(f"⚠️ Error en canal: {e}")

    for i, oferta in enumerate(ofertas_a_publicar):
        try:
            lineas = oferta['texto_completo'].split('\n')
            lineas_limpias = []
            for linea in lineas:
                pattern_basura = r'(?i)(https?://|precio|oferta|descuento|\$|-?\d{1,2}%|unete|ver|#)'
                if re.search(pattern_basura, linea): 
                    continue
                
                linea_filtrada = re.sub(r'(?i)(bbva|banorte|hsbc|citibanamex|banamex|santander|amex|coppel|mercadopago)\s*:\s*\w+', '', linea)
                linea_filtrada = re.sub(r'(?i)\b(bbva|banorte|hsbc|citibanamex|banamex|santander|amex)\b', '', linea_filtrada)
                linea_filtrada = linea_filtrada.replace('✅', '').replace('🔥', '').strip()
                
                if linea_filtrada: 
                    lineas_limpias.append(linea_filtrada)
            
            descripcion = " ".join(lineas_limpias[:2])
            descripcion = re.sub(r'(?i)^amazon\s*:\s*', '', descripcion)
            
            txt_precio = ""
            if oferta['descuento']: 
                txt_precio += f"📉 <b>Descuento: {oferta['descuento']}</b>\n"
            if oferta['p_antes']: 
                txt_precio += f"❌ Antes: <del>{oferta['p_antes']}</del>\n"
            txt_precio += f"✅ <b>Precio Hoy: {oferta['p_ahora']}</b>"

            mensaje_telegram = (
                f"🔥 <b>¡OFERTA FLASH!</b> 🔥\n\n"
                f"📦 <b>{descripcion}</b>\n\n"
                f"{txt_precio}\n\n"
                f"🛒 <b>COMPRA AQUÍ:</b>\n"
                f"👉 {oferta['url']}\n\n"
                f"🕵️ @RadarPromoMX"
            )
            
            txt_precio_wa = ""
            if oferta['descuento']: 
                txt_precio_wa += f"📉 *Descuento: {oferta['descuento']}*\n"
            if oferta['p_antes']: 
                txt_precio_wa += f"❌ Antes: ~{oferta['p_antes']}~\n"
            txt_precio_wa += f"✅ *Precio Hoy: {oferta['p_ahora']}*"

            mensaje_whatsapp = (
                f"🔥 *¡OFERTA FLASH!* 🔥\n\n"
                f"📦 *{descripcion}*\n\n"
                f"{txt_precio_wa}\n\n"
                f"🛒 *COMPRA AQUÍ:*\n"
                f"👉 {oferta['url']}\n\n"
                f"🕵️ @RadarPromoMX"
            )
            
            if oferta['foto'] and os.path.exists(oferta['foto']):
                await client.send_file(ID_MI_CANAL, oferta['foto'], caption=mensaje_telegram, parse_mode='html')
                print(f"✅ Publicada en Telegram (con foto): {oferta['asin']}")
            else:
                await client.send_message(ID_MI_CANAL, mensaje_telegram, parse_mode='html')
                print(f"✅ Publicada en Telegram (solo texto): {oferta['asin']}")
            
            enviar_a_whatsapp_grupo(mensaje_whatsapp, oferta['foto'])
            
            if oferta['foto'] and os.path.exists(oferta['foto']):
                os.remove(oferta['foto']) 
            
            registrar_db(oferta['asin'])
            
            if i < len(ofertas_a_publicar) - 1: 
                await asyncio.sleep(20)
                
        except Exception as e:
            print(f"❌ Error crítico en iteración: {e}")

    await client.disconnect()

if __name__ == "__main__":
    inicializar_db()
    asyncio.run(procesar_canales())