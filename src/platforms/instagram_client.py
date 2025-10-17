"""
Cliente para Instagram
"""

import asyncio
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from instagrapi import Client as InstagrapiClient
from instagrapi.exceptions import LoginRequired, ChallengeRequired

from src.platforms.base_platform import BasePlatform
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class InstagramClient(BasePlatform):
    """Cliente para Instagram usando instagrapi"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.username = config.get('username')
        self.password = config.get('password')
        self.session_file = config.get('session_file', f'data/instagram_session_{self.username}.json')
        
        self.client = InstagrapiClient()
        self.authenticated = False
        
        if not all([self.username, self.password]):
            logger.warning("Configuración incompleta para Instagram")
    
    async def authenticate(self) -> bool:
        """Autentica con Instagram"""
        try:
            # Intentar cargar sesión existente
            if os.path.exists(self.session_file):
                try:
                    self.client.load_settings(self.session_file)
                    self.client.login(self.username, self.password)
                    
                    # Verificar que la sesión funciona
                    user_info = self.client.user_info_by_username(self.username)
                    if user_info:
                        logger.info(f"Sesión de Instagram cargada para: {self.username}")
                        self.authenticated = True
                        return True
                except Exception as e:
                    logger.warning(f"Error cargando sesión Instagram: {e}")
                    # Eliminar archivo de sesión corrupto
                    os.remove(self.session_file)
            
            # Login nuevo
            self.client.login(self.username, self.password)
            
            # Guardar sesión
            os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
            self.client.dump_settings(self.session_file)
            
            logger.info(f"Autenticado en Instagram: {self.username}")
            self.authenticated = True
            return True
            
        except ChallengeRequired as e:
            logger.error(f"Verificación requerida para Instagram: {e}")
            return False
        except LoginRequired as e:
            logger.error(f"Login requerido para Instagram: {e}")
            return False
        except Exception as e:
            logger.error(f"Error autenticando con Instagram: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Prueba la conexión con Instagram"""
        if not self.authenticated:
            return await self.authenticate()
        
        try:
            # Verificar conexión obteniendo info del usuario
            user_info = self.client.user_info_by_username(self.username)
            return user_info is not None
        except Exception as e:
            logger.error(f"Error probando conexión Instagram: {e}")
            self.authenticated = False
            return False
    
    async def create_post(self, content: str, media_paths: Optional[List[str]] = None, 
                         **kwargs) -> Dict[str, Any]:
        """Crea una publicación en Instagram"""
        try:
            if not self.authenticated:
                auth_success = await self.authenticate()
                if not auth_success:
                    raise Exception("No se pudo autenticar con Instagram")
            
            # Preparar contenido
            prepared_content = self.prepare_content(content, max_length=2200)
            
            # Instagram requiere al menos una imagen
            if not media_paths:
                raise ValueError("Instagram requiere al menos una imagen para publicar")
            
            # Validar archivos
            valid_media = []
            for media_path in media_paths:
                if self.validate_media_file(media_path):
                    valid_media.append(media_path)
                else:
                    logger.warning(f"Archivo multimedia inválido ignorado: {media_path}")
            
            if not valid_media:
                raise ValueError("No hay archivos multimedia válidos")
            
            # Publicar según el número de archivos
            if len(valid_media) == 1:
                return await self._create_single_photo_post(valid_media[0], prepared_content, **kwargs)
            else:
                return await self._create_album_post(valid_media, prepared_content, **kwargs)
                
        except Exception as e:
            logger.error(f"Error creando post en Instagram: {e}")
            raise
    
    async def _create_single_photo_post(self, media_path: str, caption: str, **kwargs) -> Dict[str, Any]:
        """Crea un post con una sola imagen"""
        try:
            # Determinar tipo de archivo
            if media_path.lower().endswith(('.mp4', '.mov', '.avi')):
                # Video
                media = self.client.video_upload(media_path, caption)
            else:
                # Imagen
                media = self.client.photo_upload(media_path, caption)
            
            logger.info(f"Post creado en Instagram: {media.pk}")
            
            return {
                'success': True,
                'platform': 'instagram',
                'post_id': media.pk,
                'media_id': media.id,
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error subiendo media a Instagram: {e}")
            raise
    
    async def _create_album_post(self, media_paths: List[str], caption: str, **kwargs) -> Dict[str, Any]:
        """Crea un post con múltiples imágenes (álbum)"""
        try:
            # Instagram permite hasta 10 imágenes por álbum
            album_paths = media_paths[:10]
            
            media = self.client.album_upload(album_paths, caption)
            
            logger.info(f"Álbum creado en Instagram: {media.pk}")
            
            return {
                'success': True,
                'platform': 'instagram',
                'post_id': media.pk,
                'media_id': media.id,
                'album_size': len(album_paths),
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creando álbum en Instagram: {e}")
            raise
    
    async def get_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtiene publicaciones recientes"""
        try:
            if not self.authenticated:
                await self.authenticate()
            
            # Obtener info del usuario
            user_info = self.client.user_info_by_username(self.username)
            user_id = user_info.pk
            
            # Obtener medias del usuario
            medias = self.client.user_medias(user_id, amount=limit)
            
            posts = []
            for media in medias:
                post_data = {
                    'id': media.pk,
                    'caption': media.caption_text or '',
                    'created_time': media.taken_at.isoformat(),
                    'like_count': media.like_count,
                    'comment_count': media.comment_count,
                    'media_type': media.media_type,
                    'thumbnail_url': media.thumbnail_url
                }
                posts.append(self.format_post_data(post_data))
            
            return posts
            
        except Exception as e:
            logger.error(f"Error obteniendo posts de Instagram: {e}")
            return []
    
    async def delete_post(self, post_id: str) -> bool:
        """Elimina una publicación"""
        try:
            if not self.authenticated:
                await self.authenticate()
            
            result = self.client.media_delete(post_id)
            
            if result:
                logger.info(f"Post eliminado de Instagram: {post_id}")
                return True
            else:
                logger.error(f"No se pudo eliminar post de Instagram: {post_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error eliminando post de Instagram: {e}")
            return False
    
    async def get_comments(self, post_id: str) -> List[Dict[str, Any]]:
        """Obtiene comentarios de una publicación"""
        try:
            if not self.authenticated:
                await self.authenticate()
            
            comments = self.client.media_comments(post_id)
            
            formatted_comments = []
            for comment in comments:
                comment_data = {
                    'id': comment.pk,
                    'text': comment.text,
                    'user': comment.user.username,
                    'user_id': comment.user.pk,
                    'created_at': comment.created_at.isoformat(),
                    'like_count': comment.comment_like_count
                }
                formatted_comments.append(self.format_comment_data(comment_data))
            
            return formatted_comments
            
        except Exception as e:
            logger.error(f"Error obteniendo comentarios de Instagram: {e}")
            return []
    
    async def reply_to_comment(self, comment_id: str, reply_text: str) -> Dict[str, Any]:
        """Responde a un comentario"""
        try:
            if not self.authenticated:
                await self.authenticate()
            
            # Instagram no permite responder directamente a comentarios
            # En su lugar, se puede mencionar al usuario en un nuevo comentario
            
            # Obtener info del comentario original
            comment = self.client.comment_info(comment_id)
            username = comment.user.username
            
            # Crear respuesta mencionando al usuario
            reply_with_mention = f"@{username} {reply_text}"
            
            # Obtener el media_id del comentario
            media_id = comment.media_id
            
            # Crear nuevo comentario
            new_comment = self.client.media_comment(media_id, reply_with_mention)
            
            logger.info(f"Respuesta enviada en Instagram: {new_comment.pk}")
            
            return {
                'success': True,
                'reply_id': new_comment.pk,
                'platform': 'instagram'
            }
            
        except Exception as e:
            logger.error(f"Error respondiendo comentario Instagram: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_messages(self) -> List[Dict[str, Any]]:
        """Obtiene mensajes privados"""
        try:
            if not self.authenticated:
                await self.authenticate()
            
            # Obtener threads de mensajes directos
            threads = self.client.direct_threads()
            
            messages = []
            for thread in threads[:10]:  # Limitar a los 10 últimos threads
                thread_messages = self.client.direct_messages(thread.id, amount=5)
                
                for msg in thread_messages:
                    message_data = {
                        'id': msg.id,
                        'text': msg.text or '',
                        'sender': msg.user_id,
                        'sender_id': msg.user_id,
                        'created_at': msg.timestamp.isoformat(),
                        'thread_id': thread.id
                    }
                    messages.append(self.format_message_data(message_data))
            
            return messages
            
        except Exception as e:
            logger.error(f"Error obteniendo mensajes de Instagram: {e}")
            return []
    
    async def send_message(self, recipient_id: str, message: str) -> Dict[str, Any]:
        """Envía un mensaje privado"""
        try:
            if not self.authenticated:
                await self.authenticate()
            
            # Enviar mensaje directo
            result = self.client.direct_send(message, [recipient_id])
            
            if result:
                logger.info(f"Mensaje enviado en Instagram a: {recipient_id}")
                return {
                    'success': True,
                    'message_id': result[0].id if result else None,
                    'platform': 'instagram'
                }
            else:
                return {'success': False, 'error': 'No se pudo enviar el mensaje'}
                
        except Exception as e:
            logger.error(f"Error enviando mensaje Instagram: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_analytics(self, post_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene métricas y analíticas"""
        try:
            if not self.authenticated:
                await self.authenticate()
            
            if post_id:
                # Métricas de un post específico
                media_info = self.client.media_info(post_id)
                
                return {
                    'platform': 'instagram',
                    'post_id': post_id,
                    'metrics': {
                        'likes': media_info.like_count,
                        'comments': media_info.comment_count,
                        'views': getattr(media_info, 'view_count', 0)
                    },
                    'retrieved_at': datetime.now().isoformat()
                }
            else:
                # Métricas generales del perfil
                user_info = self.client.user_info_by_username(self.username)
                
                return {
                    'platform': 'instagram',
                    'metrics': {
                        'followers': user_info.follower_count,
                        'following': user_info.following_count,
                        'posts': user_info.media_count
                    },
                    'retrieved_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo analytics de Instagram: {e}")
            return {}
    
    def logout(self):
        """Cierra sesión"""
        try:
            self.client.logout()
            self.authenticated = False
            logger.info("Sesión cerrada en Instagram")
        except Exception as e:
            logger.error(f"Error cerrando sesión Instagram: {e}")