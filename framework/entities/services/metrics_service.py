"""
Metrics Service - Entity Operation Metrics

📊 Performance and Usage Tracking:
This service handles metrics collection for entity operations through dependency injection,
providing insights into entity usage patterns and performance without coupling entities to metrics systems.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING
from datetime import datetime, timedelta
from collections import defaultdict, deque
import time

if TYPE_CHECKING:
    from ..lifecycle.entity import Entity


class MetricsService(ABC):
    """
    Abstract interface for entity metrics collection.
    
    This service is injected into entities to handle metrics tracking,
    keeping business logic separate from monitoring concerns.
    """
    
    @abstractmethod
    def record_operation(self, entity: 'Entity', operation: str, duration_ms: float = None):
        """Record an operation on an entity"""
        pass
    
    @abstractmethod
    def record_event_execution(self, entity: 'Entity', event_name: str, duration_ms: float, success: bool):
        """Record event method execution"""
        pass
    
    @abstractmethod
    def record_persistence_operation(self, entity_class: Type['Entity'], operation: str, duration_ms: float):
        """Record persistence operation"""
        pass
    
    @abstractmethod
    def get_entity_metrics(self, entity: 'Entity') -> Dict[str, Any]:
        """Get metrics for a specific entity"""
        pass
    
    @abstractmethod
    def get_class_metrics(self, entity_class: Type['Entity']) -> Dict[str, Any]:
        """Get metrics for an entity class"""
        pass
    
    @abstractmethod
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics"""
        pass


class EntityMetricsService(MetricsService):
    """
    Default implementation of metrics service with comprehensive tracking.
    
    This service provides detailed metrics collection for entity operations,
    event executions, and persistence operations.
    """
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.retention_cutoff = timedelta(hours=retention_hours)
        
        # Metrics storage
        self._entity_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'operations': defaultdict(int),
            'operation_times': defaultdict(list),
            'events': defaultdict(int),
            'event_times': defaultdict(list),
            'event_errors': defaultdict(int),
            'created_at': datetime.now(),
            'last_activity': datetime.now()
        })
        
        self._class_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'instances_created': 0,
            'total_operations': defaultdict(int),
            'total_events': defaultdict(int),
            'total_event_errors': defaultdict(int),
            'avg_operation_time': defaultdict(float),
            'avg_event_time': defaultdict(float),
            'persistence_operations': defaultdict(int),
            'persistence_times': defaultdict(list)
        })
        
        self._system_metrics = {
            'total_entities': 0,
            'total_operations': 0,
            'total_events': 0,
            'total_errors': 0,
            'start_time': datetime.now(),
            'last_cleanup': datetime.now()
        }
    
    def record_operation(self, entity: 'Entity', operation: str, duration_ms: float = None):
        """Record an operation on an entity"""
        entity_key = self._get_entity_key(entity)
        class_key = self._get_class_key(type(entity))
        
        # Update entity metrics
        entity_metrics = self._entity_metrics[entity_key]
        entity_metrics['operations'][operation] += 1
        entity_metrics['last_activity'] = datetime.now()
        
        if duration_ms is not None:
            entity_metrics['operation_times'][operation].append({
                'duration_ms': duration_ms,
                'timestamp': datetime.now()
            })
        
        # Update class metrics
        class_metrics = self._class_metrics[class_key]
        class_metrics['total_operations'][operation] += 1
        
        if duration_ms is not None:
            self._update_average_time(class_metrics, 'avg_operation_time', operation, duration_ms)
        
        # Update system metrics
        self._system_metrics['total_operations'] += 1
        
        # Cleanup old data
        self._cleanup_old_data()
    
    def record_event_execution(self, entity: 'Entity', event_name: str, duration_ms: float, success: bool):
        """Record event method execution"""
        entity_key = self._get_entity_key(entity)
        class_key = self._get_class_key(type(entity))
        
        # Update entity metrics
        entity_metrics = self._entity_metrics[entity_key]
        entity_metrics['events'][event_name] += 1
        entity_metrics['event_times'][event_name].append({
            'duration_ms': duration_ms,
            'timestamp': datetime.now(),
            'success': success
        })
        entity_metrics['last_activity'] = datetime.now()
        
        if not success:
            entity_metrics['event_errors'][event_name] += 1
        
        # Update class metrics
        class_metrics = self._class_metrics[class_key]
        class_metrics['total_events'][event_name] += 1
        
        if not success:
            class_metrics['total_event_errors'][event_name] += 1
        
        self._update_average_time(class_metrics, 'avg_event_time', event_name, duration_ms)
        
        # Update system metrics
        self._system_metrics['total_events'] += 1
        if not success:
            self._system_metrics['total_errors'] += 1
    
    def record_persistence_operation(self, entity_class: Type['Entity'], operation: str, duration_ms: float):
        """Record persistence operation"""
        class_key = self._get_class_key(entity_class)
        
        # Update class metrics
        class_metrics = self._class_metrics[class_key]
        class_metrics['persistence_operations'][operation] += 1
        class_metrics['persistence_times'][operation].append({
            'duration_ms': duration_ms,
            'timestamp': datetime.now()
        })
    
    def get_entity_metrics(self, entity: 'Entity') -> Dict[str, Any]:
        """Get metrics for a specific entity"""
        entity_key = self._get_entity_key(entity)
        metrics = self._entity_metrics.get(entity_key, {})
        
        # Calculate aggregated metrics
        result = {
            'entity_id': entity.id if hasattr(entity, 'id') else None,
            'entity_class': type(entity).__name__,
            'operations': dict(metrics.get('operations', {})),
            'events': dict(metrics.get('events', {})),
            'event_errors': dict(metrics.get('event_errors', {})),
            'created_at': metrics.get('created_at'),
            'last_activity': metrics.get('last_activity'),
            'uptime_seconds': self._calculate_uptime(metrics.get('created_at')),
            'avg_operation_times': {},
            'avg_event_times': {}
        }
        
        # Calculate average times
        for operation, times in metrics.get('operation_times', {}).items():
            if times:
                avg_time = sum(t['duration_ms'] for t in times) / len(times)
                result['avg_operation_times'][operation] = avg_time
        
        for event, times in metrics.get('event_times', {}).items():
            if times:
                avg_time = sum(t['duration_ms'] for t in times) / len(times)
                result['avg_event_times'][event] = avg_time
        
        return result
    
    def get_class_metrics(self, entity_class: Type['Entity']) -> Dict[str, Any]:
        """Get metrics for an entity class"""
        class_key = self._get_class_key(entity_class)
        metrics = self._class_metrics.get(class_key, {})
        
        return {
            'class_name': entity_class.__name__,
            'instances_created': metrics.get('instances_created', 0),
            'total_operations': dict(metrics.get('total_operations', {})),
            'total_events': dict(metrics.get('total_events', {})),
            'total_event_errors': dict(metrics.get('total_event_errors', {})),
            'avg_operation_time': dict(metrics.get('avg_operation_time', {})),
            'avg_event_time': dict(metrics.get('avg_event_time', {})),
            'persistence_operations': dict(metrics.get('persistence_operations', {}))
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics"""
        uptime = datetime.now() - self._system_metrics['start_time']
        
        return {
            **self._system_metrics,
            'uptime_seconds': uptime.total_seconds(),
            'active_entity_classes': len(self._class_metrics),
            'active_entities': len(self._entity_metrics),
            'last_cleanup': self._system_metrics['last_cleanup']
        }
    
    def _get_entity_key(self, entity: 'Entity') -> str:
        """Get unique key for entity"""
        entity_id = getattr(entity, 'id', None) or id(entity)
        return f"{type(entity).__name__}:{entity_id}"
    
    def _get_class_key(self, entity_class: Type['Entity']) -> str:
        """Get unique key for entity class"""
        return f"{entity_class.__module__}.{entity_class.__name__}"
    
    def _update_average_time(self, metrics: Dict, avg_key: str, operation: str, duration_ms: float):
        """Update rolling average time for an operation"""
        current_avg = metrics[avg_key].get(operation, 0.0)
        current_count = metrics.get('total_operations', {}).get(operation, 0)
        
        if current_count == 0:
            metrics[avg_key][operation] = duration_ms
        else:
            # Calculate rolling average
            new_avg = ((current_avg * (current_count - 1)) + duration_ms) / current_count
            metrics[avg_key][operation] = new_avg
    
    def _calculate_uptime(self, created_at: Optional[datetime]) -> Optional[float]:
        """Calculate uptime in seconds"""
        if created_at:
            return (datetime.now() - created_at).total_seconds()
        return None
    
    def _cleanup_old_data(self):
        """Clean up old metrics data"""
        now = datetime.now()
        
        # Only cleanup every hour
        if now - self._system_metrics['last_cleanup'] < timedelta(hours=1):
            return
        
        cutoff_time = now - self.retention_cutoff
        
        # Clean up entity metrics
        expired_entities = []
        for entity_key, metrics in self._entity_metrics.items():
            last_activity = metrics.get('last_activity', now)
            if last_activity < cutoff_time:
                expired_entities.append(entity_key)
        
        for entity_key in expired_entities:
            del self._entity_metrics[entity_key]
        
        # Clean up time-based data in class metrics
        for class_metrics in self._class_metrics.values():
            for operation, times in class_metrics.get('persistence_times', {}).items():
                class_metrics['persistence_times'][operation] = [
                    t for t in times if t['timestamp'] > cutoff_time
                ]
        
        self._system_metrics['last_cleanup'] = now


class SimpleMetricsService(MetricsService):
    """
    Simple metrics service for testing and minimal deployments.
    
    This implementation provides basic metrics tracking without
    complex aggregations or persistence.
    """
    
    def __init__(self):
        self._operation_counts = defaultdict(int)
        self._event_counts = defaultdict(int)
        self._error_counts = defaultdict(int)
    
    def record_operation(self, entity: 'Entity', operation: str, duration_ms: float = None):
        """Record operation (simplified)"""
        key = f"{type(entity).__name__}.{operation}"
        self._operation_counts[key] += 1
    
    def record_event_execution(self, entity: 'Entity', event_name: str, duration_ms: float, success: bool):
        """Record event execution (simplified)"""
        key = f"{type(entity).__name__}.{event_name}"
        self._event_counts[key] += 1
        
        if not success:
            self._error_counts[key] += 1
    
    def record_persistence_operation(self, entity_class: Type['Entity'], operation: str, duration_ms: float):
        """Record persistence operation (simplified)"""
        key = f"{entity_class.__name__}.persistence.{operation}"
        self._operation_counts[key] += 1
    
    def get_entity_metrics(self, entity: 'Entity') -> Dict[str, Any]:
        """Get simple entity metrics"""
        return {
            'entity_class': type(entity).__name__,
            'operations': dict(self._operation_counts),
            'events': dict(self._event_counts),
            'errors': dict(self._error_counts)
        }
    
    def get_class_metrics(self, entity_class: Type['Entity']) -> Dict[str, Any]:
        """Get simple class metrics"""
        return self.get_entity_metrics(entity_class())
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get simple system metrics"""
        return {
            'total_operations': sum(self._operation_counts.values()),
            'total_events': sum(self._event_counts.values()),
            'total_errors': sum(self._error_counts.values())
        }


# Export main components
__all__ = [
    "MetricsService", "EntityMetricsService", "SimpleMetricsService"
]