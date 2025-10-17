"""
Gestor de configuración
"""

import os
import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ConfigManager:
    """Gestor de configuración de la aplicación"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        
        # Cargar variables de entorno
        load_dotenv()
    
    def load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde archivo y variables de entorno"""
        
        # Cargar configuración base desde archivo
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as file:
                    if self.config_path.suffix.lower() == '.yaml':
                        self.config = yaml.safe_load(file) or {}
                    elif self.config_path.suffix.lower() == '.json':
                        self.config = json.load(file)
                    else:
                        logger.warning(f"Formato de configuración no soportado: {self.config_path.suffix}")
                        
                logger.info(f"Configuración cargada desde: {self.config_path}")
            except Exception as e:
                logger.error(f"Error cargando configuración: {e}")
                self.config = {}
        else:
            logger.warning(f"Archivo de configuración no encontrado: {self.config_path}")
            self.config = self._get_default_config()
        
        # Sobrescribir con variables de entorno
        self._override_with_env_vars()
        
        # Validar configuración
        self._validate_config()
        
        return self.config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Retorna la configuración por defecto"""
        return {
            'general': {
                'debug': True,
                'timezone': 'UTC',
                'log_level': 'INFO'
            },
            'database': {
                'url': 'sqlite:///data/fanpage_automation.db'
            },
            'scheduler': {
                'interval': 300,
                'max_retries': 3,
                'retry_delay': 60
            },
            'api': {
                'host': 'localhost',
                'port': 8000,
                'secret_key': 'change-this-secret-key'
            },
            'platforms': {
                'facebook': {
                    'enabled': False,
                    'app_id': '',
                    'app_secret': '',
                    'access_token': ''
                },
                'instagram': {
                    'enabled': False,
                    'username': '',
                    'password': ''
                },
                'twitter': {
                    'enabled': False,
                    'api_key': '',
                    'api_secret': '',
                    'access_token': '',
                    'access_token_secret': ''
                }
            },
            'content': {
                'media_upload_path': 'data/media/',
                'templates_path': 'data/templates/',
                'max_file_size': 52428800  # 50MB
            },
            'logging': {
                'file': 'logs/fanpage_automation.log',
                'max_size': 10485760,  # 10MB
                'backup_count': 5
            }
        }
    
    def _override_with_env_vars(self):
        """Sobrescribe configuración con variables de entorno"""
        
        # Configuración general
        if os.getenv('DEBUG'):
            self.config.setdefault('general', {})['debug'] = os.getenv('DEBUG').lower() == 'true'
        
        if os.getenv('LOG_LEVEL'):
            self.config.setdefault('general', {})['log_level'] = os.getenv('LOG_LEVEL')
        
        if os.getenv('TIMEZONE'):
            self.config.setdefault('general', {})['timezone'] = os.getenv('TIMEZONE')
        
        # Base de datos
        if os.getenv('DATABASE_URL'):
            self.config.setdefault('database', {})['url'] = os.getenv('DATABASE_URL')
        
        # Scheduler
        if os.getenv('SCHEDULER_INTERVAL'):
            self.config.setdefault('scheduler', {})['interval'] = int(os.getenv('SCHEDULER_INTERVAL'))
        
        if os.getenv('MAX_RETRIES'):
            self.config.setdefault('scheduler', {})['max_retries'] = int(os.getenv('MAX_RETRIES'))
        
        # API
        if os.getenv('API_HOST'):
            self.config.setdefault('api', {})['host'] = os.getenv('API_HOST')
        
        if os.getenv('API_PORT'):
            self.config.setdefault('api', {})['port'] = int(os.getenv('API_PORT'))
        
        if os.getenv('API_SECRET_KEY'):
            self.config.setdefault('api', {})['secret_key'] = os.getenv('API_SECRET_KEY')
        
        # Plataformas
        self._load_platform_config('facebook', {
            'app_id': 'FACEBOOK_APP_ID',
            'app_secret': 'FACEBOOK_APP_SECRET',
            'access_token': 'FACEBOOK_ACCESS_TOKEN'
        })
        
        self._load_platform_config('instagram', {
            'username': 'INSTAGRAM_USERNAME',
            'password': 'INSTAGRAM_PASSWORD'
        })
        
        self._load_platform_config('twitter', {
            'api_key': 'TWITTER_API_KEY',
            'api_secret': 'TWITTER_API_SECRET',
            'access_token': 'TWITTER_ACCESS_TOKEN',
            'access_token_secret': 'TWITTER_ACCESS_TOKEN_SECRET'
        })
        
        # Contenido
        if os.getenv('MEDIA_UPLOAD_PATH'):
            self.config.setdefault('content', {})['media_upload_path'] = os.getenv('MEDIA_UPLOAD_PATH')
        
        if os.getenv('MAX_FILE_SIZE'):
            self.config.setdefault('content', {})['max_file_size'] = int(os.getenv('MAX_FILE_SIZE'))
        
        # Logging
        if os.getenv('LOG_FILE'):
            self.config.setdefault('logging', {})['file'] = os.getenv('LOG_FILE')
    
    def _load_platform_config(self, platform: str, env_mapping: Dict[str, str]):
        """Carga configuración de plataforma desde variables de entorno"""
        platform_config = self.config.setdefault('platforms', {}).setdefault(platform, {})
        
        for config_key, env_var in env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value:
                platform_config[config_key] = env_value
                platform_config['enabled'] = True
    
    def _validate_config(self):
        """Valida la configuración cargada"""
        required_sections = ['general', 'database', 'scheduler', 'api', 'platforms']
        
        for section in required_sections:
            if section not in self.config:
                logger.warning(f"Sección de configuración faltante: {section}")
                self.config[section] = {}
        
        # Validar que al menos una plataforma esté habilitada
        platforms_enabled = any(
            platform_config.get('enabled', False)
            for platform_config in self.config.get('platforms', {}).values()
        )
        
        if not platforms_enabled:
            logger.warning("No hay plataformas habilitadas. Revise la configuración.")
        
        # Crear directorios necesarios
        self._create_required_directories()
    
    def _create_required_directories(self):
        """Crea los directorios necesarios"""
        directories = [
            'data',
            'logs',
            self.config.get('content', {}).get('media_upload_path', 'data/media/'),
            self.config.get('content', {}).get('templates_path', 'data/templates/'),
            os.path.dirname(self.config.get('logging', {}).get('file', 'logs/fanpage_automation.log'))
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Obtiene un valor de configuración usando notación de puntos"""
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any):
        """Establece un valor de configuración usando notación de puntos"""
        keys = key_path.split('.')
        config_ref = self.config
        
        for key in keys[:-1]:
            if key not in config_ref or not isinstance(config_ref[key], dict):
                config_ref[key] = {}
            config_ref = config_ref[key]
        
        config_ref[keys[-1]] = value
    
    def save_config(self, path: Optional[str] = None):
        """Guarda la configuración actual en un archivo"""
        save_path = Path(path) if path else self.config_path
        
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as file:
                yaml.dump(self.config, file, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"Configuración guardada en: {save_path}")
        except Exception as e:
            logger.error(f"Error guardando configuración: {e}")
            raise