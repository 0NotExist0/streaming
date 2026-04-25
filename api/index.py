import requests
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from scuapi import API

app = Flask(__name__)
CORS(app)

# Dominio attuale. Aggiornalo se StreamingCommunity cambia in futuro
DOMINIO_SC = 'streamingcommunityz.ooo'
sc = API(DOMINIO_SC)

@app.route('/api/search', methods=['GET'])
def search_title():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Inserisci un titolo da cercare'}), 400
    
    try:
        # 1. Ricerca tramite la libreria
        raw_results = sc.search(query)
        formatted_results = []
        
        for item in raw_results:
            # 2. Setacciamo i dati: gestiamo sia i dizionari JSON che gli oggetti Python custom
            if isinstance(item, dict):
                # Cerchiamo l'ID ovunque possa essere nascosto
                item_id = item.get('id') or item.get('slug') or item.get('url') or item.get('tmdb_id')
                name = item.get('name') or item.get('title')
            else:
                item_id = getattr(item, 'id', None) or getattr(item, 'slug', None) or getattr(item, 'url', None)
                name = getattr(item, 'name', None) or getattr(item, 'title', None)
            
            # 3. L'iframe richiede solo l'ID numerico puro. 
            # Se la libreria restituisce "6203-john-wick-4", noi estraiamo solo "6203".
            numeric_id = None
            if item_id:
                match = re.search(r'^(\d+)', str(item_id))
                if match:
                    numeric_id = match.group(1)

            if numeric_id and name:
                # Creiamo un formato standardizzato e garantito per il frontend
                formatted_results.append({'id': numeric_id, 'name': name})
                
        if not formatted_results:
            return jsonify({'error': 'Nessun film compatibile trovato. Prova un altro titolo.'}), 404
            
        return jsonify(formatted_results)
    
    except Exception as e:
        return jsonify({'error': f"Errore interno durante la ricerca: {str(e)}"}), 500

@app.route('/api/get_stream', methods=['GET'])
def get_stream():
    sc_id = request.args.get('sc_id') 
    
    # 4. Blocco di sicurezza rigido: se l'HTML ci invia spazzatura, fermiamo tutto prima di crashare
    if not sc_id or sc_id == 'undefined' or sc_id == 'None':
        return jsonify({'error': "ID del film non valido o non letto correttamente dal frontend."}), 400

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        # 5. Scraping diretto dell'Iframe
        iframe_url = f'https://{DOMINIO_SC}/iframe/{sc_id}'
        sc_response = requests.get(iframe_url, headers=headers)
        
        # 6. Ricerca del player VixCloud nascosto
        match = re.search(r'src="(https://vixcloud\.[^"]+/embed/[^"]+)"', sc_response.text)
        if not match:
            return jsonify({'error': f'Iframe VixCloud non trovato nel codice della pagina {iframe_url}'}), 404
            
        vix_embed_url = match.group(1)
        
        # 7. Visitiamo VixCloud fingendoci l'Iframe originale (bypass Referer)
        headers['Referer'] = iframe_url
        vix_response = requests.get(vix_embed_url, headers=headers)
        
        # 8. Estrazione matematica dei token di sicurezza generati dinamicamente
        token_match = re.search(r"'token':\s*'([^']+)'", vix_response.text)
        expires_match = re.search(r"'expires':\s*'([^']+)'", vix_response.text)
        
        if not (token_match and expires_match):
             return jsonify({'error': 'Token di sicurezza VixCloud mancanti. Probabile blocco IP o modifica player.'}), 500
             
        token = token_match.group(1)
        expires = expires_match.group(1)
        
        # 9. Costruzione e rilascio dell'URL HLS finale
        vix_id = vix_embed_url.split('/embed/')[-1].split('?')[0]
        m3u8_url = f"https://vixcloud.co/playlist/{vix_id}?token={token}&expires={expires}"
        
        return jsonify({
            'success': True,
            'm3u8_url': m3u8_url
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
