"""
Cliente para Facebook
"""

import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.platforms.base_platform import BasePlatform
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class FacebookClient(BasePlatform):
    """Cliente para la API de Facebook"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.app_id = config.get('app_id')
        self.app_secret = config.get('app_secret')
        self.access_token = config.get('access_token')
        self.page_id = config.get('page_id')
        
        self.base_url = "https://graph.facebook.com/v18.0"
        self.session = None
        
        if not all([self.app_id, self.app_secret, self.access_token]):
            logger.warning("Configuración incompleta para Facebook")
    
    async def authenticate(self) -> bool:
        """Autentica con Facebook"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Verificar el token de acceso
            url = f"{self.base_url}/me"
            params = {
                'access_token': self.access_token,
                'fields': 'id,name'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Autenticado en Facebook como: {data.get('name')}")
                    return True
                else:
                    error_data = await response.json()
                    logger.error(f"Error de autenticación Facebook: {error_data}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error conectando con Facebook: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Prueba la conexión con Facebook"""
        return await self.authenticate()
    
    async def create_post(self, content: str, media_paths: Optional[List[str]] = None, 
                         **kwargs) -> Dict[str, Any]:
        """Crea una publicación en Facebook"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Preparar contenido
            prepared_content = self.prepare_content(content, max_length=63206)
            
            # Determinar endpoint según si hay página específica
            endpoint = f"{self.page_id}/feed" if self.page_id else "me/feed"
            url = f"{self.base_url}/{endpoint}"
            
            # Datos básicos del post
            post_data = {
                'message': prepared_content,
                'access_token': self.access_token
            }
            
            # Agregar configuraciones adicionales
            if kwargs.get('link'):
                post_data['link'] = kwargs['link']
            
            if kwargs.get('published'):
                post_data['published'] = kwargs['published']
            
            # Si hay archivos multimedia
            if media_paths:
                return await self._create_post_with_media(url, post_data, media_paths)
            else:
                return await self._create_simple_post(url, post_data)
                
        except Exception as e:
            logger.error(f"Error creando post en Facebook: {e}")
            raise
    
    async def _create_simple_post(self, url: str, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea un post de solo texto"""
        async with self.session.post(url, data=post_data) as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"Post creado en Facebook: {result.get('id')}")
                return {
                    'success': True,
                    'platform': 'facebook',
                    'post_id': result.get('id'),
                    'created_at': datetime.now().isoformat()
                }
            else:
                error_data = await response.json()
                logger.error(f"Error creando post Facebook: {error_data}")
                raise Exception(f"Error Facebook: {error_data}")
    
    async def _create_post_with_media(self, url: str, post_data: Dict[str, Any], 
                                    media_paths: List[str]) -> Dict[str, Any]:
        """Crea un post con archivos multimedia"""
        # Para múltiples imágenes, usar batch upload
        if len(media_paths) > 1:
            return await self._create_album_post(post_data, media_paths)
        
        # Para una sola imagen
        media_path = media_paths[0]
        
        if not self.validate_media_file(media_path):
            raise ValueError(f"Archivo multimedia inválido: {media_path}")
        
        # Subir foto
        photo_url = f"{self.base_url}/{self.page_id or 'me'}/photos"
        
        with open(media_path, 'rb') as media_file:
            form_data = aiohttp.FormData()
            form_data.add_field('message', post_data['message'])
            form_data.add_field('access_token', post_data['access_token'])
            form_data.add_field('source', media_file, filename=media_path.split('/')[-1])
            
            async with self.session.post(photo_url, data=form_data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Post con media creado en Facebook: {result.get('id')}")
                    return {
                        'success': True,
                        'platform': 'facebook',
                        'post_id': result.get('id'),
                        'created_at': datetime.now().isoformat()
                    }
                else:
                    error_data = await response.json()
                    raise Exception(f"Error subiendo media a Facebook: {error_data}")
    
    async def _create_album_post(self, post_data: Dict[str, Any], 
                               media_paths: List[str]) -> Dict[str, Any]:
        """Crea un post con múltiples imágenes (álbum)"""
        # Implementación simplificada - Facebook requiere un proceso más complejo para álbumes
        logger.warning("Posts con múltiples imágenes requieren implementación completa de álbumes")
        
        # Por ahora, subir solo la primera imagen
        return await self._create_post_with_media(
            f"{self.base_url}/{self.page_id or 'me'}/feed", 
            post_data, 
            [media_paths[0]]
        )
    
    async def get_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtiene publicaciones recientes"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            endpoint = f"{self.page_id}/posts" if self.page_id else "me/posts"
            url = f"{self.base_url}/{endpoint}"
            
            params = {
                'access_token': self.access_token,
                'limit': limit,
                'fields': 'id,message,created_time,likes.summary(true),comments.summary(true),shares'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    posts = []
                    
                    for post_data in data.get('data', []):
                        posts.append(self.format_post_data(post_data))
                    
                    return posts
                else:
                    error_data = await response.json()
                    logger.error(f"Error obteniendo posts Facebook: {error_data}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error obteniendo posts de Facebook: {e}")
            return []
    
    async def delete_post(self, post_id: str) -> bool:
        """Elimina una publicación"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/{post_id}"
            params = {'access_token': self.access_token}
            
            async with self.session.delete(url, params=params) as response:
                if response.status == 200:
                    logger.info(f"Post eliminado de Facebook: {post_id}")
                    return True
                else:
                    error_data = await response.json()
                    logger.error(f"Error eliminando post Facebook: {error_data}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error eliminando post de Facebook: {e}")
            return False
    
    async def get_comments(self, post_id: str) -> List[Dict[str, Any]]:
        """Obtiene comentarios de una publicación"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/{post_id}/comments"
            params = {
                'access_token': self.access_token,
                'fields': 'id,message,from,created_time,like_count'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    comments = []
                    
                    for comment_data in data.get('data', []):
                        comments.append(self.format_comment_data(comment_data))
                    
                    return comments
                else:
                    error_data = await response.json()
                    logger.error(f"Error obteniendo comentarios Facebook: {error_data}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error obteniendo comentarios de Facebook: {e}")
            return []
    
    async def reply_to_comment(self, comment_id: str, reply_text: str) -> Dict[str, Any]:
        """Responde a un comentario"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/{comment_id}/comments"
            data = {
                'message': reply_text,
                'access_token': self.access_token
            }
            
            async with self.session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Respuesta enviada en Facebook: {result.get('id')}")
                    return {
                        'success': True,
                        'reply_id': result.get('id'),
                        'platform': 'facebook'
                    }
                else:
                    error_data = await response.json()
                    logger.error(f"Error respondiendo comentario Facebook: {error_data}")
                    return {'success': False, 'error': error_data}
                    
        except Exception as e:
            logger.error(f"Error respondiendo comentario Facebook: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_messages(self) -> List[Dict[str, Any]]:
        """Obtiene mensajes privados"""
        # Los mensajes privados requieren permisos especiales y configuración de webhook
        logger.warning("Los mensajes privados de Facebook requieren configuración adicional")
        return []
    
    async def send_message(self, recipient_id: str, message: str) -> Dict[str, Any]:
        """Envía un mensaje privado"""
        # Requiere Facebook Messenger API
        logger.warning("Envío de mensajes requiere Facebook Messenger API")
        return {'success': False, 'error': 'Messenger API no implementada'}
    
    async def get_analytics(self, post_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene métricas y analíticas"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            if post_id:
                # Métricas de un post específico
                url = f"{self.base_url}/{post_id}"
                params = {
                    'access_token': self.access_token,
                    'fields': 'insights.metric(post_impressions,post_engaged_users,post_clicks)'
                }
            else:
                # Métricas generales de la página
                endpoint = f"{self.page_id}/insights" if self.page_id else "me/insights"
                url = f"{self.base_url}/{endpoint}"
                params = {
                    'access_token': self.access_token,
                    'metric': 'page_fans,page_impressions,page_engaged_users'
                }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'platform': 'facebook',
                        'post_id': post_id,
                        'metrics': data,
                        'retrieved_at': datetime.now().isoformat()
                    }
                else:
                    error_data = await response.json()
                    logger.error(f"Error obteniendo analytics Facebook: {error_data}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error obteniendo analytics de Facebook: {e}")
            return {}
    
    async def close(self):
        """Cierra la sesión HTTP"""
        if self.session:
            await self.session.close()
            self.session = None