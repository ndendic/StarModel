"""
Signal Mixin - Reactive Signal Management

⚡ Clean Architecture Signal Operations:
This mixin provides reactive signal capabilities for entities, integrating
with the Datastar reactive system while maintaining clean separation.
"""

from typing import Dict, Any, Optional, ClassVar
import json
from datetime import datetime

class SignalMixin:
    """
    Reactive signal management mixin.
    
    Provides signal generation and management capabilities for entities,
    enabling reactive UI updates through Datastar integration.
    """
    
    # Class-level configuration
    _use_namespace: ClassVar[bool] = True
    _sync_with_client: ClassVar[bool] = True
    _namespace: ClassVar[Optional[str]] = None
    
    @property
    def namespace(self) -> str:
        """Get the namespace for this entity instance."""
        return self._namespace or self.__class__.__name__
    
    @property
    def use_namespace(self) -> bool:
        """Get the use_namespace setting for this entity instance."""
        return getattr(self.__class__, '_use_namespace', True)
    
    @property
    def sync_with_client(self) -> bool:
        """Get the sync_with_client setting for this entity instance."""
        return getattr(self.__class__, '_sync_with_client', True)
    
    def signal(self, field_name: str) -> str:
        """
        Get the signal string for a specific field.
        
        Args:
            field_name: Name of the field
            
        Returns:
            Signal string (e.g., "$field" or "$Entity.field")
        """
        if self.use_namespace:
            return f"${self.namespace}.{field_name}"
        else:
            return f"${field_name}"
    
    def signals(self) -> Dict[str, Any]:
        """
        Get all signals for this entity.
        
        Returns:
            Dictionary of signals with current values
        """
        data = self._get_signal_data()
        
        if self.use_namespace:
            return {self.namespace: data}
        else:
            return data
    
    def signal_fragment(self, fields: Optional[list] = None) -> str:
        """
        Get JSON representation of signals for Datastar fragments.
        
        Args:
            fields: Optional list of specific fields to include
            
        Returns:
            JSON string of signals
        """
        if fields:
            data = {field: getattr(self, field, None) for field in fields 
                   if hasattr(self, field)}
        else:
            data = self._get_signal_data()
        
        if self.use_namespace:
            signals = {self.namespace: data}
        else:
            signals = data
        
        return json.dumps(signals)
    
    def merge_signals(self, signals_dict: Dict[str, Any]):
        """
        Merge signals from client back into entity.
        
        Args:
            signals_dict: Dictionary of signals from client
        """
        if self.use_namespace and self.namespace in signals_dict:
            data = signals_dict[self.namespace]
        else:
            data = signals_dict
        
        self._apply_signal_data(data)
    
    def _get_signal_data(self) -> Dict[str, Any]:
        """Get data for signals - override in subclasses"""
        # Default implementation uses model_dump if available
        if hasattr(self, 'model_dump'):
            return self.model_dump()
        elif hasattr(self, '__dict__'):
            # Fallback to instance dict, filtering private attributes
            return {k: v for k, v in self.__dict__.items() 
                   if not k.startswith('_')}
        else:
            return {}
    
    def _apply_signal_data(self, data: Dict[str, Any]):
        """Apply data from signals - override in subclasses"""
        # Default implementation sets attributes directly
        for field_name, value in data.items():
            if hasattr(self, field_name):
                try:
                    setattr(self, field_name, value)
                except (AttributeError, TypeError):
                    # Skip fields that can't be set
                    pass
    
    # Class-level signal descriptors
    @classmethod
    def get_field_signal(cls, field_name: str) -> str:
        """
        Get the signal string for a field on this class.
        
        Args:
            field_name: Name of the field
            
        Returns:
            Signal string
        """
        use_namespace = getattr(cls, '_use_namespace', True)
        namespace = getattr(cls, '_namespace', None) or cls.__name__
        
        if use_namespace:
            return f"${namespace}.{field_name}"
        else:
            return f"${field_name}"
    
    # Configuration methods
    @classmethod
    def configure_signals(cls, 
                         use_namespace: Optional[bool] = None,
                         sync_with_client: Optional[bool] = None,
                         namespace: Optional[str] = None):
        """
        Configure signal behavior for this entity class.
        
        Args:
            use_namespace: Whether to use namespaced signals
            sync_with_client: Whether to sync signals with client
            namespace: Custom namespace (defaults to class name)
        """
        if use_namespace is not None:
            cls._use_namespace = use_namespace
        
        if sync_with_client is not None:
            cls._sync_with_client = sync_with_client
        
        if namespace is not None:
            cls._namespace = namespace
    
    # Datastar integration helpers
    def datastar_attributes(self) -> Dict[str, str]:
        """
        Get Datastar attributes for HTML elements.
        
        Returns:
            Dictionary of data-* attributes for Datastar
        """
        signals_json = self.signal_fragment()
        
        return {
            "data-signals": signals_json,
            "id": self._get_element_id()
        }
    
    def _get_element_id(self) -> str:
        """Get HTML element ID for this entity"""
        if hasattr(self, 'id') and self.id:
            return f"{self.namespace}_{self.id}"
        else:
            return f"{self.namespace}_instance"
    
    # Real-time update helpers
    def get_signal_updates(self, previous_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get only the signals that have changed since previous state.
        
        Args:
            previous_state: Previous signal state to compare against
            
        Returns:
            Dictionary of changed signals
        """
        current_signals = self.signals()
        
        if previous_state is None:
            return current_signals
        
        changed_signals = {}
        
        # Compare current vs previous
        if self.use_namespace:
            namespace = self.namespace
            current_data = current_signals.get(namespace, {})
            previous_data = previous_state.get(namespace, {})
            
            changed_data = {}
            for field, value in current_data.items():
                if field not in previous_data or previous_data[field] != value:
                    changed_data[field] = value
            
            if changed_data:
                changed_signals[namespace] = changed_data
        else:
            for field, value in current_signals.items():
                if field not in previous_state or previous_state[field] != value:
                    changed_signals[field] = value
        
        return changed_signals
    
    def mark_signal_changed(self, field_name: str):
        """
        Mark a specific signal as changed for reactive updates.
        
        Args:
            field_name: Name of the field that changed
        """
        # This could be enhanced to integrate with event bus
        # for automatic signal propagation
        pass

# Export main components
__all__ = ["SignalMixin"]