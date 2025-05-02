// script.js

// Respuestas predefinidas del chatbot
const predefinedResponses = {
  "hola": "¡Hola humano! Soy tu asistente virtual. ¿Qué deseas saber?",
  "¿cómo estás?": "Estoy mejorando mis sistemas, ¡gracias por preguntar! ¿Y tú?",
  "adiós": "¡Hasta pronto! Que los circuitos te acompañen.",
  "quién eres": "Soy un chatbot con alma de inteligencia artificial futurista 🤖✨",
  "default": "Hmm... no tengo datos sobre eso. ¿Puedes reformular la pregunta?"
};

// Funciones del chatbot
let messageQueue = [];
let isProcessing = false;

// Función para mostrar/ocultar indicador de escritura
function toggleTypingIndicator(show) {
    const existingIndicator = document.querySelector('.typing-indicator');
    if (show && !existingIndicator) {
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator bot-message';
        indicator.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;
        document.getElementById('chat-box').appendChild(indicator);
    } else if (!show && existingIndicator) {
        existingIndicator.remove();
    }
}

// Función para agregar mensajes al chat
function appendMessage(message, type) {
    const chatBox = document.getElementById("chat-box");
    const messageContainer = document.createElement("div");
    const messageElement = document.createElement("div");
    
    messageContainer.classList.add('message-container');
    messageElement.classList.add('message', `${type}-message`);
    
    // Añadir el contenido del mensaje
    messageElement.textContent = message;
    
    // Añadir timestamp
    const timestamp = document.createElement("small");
    timestamp.classList.add('message-time');
    const time = new Date().toLocaleTimeString('es-ES', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    timestamp.textContent = time;
    messageElement.appendChild(timestamp);
    
    // Agregar al contenedor
    messageContainer.appendChild(messageElement);
    chatBox.appendChild(messageContainer);
    
    // Scroll suave al último mensaje
    chatBox.scrollTo({
        top: chatBox.scrollHeight,
        behavior: 'smooth'
    });
}

// Función para procesar la cola de mensajes
async function processMessageQueue() {
    if (isProcessing || messageQueue.length === 0) return;
    
    isProcessing = true;
    const message = messageQueue.shift();
    
    try {
        // Mostrar indicador de escritura
        toggleTypingIndicator(true);

        // Simular delay natural de escritura
        await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 1000));

        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `message=${encodeURIComponent(message)}`
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        toggleTypingIndicator(false);
        appendMessage(data.text, 'bot');

    } catch (error) {
        console.error('Error:', error);
        toggleTypingIndicator(false);
        appendMessage('Lo siento, ha ocurrido un error. ¿Podrías intentarlo de nuevo?', 'bot');
    }

    isProcessing = false;
    processMessageQueue(); // Procesar siguiente mensaje si existe
}

// Función para enviar mensaje
async function sendMessage(event) {
    event.preventDefault();
    
    const inputField = document.getElementById("user-input");
    const userInput = inputField.value.trim();
    
    if (userInput === "") return;

    // Mostrar mensaje del usuario
    appendMessage(userInput, 'user');
    inputField.value = "";
    
    // Añadir mensaje a la cola
    messageQueue.push(userInput);
    processMessageQueue();
}

// Eventos
document.getElementById("chat-form").addEventListener("submit", sendMessage);

// Mensaje de bienvenida
window.addEventListener('load', () => {
    appendMessage('👋 ¡Hola! Soy tu asistente virtual. Estoy aquí para ayudarte con tus preguntas sobre Python y programación.', 'bot');
});
