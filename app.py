from flask import Flask, request, jsonify
import whisper
import os
from flask_cors import CORS
import tempfile
import requests
from openai import OpenAI
import re, json


client = OpenAI(api_key="APIKEY")

print("Iniciando Flask...")

app = Flask(__name__)
CORS(app)




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
                {{ "fecha": "1809-10-30 10:00:00.000", "titulo": "Nacimiento de Abraham Lincoln" }},
                {{ "fecha": "2025-12-31 10:00:00.000", "titulo": "Día del Trabajo" }}
            ]
            }}

        Texto:
        \"\"\"{texto}\"\"\"
        """


    try:
        completion = client.chat.completions.create(
            # model="gpt-4o",  
            # gpt-3.5-turbo" 
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3 
        )

        respuesta_modelo = completion.choices[0].message.content
        print(respuesta_modelo)

        json_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', respuesta_modelo)
        if json_match:
            contenido_json = json_match.group(1)
        else:
            contenido_json = respuesta_modelo 

        respuesta_json = json.loads(contenido_json)
        return jsonify(respuesta_json)
        # import json
        # respuesta_json = json.loads(respuesta_modelo)
        # return jsonify(respuesta_json)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


@app.route('/generar-mapa-mental', methods=['POST'])
def generar_mapa_mental():
    data = request.get_json()
    texto = data.get("texto", "")

    if not texto:
        return jsonify({"error": "Texto vacío"}), 400

    prompt = f"""
Eres un generador de JSON estricto. No expliques nada, solo responde en JSON válido.

Analiza el siguiente texto y genera un mapa mental en formato **Mermaid Mindmap**.

El formato debe ser así:

{{
  "mermaid": "mermaid\\nmindmap\\n  root((TEMA PRINCIPAL))\\n    Subtema\\n      Idea 1\\n      Idea 2"
}}

Usa subtítulos resumidos, ideas concisas, no repitas el contenido literal, organiza el tema principal con subtemas e ideas relevantes.

No incluyas explicaciones, ni texto adicional fuera del JSON.

Texto a analizar:
\"\"\"{texto}\"\"\"
    """

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        respuesta_modelo = completion.choices[0].message.content
        print(respuesta_modelo)

        json_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', respuesta_modelo)
        if json_match:
            contenido_json = json_match.group(1)
        else:
            contenido_json = respuesta_modelo

        respuesta_json = json.loads(contenido_json)
        return jsonify(respuesta_json)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
    
