"""
Event Dispatcher - Central Command Coordination

🎯 Clean Architecture Application Service:
The dispatcher is the heart of StarModel's command processing.
It coordinates between domain entities, persistence, and real-time systems
while maintaining clean separation of concerns.

Key Responsibilities:
- Command validation and authorization
- Entity loading and parameter resolution
- Event method execution with error handling
- Transaction coordination via Unit of Work
- Real-time event publishing
- Response formatting coordination
"""

import asyncio
import inspect
import time
from typing import Any, Dict, Optional, Type, Callable, List
from dataclasses import dataclass
from datetime import datetime

# Import from screaming architecture
from .command_context import (
    CommandContext, CommandResult, BatchCommandContext, BatchCommandResult,
    CommandStatus, UserContext
)

# Forward declarations for clean dependencies
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...persistence.transactions.unit_of_work import UnitOfWork
    from ...events.streaming.event_bus import EventBus
    from ...entities.lifecycle.entity import Entity

class DispatcherError(Exception):
    """Base exception for dispatcher errors"""
    pass

class EntityNotFoundError(DispatcherError):
    """Raised when entity cannot be loaded"""
    pass

class EventNotFoundError(DispatcherError):
    """Raised when event method is not found"""
    pass

class AuthorizationError(DispatcherError):
    """Raised when user lacks required permissions"""
    pass

class ParameterValidationError(DispatcherError):
    """Raised when parameters are invalid"""
    pass

@dataclass
class DispatcherConfig:
    """Configuration for event dispatcher behavior"""
    default_timeout_seconds: int = 30
    max_parameter_size: int = 1024 * 1024  # 1MB
    enable_parameter_validation: bool = True
    enable_authorization_checks: bool = True
    enable_tracing: bool = True
    enable_metrics: bool = True
    
    # Error handling
    retry_transient_errors: bool = True
    max_retries: int = 3
    
    # Performance
    enable_entity_caching: bool = True
    cache_ttl_seconds: int = 300

class EventDispatcher:
    """
    Central event dispatcher implementing clean architecture.
    
    The dispatcher serves as the Application Service Layer,
    coordinating between domain entities and infrastructure
    while maintaining clean separation of concerns.
    
    Architecture:
    - Pure command processing (no web framework coupling)
    - Entity loading through dependency injection
    - Transaction coordination via Unit of Work
    - Event publishing through Event Bus
    - Authorization and validation
    """
    
    def __init__(
        self,
        unit_of_work: Optional['UnitOfWork'] = None,
        event_bus: Optional['EventBus'] = None,
        config: Optional[DispatcherConfig] = None
    ):
        self.unit_of_work = unit_of_work
        self.event_bus = event_bus
        self.config = config or DispatcherConfig()
        
        # Execution metrics
        self._metrics = {
            "commands_executed": 0,
            "commands_succeeded": 0,
            "commands_failed": 0,
            "total_execution_time_ms": 0.0
        }
        
        # Entity cache for performance
        self._entity_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def dispatch(self, context: CommandContext) -> CommandResult:
        """
        Dispatch a single command with full clean architecture flow.
        
        Flow:
        1. Validate command and check authorization
        2. Load target entity
        3. Resolve and validate parameters
        4. Execute event method
        5. Handle persistence and event publishing
        6. Return rich result
        """
        start_time = time.time()
        context.status = CommandStatus.EXECUTING
        
        try:
            # 1. Pre-execution validation
            await self._validate_command(context)
            await self._check_authorization(context)
            
            # 2. Load target entity
            entity = await self._load_entity(context)
            
            # 3. Resolve and validate parameters
            resolved_params = await self._resolve_parameters(context, entity)
            
            # 4. Execute event method
            execution_result = await self._execute_event(entity, context, resolved_params)
            
            # 5. Handle persistence and event publishing
            await self._handle_post_execution(entity, context, execution_result)
            
            # 6. Create successful result
            result = await self._create_success_result(entity, context, execution_result)
            
            context.status = CommandStatus.COMPLETED
            self._update_metrics(True, time.time() - start_time)
            
            return result
            
        except Exception as e:
            context.status = CommandStatus.FAILED
            self._update_metrics(False, time.time() - start_time)
            
            return await self._create_error_result(context, e)
    
    async def dispatch_batch(self, batch_context: BatchCommandContext) -> BatchCommandResult:
        """
        Dispatch multiple commands as a batch.
        
        Supports both atomic (all-or-nothing) and non-atomic execution.
        """
        batch_result = BatchCommandResult(batch_id=batch_context.batch_id)
        start_time = time.time()
        
        if batch_context.atomic:
            return await self._dispatch_atomic_batch(batch_context, batch_result)
        else:
            return await self._dispatch_non_atomic_batch(batch_context, batch_result)
    
    async def _validate_command(self, context: CommandContext):
        """Validate command structure and basic requirements"""
        if not context.entity_class:
            raise ParameterValidationError("Entity class is required")
        
        if not context.event_name:
            raise ParameterValidationError("Event name is required")
        
        # Check parameter size limits
        if self.config.enable_parameter_validation:
            param_size = len(str(context.parameters))
            if param_size > self.config.max_parameter_size:
                raise ParameterValidationError(f"Parameters too large: {param_size} bytes")
        
        # Validate entity has the requested event
        if not hasattr(context.entity_class, context.event_name):
            raise EventNotFoundError(f"Event '{context.event_name}' not found on {context.entity_name}")
        
        # Check if method is actually an event
        method = getattr(context.entity_class, context.event_name)
        if not hasattr(method, '_event_metadata') and not hasattr(method, '_event_info'):
            raise EventNotFoundError(f"Method '{context.event_name}' is not an @event method")
    
    async def _check_authorization(self, context: CommandContext):
        """Check user authorization for the command"""
        if not self.config.enable_authorization_checks:
            return
        
        if not context.user_context:
            # No user context - allow for system/internal commands
            return
        
        # Get event metadata to check required permissions
        method = getattr(context.entity_class, context.event_name)
        event_metadata = getattr(method, '_event_metadata', None) or getattr(method, '_event_info', None)
        
        if event_metadata and hasattr(event_metadata, 'permissions'):
            required_permissions = getattr(event_metadata, 'permissions', [])
            
            for permission in required_permissions:
                if not context.user_context.has_permission(permission):
                    raise AuthorizationError(f"Missing required permission: {permission}")
    
    async def _load_entity(self, context: CommandContext) -> 'Entity':
        """Load the target entity for command execution"""
        # Check cache first if enabled
        if self.config.enable_entity_caching and context.entity_id:
            cache_key = f"{context.entity_name}:{context.entity_id}"
            cached_entity = self._get_cached_entity(cache_key)
            if cached_entity:
                return cached_entity
        
        # Load entity through entity class method
        if context.entity_id:
            # Load existing entity
            try:
                entity = await context.entity_class.get(context.entity_id)
                if not entity:
                    raise EntityNotFoundError(f"Entity {context.entity_name}:{context.entity_id} not found")
            except Exception as e:
                raise EntityNotFoundError(f"Failed to load entity: {e}")
        else:
            # Create new entity instance
            entity = context.entity_class()
        
        # Cache entity if enabled
        if self.config.enable_entity_caching and context.entity_id:
            cache_key = f"{context.entity_name}:{context.entity_id}"
            self._cache_entity(cache_key, entity)
        
        return entity
    
    async def _resolve_parameters(self, context: CommandContext, entity: 'Entity') -> Dict[str, Any]:
        """Resolve and validate parameters for event method execution"""
        method = getattr(entity, context.event_name)
        signature = inspect.signature(method)
        
        resolved_params = {}
        
        # Process each parameter in the method signature
        for param_name, param_info in signature.parameters.items():
            if param_name == 'self':
                continue
            
            # Get value from context parameters
            if param_name in context.parameters:
                value = context.parameters[param_name]
                
                # Basic type validation if annotation is available
                if param_info.annotation != inspect.Parameter.empty:
                    try:
                        # Simple type checking - could be enhanced
                        if not isinstance(value, param_info.annotation):
                            # Attempt type conversion
                            value = param_info.annotation(value)
                    except (TypeError, ValueError) as e:
                        raise ParameterValidationError(f"Invalid type for parameter '{param_name}': {e}")
                
                resolved_params[param_name] = value
            
            elif param_info.default == inspect.Parameter.empty:
                # Required parameter is missing
                raise ParameterValidationError(f"Required parameter '{param_name}' is missing")
        
        return resolved_params
    
    async def _execute_event(
        self, 
        entity: 'Entity', 
        context: CommandContext, 
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute the event method on the entity"""
        method = getattr(entity, context.event_name)
        
        try:
            # Handle both async and sync methods
            if asyncio.iscoroutinefunction(method):
                result = await method(**parameters)
            else:
                result = method(**parameters)
            
            return result
            
        except Exception as e:
            # Wrap in more specific error types
            if isinstance(e, (ValueError, TypeError)):
                raise ParameterValidationError(f"Parameter error in {context.event_name}: {e}")
            else:
                raise  # Re-raise as-is for other exceptions
    
    async def _handle_post_execution(
        self, 
        entity: 'Entity', 
        context: CommandContext, 
        execution_result: Any
    ):
        """Handle persistence and event publishing after command execution"""
        if self.unit_of_work:
            # Register entity for persistence
            await self.unit_of_work.register_entity(entity)
            
            # Register command record as domain event
            command_record = {
                "entity_type": context.entity_name,
                "entity_id": entity.id if hasattr(entity, 'id') else None,
                "event_name": context.event_name,
                "parameters": context.parameters,
                "timestamp": context.request_metadata.timestamp if context.request_metadata else datetime.now(),
                "user_id": context.user_context.user_id if context.user_context else None,
                "command_id": context.command_id,
                "result": execution_result
            }
            
            await self.unit_of_work.register_event(command_record)
            
            # Commit all changes atomically
            await self.unit_of_work.commit()
    
    async def _create_success_result(
        self, 
        entity: 'Entity', 
        context: CommandContext, 
        execution_result: Any
    ) -> CommandResult:
        """Create a successful command result with rich metadata"""
        # Get updated signals from entity
        signals_updated = {}
        if hasattr(entity, 'get_signals'):
            signals_updated = entity.get_signals()
        
        # Handle fragments from execution result
        fragments_generated = []
        if hasattr(execution_result, '__iter__') and not isinstance(execution_result, (str, bytes, dict)):
            # Result is iterable (generator/list of fragments)
            fragments_generated = list(execution_result)
        elif execution_result is not None:
            # Single fragment
            fragments_generated = [execution_result]
        
        return CommandResult.success_result(
            entity=entity,
            return_value=execution_result,
            signals_updated=signals_updated,
            fragments_generated=fragments_generated,
            command_id=context.command_id
        )
    
    async def _create_error_result(self, context: CommandContext, error: Exception) -> CommandResult:
        """Create an error result with appropriate error classification"""
        error_code = error.__class__.__name__
        
        # Map internal errors to user-friendly codes
        error_mapping = {
            "EntityNotFoundError": "ENTITY_NOT_FOUND",
            "EventNotFoundError": "EVENT_NOT_FOUND", 
            "AuthorizationError": "UNAUTHORIZED",
            "ParameterValidationError": "INVALID_PARAMETERS"
        }
        
        mapped_code = error_mapping.get(error_code, error_code)
        
        return CommandResult.error_result(
            error=error,
            error_message=str(error),
            error_code=mapped_code,
            command_id=context.command_id
        )
    
    async def _dispatch_atomic_batch(
        self, 
        batch_context: BatchCommandContext, 
        batch_result: BatchCommandResult
    ) -> BatchCommandResult:
        """Execute batch atomically - all succeed or all fail"""
        start_time = time.time()
        
        try:
            # Execute all commands
            for command in batch_context.commands:
                result = await self.dispatch(command)
                batch_result.add_result(result)
                
                # If any command fails in atomic mode, rollback everything
                if not result.success:
                    if self.unit_of_work:
                        await self.unit_of_work.rollback()
                    break
            
            # If all succeeded, commit the batch
            if batch_result.success and self.unit_of_work:
                await self.unit_of_work.commit()
                
        except Exception as e:
            # Rollback on any error
            if self.unit_of_work:
                await self.unit_of_work.rollback()
            batch_result.success = False
            batch_result.errors.append(e)
        
        batch_result.execution_time_ms = (time.time() - start_time) * 1000
        return batch_result
    
    async def _dispatch_non_atomic_batch(
        self, 
        batch_context: BatchCommandContext, 
        batch_result: BatchCommandResult
    ) -> BatchCommandResult:
        """Execute batch non-atomically - continue on failures"""
        start_time = time.time()
        
        for command in batch_context.commands:
            try:
                result = await self.dispatch(command)
                batch_result.add_result(result)
            except Exception as e:
                # Continue with other commands even on failure
                error_result = await self._create_error_result(command, e)
                batch_result.add_result(error_result)
        
        batch_result.execution_time_ms = (time.time() - start_time) * 1000
        return batch_result
    
    def _get_cached_entity(self, cache_key: str) -> Optional['Entity']:
        """Get entity from cache if not expired"""
        if cache_key not in self._entity_cache:
            return None
        
        timestamp = self._cache_timestamps.get(cache_key)
        if not timestamp:
            return None
        
        # Check if cache entry is still valid
        age_seconds = (datetime.now() - timestamp).total_seconds()
        if age_seconds > self.config.cache_ttl_seconds:
            # Cache expired
            del self._entity_cache[cache_key]
            del self._cache_timestamps[cache_key]
            return None
        
        return self._entity_cache[cache_key]
    
    def _cache_entity(self, cache_key: str, entity: 'Entity'):
        """Cache entity with timestamp"""
        self._entity_cache[cache_key] = entity
        self._cache_timestamps[cache_key] = datetime.now()
    
    def _update_metrics(self, success: bool, execution_time_seconds: float):
        """Update dispatcher execution metrics"""
        self._metrics["commands_executed"] += 1
        if success:
            self._metrics["commands_succeeded"] += 1
        else:
            self._metrics["commands_failed"] += 1
        
        self._metrics["total_execution_time_ms"] += execution_time_seconds * 1000
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get dispatcher performance metrics"""
        metrics = self._metrics.copy()
        
        if metrics["commands_executed"] > 0:
            metrics["success_rate"] = (metrics["commands_succeeded"] / metrics["commands_executed"]) * 100
            metrics["average_execution_time_ms"] = metrics["total_execution_time_ms"] / metrics["commands_executed"]
        else:
            metrics["success_rate"] = 0.0
            metrics["average_execution_time_ms"] = 0.0
        
        return metrics
    
    def reset_metrics(self):
        """Reset dispatcher metrics"""
        self._metrics = {
            "commands_executed": 0,
            "commands_succeeded": 0, 
            "commands_failed": 0,
            "total_execution_time_ms": 0.0
        }

# Export main components
__all__ = [
    "EventDispatcher", "DispatcherConfig", "DispatcherError",
    "EntityNotFoundError", "EventNotFoundError", "AuthorizationError", 
    "ParameterValidationError"
]