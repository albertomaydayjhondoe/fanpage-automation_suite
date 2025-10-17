"""
Cliente para Twitter
"""

import asyncio
import aiohttp
import base64
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import urllib.parse

from src.platforms.base_platform import BasePlatform
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class TwitterClient(BasePlatform):
    """Cliente para la API de Twitter (X)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.access_token = config.get('access_token')
        self.access_token_secret = config.get('access_token_secret')
        self.bearer_token = config.get('bearer_token')
        
        self.base_url = "https://api.twitter.com/2"
        self.upload_url = "https://upload.twitter.com/1.1"
        self.session = None
        
        if not all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            logger.warning("Configuración incompleta para Twitter")
    
    async def authenticate(self) -> bool:
        """Autentica con Twitter"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Verificar credenciales obteniendo info del usuario
            url = f"{self.base_url}/users/me"
            headers = await self._get_oauth_headers("GET", url)
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    user_data = data.get('data', {})
                    logger.info(f"Autenticado en Twitter como: @{user_data.get('username')}")
                    return True
                else:
                    error_data = await response.json()
                    logger.error(f"Error de autenticación Twitter: {error_data}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error conectando con Twitter: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Prueba la conexión con Twitter"""
        return await self.authenticate()
    
    async def create_post(self, content: str, media_paths: Optional[List[str]] = None, 
                         **kwargs) -> Dict[str, Any]:
        """Crea un tweet"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Preparar contenido (280 caracteres máximo)
            prepared_content = self.prepare_content(content, max_length=280)
            
            # Datos del tweet
            tweet_data = {
                'text': prepared_content
            }
            
            # Subir medios si existen
            if media_paths:
                media_ids = await self._upload_media(media_paths)
                if media_ids:
                    tweet_data['media'] = {'media_ids': media_ids}
            
            # Configuraciones adicionales
            if kwargs.get('reply_to'):
                tweet_data['reply'] = {'in_reply_to_tweet_id': kwargs['reply_to']}
            
            # Crear tweet
            url = f"{self.base_url}/tweets"
            headers = await self._get_oauth_headers("POST", url, json.dumps(tweet_data))
            headers['Content-Type'] = 'application/json'
            
            async with self.session.post(url, headers=headers, json=tweet_data) as response:
                if response.status == 201:
                    result = await response.json()
                    tweet_id = result.get('data', {}).get('id')
                    logger.info(f"Tweet creado: {tweet_id}")
                    
                    return {
                        'success': True,
                        'platform': 'twitter',
                        'post_id': tweet_id,
                        'created_at': datetime.now().isoformat()
                    }
                else:
                    error_data = await response.json()
                    logger.error(f"Error creando tweet: {error_data}")
                    raise Exception(f"Error Twitter: {error_data}")
                    
        except Exception as e:
            logger.error(f"Error creando tweet: {e}")
            raise
    
    async def _upload_media(self, media_paths: List[str]) -> List[str]:
        """Sube archivos multimedia a Twitter"""
        media_ids = []
        
        for media_path in media_paths[:4]:  # Twitter permite hasta 4 imágenes
            if not self.validate_media_file(media_path):
                logger.warning(f"Archivo multimedia inválido: {media_path}")
                continue
            
            try:
                # Subir archivo
                url = f"{self.upload_url}/media/upload.json"
                
                with open(media_path, 'rb') as media_file:
                    files = {'media': media_file}
                    headers = await self._get_oauth_headers("POST", url)
                    
                    async with self.session.post(url, headers=headers, data=files) as response:
                        if response.status == 200:
                            result = await response.json()
                            media_ids.append(result['media_id_string'])
                            logger.info(f"Media subido: {result['media_id_string']}")
                        else:
                            error_data = await response.json()
                            logger.error(f"Error subiendo media: {error_data}")
                            
            except Exception as e:
                logger.error(f"Error subiendo archivo {media_path}: {e}")
        
        return media_ids
    
    async def get_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtiene tweets recientes del usuario"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Obtener ID del usuario primero
            user_url = f"{self.base_url}/users/me"
            user_headers = await self._get_oauth_headers("GET", user_url)
            
            async with self.session.get(user_url, headers=user_headers) as response:
                if response.status != 200:
                    logger.error("No se pudo obtener información del usuario")
                    return []
                
                user_data = await response.json()
                user_id = user_data.get('data', {}).get('id')
            
            # Obtener tweets del usuario
            tweets_url = f"{self.base_url}/users/{user_id}/tweets"
            params = {
                'max_results': min(limit, 100),
                'tweet.fields': 'created_at,public_metrics,attachments'
            }
            
            headers = await self._get_oauth_headers("GET", tweets_url)
            
            async with self.session.get(tweets_url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    tweets = []
                    
                    for tweet_data in data.get('data', []):
                        formatted_tweet = {
                            'id': tweet_data.get('id'),
                            'text': tweet_data.get('text', ''),
                            'created_time': tweet_data.get('created_at', ''),
                            'likes': tweet_data.get('public_metrics', {}).get('like_count', 0),
                            'comments': tweet_data.get('public_metrics', {}).get('reply_count', 0),
                            'shares': tweet_data.get('public_metrics', {}).get('retweet_count', 0)
                        }
                        tweets.append(self.format_post_data(formatted_tweet))
                    
                    return tweets
                else:
                    error_data = await response.json()
                    logger.error(f"Error obteniendo tweets: {error_data}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error obteniendo tweets: {e}")
            return []
    
    async def delete_post(self, post_id: str) -> bool:
        """Elimina un tweet"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}/tweets/{post_id}"
            headers = await self._get_oauth_headers("DELETE", url)
            
            async with self.session.delete(url, headers=headers) as response:
                if response.status == 200:
                    logger.info(f"Tweet eliminado: {post_id}")
                    return True
                else:
                    error_data = await response.json()
                    logger.error(f"Error eliminando tweet: {error_data}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error eliminando tweet: {e}")
            return False
    
    async def get_comments(self, post_id: str) -> List[Dict[str, Any]]:
        """Obtiene respuestas a un tweet"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Buscar respuestas al tweet
            url = f"{self.base_url}/tweets/search/recent"
            params = {
                'query': f'conversation_id:{post_id}',
                'tweet.fields': 'created_at,author_id,public_metrics',
                'max_results': 10
            }
            
            headers = await self._get_oauth_headers("GET", url)
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    replies = []
                    
                    for reply_data in data.get('data', []):
                        formatted_reply = {
                            'id': reply_data.get('id'),
                            'message': reply_data.get('text', ''),
                            'user_id': reply_data.get('author_id'),
                            'created_time': reply_data.get('created_at', ''),
                            'like_count': reply_data.get('public_metrics', {}).get('like_count', 0)
                        }
                        replies.append(self.format_comment_data(formatted_reply))
                    
                    return replies
                else:
                    error_data = await response.json()
                    logger.error(f"Error obteniendo respuestas: {error_data}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error obteniendo respuestas de Twitter: {e}")
            return []
    
    async def reply_to_comment(self, comment_id: str, reply_text: str) -> Dict[str, Any]:
        """Responde a un tweet"""
        try:
            # Crear respuesta usando create_post con reply_to
            return await self.create_post(reply_text, reply_to=comment_id)
            
        except Exception as e:
            logger.error(f"Error respondiendo en Twitter: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_messages(self) -> List[Dict[str, Any]]:
        """Obtiene mensajes directos"""
        # Los mensajes directos requieren permisos especiales en Twitter API v2
        logger.warning("Los mensajes directos requieren permisos especiales")
        return []
    
    async def send_message(self, recipient_id: str, message: str) -> Dict[str, Any]:
        """Envía un mensaje directo"""
        logger.warning("Envío de mensajes directos requiere permisos especiales")
        return {'success': False, 'error': 'Mensajes directos no implementados'}
    
    async def get_analytics(self, post_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene métricas y analíticas"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            if post_id:
                # Métricas de un tweet específico
                url = f"{self.base_url}/tweets/{post_id}"
                params = {'tweet.fields': 'public_metrics'}
                
                headers = await self._get_oauth_headers("GET", url)
                
                async with self.session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        metrics = data.get('data', {}).get('public_metrics', {})
                        
                        return {
                            'platform': 'twitter',
                            'post_id': post_id,
                            'metrics': metrics,
                            'retrieved_at': datetime.now().isoformat()
                        }
            else:
                # Métricas generales del usuario
                url = f"{self.base_url}/users/me"
                params = {'user.fields': 'public_metrics'}
                
                headers = await self._get_oauth_headers("GET", url)
                
                async with self.session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        metrics = data.get('data', {}).get('public_metrics', {})
                        
                        return {
                            'platform': 'twitter',
                            'metrics': metrics,
                            'retrieved_at': datetime.now().isoformat()
                        }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error obteniendo analytics de Twitter: {e}")
            return {}
    
    async def _get_oauth_headers(self, method: str, url: str, body: str = "") -> Dict[str, str]:
        """Genera headers OAuth 1.0a para autenticación"""
        import hmac
        import hashlib
        import time
        import secrets
        import urllib.parse
        
        # Parámetros OAuth
        oauth_params = {
            'oauth_consumer_key': self.api_key,
            'oauth_token': self.access_token,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': secrets.token_hex(16),
            'oauth_version': '1.0'
        }
        
        # Crear base string para la firma
        params_string = '&'.join([f"{k}={urllib.parse.quote(str(v), safe='')}" 
                                 for k, v in sorted(oauth_params.items())])
        
        base_url = url.split('?')[0]  # Remover query parameters
        base_string = f"{method}&{urllib.parse.quote(base_url, safe='')}&{urllib.parse.quote(params_string, safe='')}"
        
        # Crear signing key
        signing_key = f"{urllib.parse.quote(self.api_secret, safe='')}&{urllib.parse.quote(self.access_token_secret, safe='')}"
        
        # Generar firma
        signature = base64.b64encode(
            hmac.new(
                signing_key.encode(),
                base_string.encode(),
                hashlib.sha1
            ).digest()
        ).decode()
        
        oauth_params['oauth_signature'] = signature
        
        # Crear header Authorization
        auth_header = 'OAuth ' + ', '.join([f'{k}="{urllib.parse.quote(str(v), safe="")}"' 
                                           for k, v in sorted(oauth_params.items())])
        
        return {'Authorization': auth_header}
    
    async def close(self):
        """Cierra la sesión HTTP"""
        if self.session:
            await self.session.close()
            self.session = None