# Copilot Instructions for Fanpage Automation Suite

## Project Overview
This is a comprehensive social media automation suite designed for managing fanpages across multiple platforms (Facebook, Instagram, Twitter). The system handles scheduled posting, automated interactions, content management, and analytics collection.

## Architecture & Core Patterns

### Modular Platform Integration
- Each social platform has its own client (`src/platforms/`) extending `BasePlatform`
- Use `PlatformFactory` to get platform clients - never instantiate clients directly
- All platform methods are async and follow standard interface (create_post, get_posts, etc.)

### Configuration Management
- Central config in `config/config.yaml` with environment variable overrides
- Use `ConfigManager` for all config access: `config_manager.get('platforms.facebook.enabled')`
- Database URL, API keys, and platform settings all configurable

### Content & Scheduling Flow
1. Content created via `ContentManager.add_content()`
2. Posts scheduled via `ContentManager.schedule_post()`
3. `SchedulerManager` executes scheduled posts using platform clients
4. Results tracked in database with retry logic for failures

### Database Layer
- SQLAlchemy models in `src/utils/database.py`
- Supports both SQLite (default) and PostgreSQL
- All operations async-compatible
- Models: ContentModel, ScheduledPostModel, CommentModel, etc.

## Key Development Patterns

### Error Handling & Retries
```python
# Platform operations include automatic retry logic
try:
    result = await client.create_post(content, media_paths)
    await content_manager.mark_post_published(post_id, result)
except Exception as e:
    await content_manager.mark_post_failed(post_id, str(e))
```

### Async Architecture
- All platform interactions are async
- Use `asyncio.sleep()` between API calls to respect rate limits
- Database operations support both sync and async modes

### Platform-Specific Handling
- Instagram requires media files for posts
- Twitter has 280 character limit
- Facebook supports albums and detailed targeting
- Check platform availability before operations: `platform_factory.is_platform_available()`

## Critical Components

### AutomationManager (`src/core/automation_manager.py`)
Central orchestrator with three modes:
- `start_scheduler()`: Background task processing
- `start_interactive_mode()`: CLI interface
- `start_api_server()`: REST API mode

### ContentManager (`src/core/content_manager.py`)
Handles all content operations:
- Content CRUD with media file management
- Post scheduling with platform-specific configs
- Template system for reusable content

### Platform Clients (`src/platforms/`)
Each client implements `BasePlatform` interface:
- Authentication handling with session persistence
- Media upload with validation
- Rate limit management
- Standardized data formatting

## Development Workflows

### Adding New Platform Support
1. Create new client extending `BasePlatform`
2. Implement all abstract methods
3. Add configuration section to `config.yaml`
4. Register in `PlatformFactory._initialize_clients()`
5. Add tests in `tests/`

### Testing Strategy
- Mock platform clients for unit tests
- Use in-memory SQLite for database tests
- Test configuration loading with various scenarios
- Platform integration tests should use mock responses

### Running the Application
```bash
# Setup (first time)
./scripts/setup.sh

# Scheduler mode (production)
python main.py --mode scheduler --platform all

# Interactive mode (development)
python main.py --mode interactive

# API server mode
python main.py --mode api
```

## Important Implementation Notes

### Authentication Persistence
- Instagram: Session files stored in `data/`
- Facebook: Long-lived tokens in config
- Twitter: OAuth 1.0a with stored credentials

### Media Handling
- Files validated before upload (`BasePlatform.validate_media_file()`)
- Stored in `data/media/` with unique naming
- Platform-specific size/format restrictions

### Database Considerations
- All timestamps in UTC
- JSON fields for flexible metadata storage
- Retry logic built into scheduled post processing
- Soft deletes for content (status = 'deleted')

When modifying this codebase:
- Always use the factory pattern for platform clients
- Respect async patterns throughout
- Add comprehensive error handling with logging
- Update tests when adding new functionality
- Follow the established configuration patterns