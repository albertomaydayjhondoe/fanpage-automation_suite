"""
Gestor principal de automatización
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.core.config_manager import ConfigManager
from src.core.content_manager import ContentManager
from src.core.scheduler import SchedulerManager
from src.platforms.platform_factory import PlatformFactory
from src.automations.post_automation import PostAutomation
from src.automations.interaction_automation import InteractionAutomation
from src.utils.logger import setup_logger
from src.utils.database import DatabaseManager

logger = setup_logger(__name__)


class AutomationManager:
    """Gestor principal de todas las automatizaciones"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.content_manager = ContentManager(config)
        self.scheduler = SchedulerManager(config)
        self.platform_factory = PlatformFactory(config)
        self.db_manager = DatabaseManager(config)
        
        # Automatizaciones disponibles
        self.automations = {
            'post': PostAutomation(config),
            'interaction': InteractionAutomation(config)
        }
        
        self._running = False
    
    async def start_scheduler(self, platform: str = "all"):
        """Inicia el programador de tareas"""
        logger.info(f"Iniciando scheduler para plataforma: {platform}")
        
        try:
            self._running = True
            
            # Configurar tareas programadas
            await self._setup_scheduled_tasks(platform)
            
            # Iniciar el scheduler
            await self.scheduler.start()
            
            # Mantener el bucle principal
            while self._running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error en scheduler: {e}")
            raise
    
    async def start_interactive_mode(self):
        """Inicia el modo interactivo"""
        logger.info("Iniciando modo interactivo")
        
        while True:
            print("\n=== Fanpage Automation Suite ===")
            print("1. Publicar contenido ahora")
            print("2. Ver publicaciones programadas")
            print("3. Gestionar contenido")
            print("4. Ver estadísticas")
            print("5. Configurar automatizaciones")
            print("0. Salir")
            
            choice = input("\nSeleccione una opción: ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                await self._interactive_post()
            elif choice == "2":
                await self._show_scheduled_posts()
            elif choice == "3":
                await self._manage_content()
            elif choice == "4":
                await self._show_statistics()
            elif choice == "5":
                await self._configure_automations()
            else:
                print("Opción no válida")
    
    async def start_api_server(self):
        """Inicia el servidor API"""
        from src.api.main import create_app
        import uvicorn
        
        app = create_app(self)
        
        logger.info("Iniciando servidor API")
        config = uvicorn.Config(
            app,
            host=self.config.get('api', {}).get('host', 'localhost'),
            port=self.config.get('api', {}).get('port', 8000),
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def _setup_scheduled_tasks(self, platform: str):
        """Configura las tareas programadas"""
        # Obtener publicaciones programadas
        scheduled_posts = await self.content_manager.get_scheduled_posts(platform)
        
        for post in scheduled_posts:
            await self.scheduler.schedule_post(post)
        
        # Configurar automatizaciones periódicas
        if platform in ["all", "facebook"]:
            self.scheduler.add_recurring_task(
                self._process_facebook_interactions,
                interval=300  # cada 5 minutos
            )
        
        if platform in ["all", "instagram"]:
            self.scheduler.add_recurring_task(
                self._process_instagram_interactions,
                interval=600  # cada 10 minutos
            )
    
    async def _interactive_post(self):
        """Maneja la publicación interactiva"""
        print("\n--- Publicar Contenido ---")
        
        # Mostrar plataformas disponibles
        platforms = list(self.platform_factory.get_available_platforms())
        print("Plataformas disponibles:")
        for i, platform in enumerate(platforms, 1):
            print(f"{i}. {platform.title()}")
        
        platform_choice = input("Seleccione plataforma: ").strip()
        try:
            platform = platforms[int(platform_choice) - 1]
        except (ValueError, IndexError):
            print("Selección inválida")
            return
        
        # Obtener contenido
        content = input("Contenido del post: ").strip()
        media_path = input("Ruta de media (opcional): ").strip()
        
        if content:
            try:
                client = self.platform_factory.get_client(platform)
                result = await client.create_post(
                    content=content,
                    media_path=media_path if media_path else None
                )
                print(f"✅ Post publicado exitosamente: {result}")
            except Exception as e:
                print(f"❌ Error al publicar: {e}")
    
    async def _show_scheduled_posts(self):
        """Muestra las publicaciones programadas"""
        posts = await self.content_manager.get_scheduled_posts()
        
        if not posts:
            print("No hay publicaciones programadas")
            return
        
        print("\n--- Publicaciones Programadas ---")
        for post in posts[:10]:  # Mostrar últimas 10
            print(f"📅 {post['scheduled_time']} - {post['platform']}")
            print(f"   {post['content'][:50]}...")
            print()
    
    async def _manage_content(self):
        """Gestiona el contenido"""
        print("\n--- Gestión de Contenido ---")
        print("1. Ver contenido disponible")
        print("2. Agregar nuevo contenido")
        print("3. Programar publicación")
        
        choice = input("Seleccione opción: ").strip()
        
        if choice == "1":
            content_list = await self.content_manager.list_content()
            for content in content_list[:5]:
                print(f"- {content['title']}: {content['content'][:30]}...")
        
        elif choice == "2":
            title = input("Título: ").strip()
            content = input("Contenido: ").strip()
            
            if title and content:
                await self.content_manager.add_content({
                    'title': title,
                    'content': content,
                    'created_at': datetime.now()
                })
                print("✅ Contenido agregado")
        
        elif choice == "3":
            # Lógica para programar publicación
            print("Función de programación en desarrollo...")
    
    async def _show_statistics(self):
        """Muestra estadísticas"""
        print("\n--- Estadísticas ---")
        
        stats = await self.db_manager.get_statistics()
        print(f"Total de posts publicados: {stats.get('total_posts', 0)}")
        print(f"Posts programados: {stats.get('scheduled_posts', 0)}")
        print(f"Interacciones procesadas: {stats.get('interactions', 0)}")
    
    async def _configure_automations(self):
        """Configura las automatizaciones"""
        print("\n--- Configurar Automatizaciones ---")
        print("1. Configurar respuestas automáticas")
        print("2. Configurar programación de posts")
        print("3. Configurar métricas")
        
        choice = input("Seleccione opción: ").strip()
        # Implementar configuraciones según la opción
        print("Configuración en desarrollo...")
    
    async def _process_facebook_interactions(self):
        """Procesa interacciones de Facebook"""
        try:
            facebook_client = self.platform_factory.get_client('facebook')
            if facebook_client:
                await self.automations['interaction'].process_platform_interactions(
                    'facebook', facebook_client
                )
        except Exception as e:
            logger.error(f"Error procesando interacciones de Facebook: {e}")
    
    async def _process_instagram_interactions(self):
        """Procesa interacciones de Instagram"""
        try:
            instagram_client = self.platform_factory.get_client('instagram')
            if instagram_client:
                await self.automations['interaction'].process_platform_interactions(
                    'instagram', instagram_client
                )
        except Exception as e:
            logger.error(f"Error procesando interacciones de Instagram: {e}")
    
    def stop(self):
        """Detiene el gestor de automatización"""
        logger.info("Deteniendo AutomationManager")
        self._running = False
        self.scheduler.stop()