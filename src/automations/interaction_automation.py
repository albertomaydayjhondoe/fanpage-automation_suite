"""
Automatización de interacciones
"""

import asyncio
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from src.platforms.base_platform import BasePlatform
from src.utils.logger import setup_logger
from src.utils.database import DatabaseManager

logger = setup_logger(__name__)


class InteractionAutomation:
    """Automatización para interacciones y respuestas"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_manager = DatabaseManager(config)
        
        # Configuraciones de automatización
        self.auto_reply_config = config.get('automation', {}).get('auto_reply', {})
        self.interaction_config = config.get('automation', {}).get('interactions', {})
        
        # Patrones de respuesta automática
        self.response_patterns = self._load_response_patterns()
        
        # Lista de palabras clave para filtrar
        self.keyword_filters = self._load_keyword_filters()
    
    def _load_response_patterns(self) -> Dict[str, str]:
        """Carga patrones de respuesta automática"""
        default_patterns = {
            r'\b(gracias|thank you|thanks)\b': "¡De nada! 😊 ¡Gracias por seguirnos!",
            r'\b(hola|hello|hi)\b': "¡Hola! 👋 ¡Bienvenido/a a nuestra página!",
            r'\b(precio|price|costo|cost)\b': "Te enviaremos información sobre precios por mensaje privado 📩",
            r'\b(horario|hours|schedule)\b': "Nuestro horario de atención es de Lunes a Viernes, 9am a 6pm 🕒",
            r'\b(ubicación|location|dirección|address)\b': "Te compartimos nuestra ubicación por mensaje privado 📍",
            r'\b(contacto|contact|teléfono|phone)\b': "¡Contáctanos! Te enviaremos la información por mensaje privado 📞",
        }
        
        # Cargar patrones personalizados desde configuración
        custom_patterns = self.auto_reply_config.get('patterns', {})
        default_patterns.update(custom_patterns)
        
        return default_patterns
    
    def _load_keyword_filters(self) -> Dict[str, List[str]]:
        """Carga filtros de palabras clave"""
        return {
            'negative': ['spam', 'fake', 'estafa', 'scam', 'malo', 'terrible'],
            'positive': ['excelente', 'genial', 'amazing', 'love', 'great', 'bueno'],
            'questions': ['?', 'cómo', 'cuándo', 'dónde', 'por qué', 'how', 'when', 'where', 'why'],
            'urgent': ['urgente', 'emergencia', 'urgent', 'emergency', 'ayuda', 'help']
        }
    
    async def process_platform_interactions(self, platform: str, client: BasePlatform):
        """Procesa interacciones para una plataforma específica"""
        try:
            logger.info(f"Procesando interacciones para {platform}")
            
            # Procesar comentarios nuevos
            await self._process_new_comments(platform, client)
            
            # Procesar mensajes privados
            await self._process_private_messages(platform, client)
            
            # Actualizar métricas de interacción
            await self._update_interaction_metrics(platform, client)
            
        except Exception as e:
            logger.error(f"Error procesando interacciones de {platform}: {e}")
    
    async def _process_new_comments(self, platform: str, client: BasePlatform):
        """Procesa comentarios nuevos"""
        try:
            # Obtener posts recientes
            recent_posts = await client.get_posts(limit=5)
            
            for post in recent_posts:
                post_id = post.get('id')
                if not post_id:
                    continue
                
                # Obtener comentarios del post
                comments = await client.get_comments(post_id)
                
                for comment in comments:
                    await self._process_single_comment(platform, client, post_id, comment)
                
                # Pausa entre posts para evitar rate limits
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error procesando comentarios de {platform}: {e}")
    
    async def _process_single_comment(self, platform: str, client: BasePlatform, 
                                    post_id: str, comment: Dict[str, Any]):
        """Procesa un comentario individual"""
        try:
            comment_id = comment.get('id')
            comment_text = comment.get('content', '').lower()
            author = comment.get('author', '')
            created_at = comment.get('created_at', '')
            
            # Verificar si ya procesamos este comentario
            if await self._is_comment_processed(comment_id):
                return
            
            # Analizar sentimiento y contenido
            analysis = self._analyze_comment(comment_text)
            
            # Guardar comentario en base de datos
            await self._save_comment_record(platform, post_id, comment, analysis)
            
            # Decidir si responder automáticamente
            should_reply = await self._should_auto_reply(comment_text, analysis)
            
            if should_reply:
                reply_text = self._generate_auto_reply(comment_text, analysis)
                
                if reply_text:
                    # Enviar respuesta
                    result = await client.reply_to_comment(comment_id, reply_text)
                    
                    if result.get('success'):
                        logger.info(f"Respuesta automática enviada en {platform}: {comment_id}")
                        await self._save_reply_record(platform, comment_id, reply_text, result)
            
            # Marcar comentario como procesado
            await self._mark_comment_processed(comment_id)
            
        except Exception as e:
            logger.error(f"Error procesando comentario {comment.get('id')}: {e}")
    
    def _analyze_comment(self, comment_text: str) -> Dict[str, Any]:
        """Analiza el sentimiento y contenido de un comentario"""
        analysis = {
            'sentiment': 'neutral',
            'keywords': [],
            'is_question': False,
            'is_urgent': False,
            'confidence': 0.5
        }
        
        # Detectar sentimiento básico
        positive_count = sum(1 for word in self.keyword_filters['positive'] 
                           if word in comment_text)
        negative_count = sum(1 for word in self.keyword_filters['negative'] 
                           if word in comment_text)
        
        if positive_count > negative_count:
            analysis['sentiment'] = 'positive'
            analysis['confidence'] = min(0.8, 0.5 + positive_count * 0.1)
        elif negative_count > positive_count:
            analysis['sentiment'] = 'negative'
            analysis['confidence'] = min(0.8, 0.5 + negative_count * 0.1)
        
        # Detectar preguntas
        question_indicators = sum(1 for word in self.keyword_filters['questions'] 
                                if word in comment_text)
        analysis['is_question'] = question_indicators > 0
        
        # Detectar urgencia
        urgent_indicators = sum(1 for word in self.keyword_filters['urgent'] 
                              if word in comment_text)
        analysis['is_urgent'] = urgent_indicators > 0
        
        # Extraer palabras clave
        words = comment_text.split()
        analysis['keywords'] = [word for word in words if len(word) > 3][:5]
        
        return analysis
    
    async def _should_auto_reply(self, comment_text: str, analysis: Dict[str, Any]) -> bool:
        """Determina si se debe responder automáticamente"""
        
        # No responder si la auto-respuesta está deshabilitada
        if not self.auto_reply_config.get('enabled', False):
            return False
        
        # No responder a comentarios negativos automáticamente
        if analysis['sentiment'] == 'negative':
            return False
        
        # Responder a preguntas frecuentes
        if analysis['is_question']:
            return True
        
        # Responder a comentarios positivos ocasionalmente
        if analysis['sentiment'] == 'positive' and analysis['confidence'] > 0.7:
            return True
        
        # Verificar patrones específicos
        for pattern in self.response_patterns.keys():
            if re.search(pattern, comment_text, re.IGNORECASE):
                return True
        
        return False
    
    def _generate_auto_reply(self, comment_text: str, analysis: Dict[str, Any]) -> Optional[str]:
        """Genera una respuesta automática"""
        
        # Buscar patrón específico
        for pattern, response in self.response_patterns.items():
            if re.search(pattern, comment_text, re.IGNORECASE):
                return response
        
        # Respuestas por sentimiento
        if analysis['sentiment'] == 'positive':
            positive_replies = [
                "¡Gracias por tu comentario positivo! 😊",
                "¡Nos alegra saber eso! 🎉",
                "¡Muchas gracias! ❤️"
            ]
            import random
            return random.choice(positive_replies)
        
        # Respuesta para preguntas generales
        if analysis['is_question']:
            return "¡Gracias por tu pregunta! Te responderemos pronto 😊"
        
        return None
    
    async def _process_private_messages(self, platform: str, client: BasePlatform):
        """Procesa mensajes privados"""
        try:
            messages = await client.get_messages()
            
            for message in messages:
                if not message.get('is_read', True):
                    await self._process_single_message(platform, client, message)
                    
        except Exception as e:
            logger.error(f"Error procesando mensajes privados de {platform}: {e}")
    
    async def _process_single_message(self, platform: str, client: BasePlatform, 
                                    message: Dict[str, Any]):
        """Procesa un mensaje privado individual"""
        try:
            message_id = message.get('id')
            message_text = message.get('content', '')
            sender_id = message.get('sender_id', '')
            
            # Guardar mensaje en base de datos
            await self._save_message_record(platform, message)
            
            # Respuesta automática para mensajes (más conservadora)
            if self.auto_reply_config.get('private_messages', {}).get('enabled', False):
                
                # Solo respuestas automáticas muy básicas
                auto_response = None
                
                if any(word in message_text.lower() for word in ['hola', 'hello', 'hi']):
                    auto_response = "¡Hola! Gracias por contactarnos. Te responderemos pronto 😊"
                elif any(word in message_text.lower() for word in ['gracias', 'thanks']):
                    auto_response = "¡De nada! Estamos aquí para ayudarte 😊"
                
                if auto_response:
                    result = await client.send_message(sender_id, auto_response)
                    if result.get('success'):
                        logger.info(f"Respuesta automática a mensaje privado enviada en {platform}")
            
        except Exception as e:
            logger.error(f"Error procesando mensaje privado: {e}")
    
    async def _update_interaction_metrics(self, platform: str, client: BasePlatform):
        """Actualiza métricas de interacción"""
        try:
            # Obtener analytics generales
            analytics = await client.get_analytics()
            
            if analytics:
                # Guardar métricas en base de datos
                await self._save_analytics_record(platform, analytics)
                
        except Exception as e:
            logger.error(f"Error actualizando métricas de {platform}: {e}")
    
    # Métodos de base de datos (simplificados)
    
    async def _is_comment_processed(self, comment_id: str) -> bool:
        """Verifica si un comentario ya fue procesado"""
        try:
            return await self.db_manager.is_comment_processed(comment_id)
        except:
            return False
    
    async def _mark_comment_processed(self, comment_id: str):
        """Marca un comentario como procesado"""
        try:
            await self.db_manager.mark_comment_processed(comment_id)
        except Exception as e:
            logger.error(f"Error marcando comentario como procesado: {e}")
    
    async def _save_comment_record(self, platform: str, post_id: str, 
                                 comment: Dict[str, Any], analysis: Dict[str, Any]):
        """Guarda registro del comentario"""
        try:
            record = {
                'platform': platform,
                'post_id': post_id,
                'comment_id': comment.get('id'),
                'author': comment.get('author'),
                'content': comment.get('content'),
                'sentiment': analysis.get('sentiment'),
                'is_question': analysis.get('is_question'),
                'is_urgent': analysis.get('is_urgent'),
                'processed_at': datetime.now(),
                'raw_data': comment
            }
            
            await self.db_manager.save_comment_record(record)
            
        except Exception as e:
            logger.error(f"Error guardando registro de comentario: {e}")
    
    async def _save_reply_record(self, platform: str, comment_id: str, 
                               reply_text: str, result: Dict[str, Any]):
        """Guarda registro de respuesta enviada"""
        try:
            record = {
                'platform': platform,
                'comment_id': comment_id,
                'reply_text': reply_text,
                'reply_id': result.get('reply_id'),
                'sent_at': datetime.now(),
                'success': result.get('success', False)
            }
            
            await self.db_manager.save_reply_record(record)
            
        except Exception as e:
            logger.error(f"Error guardando registro de respuesta: {e}")
    
    async def _save_message_record(self, platform: str, message: Dict[str, Any]):
        """Guarda registro de mensaje privado"""
        try:
            record = {
                'platform': platform,
                'message_id': message.get('id'),
                'sender_id': message.get('sender_id'),
                'content': message.get('content'),
                'received_at': datetime.now(),
                'raw_data': message
            }
            
            await self.db_manager.save_message_record(record)
            
        except Exception as e:
            logger.error(f"Error guardando registro de mensaje: {e}")
    
    async def _save_analytics_record(self, platform: str, analytics: Dict[str, Any]):
        """Guarda registro de analytics"""
        try:
            record = {
                'platform': platform,
                'metrics': analytics.get('metrics', {}),
                'recorded_at': datetime.now(),
                'raw_data': analytics
            }
            
            await self.db_manager.save_analytics_record(record)
            
        except Exception as e:
            logger.error(f"Error guardando registro de analytics: {e}")
    
    async def get_interaction_summary(self, days: int = 7) -> Dict[str, Any]:
        """Obtiene resumen de interacciones"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            summary = {
                'period_days': days,
                'total_comments_processed': 0,
                'auto_replies_sent': 0,
                'messages_received': 0,
                'sentiment_breakdown': {
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0
                },
                'platforms': {}
            }
            
            # Obtener estadísticas de la base de datos
            stats = await self.db_manager.get_interaction_stats(cutoff_date)
            
            summary.update(stats)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generando resumen de interacciones: {e}")
            return {}