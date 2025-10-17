"""
Gestor de base de datos
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

# SQLAlchemy imports
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

Base = declarative_base()


class ContentModel(Base):
    """Modelo para contenido"""
    __tablename__ = 'content'
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    media_paths = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)
    status = Column(String, default='active')


class ScheduledPostModel(Base):
    """Modelo para publicaciones programadas"""
    __tablename__ = 'scheduled_posts'
    
    id = Column(String, primary_key=True)
    content_id = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(String, default='scheduled')  # scheduled, published, failed
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.now)
    published_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    result = Column(JSON, nullable=True)
    last_error = Column(Text, nullable=True)


class CommentModel(Base):
    """Modelo para comentarios procesados"""
    __tablename__ = 'comments'
    
    id = Column(String, primary_key=True)
    platform = Column(String, nullable=False)
    post_id = Column(String, nullable=False)
    comment_id = Column(String, nullable=False, unique=True)
    author = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    sentiment = Column(String, nullable=True)
    is_question = Column(Boolean, default=False)
    is_urgent = Column(Boolean, default=False)
    processed_at = Column(DateTime, default=datetime.now)
    raw_data = Column(JSON, nullable=True)


class ReplyModel(Base):
    """Modelo para respuestas enviadas"""
    __tablename__ = 'replies'
    
    id = Column(String, primary_key=True)
    platform = Column(String, nullable=False)
    comment_id = Column(String, nullable=False)
    reply_text = Column(Text, nullable=False)
    reply_id = Column(String, nullable=True)
    sent_at = Column(DateTime, default=datetime.now)
    success = Column(Boolean, default=False)


class MessageModel(Base):
    """Modelo para mensajes privados"""
    __tablename__ = 'messages'
    
    id = Column(String, primary_key=True)
    platform = Column(String, nullable=False)
    message_id = Column(String, nullable=False, unique=True)
    sender_id = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    received_at = Column(DateTime, default=datetime.now)
    raw_data = Column(JSON, nullable=True)


class AnalyticsModel(Base):
    """Modelo para métricas y analytics"""
    __tablename__ = 'analytics'
    
    id = Column(String, primary_key=True)
    platform = Column(String, nullable=False)
    post_id = Column(String, nullable=True)
    metrics = Column(JSON, nullable=False)
    recorded_at = Column(DateTime, default=datetime.now)
    raw_data = Column(JSON, nullable=True)


class DatabaseManager:
    """Gestor de base de datos"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.database_url = config.get('database', {}).get('url', 'sqlite:///data/fanpage_automation.db')
        
        # Configurar engine
        if self.database_url.startswith('sqlite'):
            # SQLite síncrono
            self.engine = create_engine(self.database_url, echo=False)
            self.SessionLocal = sessionmaker(bind=self.engine)
            self.async_mode = False
        else:
            # PostgreSQL u otra DB asíncrona
            async_url = self.database_url.replace('postgresql://', 'postgresql+asyncpg://')
            self.async_engine = create_async_engine(async_url, echo=False)
            self.AsyncSessionLocal = async_sessionmaker(self.async_engine)
            self.async_mode = True
        
        # Crear tablas
        self._create_tables()
    
    def _create_tables(self):
        """Crea las tablas de la base de datos"""
        try:
            if not self.async_mode:
                Base.metadata.create_all(bind=self.engine)
            else:
                # Para bases de datos asíncronas, crear tablas de forma síncrona inicialmente
                sync_engine = create_engine(
                    self.database_url.replace('postgresql+asyncpg://', 'postgresql://'),
                    echo=False
                )
                Base.metadata.create_all(bind=sync_engine)
            
            logger.info("Tablas de base de datos creadas/verificadas")
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
    
    def _get_session(self):
        """Obtiene sesión de base de datos"""
        if self.async_mode:
            return self.AsyncSessionLocal()
        else:
            return self.SessionLocal()
    
    async def save_content(self, content_data: Dict[str, Any]):
        """Guarda contenido en la base de datos"""
        try:
            if self.async_mode:
                async with self._get_session() as session:
                    content = ContentModel(**content_data)
                    session.add(content)
                    await session.commit()
            else:
                with self._get_session() as session:
                    content = ContentModel(**content_data)
                    session.add(content)
                    session.commit()
            
            logger.debug(f"Contenido guardado: {content_data.get('id')}")
        except Exception as e:
            logger.error(f"Error guardando contenido: {e}")
            raise
    
    async def get_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene contenido por ID"""
        try:
            if self.async_mode:
                async with self._get_session() as session:
                    content = await session.get(ContentModel, content_id)
            else:
                with self._get_session() as session:
                    content = session.get(ContentModel, content_id)
            
            if content:
                return {
                    'id': content.id,
                    'title': content.title,
                    'content': content.content,
                    'media_paths': content.media_paths or [],
                    'tags': content.tags or [],
                    'created_at': content.created_at,
                    'updated_at': content.updated_at,
                    'status': content.status
                }
            return None
        except Exception as e:
            logger.error(f"Error obteniendo contenido {content_id}: {e}")
            return None
    
    async def list_content(self, limit: int = 50, status: str = 'active') -> List[Dict[str, Any]]:
        """Lista contenido"""
        try:
            if self.async_mode:
                async with self._get_session() as session:
                    result = await session.execute(
                        ContentModel.query.filter_by(status=status).limit(limit)
                    )
                    contents = result.scalars().all()
            else:
                with self._get_session() as session:
                    contents = session.query(ContentModel).filter_by(status=status).limit(limit).all()
            
            return [
                {
                    'id': content.id,
                    'title': content.title,
                    'content': content.content,
                    'created_at': content.created_at,
                    'status': content.status
                }
                for content in contents
            ]
        except Exception as e:
            logger.error(f"Error listando contenido: {e}")
            return []
    
    async def update_content(self, content_id: str, updates: Dict[str, Any]) -> bool:
        """Actualiza contenido"""
        try:
            if self.async_mode:
                async with self._get_session() as session:
                    content = await session.get(ContentModel, content_id)
                    if content:
                        for key, value in updates.items():
                            setattr(content, key, value)
                        await session.commit()
                        return True
            else:
                with self._get_session() as session:
                    content = session.get(ContentModel, content_id)
                    if content:
                        for key, value in updates.items():
                            setattr(content, key, value)
                        session.commit()
                        return True
            return False
        except Exception as e:
            logger.error(f"Error actualizando contenido {content_id}: {e}")
            return False
    
    async def save_scheduled_post(self, post_data: Dict[str, Any]):
        """Guarda publicación programada"""
        try:
            if self.async_mode:
                async with self._get_session() as session:
                    post = ScheduledPostModel(**post_data)
                    session.add(post)
                    await session.commit()
            else:
                with self._get_session() as session:
                    post = ScheduledPostModel(**post_data)
                    session.add(post)
                    session.commit()
            
            logger.debug(f"Publicación programada guardada: {post_data.get('id')}")
        except Exception as e:
            logger.error(f"Error guardando publicación programada: {e}")
            raise
    
    async def get_scheduled_posts(self, platform: Optional[str] = None, 
                                 status: str = 'scheduled') -> List[Dict[str, Any]]:
        """Obtiene publicaciones programadas"""
        try:
            if self.async_mode:
                async with self._get_session() as session:
                    query = session.query(ScheduledPostModel).filter_by(status=status)
                    if platform:
                        query = query.filter_by(platform=platform)
                    posts = await query.all()
            else:
                with self._get_session() as session:
                    query = session.query(ScheduledPostModel).filter_by(status=status)
                    if platform:
                        query = query.filter_by(platform=platform)
                    posts = query.all()
            
            return [
                {
                    'id': post.id,
                    'content_id': post.content_id,
                    'platform': post.platform,
                    'scheduled_time': post.scheduled_time,
                    'status': post.status,
                    'config': post.config or {},
                    'attempts': post.attempts,
                    'max_attempts': post.max_attempts
                }
                for post in posts
            ]
        except Exception as e:
            logger.error(f"Error obteniendo publicaciones programadas: {e}")
            return []
    
    async def get_due_posts(self, current_time: datetime) -> List[Dict[str, Any]]:
        """Obtiene publicaciones que deben ejecutarse"""
        try:
            if self.async_mode:
                async with self._get_session() as session:
                    posts = await session.query(ScheduledPostModel).filter(
                        ScheduledPostModel.status == 'scheduled',
                        ScheduledPostModel.scheduled_time <= current_time
                    ).all()
            else:
                with self._get_session() as session:
                    posts = session.query(ScheduledPostModel).filter(
                        ScheduledPostModel.status == 'scheduled',
                        ScheduledPostModel.scheduled_time <= current_time
                    ).all()
            
            return [
                {
                    'id': post.id,
                    'content_id': post.content_id,
                    'platform': post.platform,
                    'scheduled_time': post.scheduled_time,
                    'config': post.config or {},
                    'attempts': post.attempts,
                    'max_attempts': post.max_attempts
                }
                for post in posts
            ]
        except Exception as e:
            logger.error(f"Error obteniendo posts para ejecutar: {e}")
            return []
    
    async def update_scheduled_post(self, post_id: str, updates: Dict[str, Any]) -> bool:
        """Actualiza publicación programada"""
        try:
            if self.async_mode:
                async with self._get_session() as session:
                    post = await session.get(ScheduledPostModel, post_id)
                    if post:
                        for key, value in updates.items():
                            setattr(post, key, value)
                        await session.commit()
                        return True
            else:
                with self._get_session() as session:
                    post = session.get(ScheduledPostModel, post_id)
                    if post:
                        for key, value in updates.items():
                            setattr(post, key, value)
                        session.commit()
                        return True
            return False
        except Exception as e:
            logger.error(f"Error actualizando publicación programada {post_id}: {e}")
            return False
    
    async def get_scheduled_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una publicación programada específica"""
        try:
            if self.async_mode:
                async with self._get_session() as session:
                    post = await session.get(ScheduledPostModel, post_id)
            else:
                with self._get_session() as session:
                    post = session.get(ScheduledPostModel, post_id)
            
            if post:
                return {
                    'id': post.id,
                    'content_id': post.content_id,
                    'platform': post.platform,
                    'scheduled_time': post.scheduled_time,
                    'status': post.status,
                    'config': post.config or {},
                    'attempts': post.attempts,
                    'max_attempts': post.max_attempts,
                    'result': post.result,
                    'last_error': post.last_error
                }
            return None
        except Exception as e:
            logger.error(f"Error obteniendo publicación programada {post_id}: {e}")
            return None
    
    # Métodos para interacciones
    
    async def is_comment_processed(self, comment_id: str) -> bool:
        """Verifica si un comentario ya fue procesado"""
        try:
            if self.async_mode:
                async with self._get_session() as session:
                    comment = await session.query(CommentModel).filter_by(comment_id=comment_id).first()
            else:
                with self._get_session() as session:
                    comment = session.query(CommentModel).filter_by(comment_id=comment_id).first()
            
            return comment is not None
        except Exception as e:
            logger.error(f"Error verificando comentario procesado: {e}")
            return False
    
    async def mark_comment_processed(self, comment_id: str):
        """Marca un comentario como procesado"""
        # Este método se llama después de save_comment_record, 
        # por lo que el comentario ya debería estar en la base de datos
        pass
    
    async def save_comment_record(self, record: Dict[str, Any]):
        """Guarda registro de comentario"""
        try:
            # Generar ID único
            import hashlib
            record_id = hashlib.md5(f"{record['comment_id']}{record['platform']}".encode()).hexdigest()
            record['id'] = record_id
            
            if self.async_mode:
                async with self._get_session() as session:
                    comment = CommentModel(**record)
                    session.add(comment)
                    await session.commit()
            else:
                with self._get_session() as session:
                    comment = CommentModel(**record)
                    session.add(comment)
                    session.commit()
        except Exception as e:
            logger.error(f"Error guardando registro de comentario: {e}")
    
    async def save_reply_record(self, record: Dict[str, Any]):
        """Guarda registro de respuesta"""
        try:
            import hashlib
            record_id = hashlib.md5(f"{record['comment_id']}{record['platform']}{datetime.now().isoformat()}".encode()).hexdigest()
            record['id'] = record_id
            
            if self.async_mode:
                async with self._get_session() as session:
                    reply = ReplyModel(**record)
                    session.add(reply)
                    await session.commit()
            else:
                with self._get_session() as session:
                    reply = ReplyModel(**record)
                    session.add(reply)
                    session.commit()
        except Exception as e:
            logger.error(f"Error guardando registro de respuesta: {e}")
    
    async def save_message_record(self, record: Dict[str, Any]):
        """Guarda registro de mensaje"""
        try:
            import hashlib
            record_id = hashlib.md5(f"{record['message_id']}{record['platform']}".encode()).hexdigest()
            record['id'] = record_id
            
            if self.async_mode:
                async with self._get_session() as session:
                    message = MessageModel(**record)
                    session.add(message)
                    await session.commit()
            else:
                with self._get_session() as session:
                    message = MessageModel(**record)
                    session.add(message)
                    session.commit()
        except Exception as e:
            logger.error(f"Error guardando registro de mensaje: {e}")
    
    async def save_analytics_record(self, record: Dict[str, Any]):
        """Guarda registro de analytics"""
        try:
            import hashlib
            record_id = hashlib.md5(f"{record['platform']}{datetime.now().isoformat()}".encode()).hexdigest()
            record['id'] = record_id
            
            if self.async_mode:
                async with self._get_session() as session:
                    analytics = AnalyticsModel(**record)
                    session.add(analytics)
                    await session.commit()
            else:
                with self._get_session() as session:
                    analytics = AnalyticsModel(**record)
                    session.add(analytics)
                    session.commit()
        except Exception as e:
            logger.error(f"Error guardando registro de analytics: {e}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas generales"""
        try:
            stats = {
                'total_posts': 0,
                'scheduled_posts': 0,
                'published_posts': 0,
                'failed_posts': 0,
                'total_content': 0,
                'interactions': 0
            }
            
            if self.async_mode:
                async with self._get_session() as session:
                    # Contar posts
                    total_posts = await session.query(ScheduledPostModel).count()
                    scheduled_posts = await session.query(ScheduledPostModel).filter_by(status='scheduled').count()
                    published_posts = await session.query(ScheduledPostModel).filter_by(status='published').count()
                    failed_posts = await session.query(ScheduledPostModel).filter_by(status='failed').count()
                    
                    # Contar contenido
                    total_content = await session.query(ContentModel).filter_by(status='active').count()
                    
                    # Contar interacciones
                    interactions = await session.query(CommentModel).count()
            else:
                with self._get_session() as session:
                    total_posts = session.query(ScheduledPostModel).count()
                    scheduled_posts = session.query(ScheduledPostModel).filter_by(status='scheduled').count()
                    published_posts = session.query(ScheduledPostModel).filter_by(status='published').count()
                    failed_posts = session.query(ScheduledPostModel).filter_by(status='failed').count()
                    
                    total_content = session.query(ContentModel).filter_by(status='active').count()
                    interactions = session.query(CommentModel).count()
            
            stats.update({
                'total_posts': total_posts,
                'scheduled_posts': scheduled_posts,
                'published_posts': published_posts,
                'failed_posts': failed_posts,
                'total_content': total_content,
                'interactions': interactions
            })
            
            return stats
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
    
    async def get_interaction_stats(self, cutoff_date: datetime) -> Dict[str, Any]:
        """Obtiene estadísticas de interacciones"""
        try:
            stats = {
                'total_comments_processed': 0,
                'auto_replies_sent': 0,
                'messages_received': 0,
                'sentiment_breakdown': {
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0
                }
            }
            
            if self.async_mode:
                async with self._get_session() as session:
                    comments = await session.query(CommentModel).filter(
                        CommentModel.processed_at >= cutoff_date
                    ).all()
                    
                    replies = await session.query(ReplyModel).filter(
                        ReplyModel.sent_at >= cutoff_date,
                        ReplyModel.success == True
                    ).count()
                    
                    messages = await session.query(MessageModel).filter(
                        MessageModel.received_at >= cutoff_date
                    ).count()
            else:
                with self._get_session() as session:
                    comments = session.query(CommentModel).filter(
                        CommentModel.processed_at >= cutoff_date
                    ).all()
                    
                    replies = session.query(ReplyModel).filter(
                        ReplyModel.sent_at >= cutoff_date,
                        ReplyModel.success == True
                    ).count()
                    
                    messages = session.query(MessageModel).filter(
                        MessageModel.received_at >= cutoff_date
                    ).count()
            
            # Procesar comentarios para análisis de sentimiento
            sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
            for comment in comments:
                sentiment = comment.sentiment or 'neutral'
                sentiment_counts[sentiment] += 1
            
            stats.update({
                'total_comments_processed': len(comments),
                'auto_replies_sent': replies,
                'messages_received': messages,
                'sentiment_breakdown': sentiment_counts
            })
            
            return stats
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de interacciones: {e}")
            return {}
    
    def close(self):
        """Cierra conexiones de base de datos"""
        try:
            if hasattr(self, 'engine'):
                self.engine.dispose()
            if hasattr(self, 'async_engine'):
                # Para async engines, usar asyncio para cerrar
                import asyncio
                asyncio.create_task(self.async_engine.dispose())
            
            logger.info("Conexiones de base de datos cerradas")
        except Exception as e:
            logger.error(f"Error cerrando base de datos: {e}")