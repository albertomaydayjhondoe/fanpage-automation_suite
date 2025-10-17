"""
Clase base para todos los clientes de plataformas
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime


class BasePlatform(ABC):
    """Clase base abstracta para todas las plataformas de redes sociales"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.platform_name = self.__class__.__name__.replace('Client', '').lower()
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Autentica con la plataforma"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Prueba la conexión con la plataforma"""
        pass
    
    @abstractmethod
    async def create_post(self, content: str, media_paths: Optional[List[str]] = None, 
                         **kwargs) -> Dict[str, Any]:
        """Crea una nueva publicación"""
        pass
    
    @abstractmethod
    async def get_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtiene publicaciones recientes"""
        pass
    
    @abstractmethod
    async def delete_post(self, post_id: str) -> bool:
        """Elimina una publicación"""
        pass
    
    @abstractmethod
    async def get_comments(self, post_id: str) -> List[Dict[str, Any]]:
        """Obtiene comentarios de una publicación"""
        pass
    
    @abstractmethod
    async def reply_to_comment(self, comment_id: str, reply_text: str) -> Dict[str, Any]:
        """Responde a un comentario"""
        pass
    
    @abstractmethod
    async def get_messages(self) -> List[Dict[str, Any]]:
        """Obtiene mensajes privados"""
        pass
    
    @abstractmethod
    async def send_message(self, recipient_id: str, message: str) -> Dict[str, Any]:
        """Envía un mensaje privado"""
        pass
    
    @abstractmethod
    async def get_analytics(self, post_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene métricas y analíticas"""
        pass
    
    # Métodos comunes (no abstractos)
    
    def get_platform_name(self) -> str:
        """Retorna el nombre de la plataforma"""
        return self.platform_name
    
    def validate_media_file(self, media_path: str) -> bool:
        """Valida un archivo multimedia"""
        import os
        from pathlib import Path
        
        if not os.path.exists(media_path):
            return False
        
        file_path = Path(media_path)
        
        # Verificar extensión
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi'}
        if file_path.suffix.lower() not in allowed_extensions:
            return False
        
        # Verificar tamaño (50MB máximo por defecto)
        max_size = self.config.get('max_file_size', 52428800)  # 50MB
        if file_path.stat().st_size > max_size:
            return False
        
        return True
    
    def prepare_content(self, content: str, max_length: Optional[int] = None) -> str:
        """Prepara el contenido para la plataforma"""
        if max_length and len(content) > max_length:
            return content[:max_length-3] + "..."
        return content
    
    def format_post_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea datos de publicación a formato estándar"""
        return {
            'id': raw_data.get('id', ''),
            'content': raw_data.get('text', raw_data.get('message', '')),
            'created_at': raw_data.get('created_time', raw_data.get('created_at', '')),
            'likes': raw_data.get('likes', {}).get('summary', {}).get('total_count', 0),
            'comments': raw_data.get('comments', {}).get('summary', {}).get('total_count', 0),
            'shares': raw_data.get('shares', {}).get('count', 0),
            'platform': self.platform_name,
            'raw_data': raw_data
        }
    
    def format_comment_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea datos de comentario a formato estándar"""
        return {
            'id': raw_data.get('id', ''),
            'content': raw_data.get('message', raw_data.get('text', '')),
            'author': raw_data.get('from', {}).get('name', raw_data.get('user', '')),
            'author_id': raw_data.get('from', {}).get('id', raw_data.get('user_id', '')),
            'created_at': raw_data.get('created_time', raw_data.get('created_at', '')),
            'likes': raw_data.get('like_count', 0),
            'platform': self.platform_name,
            'raw_data': raw_data
        }
    
    def format_message_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea datos de mensaje a formato estándar"""
        return {
            'id': raw_data.get('id', ''),
            'content': raw_data.get('message', raw_data.get('text', '')),
            'sender': raw_data.get('from', {}).get('name', raw_data.get('sender', '')),
            'sender_id': raw_data.get('from', {}).get('id', raw_data.get('sender_id', '')),
            'created_at': raw_data.get('created_time', raw_data.get('created_at', '')),
            'is_read': raw_data.get('unread', 0) == 0,
            'platform': self.platform_name,
            'raw_data': raw_data
        }
    
    async def handle_rate_limit(self, retry_after: int = 60):
        """Maneja límites de velocidad de API"""
        import asyncio
        from src.utils.logger import setup_logger
        
        logger = setup_logger(f"{self.__class__.__name__}")
        logger.warning(f"Rate limit alcanzado, esperando {retry_after} segundos")
        await asyncio.sleep(retry_after)