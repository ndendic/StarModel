"""
Configuration Management for StarModel Applications

🔧 Unified Configuration System:
This module provides configuration management for StarModel applications,
supporting different environments and deployment scenarios.
"""

from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import os
from pathlib import Path

class Environment(Enum):
    """Application environments"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class EventBusConfig:
    """Event bus configuration"""
    implementation: str = "InProcessEventBus"
    max_concurrent_handlers: int = 100
    enable_metrics: bool = True
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PersistenceConfig:
    """Persistence layer configuration"""
    default_backend: str = "memory"
    backends: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "memory": {
            "cleanup_interval": 300,
            "default_ttl": None
        },
        "sql": {
            "url": "sqlite:///starmodel.db",
            "echo": False,
            "pool_size": 5,
            "pool_timeout": 30
        },
        "redis": {
            "url": "redis://localhost:6379/0",
            "max_connections": 10
        }
    })

@dataclass
class WebConfig:
    """Web framework configuration"""
    adapter: str = "FastHTMLAdapter"
    host: str = "localhost"
    port: int = 8000
    debug: bool = False
    auto_reload: bool = False
    static_files: Optional[str] = None
    templates: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_key: Optional[str] = None
    session_timeout: int = 3600  # 1 hour
    csrf_protection: bool = True
    cors_enabled: bool = False
    cors_origins: list = field(default_factory=list)

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

@dataclass
class ApplicationConfig:
    """Complete application configuration"""
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    
    # Core configurations
    event_bus: EventBusConfig = field(default_factory=EventBusConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    web: WebConfig = field(default_factory=WebConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Custom configuration
    custom: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def for_environment(cls, environment: Environment) -> 'ApplicationConfig':
        """Create configuration for specific environment"""
        config = cls(environment=environment)
        
        if environment == Environment.DEVELOPMENT:
            config.debug = True
            config.web.debug = True
            config.web.auto_reload = True
            config.logging.level = "DEBUG"
            config.persistence.backends["sql"]["echo"] = True
            
        elif environment == Environment.TESTING:
            config.persistence.backends["sql"]["url"] = "sqlite:///:memory:"
            config.logging.level = "WARNING"
            
        elif environment == Environment.PRODUCTION:
            config.debug = False
            config.web.debug = False
            config.web.auto_reload = False
            config.logging.level = "INFO"
            config.logging.file_path = "/var/log/starmodel/app.log"
            config.security.csrf_protection = True
            
        return config
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ApplicationConfig':
        """Create configuration from dictionary"""
        # This would parse a config dictionary and create the appropriate dataclass
        # For now, simplified implementation
        config = cls()
        
        # Update from dictionary
        if "environment" in config_dict:
            config.environment = Environment(config_dict["environment"])
        
        if "debug" in config_dict:
            config.debug = config_dict["debug"]
        
        # Update nested configs
        if "event_bus" in config_dict:
            for key, value in config_dict["event_bus"].items():
                if hasattr(config.event_bus, key):
                    setattr(config.event_bus, key, value)
        
        if "persistence" in config_dict:
            for key, value in config_dict["persistence"].items():
                if hasattr(config.persistence, key):
                    setattr(config.persistence, key, value)
        
        if "web" in config_dict:
            for key, value in config_dict["web"].items():
                if hasattr(config.web, key):
                    setattr(config.web, key, value)
        
        return config
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> 'ApplicationConfig':
        """Load configuration from file"""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        if config_path.suffix == '.json':
            import json
            with open(config_path) as f:
                config_dict = json.load(f)
        elif config_path.suffix in ('.yml', '.yaml'):
            try:
                import yaml
                with open(config_path) as f:
                    config_dict = yaml.safe_load(f)
            except ImportError:
                raise ImportError("PyYAML is required for YAML configuration files")
        else:
            raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
        
        return cls.from_dict(config_dict)
    
    @classmethod
    def from_environment(cls) -> 'ApplicationConfig':
        """Create configuration from environment variables"""
        env_name = os.getenv('STARMODEL_ENV', 'development')
        environment = Environment(env_name)
        
        config = cls.for_environment(environment)
        
        # Override with environment variables
        if os.getenv('STARMODEL_DEBUG'):
            config.debug = os.getenv('STARMODEL_DEBUG').lower() == 'true'
        
        if os.getenv('STARMODEL_DATABASE_URL'):
            config.persistence.backends["sql"]["url"] = os.getenv('STARMODEL_DATABASE_URL')
        
        if os.getenv('STARMODEL_REDIS_URL'):
            config.persistence.backends["redis"]["url"] = os.getenv('STARMODEL_REDIS_URL')
        
        if os.getenv('STARMODEL_SECRET_KEY'):
            config.security.secret_key = os.getenv('STARMODEL_SECRET_KEY')
        
        if os.getenv('STARMODEL_HOST'):
            config.web.host = os.getenv('STARMODEL_HOST')
        
        if os.getenv('STARMODEL_PORT'):
            config.web.port = int(os.getenv('STARMODEL_PORT'))
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "environment": self.environment.value,
            "debug": self.debug,
            "event_bus": {
                "implementation": self.event_bus.implementation,
                "max_concurrent_handlers": self.event_bus.max_concurrent_handlers,
                "enable_metrics": self.event_bus.enable_metrics,
                "config": self.event_bus.config
            },
            "persistence": {
                "default_backend": self.persistence.default_backend,
                "backends": self.persistence.backends
            },
            "web": {
                "adapter": self.web.adapter,
                "host": self.web.host,
                "port": self.web.port,
                "debug": self.web.debug,
                "auto_reload": self.web.auto_reload,
                "static_files": self.web.static_files,
                "templates": self.web.templates,
                "config": self.web.config
            },
            "security": {
                "secret_key": self.security.secret_key,
                "session_timeout": self.security.session_timeout,
                "csrf_protection": self.security.csrf_protection,
                "cors_enabled": self.security.cors_enabled,
                "cors_origins": self.security.cors_origins
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file_path": self.logging.file_path,
                "max_file_size": self.logging.max_file_size,
                "backup_count": self.logging.backup_count
            },
            "custom": self.custom
        }

# Global configuration management
_current_config: Optional[ApplicationConfig] = None

def set_config(config: ApplicationConfig):
    """Set the global configuration"""
    global _current_config
    _current_config = config

def get_config() -> ApplicationConfig:
    """Get the current global configuration"""
    global _current_config
    
    if _current_config is None:
        # Auto-create from environment if not set
        _current_config = ApplicationConfig.from_environment()
    
    return _current_config

def configure_from_file(config_path: Union[str, Path]):
    """Configure application from file"""
    config = ApplicationConfig.from_file(config_path)
    set_config(config)
    return config

def configure_from_dict(config_dict: Dict[str, Any]):
    """Configure application from dictionary"""
    config = ApplicationConfig.from_dict(config_dict)
    set_config(config)
    return config

# Export main components
__all__ = [
    "ApplicationConfig", "Environment", "EventBusConfig", "PersistenceConfig",
    "WebConfig", "SecurityConfig", "LoggingConfig",
    "set_config", "get_config", "configure_from_file", "configure_from_dict"
]