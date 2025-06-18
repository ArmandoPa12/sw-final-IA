from flask import Flask, request, jsonify
import whisper
import os
from flask_cors import CORS
import tempfile
import requests
from openai import OpenAI


client = OpenAI(api_key="charGPT-APIKEY")

print("Iniciando Flask...")

app = Flask(__name__)
CORS(app)


# Cargar modelo una sola vez (esto evita cargarlo en cada petición)
model = whisper.load_model("tiny")

@app.route('/transcribir', methods=['POST'])
def transcribir_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No se envió archivo de audio'}), 400

    audio_file = request.files['audio']

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp:
        audio_path = temp.name
        audio_file.save(audio_path)

    try:
        result = model.transcribe(audio_path, language="Spanish")
        texto = result["text"]
        return jsonify({'transcripcion': texto})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        os.remove(audio_path)


@app.route('/transcribir/url', methods=['POST'])
def transcribir_desde_url():
    data = request.get_json()

    if not data or 'url' not in data:
        return jsonify({'error': 'No se envió la URL del audio'}), 400

    audio_url = data['url']

    try:
        response = requests.get(audio_url)
        if response.status_code != 200:
            return jsonify({'error': 'No se pudo descargar el audio'}), 400

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp:
            audio_path = temp.name
            temp.write(response.content)

        result = model.transcribe(audio_path, language="Spanish")
        texto = result["text"]
        return jsonify({'transcripcion': texto})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.remove(audio_path)



@app.route('/resumir', methods=['POST'])
def resumir_texto():
    data = request.get_json()

    if not data or 'texto' not in data:
        return jsonify({'error': 'No se envió texto para resumir'}), 400

    texto = data['texto']

    prompt = f"""
Dado el siguiente texto:

{texto}

Haz lo siguiente:

1. Resume el contenido en formato **Markdown**, con viñetas o secciones claras si es posible.
2. Extrae todas las fechas importantes (en cualquier formato: "12 de mayo de 1990", "1990-05-12", "1ro de mayo", etc.).
3. Por cada fecha extraída, crea un objeto JSON con:
   - `"fecha"`: la fecha en formato estándar (YYYY-MM-DD o MM-DD si no hay año).
   - `"titulo"`: una breve descripción del evento o hecho relacionado con esa fecha.

Devuelve una **respuesta en JSON** con dos claves:
- `"markdown"`: el resumen en formato Markdown.
- `"fechas"`: una lista de objetos con las fechas extraídas y sus títulos.

NO EXPLIQUES NADA. SOLO DEVUELVE EL JSON DE RESPUESTA.
"""

    try:
        respuesta = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False
            }
        )

        if respuesta.status_code != 200:
            return jsonify({'error': 'Error al generar respuesta con Mistral'}), 500

        contenido = respuesta.json().get("response", "").strip()

        inicio = contenido.find('{')
        if inicio != -1:
            try:
                contenido_json = contenido[inicio:]
                return jsonify(eval(contenido_json))
            except Exception as e:
                return jsonify({'error': 'Error al procesar JSON: ' + str(e), 'raw': contenido}), 500

        return jsonify({'error': 'No se pudo extraer JSON de la respuesta', 'raw': contenido})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/mapa', methods=['POST'])
def mapa_mental():
    data = request.get_json()
    print('=====inicio de mapa===========')
    if not data or 'texto' not in data:
        return jsonify({'error': 'No se envió texto para resumir'}), 400

    texto = data['texto']

    prompt = f"""
Dado el siguiente texto:

{texto}

saluda tambien 
"""

    try:
        respuesta = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False
            }
        )

        if respuesta.status_code != 200:
            return jsonify({'error': 'Error al generar respuesta con Mistral'}), 500

        # Tratar de parsear directamente la respuesta como JSON
        contenido = respuesta.json().get("response", "").strip()

        # # A veces Ollama devuelve texto no válido. Intentamos aislar solo el JSON:
        # inicio = contenido.find('{')
        # if inicio != -1:
        #     try:
        #         contenido_json = contenido[inicio:]
        #         return jsonify(eval(contenido_json))
        #     except Exception as e:
        #         return jsonify({'error': 'Error al procesar JSON: ' + str(e), 'raw': contenido}), 500
        print('===== fin de mapa===========')

        return jsonify({'raw': contenido})

    except Exception as e:
        return jsonify({'error': str(e)}), 500




@app.route('/resumir-chatgpt', methods=['POST'])
def resumir_con_chatgpt():
    data = request.get_json()
    texto = data.get("texto", "")

    if not texto:
        return jsonify({"error": "Texto vacío"}), 400

    prompt = f"""
        Eres un generador de JSON estricto. No expliques nada, solo responde en JSON válido.

        Analiza el siguiente texto y:

        1. Haz un resumen formal, extenso y sin emojis, en formato Markdown (campo "markdown").
        2. Extrae todas las fechas importantes y escribe un título resumido para cada una (campo "fechas").

        Devuelve únicamente un JSON con la siguiente estructura, sin ningún texto adicional:

            {{
            "markdown": "### Resumen\\n- Abraham Lincoln nació en 1809-02-12.\\n- El Día del Trabajo se celebra el 01-05 cada año.",
            "fechas": [
                {{ "fecha": "1809-02-12", "titulo": "Nacimiento de Abraham Lincoln" }},
                {{ "fecha": "05-01", "titulo": "Día del Trabajo" }}
            ]
            }}

        Texto:
        \"\"\"{texto}\"\"\"
        """


    try:
        completion = client.chat.completions.create(
            # model="gpt-4o",  # o "gpt-3.5-turbo" si prefieres algo más rápido
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3 
        )
        respuesta_modelo = completion.choices[0].message.content

        # Intentamos parsear como JSON (solo si el modelo responde en JSON bien formado)
        import json
        respuesta_json = json.loads(respuesta_modelo)
        return jsonify(respuesta_json)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
    
