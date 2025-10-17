# Fanpage Automation Suite

Una suite completa de automatización para páginas de fans en redes sociales que permite programar publicaciones, automatizar respuestas, gestionar contenido y analizar métricas en múltiples plataformas.

## 🚀 Características

- **Publicación Automática**: Programa y publica contenido en Facebook, Instagram y Twitter
- **Gestión de Contenido**: Sistema completo de gestión de contenido multimedia
- **Automatización de Respuestas**: Respuestas automáticas a comentarios y mensajes
- **Análisis de Métricas**: Recopilación y análisis de métricas de engagement
- **Interfaz Múltiple**: Modo interactivo, programador y API REST
- **Base de Datos**: Almacenamiento persistente de contenido y métricas

## 📋 Requisitos

- Python 3.8+
- Base de datos SQLite (incluida) o PostgreSQL (opcional)
- Credenciales de API para las plataformas que desees usar

## 🛠️ Instalación

1. **Clonar el repositorio**:
```bash
git clone https://github.com/albertomaydayjhondoe/fanpage-automation_suite.git
cd fanpage-automation_suite
```

2. **Ejecutar script de configuración**:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

3. **Configurar credenciales**:
```bash
cp .env.example .env
# Editar .env con tus credenciales de API
```

4. **Configurar plataformas** (editar `config/config.yaml`):
```yaml
platforms:
  facebook:
    enabled: true
    app_id: "tu_app_id"
    app_secret: "tu_app_secret"
    access_token: "tu_access_token"
  
  instagram:
    enabled: true
    username: "tu_username"
    password: "tu_password"
  
  twitter:
    enabled: true
    api_key: "tu_api_key"
    api_secret: "tu_api_secret"
    access_token: "tu_access_token"
    access_token_secret: "tu_access_token_secret"
```

## 🚀 Uso

### Modo Programador (Recomendado)
```bash
source venv/bin/activate
python main.py --mode scheduler --platform all
```

### Modo Interactivo
```bash
python main.py --mode interactive
```

### Servidor API
```bash
python main.py --mode api
```

## 📂 Estructura del Proyecto

```
fanpage-automation_suite/
├── src/
│   ├── core/                  # Funcionalidades centrales
│   │   ├── automation_manager.py
│   │   ├── config_manager.py
│   │   ├── content_manager.py
│   │   └── scheduler.py
│   ├── platforms/             # Integraciones con redes sociales
│   │   ├── base_platform.py
│   │   ├── facebook_client.py
│   │   ├── instagram_client.py
│   │   ├── twitter_client.py
│   │   └── platform_factory.py
│   ├── automations/           # Lógica de automatización
│   │   ├── post_automation.py
│   │   └── interaction_automation.py
│   └── utils/                 # Utilidades
│       ├── database.py
│       └── logger.py
├── config/
│   └── config.yaml           # Configuración principal
├── data/                     # Datos y media
├── logs/                     # Archivos de log
├── tests/                    # Tests unitarios
└── scripts/                  # Scripts de utilidad
```

## 🔧 Configuración Avanzada

### Base de Datos PostgreSQL
```yaml
database:
  url: "postgresql://user:password@localhost:5432/fanpage_db"
```

### Respuestas Automáticas
```yaml
automation:
  auto_reply:
    enabled: true
    patterns:
      "\\b(gracias|thank you)\\b": "¡De nada! 😊"
      "\\b(precio|price)\\b": "Te enviaremos info por DM 📩"
```

### Programación de Contenido
```python
# Ejemplo de uso programático
from src.core.automation_manager import AutomationManager
from src.core.config_manager import ConfigManager

config_manager = ConfigManager()
config = config_manager.load_config()

automation = AutomationManager(config)

# Programar publicación
content_id = await automation.content_manager.add_content({
    'title': 'Mi Post',
    'content': 'Contenido del post',
    'media_paths': ['data/media/imagen.jpg']
})

await automation.content_manager.schedule_post(
    content_id=content_id,
    platform='facebook',
    scheduled_time=datetime.now() + timedelta(hours=1)
)
```

## 📊 API REST

Cuando se ejecuta en modo API (`--mode api`), la aplicación expone endpoints REST:

- `GET /api/content` - Listar contenido
- `POST /api/content` - Crear contenido
- `POST /api/posts/schedule` - Programar publicación
- `GET /api/analytics` - Obtener métricas
- `GET /api/status` - Estado de las plataformas

## 🧪 Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

## 📝 Logging

Los logs se guardan en `logs/fanpage_automation.log` con rotación automática. Niveles configurables:

- DEBUG: Información detallada
- INFO: Información general (por defecto)
- WARNING: Advertencias
- ERROR: Errores

## 🔒 Seguridad

- **Nunca** commits credenciales al repositorio
- Usa variables de entorno para datos sensibles
- Implementa rotación de tokens periódica
- Monitorea los logs por actividad sospechosa

## 🤝 Contribuciones

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🆘 Soporte

- **Issues**: Reporta bugs en GitHub Issues
- **Documentación**: Ver ejemplos en `docs/`
- **Discord**: [Únete a nuestro servidor](https://discord.gg/fanpage-automation)

## 🗺️ Roadmap

- [ ] Soporte para TikTok
- [ ] Dashboard web
- [ ] Análisis de sentimientos avanzado
- [ ] Integración con Zapier
- [ ] App móvil de gestión
- [ ] IA para generación de contenido

---

⭐ **¡No olvides dar una estrella al repo si te resulta útil!**