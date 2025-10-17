"""
Programador de tareas
"""

import asyncio
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime, timedelta
import schedule
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SchedulerManager:
    """Gestor de programación de tareas"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scheduler = AsyncIOScheduler()
        self.running_tasks: Dict[str, Any] = {}
        self._is_running = False
    
    async def start(self):
        """Inicia el programador"""
        if not self._is_running:
            self.scheduler.start()
            self._is_running = True
            logger.info("Scheduler iniciado")
    
    def stop(self):
        """Detiene el programador"""
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
            logger.info("Scheduler detenido")
    
    async def schedule_post(self, post_data: Dict[str, Any]):
        """Programa una publicación específica"""
        post_id = post_data.get('id')
        scheduled_time = post_data.get('scheduled_time')
        
        if not post_id or not scheduled_time:
            logger.error("Datos insuficientes para programar publicación")
            return
        
        # Convertir a datetime si es string
        if isinstance(scheduled_time, str):
            scheduled_time = datetime.fromisoformat(scheduled_time)
        
        # Verificar que la fecha sea futura
        if scheduled_time <= datetime.now():
            logger.warning(f"Fecha de programación ya pasó para post {post_id}")
            return
        
        # Programar la tarea
        job = self.scheduler.add_job(
            self._execute_scheduled_post,
            trigger=DateTrigger(run_date=scheduled_time),
            args=[post_data],
            id=f"post_{post_id}",
            name=f"Publicación programada: {post_id}",
            replace_existing=True
        )
        
        self.running_tasks[post_id] = job
        logger.info(f"Post programado: {post_id} para {scheduled_time}")
    
    def add_recurring_task(self, func: Callable, interval: int, 
                          task_id: Optional[str] = None, **kwargs):
        """Agrega una tarea recurrente"""
        
        if task_id is None:
            task_id = f"recurring_{func.__name__}_{interval}"
        
        job = self.scheduler.add_job(
            func,
            trigger=IntervalTrigger(seconds=interval),
            id=task_id,
            name=f"Tarea recurrente: {func.__name__}",
            replace_existing=True,
            **kwargs
        )
        
        self.running_tasks[task_id] = job
        logger.info(f"Tarea recurrente agregada: {task_id} cada {interval}s")
    
    def add_cron_task(self, func: Callable, cron_expression: str, 
                     task_id: Optional[str] = None, **kwargs):
        """Agrega una tarea con expresión cron"""
        
        if task_id is None:
            task_id = f"cron_{func.__name__}"
        
        # Parsear expresión cron
        cron_parts = cron_expression.split()
        if len(cron_parts) != 5:
            logger.error(f"Expresión cron inválida: {cron_expression}")
            return
        
        minute, hour, day, month, day_of_week = cron_parts
        
        job = self.scheduler.add_job(
            func,
            trigger=CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            ),
            id=task_id,
            name=f"Tarea cron: {func.__name__}",
            replace_existing=True,
            **kwargs
        )
        
        self.running_tasks[task_id] = job
        logger.info(f"Tarea cron agregada: {task_id} - {cron_expression}")
    
    def remove_task(self, task_id: str):
        """Elimina una tarea programada"""
        try:
            self.scheduler.remove_job(task_id)
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            logger.info(f"Tarea eliminada: {task_id}")
        except Exception as e:
            logger.error(f"Error eliminando tarea {task_id}: {e}")
    
    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Obtiene lista de trabajos programados"""
        jobs = []
        
        for job in self.scheduler.get_jobs():
            job_info = {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger),
                'func_name': job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)
            }
            jobs.append(job_info)
        
        return jobs
    
    async def _execute_scheduled_post(self, post_data: Dict[str, Any]):
        """Ejecuta una publicación programada"""
        post_id = post_data.get('id')
        
        try:
            logger.info(f"Ejecutando publicación programada: {post_id}")
            
            # Importar aquí para evitar dependencia circular
            from src.core.automation_manager import AutomationManager
            from src.platforms.platform_factory import PlatformFactory
            from src.core.content_manager import ContentManager
            
            # Obtener el contenido
            content_manager = ContentManager(self.config)
            content = await content_manager.get_content(post_data.get('content_id'))
            
            if not content:
                raise ValueError(f"Contenido no encontrado para post {post_id}")
            
            # Obtener cliente de la plataforma
            platform_factory = PlatformFactory(self.config)
            platform = post_data.get('platform')
            client = platform_factory.get_client(platform)
            
            if not client:
                raise ValueError(f"Cliente no disponible para plataforma: {platform}")
            
            # Preparar datos para publicación
            post_content = content.get('content', '')
            media_paths = content.get('media_paths', [])
            post_config = post_data.get('config', {})
            
            # Publicar contenido
            result = await client.create_post(
                content=post_content,
                media_paths=media_paths,
                **post_config
            )
            
            # Marcar como publicado
            await content_manager.mark_post_published(post_id, result)
            
            logger.info(f"Publicación ejecutada exitosamente: {post_id}")
            
        except Exception as e:
            logger.error(f"Error ejecutando publicación {post_id}: {e}")
            
            # Marcar como fallida
            try:
                content_manager = ContentManager(self.config)
                await content_manager.mark_post_failed(post_id, str(e))
            except Exception as mark_error:
                logger.error(f"Error marcando publicación como fallida: {mark_error}")
        
        finally:
            # Limpiar tarea de la lista
            if post_id in self.running_tasks:
                del self.running_tasks[post_id]
    
    def schedule_daily_task(self, func: Callable, hour: int, minute: int = 0, 
                           task_id: Optional[str] = None):
        """Programa una tarea diaria"""
        cron_expression = f"{minute} {hour} * * *"
        self.add_cron_task(func, cron_expression, task_id)
    
    def schedule_weekly_task(self, func: Callable, day_of_week: int, 
                           hour: int, minute: int = 0, task_id: Optional[str] = None):
        """Programa una tarea semanal"""
        cron_expression = f"{minute} {hour} * * {day_of_week}"
        self.add_cron_task(func, cron_expression, task_id)
    
    async def reschedule_failed_posts(self):
        """Reprograma publicaciones fallidas que pueden reintentarse"""
        try:
            from src.core.content_manager import ContentManager
            
            content_manager = ContentManager(self.config)
            
            # Obtener posts que necesitan reintento
            retry_posts = await content_manager.get_scheduled_posts(status='scheduled')
            
            for post in retry_posts:
                scheduled_time = post.get('scheduled_time')
                if isinstance(scheduled_time, str):
                    scheduled_time = datetime.fromisoformat(scheduled_time)
                
                # Solo reprogramar si la fecha ya pasó y no se ha alcanzado el máximo de intentos
                if (scheduled_time <= datetime.now() and 
                    post.get('attempts', 0) < post.get('max_attempts', 3)):
                    
                    await self.schedule_post(post)
                    
        except Exception as e:
            logger.error(f"Error reprogramando posts fallidos: {e}")