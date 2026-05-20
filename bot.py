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
    Envía las ofertas al canal de WhatsApp usando la pasarela gratuita de CallMeBot.
    Mantiene el flujo 100% automatizado desde la nube.
    """
    try:
        # Reutilizamos las variables existentes en tus Secrets para no alterar el YAML
        phone = os.getenv("GREEN_API_INSTANCE")   # Tu número de celular internacional (ej: 521...)
        api_key = os.getenv("GREEN_API_TOKEN")    # Tu API Key de 6 dígitos de CallMeBot
        url_canal = os.getenv("WHATSAPP_CHANNEL_URL")
        
        if not phone or not api_key or not url_canal:
            print("  ❌ WHATSAPP ERROR: Credenciales de CallMeBot ausentes en la nube.")
            return False
            
        # Extraemos el hash único del canal (lo que va después de /channel/)
        channel_pure_id = url_canal.split('/')[-1]
        
        # Endpoint oficial de CallMeBot para Canales/Newsletters
        url = "https://api.callmebot.com/whatsapp.php"
        
        params = {
            "phone": phone,            # Tu celular registrado en la API
            "text": mensaje_wa,         # El mensaje formateado
            "apikey": api_key,         # La llave que te dio el bot
            "channel": channel_pure_id  # El identificador de tu canal destino
        }
        
        # Petición HTTP GET nativa de CallMeBot
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            print("  ✅ CALLMEBOT: ¡Oferta enviada con éxito al Canal de WhatsApp!")
            return True
        else:
            print(f"  ❌ CALLMEBOT ERROR: Código {response.status_code}, Servidor dice: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ⚠️ Error en la pasarela de CallMeBot: {e}")
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
            # --- LIMPIEZA DE TEXTO Y CUPONES BANCARIOS ---
            lineas = oferta['texto_completo'].split('\n')
            lineas_limpias = []
            for linea in lineas:
                # 1. Filtramos líneas completas basura de enlaces, precios o hashtags de siempre
                pattern_basura = r'(?i)(https?://|precio|oferta|descuento|\$|-?\d{1,2}%|unete|ver|#)'
                if re.search(pattern_basura, linea): 
                    continue
                
                # 2. Pulido de cupones bancarios para mantener la estética limpia
                linea_filtrada = re.sub(r'(?i)(bbva|banorte|hsbc|citibanamex|banamex|santander|amex|coppel|mercadopago)\s*:\s*\w+', '', linea)
                linea_filtrada = re.sub(r'(?i)\b(bbva|banorte|hsbc|citibanamex|banamex|santander|amex)\b', '', linea_filtrada)
                
                # Limpiamos remanentes de emojis que se usan en las promociones bancarias
                linea_filtrada = linea_filtrada.replace('✅', '').replace('🔥', '').strip()
                
                if linea_filtrada: 
                    lineas_limpias.append(linea_filtrada)
            
            descripcion = " ".join(lineas_limpias[:2])
            
            # Bandera (?i) corregida al inicio para evitar el DeprecationWarning de Python
            descripcion = re.sub(r'(?i)^amazon\s*:\s*', '', descripcion)
            
            # --- CONSTRUCCIÓN DE PLANTILLAS