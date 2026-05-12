import os
import re
import sqlite3
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetHistoryRequest
from dotenv import load_dotenv

# 1. CONFIGURACIÓN
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

# 3. LÓGICA DE PROCESAMIENTO
async def procesar_canales():
    client = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)
    await client.start()
    
    print("🛰️ RadarPromoMX: Buscando nuevas gangas...")
    ofertas_a_publicar = []

    for canal_user in CANALES_A_MONITOREAR:
        try:
            history = await client(GetHistoryRequest(
                peer=canal_user, limit=15, offset_date=None, offset_id=0,
                max_id=0, min_id=0, add_offset=0, hash=0
            ))
            
            contador = 0
            for msg in history.messages:
                if contador >= 5: break # Subimos a 5 por canal
                
                if msg.message:
                    urls = re.findall(r'(https?://[^\s]+)', msg.message)
                    if urls:
                        match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', urls[0])
                        if match:
                            asin = match.group(1)
                            if not ya_publicado(asin):
                                # Extraer precios
                                precios = re.findall(r'\$\s?[\d,.]+', msg.message)
                                p_ahora = precios[0] if len(precios) >= 1 else "Ver en tienda"
                                p_antes = precios[1] if len(precios) >= 2 else None
                                
                                foto = None
                                if msg.media:
                                    foto = await msg.download_media()
                                elif msg.web_preview and msg.web_preview.photo:
                                    foto = await client.download_media(msg.web_preview.photo)
                                
                                ofertas_a_publicar.append({
                                    'asin': asin,
                                    'url': f"https://www.amazon.com.mx/dp/{asin}?tag={AMAZON_TAG}",
                                    'texto': msg.message,
                                    'p_ahora': p_ahora,
                                    'p_antes': p_antes,
                                    'foto': foto
                                })
                                contador += 1
        except Exception as e:
            print(f"⚠️ Error en {canal_user}: {e}")

    # 4. DISEÑO FINAL (MEJORADO SEGÚN image_8310bc.png)
    for i, oferta in enumerate(ofertas_a_publicar):
        try:
            # Limpieza selectiva: solo quitamos links y hashtags, dejamos el texto intacto
            t = re.sub(r'https?://[^\s]+', '', oferta['texto'])
            t = re.sub(r'#\S+', '', t)
            # Quitamos frases específicas de otros grupos si aparecen
            t = re.sub(r'(?i)unete a nuestros otros grupos.*', '', t)
            t = re.sub(r'(?i)ver oferta.*', '', t)
            t = t.replace('👉', '').replace('🔥', '').strip()
            
            # Formato de precio
            txt_precio = f"✅ <b>Precio: {oferta['p_ahora']}</b>"
            if oferta['p_antes']:
                txt_precio = f"❌ Antes: <del>{oferta['p_antes']}</del>\n{txt_precio}"

            mensaje = (
                f"🔥 <b>¡OFERTA FLASH!</b> 🔥\n\n"
                f"📦 {t[:300]}...\n\n"
                f"{txt_precio}\n\n"
                f"🛒 <b>COMPRA AQUÍ:</b>\n"
                f"👉 {oferta['url']}\n\n"
                f"🕵️ @RadarPromoMX"
            )
            
            if oferta['foto']:
                await client.send_file(ID_MI_CANAL, oferta['foto'], caption=mensaje, parse_mode='html')
                if os.path.exists(oferta['foto']): os.remove(oferta['foto'])
            else:
                await client.send_message(ID_MI_CANAL, mensaje, parse_mode='html')
            
            registrar_db(oferta['asin'])
            print(f"✅ Publicada: {oferta['asin']}")
            
        except Exception as e:
            print(f"❌ Error al enviar: {e}")

        if i < len(ofertas_a_publicar) - 1:
            print("⏳ Esperando 5 minutos para evitar spam...")
            await asyncio.sleep(300) 

    await client.disconnect()
    print("🏁 Ráfaga terminada. El bot se cierra hasta la siguiente hora.")

if __name__ == "__main__":
    inicializar_db()
    asyncio.run(procesar_canales())