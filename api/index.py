from flask import Flask, request, jsonify
from flask_cors import CORS
from scuapi import API

app = Flask(__name__)
# Abilitiamo CORS in caso tu voglia testare in locale con server separati
CORS(app) 

DOMINIO_SC = 'streamingcommunity.cz'
DOMINIO_VIX = 'vixcloud.co'
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
    tmdb_id = request.args.get('tmdb_id')
    is_serie = request.args.get('is_serie', 'false').lower() == 'true'
    season = request.args.get('season', 1, type=int)
    episode = request.args.get('episode', 1, type=int)

    if not tmdb_id:
        return jsonify({'error': 'Manca il parametro tmdb_id'}), 400

    try:
        if is_serie:
            iframe, m3u_url = sc.get_links(DOMINIO_VIX, int(tmdb_id), (season, episode))
        else:
            iframe, m3u_url = sc.get_links(DOMINIO_VIX, int(tmdb_id))

        return jsonify({
            'success': True,
            'iframe': iframe,
            'm3u8_url': m3u_url
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Nessun blocco if __name__ == '__main__': richiesto su Vercel.
# L'oggetto 'app' viene esposto ed eseguito direttamente dall'infrastruttura Serverless.
