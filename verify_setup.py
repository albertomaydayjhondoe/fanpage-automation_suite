#!/usr/bin/env python3
"""
Script de verificación para Fanpage Automation Suite
"""

def test_imports():
    """Prueba que todas las importaciones críticas funcionen"""
    
    print("🔍 Probando importaciones...")
    
    try:
        # Core modules
        from src.core.config_manager import ConfigManager
        from src.core.content_manager import ContentManager
        from src.core.scheduler import SchedulerManager
        from src.core.automation_manager import AutomationManager
        print("✅ Módulos core importados")
        
        # Platform modules
        from src.platforms.platform_factory import PlatformFactory
        from src.platforms.base_platform import BasePlatform
        from src.platforms.facebook_client import FacebookClient
        from src.platforms.instagram_client import InstagramClient
        from src.platforms.twitter_client import TwitterClient
        print("✅ Módulos de plataformas importados")
        
        # Automation modules
        from src.automations.post_automation import PostAutomation
        from src.automations.interaction_automation import InteractionAutomation
        print("✅ Módulos de automatización importados")
        
        # Utility modules
        from src.utils.database import DatabaseManager
        from src.utils.logger import setup_logger
        print("✅ Módulos de utilidades importados")
        
        # External dependencies
        import apscheduler
        import aiohttp
        import sqlalchemy
        import requests
        print("✅ Dependencias externas importadas")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en importaciones: {e}")
        return False

def test_configuration():
    """Prueba la carga de configuración"""
    
    print("\n📋 Probando configuración...")
    
    try:
        from src.core.config_manager import ConfigManager
        
        config_manager = ConfigManager("config/config.yaml")
        config = config_manager.load_config()
        
        if config:
            print("✅ Configuración cargada correctamente")
            print(f"   - Base de datos: {config.get('database', {}).get('url', 'No configurada')}")
            print(f"   - Debug mode: {config.get('general', {}).get('debug', False)}")
            print(f"   - Log level: {config.get('general', {}).get('log_level', 'INFO')}")
            return True
        else:
            print("❌ Error cargando configuración")
            return False
            
    except Exception as e:
        print(f"❌ Error en configuración: {e}")
        return False

def test_database_connection():
    """Prueba la conexión a la base de datos"""
    
    print("\n🗄️ Probando base de datos...")
    
    try:
        from src.core.config_manager import ConfigManager
        from src.utils.database import DatabaseManager
        
        config_manager = ConfigManager("config/config.yaml")
        config = config_manager.load_config()
        
        db_manager = DatabaseManager(config)
        print("✅ Base de datos inicializada correctamente")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en base de datos: {e}")
        return False

def main():
    """Función principal de verificación"""
    
    print("🚀 Verificación de Fanpage Automation Suite")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_configuration,
        test_database_connection
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Resultado: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todo está funcionando correctamente!")
        print("\n💡 Próximos pasos:")
        print("1. Configurar credenciales en .env")
        print("2. Ejecutar: python main.py --mode interactive")
    else:
        print("⚠️ Algunas pruebas fallaron. Revisa los errores arriba.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())