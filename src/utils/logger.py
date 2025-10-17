"""
Sistema de logging configurado
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

def setup_logger(name: str, log_file: Optional[str] = None, level: str = "INFO") -> logging.Logger:
    """
    Configura y retorna un logger personalizado
    
    Args:
        name: Nombre del logger
        log_file: Archivo de log (opcional)
        level: Nivel de logging
    
    Returns:
        Logger configurado
    """
    
    # Crear logger
    logger = logging.getLogger(name)
    
    # Evitar duplicar handlers
    if logger.handlers:
        return logger
    
    # Configurar nivel
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Formato de mensajes
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para archivo si se especifica
    if log_file:
        # Crear directorio si no existe
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Handler rotativo para archivo
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def configure_logging_from_config(config: dict):
    """
    Configura el logging global basado en configuración
    
    Args:
        config: Diccionario de configuración
    """
    
    logging_config = config.get('logging', {})
    
    # Configuración básica
    log_level = config.get('general', {}).get('log_level', 'INFO')
    log_file = logging_config.get('file', 'logs/fanpage_automation.log')
    
    # Configurar logging root
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Limpiar handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configurar nuevo logger principal
    main_logger = setup_logger('fanpage_automation', log_file, log_level)
    
    # Configurar loggers de librerías externas
    # Reducir verbosidad de algunos loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('instagrapi').setLevel(logging.WARNING)
    
    return main_logger


class ContextLogger:
    """Logger con contexto adicional"""
    
    def __init__(self, logger: logging.Logger, context: dict):
        self.logger = logger
        self.context = context
    
    def _format_message(self, message: str) -> str:
        """Formatea mensaje con contexto"""
        context_str = " | ".join([f"{k}={v}" for k, v in self.context.items()])
        return f"[{context_str}] {message}"
    
    def debug(self, message: str):
        self.logger.debug(self._format_message(message))
    
    def info(self, message: str):
        self.logger.info(self._format_message(message))
    
    def warning(self, message: str):
        self.logger.warning(self._format_message(message))
    
    def error(self, message: str):
        self.logger.error(self._format_message(message))
    
    def critical(self, message: str):
        self.logger.critical(self._format_message(message))


def get_platform_logger(platform: str, user_id: Optional[str] = None) -> ContextLogger:
    """
    Obtiene logger con contexto de plataforma
    
    Args:
        platform: Nombre de la plataforma
        user_id: ID del usuario (opcional)
    
    Returns:
        Logger con contexto
    """
    base_logger = setup_logger(f"platform.{platform}")
    
    context = {'platform': platform}
    if user_id:
        context['user'] = user_id
    
    return ContextLogger(base_logger, context)


def log_performance(func):
    """
    Decorador para medir y loggear performance de funciones
    """
    import time
    import functools
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = setup_logger(f"performance.{func.__module__}.{func.__name__}")
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Ejecutado en {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error después de {execution_time:.3f}s: {str(e)}")
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = setup_logger(f"performance.{func.__module__}.{func.__name__}")
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Ejecutado en {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error después de {execution_time:.3f}s: {str(e)}")
            raise
    
    # Determinar si la función es async
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def setup_error_reporting(config: dict):
    """
    Configura reportes de errores (placeholder para servicios como Sentry)
    """
    error_config = config.get('error_reporting', {})
    
    if error_config.get('enabled', False):
        # Aquí se podría integrar con servicios como Sentry
        logger = setup_logger('error_reporting')
        logger.info("Sistema de reporte de errores configurado")
        
        # Ejemplo de configuración para Sentry:
        # import sentry_sdk
        # sentry_sdk.init(
        #     dsn=error_config.get('sentry_dsn'),
        #     traces_sample_rate=0.1
        # )


# Logger principal para importación fácil
main_logger = setup_logger('fanpage_automation')