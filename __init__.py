"""
Fanpage Automation Suite
========================

Una suite completa de automatización para páginas de fans en redes sociales.
Permite programar publicaciones, automatizar respuestas, gestionar contenido
y analizar métricas en múltiples plataformas.

Funcionalidades principales:
- Publicación automática programada
- Gestión de contenido multimedia
- Automatización de respuestas e interacciones
- Análisis de métricas y reportes
- Soporte para múltiples plataformas (Facebook, Instagram, Twitter, etc.)
"""

__version__ = "1.0.0"
__author__ = "Fanpage Automation Team"

from src.core.automation_manager import AutomationManager
from src.core.content_manager import ContentManager
from src.core.scheduler import SchedulerManager

__all__ = [
    "AutomationManager",
    "ContentManager", 
    "SchedulerManager"
]