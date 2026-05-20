def enviar_a_whatsapp_canal_gratis(mensaje_wa):
    """
    Envía las ofertas al canal de WhatsApp usando la pasarela gratuita de CallMeBot.
    Mantiene el flujo 100% automatizado y desatendido desde la nube.
    """
    try:
        # Reutilizamos tus variables de GitHub Secrets para no alterar el archivo YAML
        phone = os.getenv("GREEN_API_INSTANCE")   # Tu número de teléfono registrado (asociado a la API Key)
        api_key = os.getenv("GREEN_API_TOKEN")    # Tu API Key de 6 dígitos de CallMeBot
        url_canal = os.getenv("WHATSAPP_CHANNEL_URL")
        
        if not phone or not api_key or not url_canal:
            print("  ❌ WHATSAPP ERROR: Credenciales de CallMeBot ausentes en la nube.")
            return False
            
        # Extraemos el hash único del canal (lo que va después de /channel/)
        channel_pure_id = url_canal.split('/')[-1]
        
        # Endpoint oficial de CallMeBot para publicación en Canales/Newsletters
        url = "https://api.callmebot.com/whatsapp.php"
        
        params = {
            "phone": phone,            # Tu número de celular vinculado
            "text": mensaje_wa,         # El texto de la oferta formateado
            "apikey": api_key,         # La llave de 6 dígitos que te dio el bot
            "channel": channel_pure_id  # El ID de tu canal de WhatsApp destino
        }
        
        # La API de CallMeBot procesa las peticiones mediante el método GET
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