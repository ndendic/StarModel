"""
Event Dispatching - Command Coordination and Execution

🎯 Clean Architecture Application Layer:
This module implements the command dispatching infrastructure
that coordinates between domain entities and infrastructure adapters.

Components:
- CommandContext: Framework-agnostic command representation
- CommandResult: Execution result with metadata
- EventDispatcher: Central command coordination
- ParameterResolver: Clean parameter extraction
"""

from .dispatcher import EventDispatcher, CommandContext, CommandResult
from .parameter_resolver import ParameterResolver
from .command_factory import CommandFactory

__all__ = [
    "EventDispatcher", "CommandContext", "CommandResult",
    "ParameterResolver", "CommandFactory"
]