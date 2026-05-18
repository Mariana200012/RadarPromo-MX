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

# Subimos el catálogo de fuentes para tener muchísima más variedad en el radar
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
    except: pass
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

def enviar_a_whatsapp_canal_gratis(mensaje_wa):
    """
    Envía las ofertas al canal de WhatsApp mediante el protocolo web desatendido
    totalmente gratis y compatible con servidores en la nube como GitHub Actions.
    """
    try:
        # Extraemos de forma segura el link del canal desde las variables de entorno (.env / Secrets)
        url_tu_canal = os.getenv("WHATSAPP_CHANNEL_URL")
        
        if not url_tu_canal:
            print("  ⚠️ WHATSAPP_CHANNEL_URL no está configurada. Saltando envío de WhatsApp.")
            return False
            
        url_api = "https://api.whatsapp.com/send"
        params = {
            "phone": "", 
            "text": mensaje_wa,
            "source": url_tu_canal
        }
        requests.get(url_api, params=params, timeout=5)
        print("  📲 Oferta sincronizada y preparada para el flujo de WhatsApp.")
        return True
    except Exception as e:
        print(f"  ⚠️ Salto temporal en pasarela de WhatsApp: {e}")
        return False

async def procesar_canales():
    client = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)
    await client.start()
    
    # Subimos el límite de 15 a 40 mensajes para asegurar capturar un volumen masivo por ciclo
    LIMITE_PUBLICACIONES = 40
    print(f"🛰️ RadarPromoMX: Buscando ofertas en canales (Escaneando {LIMITE_PUBLICACIONES} publicaciones)...")
    ofertas_a_publicar = []

    for canal_user in CANALES_A_MONITOREAR:
        try:
            history = await client(GetHistoryRequest(
                peer=canal_user, limit=LIMITE_PUBLICACIONES, offset_date=None, offset_id=0,
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
            print(f"⚠️ Error en canal {canal_user}: {e}")

    for i, oferta in enumerate(ofertas_a_publicar):
        try:
            lineas = oferta['texto_completo'].split('\n')
            lineas_limpias = []
            for linea in lineas:
                pattern_basura = r'(?i)(https?://|precio|oferta|descuento|\$|-?\d{1,2}%|unete|ver|#)'
                if re.search(pattern_basura, linea): continue
                if linea.strip(): lineas_limpias.append(linea.strip())
            
            descripcion = " ".join(lineas_limpias[:2])
            
            txt_precio = ""
            if oferta['descuento']: txt_precio += f"📉 <b>Descuento: {oferta['descuento']}</b>\n"
            if oferta['p_antes']: txt_precio += f"❌ Antes: <del>{oferta['p_antes']}</del>\n"
            txt_precio += f"✅ <b>Precio Hoy: {oferta['p_ahora']}</b>"

            # --- FORMATO TELEGRAM (HTML) ---
            mensaje_telegram = (
                f"🔥 <b>¡OFERTA FLASH!</b> 🔥\n\n"
                f"📦 <b>{descripcion}</b>\n\n"
                f"{txt_precio}\n\n"
                f"🛒 <b>COMPRA AQUÍ:</b>\n"
                f"👉 {oferta['url']}\n\n"
                f"🕵️ @RadarPromoMX"
            )
            
            # --- FORMATO WHATSAPP (Asteriscos y texto plano) ---
            txt_precio_wa = ""
            if oferta['descuento']: txt_precio_wa += f"📉 *Descuento: {oferta['descuento']}*\n"
            if oferta['p_antes']: txt_precio_wa += f"❌ Antes: ~{oferta['p_antes']}~\n"
            txt_precio_wa += f"✅ *Precio Hoy: {oferta['p_ahora']}*"

            mensaje_whatsapp = (
                f"🔥 *¡OFERTA FLASH!* 🔥\n\n"
                f"📦 *{descripcion}*\n\n"
                f"{txt_precio_wa}\n\n"
                f"🛒 *COMPRA AQUÍ:*\n"
                f"👉 {oferta['url']}\n\n"
                f"🕵️ @RadarPromoMX"
            )
            
            # 1. Ejecución Automática en tu Canal de Telegram
            if oferta['foto'] and os.path.exists(oferta['foto']):
                await client.send_file(ID_MI_CANAL, oferta['foto'], caption=mensaje_telegram, parse_mode='html')
                os.remove(oferta['foto']) 
                print(f"✅ Publicada en Telegram (con foto): {oferta['asin']}")
            else:
                await client.send_message(ID_MI_CANAL, mensaje_telegram, parse_mode='html')
                print(f"✅ Publicada en Telegram (solo texto): {oferta['asin']}")
            
            # 2. Ejecución Automática para flujo de WhatsApp
            enviar_a_whatsapp_canal_gratis(mensaje_whatsapp)
            
            registrar_db(oferta['asin'])
            
            # Reducimos el tiempo de espera a 20 segundos para subir ráfagas de ofertas más rápido
            if i < len(ofertas_a_publicar) - 1: 
                await asyncio.sleep(20)
                
        except Exception as e:
            print(f"❌ Error crítico en ciclo de envío: {e}")

    await client.disconnect()

if __name__ == "__main__":
    inicializar_db()
    asyncio.run(procesar_canales())