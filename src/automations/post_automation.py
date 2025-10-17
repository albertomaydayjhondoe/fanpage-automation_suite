"""
Automatización de publicaciones
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from src.core.content_manager import ContentManager
from src.platforms.platform_factory import PlatformFactory
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PostAutomation:
    """Automatización para publicaciones programadas"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.content_manager = ContentManager(config)
        self.platform_factory = PlatformFactory(config)
    
    async def process_scheduled_posts(self):
        """Procesa todas las publicaciones programadas que están listas"""
        try:
            # Obtener posts que deben ejecutarse
            due_posts = await self.content_manager.get_due_posts()
            
            if not due_posts:
                logger.debug("No hay publicaciones programadas para ejecutar")
                return
            
            logger.info(f"Procesando {len(due_posts)} publicaciones programadas")
            
            # Procesar cada post
            for post in due_posts:
                await self._process_single_post(post)
                
                # Pausa entre publicaciones para evitar rate limits
                await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"Error procesando publicaciones programadas: {e}")
    
    async def _process_single_post(self, post: Dict[str, Any]):
        """Procesa una publicación individual"""
        post_id = post.get('id')
        platform = post.get('platform')
        content_id = post.get('content_id')
        
        try:
            logger.info(f"Procesando publicación {post_id} para {platform}")
            
            # Obtener contenido
            content = await self.content_manager.get_content(content_id)
            if not content:
                raise Exception(f"Contenido no encontrado: {content_id}")
            
            # Obtener cliente de plataforma
            client = self.platform_factory.get_client(platform)
            if not client:
                raise Exception(f"Cliente no disponible para {platform}")
            
            # Preparar datos de publicación
            post_content = content.get('content', '')
            media_paths = content.get('media_paths', [])
            post_config = post.get('config', {})
            
            # Validar archivos multimedia
            valid_media_paths = []
            for media_path in media_paths:
                if client.validate_media_file(media_path):
                    valid_media_paths.append(media_path)
                else:
                    logger.warning(f"Archivo multimedia inválido: {media_path}")
            
            # Ejecutar publicación
            result = await client.create_post(
                content=post_content,
                media_paths=valid_media_paths if valid_media_paths else None,
                **post_config
            )
            
            # Marcar como publicado exitosamente
            await self.content_manager.mark_post_published(post_id, result)
            
            logger.info(f"✅ Publicación exitosa: {post_id} -> {result.get('post_id')}")
            
        except Exception as e:
            logger.error(f"❌ Error en publicación {post_id}: {e}")
            
            # Marcar como fallida para reintento
            await self.content_manager.mark_post_failed(post_id, str(e))
    
    async def create_automated_post_series(self, content_list: List[Dict[str, Any]], 
                                         platform: str, start_time: datetime, 
                                         interval_hours: int = 24) -> List[str]:
        """Crea una serie de publicaciones automatizadas"""
        post_ids = []
        current_time = start_time
        
        try:
            for i, content_data in enumerate(content_list):
                # Crear contenido
                content_id = await self.content_manager.add_content(content_data)
                
                # Programar publicación
                post_id = await self.content_manager.schedule_post(
                    content_id=content_id,
                    platform=platform,
                    scheduled_time=current_time
                )
                
                post_ids.append(post_id)
                
                # Incrementar tiempo para la siguiente publicación
                current_time += timedelta(hours=interval_hours)
                
                logger.info(f"Publicación programada {i+1}/{len(content_list)}: {post_id}")
            
            logger.info(f"Serie de {len(post_ids)} publicaciones creada para {platform}")
            return post_ids
            
        except Exception as e:
            logger.error(f"Error creando serie de publicaciones: {e}")
            raise
    
    async def duplicate_post_across_platforms(self, content_id: str, 
                                            platforms: List[str], 
                                            scheduled_time: datetime,
                                            platform_configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, str]:
        """Duplica un post a través de múltiples plataformas"""
        post_ids = {}
        
        try:
            # Verificar que el contenido existe
            content = await self.content_manager.get_content(content_id)
            if not content:
                raise Exception(f"Contenido no encontrado: {content_id}")
            
            for platform in platforms:
                try:
                    # Verificar que la plataforma está disponible
                    if not self.platform_factory.is_platform_available(platform):
                        logger.warning(f"Plataforma no disponible: {platform}")
                        continue
                    
                    # Obtener configuración específica de la plataforma
                    platform_config = {}
                    if platform_configs and platform in platform_configs:
                        platform_config = platform_configs[platform]
                    
                    # Programar publicación
                    post_id = await self.content_manager.schedule_post(
                        content_id=content_id,
                        platform=platform,
                        scheduled_time=scheduled_time,
                        post_config=platform_config
                    )
                    
                    post_ids[platform] = post_id
                    logger.info(f"Post programado para {platform}: {post_id}")
                    
                except Exception as e:
                    logger.error(f"Error programando post para {platform}: {e}")
                    post_ids[platform] = f"ERROR: {str(e)}"
            
            return post_ids
            
        except Exception as e:
            logger.error(f"Error duplicando post: {e}")
            raise
    
    async def reschedule_failed_posts(self, max_age_hours: int = 24):
        """Reprograma publicaciones fallidas recientes"""
        try:
            # Obtener posts fallidos recientes
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            # Esta funcionalidad requiere extender el DatabaseManager
            # para obtener posts fallidos en un rango de tiempo
            logger.info("Reprogramando publicaciones fallidas...")
            
            # Por ahora, log de placeholder
            logger.info("Función de reprogramación en desarrollo")
            
        except Exception as e:
            logger.error(f"Error reprogramando posts fallidos: {e}")
    
    async def get_post_analytics_summary(self, days: int = 7) -> Dict[str, Any]:
        """Obtiene resumen de analíticas de publicaciones recientes"""
        try:
            summary = {
                'total_published': 0,
                'total_failed': 0,
                'total_scheduled': 0,
                'platforms': {},
                'performance': {}
            }
            
            # Obtener estadísticas de publicaciones
            # Esta funcionalidad requiere implementación en DatabaseManager
            
            logger.info(f"Generando resumen de analíticas para {days} días")
            
            # Por ahora, retornar estructura básica
            return summary
            
        except Exception as e:
            logger.error(f"Error generando resumen de analíticas: {e}")
            return {}
    
    async def optimize_posting_times(self, platform: str) -> Dict[str, Any]:
        """Analiza y sugiere mejores horarios de publicación"""
        try:
            # Obtener cliente de plataforma
            client = self.platform_factory.get_client(platform)
            if not client:
                raise Exception(f"Plataforma no disponible: {platform}")
            
            # Obtener posts recientes con analytics
            recent_posts = await client.get_posts(limit=50)
            
            # Analizar performance por hora del día
            hourly_performance = {}
            
            for post in recent_posts:
                # Extraer hora de creación
                created_at = post.get('created_at', '')
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        hour = dt.hour
                        
                        if hour not in hourly_performance:
                            hourly_performance[hour] = {
                                'posts': 0,
                                'total_engagement': 0
                            }
                        
                        # Calcular engagement (likes + comments + shares)
                        engagement = (
                            post.get('likes', 0) + 
                            post.get('comments', 0) + 
                            post.get('shares', 0)
                        )
                        
                        hourly_performance[hour]['posts'] += 1
                        hourly_performance[hour]['total_engagement'] += engagement
                        
                    except Exception as e:
                        logger.warning(f"Error procesando fecha: {created_at}")
            
            # Calcular engagement promedio por hora
            recommendations = []
            for hour, data in hourly_performance.items():
                if data['posts'] > 0:
                    avg_engagement = data['total_engagement'] / data['posts']
                    recommendations.append({
                        'hour': hour,
                        'avg_engagement': avg_engagement,
                        'posts_count': data['posts']
                    })
            
            # Ordenar por engagement promedio
            recommendations.sort(key=lambda x: x['avg_engagement'], reverse=True)
            
            return {
                'platform': platform,
                'best_hours': recommendations[:5],  # Top 5 horas
                'analysis_period': '50 posts recientes',
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error optimizando horarios para {platform}: {e}")
            return {}