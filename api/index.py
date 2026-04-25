import requests
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from scuapi import API

app = Flask(__name__)
CORS(app)

# Dominio attuale. Aggiornalo se StreamingCommunity cambia dominio in futuro
DOMINIO_SC = 'streamingcommunityz.ooo'

# Inizializziamo l'API solo per usare la funzione di ricerca testuale (che funziona ancora)
sc = API(DOMINIO_SC)

@app.route('/api/search', methods=['GET'])
def search_title():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Inserisci un titolo da cercare'}), 400
    try:
        results = sc.search(query)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_stream', methods=['GET'])
def get_stream():
    sc_id = request.args.get('sc_id') 
    
    if not sc_id:
        return jsonify({'error': 'Manca il parametro sc_id (ID interno di StreamingCommunity)'}), 400

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        # 1. Scraping diretto: visitiamo la pagina dell'Iframe di SC
        iframe_url = f'https://{DOMINIO_SC}/iframe/{sc_id}'
        sc_response = requests.get(iframe_url, headers=headers)
        
        # 2. Cerchiamo l'URL del player VixCloud nascosto nell'HTML
        # Cerca un pattern tipo: src="https://vixcloud.co/embed/123456"
        match = re.search(r'src="(https://vixcloud\.[^"]+/embed/[^"]+)"', sc_response.text)
        if not match:
            return jsonify({'error': 'Player VixCloud non trovato. Potrebbe essere necessario un proxy o SC ha cambiato struttura.'}), 404
            
        vix_embed_url = match.group(1)
        
        # 3. Visitiamo VixCloud fingendoci il browser che proviene da SC
        headers['Referer'] = iframe_url
        vix_response = requests.get(vix_embed_url, headers=headers)
        
        # 4. Estraiamo i token di sicurezza tramite Regex dal codice sorgente
        token_match = re.search(r"'token':\s*'([^']+)'", vix_response.text)
        expires_match = re.search(r"'expires':\s*'([^']+)'", vix_response.text)
        
        if not (token_match and expires_match):
             return jsonify({'error': 'Impossibile estrarre i token di sicurezza. VixCloud ha cambiato il player.'}), 500
             
        token = token_match.group(1)
        expires = expires_match.group(1)
        
        # 5. Costruiamo l'URL finale HLS (Playlist m3u8)
        # Estraiamo l'ID del video (es. 237396) dall'URL dell'embed
        vix_id = vix_embed_url.split('/embed/')[-1].split('?')[0]
        m3u8_url = f"https://vixcloud.co/playlist/{vix_id}?token={token}&expires={expires}"
        
        return jsonify({
            'success': True,
            'm3u8_url': m3u8_url
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
