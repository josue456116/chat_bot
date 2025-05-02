class Chatbot:
    def __init__(self, responses):
        self.responses = responses

    def respond(self, user_input):
        # Aquí se puede implementar la lógica para generar una respuesta
        return self.responses.get(user_input, "Lo siento, no entiendo la pregunta.")