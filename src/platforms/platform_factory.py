"""
Factory para crear clientes de plataformas
"""

from typing import Dict, Any, Optional, List
from src.platforms.facebook_client import FacebookClient
from src.platforms.instagram_client import InstagramClient
from src.platforms.twitter_client import TwitterClient
from src.platforms.base_platform import BasePlatform
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PlatformFactory:
    """Factory para crear clientes de redes sociales"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.clients: Dict[str, BasePlatform] = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Inicializa los clientes disponibles"""
        platforms_config = self.config.get('platforms', {})
        
        # Facebook
        if platforms_config.get('facebook', {}).get('enabled', False):
            try:
                self.clients['facebook'] = FacebookClient(platforms_config['facebook'])
                logger.info("Cliente de Facebook inicializado")
            except Exception as e:
                logger.error(f"Error inicializando cliente de Facebook: {e}")
        
        # Instagram
        if platforms_config.get('instagram', {}).get('enabled', False):
            try:
                self.clients['instagram'] = InstagramClient(platforms_config['instagram'])
                logger.info("Cliente de Instagram inicializado")
            except Exception as e:
                logger.error(f"Error inicializando cliente de Instagram: {e}")
        
        # Twitter
        if platforms_config.get('twitter', {}).get('enabled', False):
            try:
                self.clients['twitter'] = TwitterClient(platforms_config['twitter'])
                logger.info("Cliente de Twitter inicializado")
            except Exception as e:
                logger.error(f"Error inicializando cliente de Twitter: {e}")
    
    def get_client(self, platform: str) -> Optional[BasePlatform]:
        """Obtiene cliente para una plataforma específica"""
        return self.clients.get(platform.lower())
    
    def get_available_platforms(self) -> List[str]:
        """Obtiene lista de plataformas disponibles"""
        return list(self.clients.keys())
    
    def is_platform_available(self, platform: str) -> bool:
        """Verifica si una plataforma está disponible"""
        return platform.lower() in self.clients
    
    def get_all_clients(self) -> Dict[str, BasePlatform]:
        """Obtiene todos los clientes disponibles"""
        return self.clients.copy()
    
    def refresh_client(self, platform: str):
        """Refresca un cliente específico"""
        platform = platform.lower()
        platforms_config = self.config.get('platforms', {})
        
        if platform in self.clients:
            del self.clients[platform]
        
        if platform == 'facebook' and platforms_config.get('facebook', {}).get('enabled', False):
            try:
                self.clients['facebook'] = FacebookClient(platforms_config['facebook'])
                logger.info("Cliente de Facebook refrescado")
            except Exception as e:
                logger.error(f"Error refrescando cliente de Facebook: {e}")
        
        elif platform == 'instagram' and platforms_config.get('instagram', {}).get('enabled', False):
            try:
                self.clients['instagram'] = InstagramClient(platforms_config['instagram'])
                logger.info("Cliente de Instagram refrescado")
            except Exception as e:
                logger.error(f"Error refrescando cliente de Instagram: {e}")
        
        elif platform == 'twitter' and platforms_config.get('twitter', {}).get('enabled', False):
            try:
                self.clients['twitter'] = TwitterClient(platforms_config['twitter'])
                logger.info("Cliente de Twitter refrescado")
            except Exception as e:
                logger.error(f"Error refrescando cliente de Twitter: {e}")
    
    def get_platform_status(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene el estado de todas las plataformas"""
        status = {}
        
        for platform_name, client in self.clients.items():
            try:
                # Verificar conexión
                is_connected = asyncio.run(client.test_connection())
                
                status[platform_name] = {
                    'available': True,
                    'connected': is_connected,
                    'last_check': datetime.now().isoformat()
                }
            except Exception as e:
                status[platform_name] = {
                    'available': False,
                    'connected': False,
                    'error': str(e),
                    'last_check': datetime.now().isoformat()
                }
        
        return status