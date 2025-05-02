import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import numpy as np
import random
import torch
import torch.nn as nn
from sklearn.preprocessing import LabelEncoder
import pandas as pd
import logging
from pathlib import Path
import json
import pickle
from torch.serialization import add_safe_globals

class ChatBotNN(nn.Module):
    def __init__(self, vocab_size, embedding_dim, hidden_dim, output_dim):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.lstm = nn.LSTM(embedding_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, output_dim)
    
    def forward(self, text):
        embedded = self.embedding(text)
        lstm_out, _ = self.lstm(embedded)
        return self.fc(lstm_out[:, -1, :])

class ChatBot:
    def __init__(self):
        # Descargamos los recursos necesarios de NLTK
        nltk.download('punkt')
        nltk.download('stopwords')
        nltk.download('wordnet')
        
        self.lemmatizer = WordNetLemmatizer()
        self.label_encoder = LabelEncoder()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Parámetros del modelo
        self.vocab_size = 10000  # Aumentamos más el vocabulario
        self.embedding_dim = 200  # Aumentamos dimensión de embeddings
        self.hidden_dim = 256    # Aumentamos capas ocultas
        
        # Umbral de confianza más bajo para más flexibilidad
        self.confidence_threshold = 0.4
        
        self.current_context = 'general'
        self.conversation_history = []
        self.context_threshold = 0.85

        # Configurar directorios
        self.data_dir = Path(__file__).parent.parent / 'data'
        self.model_dir = self.data_dir / 'models'
        
        # Crear directorios si no existen
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Intentar cargar modelo existente
        if not self.load_model():
            logging.info("No se encontró modelo guardado. Entrenando nuevo modelo...")
            self._load_training_data()
            self._train_initial_model()
            self.save_model()
        else:
            self._load_training_data()  # Solo para tener las respuestas disponibles

    def _load_training_data(self):
        csv_path = self.data_dir / 'training_data.csv'
        if not csv_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo de entrenamiento en: {csv_path}")
        
        self.training_data = pd.read_csv(csv_path)
        
        # Verificar las columnas
        expected_columns = ['pregunta', 'respuesta', 'categoria']
        if not all(col in self.training_data.columns for col in expected_columns):
            raise ValueError(f"El CSV debe tener las columnas: {expected_columns}")
        
        # Convertir a string y limpiar datos
        self.training_data['pregunta'] = self.training_data['pregunta'].astype(str).str.lower()
        logging.info(f"Categorías cargadas: {self.training_data['categoria'].unique()}")

    def _train_initial_model(self):
        # Preparar datos
        X_train = self.training_data['pregunta'].astype(str).tolist()
        y_train = self.training_data['categoria'].tolist()

        # Codificar las categorías
        y_encoded = self.label_encoder.fit_transform(y_train)
        
        # Procesar texto
        X_processed = [self.preprocess_text(text) for text in X_train]
        X_padded = torch.tensor(self._pad_sequences(X_processed), dtype=torch.long).to(self.device)
        y_tensor = torch.tensor(y_encoded, dtype=torch.long).to(self.device)

        # Crear el modelo
        num_categories = len(set(y_train))
        self.model = ChatBotNN(
            vocab_size=self.vocab_size,
            embedding_dim=self.embedding_dim,
            hidden_dim=self.hidden_dim,
            output_dim=num_categories
        ).to(self.device)

        # Entrenamiento
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(self.model.parameters())
        
        self.model.train()
        num_epochs = 100
        best_loss = float('inf')
        
        for epoch in range(num_epochs):
            optimizer.zero_grad()
            output = self.model(X_padded)
            loss = criterion(output, y_tensor)
            loss.backward()
            optimizer.step()
            
            if epoch % 10 == 0:
                print(f"Época {epoch}/{num_epochs}, Loss: {loss.item():.4f}")

    def preprocess_text(self, text):
        # Asegurarnos de que el texto sea string
        text = str(text)
        tokens = word_tokenize(text.lower())
        stop_words = set(stopwords.words('spanish'))
        tokens = [self.lemmatizer.lemmatize(token) for token in tokens if token not in stop_words]
        return tokens

    def _pad_sequences(self, sequences, max_length=10):
        padded = np.zeros((len(sequences), max_length), dtype=np.int64)  # Cambiado a int64
        for i, seq in enumerate(sequences):
            padded[i, :len(seq)] = [hash(word) % self.vocab_size for word in seq[:max_length]]
        return padded

    def get_response(self, text):
        """Procesa el texto de entrada y retorna una respuesta."""
        self.model.eval()
        with torch.no_grad():
            # Normalizar texto
            text_lower = text.lower().strip()
            
            # Proceso directo para preguntas tipo "qué es"
            if text_lower.startswith(('que es', 'qué es', 'q es')):
                search_term = text_lower.replace('que es', '').replace('qué es', '').replace('q es', '').strip()
                # Buscar en el dataset
                matches = self.training_data[
                    self.training_data['pregunta'].str.contains(search_term, case=False, na=False)
                ]
                if not matches.empty:
                    return random.choice(matches['respuesta'].tolist())
            
            # Procesar texto para el modelo
            processed = self.preprocess_text(text_lower)
            padded = torch.tensor(self._pad_sequences([processed]), dtype=torch.long).to(self.device)
            
            output = self.model(padded)
            probabilities = torch.softmax(output, dim=1)
            confidence, pred_idx = torch.max(probabilities, dim=1)
            
            logging.info(f"Texto: '{text}', Confianza: {confidence.item():.4f}")
            
            # Si la confianza es baja, buscar coincidencias exactas
            if confidence.item() < self.confidence_threshold:
                exact_match = self.training_data[
                    self.training_data['pregunta'].str.lower() == text_lower
                ]
                if not exact_match.empty:
                    return random.choice(exact_match['respuesta'].tolist())
                
                # Buscar coincidencias parciales
                partial_matches = self.training_data[
                    self.training_data['pregunta'].str.contains(text_lower, case=False, na=False)
                ]
                if not partial_matches.empty:
                    return random.choice(partial_matches['respuesta'].tolist())
                    
                return "Lo siento, no estoy seguro de cómo responder eso. ¿Podrías reformularlo?"
            
            # Obtener respuesta basada en la categoría
            intent = self.label_encoder.inverse_transform([pred_idx.item()])[0]
            possible_responses = self.training_data[
                self.training_data['categoria'] == intent
            ]['respuesta'].tolist()
            
            if not possible_responses:
                return "No tengo una respuesta específica para eso."
                
            return random.choice(possible_responses)

    def save_model(self):
        """Guarda el modelo entrenado y sus parámetros."""
        model_path = self.model_dir / 'model.pth'
        params_path = self.model_dir / 'params.json'
        
        try:
            # Guardar el modelo completo
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'vocab_size': self.vocab_size,
                'embedding_dim': self.embedding_dim,
                'hidden_dim': self.hidden_dim,
                'label_encoder': self.label_encoder
            }, model_path)
            
            # Guardar parámetros adicionales
            with open(params_path, 'wb') as f:
                pickle.dump({
                    'confidence_threshold': self.confidence_threshold,
                    'context_threshold': self.context_threshold,
                    'categories': list(self.training_data['categoria'].unique())
                }, f)
            
            logging.info(f"Modelo y parámetros guardados en {self.model_dir}")
            return True
            
        except Exception as e:
            logging.error(f"Error al guardar el modelo: {str(e)}")
            return False

    def load_model(self):
        """Carga el modelo guardado."""
        model_path = self.model_dir / 'model.pth'
        
        if not model_path.exists():
            return False
            
        try:
            # Permitir cargar el LabelEncoder de forma segura
            torch.serialization.add_safe_globals(['sklearn.preprocessing._label.LabelEncoder'])
            
            # Cargar el modelo
            checkpoint = torch.load(
                model_path, 
                weights_only=False,
                map_location=self.device
            )
            
            # Recrear el modelo
            self.model = ChatBotNN(
                vocab_size=checkpoint['vocab_size'],
                embedding_dim=checkpoint['embedding_dim'],
                hidden_dim=checkpoint['hidden_dim'],
                output_dim=len(checkpoint['label_encoder'].classes_)
            ).to(self.device)
            
            # Cargar pesos y label encoder
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.label_encoder = checkpoint['label_encoder']
            
            logging.info("Modelo cargado correctamente")
            return True
            
        except Exception as e:
            logging.warning(f"Error al cargar el modelo: {str(e)}")
            logging.info("Continuando con entrenamiento nuevo...")
            return False