"""
Domain Events - Clean Event Representation

Domain events represent things that have happened in the business domain.
They are published after successful transaction commits to trigger
side effects like real-time updates, notifications, or integrations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from datetime import datetime
from enum import Enum
import uuid

class EventType(Enum):
    """Types of domain events"""
    ENTITY_CREATED = "entity.created"
    ENTITY_UPDATED = "entity.updated"
    ENTITY_DELETED = "entity.deleted"
    COMMAND_EXECUTED = "command.executed"
    CUSTOM = "custom"

class EventPriority(Enum):
    """Event processing priority"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class DomainEvent:
    """
    Clean domain event representation.
    
    Domain events are immutable records of things that happened
    in the business domain. They are published after successful
    transaction commits to maintain consistency.
    """
    # Core event information
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.CUSTOM
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Entity information
    entity_type: str = ""
    entity_id: Optional[str] = None
    
    # Event details
    event_name: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # Execution context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    command_id: Optional[str] = None
    
    # Event metadata
    priority: EventPriority = EventPriority.NORMAL
    tags: List[str] = field(default_factory=list)
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    
    # Version for event schema evolution
    version: str = "1.0"
    
    def __post_init__(self):
        """Ensure event is immutable after creation"""
        # Note: In production, you might want to use frozen=True on the dataclass
        # and handle initialization differently
        pass
    
    @classmethod
    def entity_created(
        cls,
        entity_type: str,
        entity_id: str,
        entity_data: Dict[str, Any],
        user_id: Optional[str] = None,
        **kwargs
    ) -> 'DomainEvent':
        """Create an entity created event"""
        return cls(
            event_type=EventType.ENTITY_CREATED,
            entity_type=entity_type,
            entity_id=entity_id,
            event_name="created",
            payload={"entity_data": entity_data},
            user_id=user_id,
            **kwargs
        )
    
    @classmethod
    def entity_updated(
        cls,
        entity_type: str,
        entity_id: str,
        changes: Dict[str, Any],
        user_id: Optional[str] = None,
        **kwargs
    ) -> 'DomainEvent':
        """Create an entity updated event"""
        return cls(
            event_type=EventType.ENTITY_UPDATED,
            entity_type=entity_type,
            entity_id=entity_id,
            event_name="updated",
            payload={"changes": changes},
            user_id=user_id,
            **kwargs
        )
    
    @classmethod
    def entity_deleted(
        cls,
        entity_type: str,
        entity_id: str,
        user_id: Optional[str] = None,
        **kwargs
    ) -> 'DomainEvent':
        """Create an entity deleted event"""
        return cls(
            event_type=EventType.ENTITY_DELETED,
            entity_type=entity_type,
            entity_id=entity_id,
            event_name="deleted",
            user_id=user_id,
            **kwargs
        )
    
    @classmethod
    def command_executed(
        cls,
        entity_type: str,
        entity_id: Optional[str],
        command_name: str,
        parameters: Dict[str, Any],
        result: Any = None,
        user_id: Optional[str] = None,
        command_id: Optional[str] = None,
        **kwargs
    ) -> 'DomainEvent':
        """Create a command executed event"""
        payload = {
            "command_name": command_name,
            "parameters": parameters
        }
        
        if result is not None:
            payload["result"] = result
        
        return cls(
            event_type=EventType.COMMAND_EXECUTED,
            entity_type=entity_type,
            entity_id=entity_id,
            event_name=command_name,
            payload=payload,
            user_id=user_id,
            command_id=command_id,
            **kwargs
        )
    
    def add_tag(self, tag: str):
        """Add a tag to the event"""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if event has a specific tag"""
        return tag in self.tags
    
    def get_entity_key(self) -> str:
        """Get a key identifying the entity this event relates to"""
        return f"{self.entity_type}:{self.entity_id}" if self.entity_id else self.entity_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "event_name": self.event_name,
            "payload": self.payload,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "command_id": self.command_id,
            "priority": self.priority.value,
            "tags": self.tags,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainEvent':
        """Create event from dictionary"""
        # Handle enum conversions
        event_type = EventType(data.get("event_type", EventType.CUSTOM.value))
        priority = EventPriority(data.get("priority", EventPriority.NORMAL.value))
        
        # Handle datetime conversion
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()
        
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            event_type=event_type,
            timestamp=timestamp,
            entity_type=data.get("entity_type", ""),
            entity_id=data.get("entity_id"),
            event_name=data.get("event_name", ""),
            payload=data.get("payload", {}),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            command_id=data.get("command_id"),
            priority=priority,
            tags=data.get("tags", []),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            version=data.get("version", "1.0")
        )
    
    def __str__(self) -> str:
        return f"DomainEvent({self.event_type.value}: {self.entity_type}.{self.event_name})"
    
    def __repr__(self) -> str:
        return (
            f"DomainEvent(event_id='{self.event_id}', "
            f"event_type={self.event_type}, "
            f"entity_type='{self.entity_type}', "
            f"event_name='{self.event_name}')"
        )

# Export main components
__all__ = ["DomainEvent", "EventType", "EventPriority"]