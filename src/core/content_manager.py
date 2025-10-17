"""
Gestor de contenido
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib

from src.utils.database import DatabaseManager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ContentManager:
    """Gestor de contenido y publicaciones"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_manager = DatabaseManager(config)
        self.media_path = Path(config.get('content', {}).get('media_upload_path', 'data/media/'))
        self.templates_path = Path(config.get('content', {}).get('templates_path', 'data/templates/'))
        
        # Crear directorios si no existen
        self.media_path.mkdir(parents=True, exist_ok=True)
        self.templates_path.mkdir(parents=True, exist_ok=True)
    
    async def add_content(self, content_data: Dict[str, Any]) -> str:
        """Agrega nuevo contenido"""
        content_id = self._generate_content_id(content_data)
        
        content_record = {
            'id': content_id,
            'title': content_data.get('title', ''),
            'content': content_data.get('content', ''),
            'media_paths': content_data.get('media_paths', []),
            'tags': content_data.get('tags', []),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'status': 'active'
        }
        
        await self.db_manager.save_content(content_record)
        logger.info(f"Contenido agregado: {content_id}")
        
        return content_id
    
    async def get_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene contenido por ID"""
        return await self.db_manager.get_content(content_id)
    
    async def list_content(self, limit: int = 50, status: str = 'active') -> List[Dict[str, Any]]:
        """Lista contenido disponible"""
        return await self.db_manager.list_content(limit=limit, status=status)
    
    async def update_content(self, content_id: str, updates: Dict[str, Any]) -> bool:
        """Actualiza contenido existente"""
        updates['updated_at'] = datetime.now()
        result = await self.db_manager.update_content(content_id, updates)
        
        if result:
            logger.info(f"Contenido actualizado: {content_id}")
        
        return result
    
    async def delete_content(self, content_id: str) -> bool:
        """Elimina contenido (soft delete)"""
        return await self.update_content(content_id, {'status': 'deleted'})
    
    async def schedule_post(self, content_id: str, platform: str, scheduled_time: datetime, 
                           post_config: Optional[Dict[str, Any]] = None) -> str:
        """Programa una publicación"""
        
        # Verificar que el contenido existe
        content = await self.get_content(content_id)
        if not content:
            raise ValueError(f"Contenido no encontrado: {content_id}")
        
        # Crear registro de publicación programada
        post_id = self._generate_post_id(content_id, platform, scheduled_time)
        
        post_record = {
            'id': post_id,
            'content_id': content_id,
            'platform': platform,
            'scheduled_time': scheduled_time,
            'status': 'scheduled',
            'config': post_config or {},
            'created_at': datetime.now(),
            'attempts': 0,
            'max_attempts': self.config.get('scheduler', {}).get('max_retries', 3)
        }
        
        await self.db_manager.save_scheduled_post(post_record)
        logger.info(f"Publicación programada: {post_id} para {scheduled_time}")
        
        return post_id
    
    async def get_scheduled_posts(self, platform: Optional[str] = None, 
                                  status: str = 'scheduled') -> List[Dict[str, Any]]:
        """Obtiene publicaciones programadas"""
        return await self.db_manager.get_scheduled_posts(platform=platform, status=status)
    
    async def get_due_posts(self, current_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Obtiene publicaciones que deben ejecutarse ahora"""
        if current_time is None:
            current_time = datetime.now()
        
        return await self.db_manager.get_due_posts(current_time)
    
    async def mark_post_published(self, post_id: str, result: Dict[str, Any]):
        """Marca una publicación como publicada"""
        updates = {
            'status': 'published',
            'published_at': datetime.now(),
            'result': result
        }
        
        await self.db_manager.update_scheduled_post(post_id, updates)
        logger.info(f"Publicación marcada como publicada: {post_id}")
    
    async def mark_post_failed(self, post_id: str, error: str):
        """Marca una publicación como fallida"""
        post = await self.db_manager.get_scheduled_post(post_id)
        if not post:
            return
        
        attempts = post.get('attempts', 0) + 1
        max_attempts = post.get('max_attempts', 3)
        
        updates = {
            'attempts': attempts,
            'last_error': error,
            'updated_at': datetime.now()
        }
        
        if attempts >= max_attempts:
            updates['status'] = 'failed'
            logger.error(f"Publicación falló permanentemente: {post_id}")
        else:
            # Reprogramar para más tarde
            retry_delay = self.config.get('scheduler', {}).get('retry_delay', 60)
            new_time = datetime.now() + timedelta(seconds=retry_delay * attempts)
            updates['scheduled_time'] = new_time
            logger.warning(f"Reprogramando publicación {post_id} para {new_time}")
        
        await self.db_manager.update_scheduled_post(post_id, updates)
    
    async def save_media(self, media_data: bytes, filename: str, 
                        content_type: str = 'image/jpeg') -> str:
        """Guarda archivo multimedia"""
        
        # Generar nombre de archivo único
        file_hash = hashlib.md5(media_data).hexdigest()[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = self._sanitize_filename(filename)
        
        new_filename = f"{timestamp}_{file_hash}_{safe_filename}"
        file_path = self.media_path / new_filename
        
        # Guardar archivo
        with open(file_path, 'wb') as f:
            f.write(media_data)
        
        logger.info(f"Media guardado: {file_path}")
        return str(file_path)
    
    async def get_media_path(self, filename: str) -> Optional[str]:
        """Obtiene la ruta completa de un archivo multimedia"""
        file_path = self.media_path / filename
        
        if file_path.exists():
            return str(file_path)
        return None
    
    async def create_content_template(self, template_name: str, 
                                     template_data: Dict[str, Any]) -> str:
        """Crea una plantilla de contenido"""
        
        template_file = self.templates_path / f"{template_name}.json"
        
        template_record = {
            'name': template_name,
            'content_template': template_data.get('content', ''),
            'variables': template_data.get('variables', []),
            'platforms': template_data.get('platforms', []),
            'created_at': datetime.now().isoformat(),
            'created_by': template_data.get('created_by', 'system')
        }
        
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template_record, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Plantilla creada: {template_name}")
        return str(template_file)
    
    async def load_content_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Carga una plantilla de contenido"""
        template_file = self.templates_path / f"{template_name}.json"
        
        if not template_file.exists():
            return None
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando plantilla {template_name}: {e}")
            return None
    
    async def generate_content_from_template(self, template_name: str, 
                                           variables: Dict[str, Any]) -> Dict[str, Any]:
        """Genera contenido a partir de una plantilla"""
        template = await self.load_content_template(template_name)
        
        if not template:
            raise ValueError(f"Plantilla no encontrada: {template_name}")
        
        content_template = template.get('content_template', '')
        
        # Reemplazar variables en la plantilla
        for var_name, var_value in variables.items():
            content_template = content_template.replace(f"{{{var_name}}}", str(var_value))
        
        return {
            'title': f"Contenido desde plantilla {template_name}",
            'content': content_template,
            'template_used': template_name,
            'variables_used': variables
        }
    
    def _generate_content_id(self, content_data: Dict[str, Any]) -> str:
        """Genera ID único para contenido"""
        content_text = content_data.get('content', '')
        timestamp = datetime.now().isoformat()
        
        hash_source = f"{content_text[:100]}{timestamp}"
        return f"content_{hashlib.md5(hash_source.encode()).hexdigest()[:12]}"
    
    def _generate_post_id(self, content_id: str, platform: str, scheduled_time: datetime) -> str:
        """Genera ID único para publicación programada"""
        hash_source = f"{content_id}{platform}{scheduled_time.isoformat()}"
        return f"post_{hashlib.md5(hash_source.encode()).hexdigest()[:12]}"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitiza nombre de archivo"""
        # Remover caracteres peligrosos
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
        return ''.join(c for c in filename if c in safe_chars)