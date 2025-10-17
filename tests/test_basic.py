"""
Tests básicos para Fanpage Automation Suite
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

# Importar módulos a testear
from src.core.config_manager import ConfigManager
from src.core.content_manager import ContentManager
from src.platforms.platform_factory import PlatformFactory


class TestConfigManager:
    """Tests para ConfigManager"""
    
    def test_load_default_config(self):
        """Test de carga de configuración por defecto"""
        config_manager = ConfigManager("config/nonexistent.yaml")
        config = config_manager.load_config()
        
        assert config is not None
        assert 'general' in config
        assert 'database' in config
        assert 'platforms' in config
    
    def test_get_config_value(self):
        """Test de obtención de valores de configuración"""
        config_manager = ConfigManager("config/nonexistent.yaml")
        config_manager.load_config()
        
        # Test con valor existente
        debug_value = config_manager.get('general.debug')
        assert isinstance(debug_value, bool)
        
        # Test con valor no existente
        nonexistent = config_manager.get('nonexistent.key', 'default')
        assert nonexistent == 'default'
    
    def test_set_config_value(self):
        """Test de establecimiento de valores de configuración"""
        config_manager = ConfigManager("config/nonexistent.yaml")
        config_manager.load_config()
        
        config_manager.set('test.key', 'test_value')
        assert config_manager.get('test.key') == 'test_value'


class TestContentManager:
    """Tests para ContentManager"""
    
    @pytest.fixture
    def content_manager(self):
        """Fixture para ContentManager"""
        config = {
            'database': {'url': 'sqlite:///:memory:'},
            'content': {
                'media_upload_path': '/tmp/test_media',
                'templates_path': '/tmp/test_templates'
            }
        }
        return ContentManager(config)
    
    @pytest.mark.asyncio
    async def test_add_content(self, content_manager):
        """Test de adición de contenido"""
        content_data = {
            'title': 'Test Content',
            'content': 'This is test content',
            'tags': ['test', 'content']
        }
        
        # Mock de la base de datos
        content_manager.db_manager.save_content = AsyncMock()
        
        content_id = await content_manager.add_content(content_data)
        
        assert content_id is not None
        assert content_id.startswith('content_')
        content_manager.db_manager.save_content.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_schedule_post(self, content_manager):
        """Test de programación de posts"""
        content_id = "test_content_id"
        platform = "facebook"
        scheduled_time = datetime.now()
        
        # Mock de métodos de base de datos
        content_manager.db_manager.get_content = AsyncMock(return_value={
            'id': content_id,
            'content': 'Test content'
        })
        content_manager.db_manager.save_scheduled_post = AsyncMock()
        
        post_id = await content_manager.schedule_post(
            content_id, platform, scheduled_time
        )
        
        assert post_id is not None
        assert post_id.startswith('post_')
        content_manager.db_manager.save_scheduled_post.assert_called_once()


class TestPlatformFactory:
    """Tests para PlatformFactory"""
    
    def test_empty_config(self):
        """Test con configuración vacía"""
        config = {'platforms': {}}
        factory = PlatformFactory(config)
        
        assert len(factory.get_available_platforms()) == 0
        assert factory.get_client('facebook') is None
    
    def test_facebook_client_creation(self):
        """Test de creación de cliente Facebook"""
        config = {
            'platforms': {
                'facebook': {
                    'enabled': True,
                    'app_id': 'test_app_id',
                    'app_secret': 'test_app_secret',
                    'access_token': 'test_access_token'
                }
            }
        }
        
        factory = PlatformFactory(config)
        
        assert 'facebook' in factory.get_available_platforms()
        client = factory.get_client('facebook')
        assert client is not None
        assert client.get_platform_name() == 'facebook'
    
    def test_platform_availability(self):
        """Test de verificación de disponibilidad de plataformas"""
        config = {
            'platforms': {
                'facebook': {'enabled': True, 'app_id': 'test', 'app_secret': 'test', 'access_token': 'test'},
                'instagram': {'enabled': False}
            }
        }
        
        factory = PlatformFactory(config)
        
        assert factory.is_platform_available('facebook')
        assert not factory.is_platform_available('instagram')
        assert not factory.is_platform_available('nonexistent')


class TestBasePlatform:
    """Tests para funcionalidades base de plataformas"""
    
    def test_validate_media_file(self):
        """Test de validación de archivos multimedia"""
        from src.platforms.base_platform import BasePlatform
        
        # Crear una implementación de prueba
        class TestPlatform(BasePlatform):
            async def authenticate(self): return True
            async def test_connection(self): return True
            async def create_post(self, content, media_paths=None, **kwargs): return {}
            async def get_posts(self, limit=10): return []
            async def delete_post(self, post_id): return True
            async def get_comments(self, post_id): return []
            async def reply_to_comment(self, comment_id, reply_text): return {}
            async def get_messages(self): return []
            async def send_message(self, recipient_id, message): return {}
            async def get_analytics(self, post_id=None): return {}
        
        platform = TestPlatform({'max_file_size': 1000000})
        
        # Test con archivo no existente
        assert not platform.validate_media_file('/nonexistent/file.jpg')
    
    def test_prepare_content(self):
        """Test de preparación de contenido"""
        from src.platforms.base_platform import BasePlatform
        
        class TestPlatform(BasePlatform):
            async def authenticate(self): return True
            async def test_connection(self): return True
            async def create_post(self, content, media_paths=None, **kwargs): return {}
            async def get_posts(self, limit=10): return []
            async def delete_post(self, post_id): return True
            async def get_comments(self, post_id): return []
            async def reply_to_comment(self, comment_id, reply_text): return {}
            async def get_messages(self): return []
            async def send_message(self, recipient_id, message): return {}
            async def get_analytics(self, post_id=None): return {}
        
        platform = TestPlatform({})
        
        # Test con contenido normal
        content = "This is normal content"
        result = platform.prepare_content(content, max_length=100)
        assert result == content
        
        # Test con contenido largo
        long_content = "A" * 100
        result = platform.prepare_content(long_content, max_length=50)
        assert len(result) <= 50
        assert result.endswith("...")


if __name__ == "__main__":
    # Ejecutar tests
    pytest.main([__file__, "-v"])