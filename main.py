#!/usr/bin/env python3
"""
Aplicación principal del Fanpage Automation Suite
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from src.core.automation_manager import AutomationManager
from src.core.config_manager import ConfigManager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def main():
    """Función principal de la aplicación"""
    parser = argparse.ArgumentParser(description="Fanpage Automation Suite")
    parser.add_argument(
        "--mode", 
        choices=["scheduler", "interactive", "api"], 
        default="scheduler",
        help="Modo de ejecución"
    )
    parser.add_argument(
        "--config", 
        default="config/config.yaml",
        help="Archivo de configuración"
    )
    parser.add_argument(
        "--platform",
        choices=["facebook", "instagram", "twitter", "all"],
        default="all",
        help="Plataforma específica a usar"
    )
    
    args = parser.parse_args()
    
    try:
        # Cargar configuración
        config_manager = ConfigManager(args.config)
        config = config_manager.load_config()
        
        # Inicializar el gestor de automatización
        automation_manager = AutomationManager(config)
        
        logger.info(f"Iniciando Fanpage Automation Suite en modo: {args.mode}")
        
        if args.mode == "scheduler":
            await automation_manager.start_scheduler(platform=args.platform)
        elif args.mode == "interactive":
            await automation_manager.start_interactive_mode()
        elif args.mode == "api":
            await automation_manager.start_api_server()
            
    except KeyboardInterrupt:
        logger.info("Deteniendo aplicación...")
    except Exception as e:
        logger.error(f"Error en la aplicación: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())