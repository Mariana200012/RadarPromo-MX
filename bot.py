import os
import re
import sqlite3
import requests
import asyncio
import time
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from dotenv import load_dotenv

load_dotenv()
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_STR = os.getenv("TELEGRAM_SESSION") # Usaremos un string de sesión para GitHub Actions
ID_MI_CANAL = '@RadarPromoMX_Oficial'
CANALES_A_MONITOREAR = ['@ofertones', '@radar_deofertas2728'] # Cambia por tus canales reales
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
    cursor.execute("INSERT INTO ofertas_publicadas (source_id) VALUES (?)", (source_id,))
    conn.commit()
    conn.close()

async def procesar_canales():
    # Usamos StringSession para que GitHub Actions no pida código cada vez
    from telethon.sessions import StringSession
    client = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)
    await client.start()

    ofertas_a_publicar = []

    for canal in CANALES_A_MONITOREAR:
        print(f"Revisando {canal}...")
        # Obtenemos los últimos 20 mensajes para buscar ofertas
        history = await client(GetHistoryRequest(
            peer=canal, limit=20, offset_date=None, offset_id=0,
            max_id=0, min_id=0, add_offset=0, hash=0
        ))
        
        contador_canal = 0
        for msg in history.messages:
            if contador_canal >= 4: break # Límite de 4 por canal
            
            if msg.message:
                urls = re.findall(r'(https?://[^\s]+)', msg.message)
                if urls:
                    # Lógica de limpieza simplificada
                    url_raw = urls[0]
                    match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url_raw)
                    if match:
                        asin = match.group(1)
                        if not ya_publicado(asin):
                            foto = await msg.download_media()
                            ofertas_a_publicar.append({
                                'asin': asin,
                                'url': f"https://www.amazon.com.mx/dp/{asin}?tag={AMAZON_TAG}",
                                'foto': foto,
                                'texto': msg.message[:100]
                            })
                            contador_canal += 1

    # Publicación con separación de 5 minutos
    for i, oferta in enumerate(ofertas_a_publicar):
        mensaje = f"🔥 <b>OFERTA RADAR</b>\n\n{oferta['texto']}...\n\n🛒: {oferta['url']}"
        await client.send_file(ID_MI_CANAL, oferta['foto'], caption=mensaje, parse_mode='html')
        registrar_db(oferta['asin'])
        
        if oferta['foto'] and os.path.exists(oferta['foto']):
            os.remove(oferta['foto'])
            
        if i < len(ofertas_a_publicar) - 1:
            print("Esperando 5 minutos para la siguiente publicación...")
            await asyncio.sleep(300) # 300 segundos = 5 minutos

    await client.disconnect()

if __name__ == "__main__":
    inicializar_db()
    asyncio.run(procesar_canales())