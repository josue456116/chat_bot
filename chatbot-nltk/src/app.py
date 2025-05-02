from flask import Flask, request, jsonify, render_template, url_for
from chatbot.bot import ChatBot
import logging

app = Flask(__name__, 
    static_folder='static',
    template_folder='templates'
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Inicializar el chatbot
try:
    chatbot = ChatBot()
    logging.info("ChatBot inicializado correctamente")
except Exception as e:
    logging.error(f"Error al inicializar ChatBot: {str(e)}")
    raise

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.form['message']
        bot_response = chatbot.get_response(user_message)
        return jsonify({
            'text': bot_response,
            'type': 'bot'
        })
    except Exception as e:
        return jsonify({
            "message": "Lo siento, ocurrió un error al procesar tu mensaje.",
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)