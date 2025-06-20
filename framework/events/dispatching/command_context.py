"""
Command Context - Framework-Agnostic Command Representation

This module defines the clean command structures used throughout
the application service layer, ensuring no coupling to specific
web frameworks or infrastructure concerns.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Type, Union
from datetime import datetime
from enum import Enum
import uuid

class CommandStatus(Enum):
    """Status of command execution"""
    PENDING = "pending"
    EXECUTING = "executing" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CommandPriority(Enum):
    """Command execution priority"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class UserContext:
    """Clean user context without web framework coupling"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return role in self.roles

@dataclass
class RequestMetadata:
    """Metadata about the originating request"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"  # web, api, cli, etc.
    client_info: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None
    span_id: Optional[str] = None

@dataclass
class CommandContext:
    """
    Framework-agnostic command context.
    
    Contains all information needed to execute a command
    without coupling to specific web frameworks or infrastructure.
    """
    # Core command information
    entity_class: Type
    entity_id: Optional[str]
    event_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Execution context
    user_context: Optional[UserContext] = None
    request_metadata: Optional[RequestMetadata] = None
    
    # Command metadata
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: CommandStatus = CommandStatus.PENDING
    priority: CommandPriority = CommandPriority.NORMAL
    
    # Datastar/reactive payload (if applicable)
    reactive_payload: Optional[Dict[str, Any]] = None
    
    # Execution options
    async_execution: bool = False
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 0
    
    def __post_init__(self):
        """Initialize default request metadata if not provided"""
        if self.request_metadata is None:
            self.request_metadata = RequestMetadata()
    
    @property
    def entity_name(self) -> str:
        """Get entity class name"""
        return self.entity_class.__name__
    
    def get_parameter(self, name: str, default: Any = None) -> Any:
        """Get a specific parameter with default"""
        return self.parameters.get(name, default)
    
    def has_parameter(self, name: str) -> bool:
        """Check if parameter exists"""
        return name in self.parameters
    
    def add_parameter(self, name: str, value: Any):
        """Add a parameter to the context"""
        self.parameters[name] = value
    
    def set_user_context(self, user_context: UserContext):
        """Set the user context"""
        self.user_context = user_context
    
    def require_permission(self, permission: str) -> bool:
        """Check if user has required permission"""
        if not self.user_context:
            return False
        return self.user_context.has_permission(permission)
    
    def get_trace_info(self) -> Dict[str, Optional[str]]:
        """Get tracing information for observability"""
        if not self.request_metadata:
            return {"trace_id": None, "span_id": None}
        return {
            "trace_id": self.request_metadata.trace_id,
            "span_id": self.request_metadata.span_id
        }

@dataclass
class CommandResult:
    """
    Result of command execution with rich metadata.
    
    Provides all information needed for response formatting,
    real-time updates, and error handling.
    """
    # Execution results
    success: bool
    entity: Optional[Any] = None
    return_value: Any = None
    
    # Error information
    error: Optional[Exception] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # Real-time/reactive information
    signals_updated: Dict[str, Any] = field(default_factory=dict)
    fragments_generated: List[Any] = field(default_factory=list)
    events_published: List[str] = field(default_factory=list)
    
    # Execution metadata
    command_id: Optional[str] = None
    execution_time_ms: Optional[float] = None
    entity_changes: Dict[str, Any] = field(default_factory=dict)
    
    # Response hints for adapters
    response_hints: Dict[str, Any] = field(default_factory=dict)
    cache_ttl: Optional[int] = None
    
    @classmethod
    def success_result(
        cls,
        entity: Any = None,
        return_value: Any = None,
        **kwargs
    ) -> 'CommandResult':
        """Create a successful command result"""
        return cls(
            success=True,
            entity=entity,
            return_value=return_value,
            **kwargs
        )
    
    @classmethod
    def error_result(
        cls,
        error: Exception,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        **kwargs
    ) -> 'CommandResult':
        """Create an error command result"""
        return cls(
            success=False,
            error=error,
            error_message=error_message or str(error),
            error_code=error_code or error.__class__.__name__,
            **kwargs
        )
    
    def add_signal_update(self, signal_name: str, value: Any):
        """Add a signal update to the result"""
        self.signals_updated[signal_name] = value
    
    def add_fragment(self, fragment: Any):
        """Add a UI fragment to the result"""
        self.fragments_generated.append(fragment)
    
    def add_event_published(self, event_name: str):
        """Record that an event was published"""
        self.events_published.append(event_name)
    
    def set_response_hint(self, key: str, value: Any):
        """Set a hint for response formatting"""
        self.response_hints[key] = value
    
    def get_response_hint(self, key: str, default: Any = None) -> Any:
        """Get a response formatting hint"""
        return self.response_hints.get(key, default)
    
    def has_errors(self) -> bool:
        """Check if result contains errors"""
        return not self.success or self.error is not None
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error information summary"""
        if not self.has_errors():
            return {}
        
        return {
            "error_code": self.error_code,
            "error_message": self.error_message,
            "error_type": self.error.__class__.__name__ if self.error else None
        }

@dataclass
class BatchCommandContext:
    """Context for executing multiple commands as a batch"""
    commands: List[CommandContext] = field(default_factory=list)
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    atomic: bool = True  # All commands succeed or all fail
    user_context: Optional[UserContext] = None
    request_metadata: Optional[RequestMetadata] = None
    
    def add_command(self, command: CommandContext):
        """Add a command to the batch"""
        self.commands.append(command)
        
        # Inherit user context if command doesn't have one
        if not command.user_context and self.user_context:
            command.user_context = self.user_context
        
        # Inherit request metadata if command doesn't have one
        if not command.request_metadata and self.request_metadata:
            command.request_metadata = self.request_metadata
    
    def get_command_count(self) -> int:
        """Get number of commands in batch"""
        return len(self.commands)

@dataclass
class BatchCommandResult:
    """Result of batch command execution"""
    batch_id: str
    results: List[CommandResult] = field(default_factory=list)
    success: bool = True
    errors: List[Exception] = field(default_factory=list)
    execution_time_ms: Optional[float] = None
    
    def add_result(self, result: CommandResult):
        """Add a command result to the batch"""
        self.results.append(result)
        
        # Update overall success status
        if not result.success:
            self.success = False
            if result.error:
                self.errors.append(result.error)
    
    def get_successful_results(self) -> List[CommandResult]:
        """Get all successful command results"""
        return [r for r in self.results if r.success]
    
    def get_failed_results(self) -> List[CommandResult]:
        """Get all failed command results"""
        return [r for r in self.results if not r.success]
    
    def get_success_rate(self) -> float:
        """Get success rate as percentage"""
        if not self.results:
            return 0.0
        successful = len(self.get_successful_results())
        return (successful / len(self.results)) * 100

# Export all command structures
__all__ = [
    "CommandContext", "CommandResult", "UserContext", "RequestMetadata",
    "BatchCommandContext", "BatchCommandResult", 
    "CommandStatus", "CommandPriority"
]