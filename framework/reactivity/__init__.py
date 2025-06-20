"""
Reactivity - Reactive State Management and UI Updates

🔄 Automatic UI Synchronization:
Manages reactive signals, data binding, and automatic UI updates.
Ensures UI stays in sync with entity state changes automatically.

Structure:
- signals/: Reactive signal system and dependency tracking
- binding/: Data-to-UI binding mechanisms and templates
- updates/: Update coordination, batching, and scheduling
- subscriptions/: Change detection and observer patterns

Example:
    from starmodel.reactivity import reactive_signal, bind_to_ui
    
    class Dashboard(Entity):
        metrics: Dict[str, float] = {}
        
        @reactive_signal
        def total_metric(self) -> float:
            return sum(self.metrics.values())
        
        @event
        async def update_metric(self, name: str, value: float):
            self.metrics[name] = value
            # total_metric automatically updates in UI
"""

# Primary exports
try:
    from .signals.signal_system import SignalSystem, reactive_signal
    from .binding.data_binding import DataBinding, bind_to_ui
    from .updates.update_engine import UpdateEngine
    from .subscriptions.observers import Observer, watch_changes
except ImportError:
    # Placeholders during migration
    SignalSystem = None
    reactive_signal = None
    DataBinding = None
    bind_to_ui = None
    UpdateEngine = None
    Observer = None
    watch_changes = None

def configure_reactivity(**config):
    """Configure reactive system behavior"""
    # Placeholder implementation
    pass

__all__ = [
    "SignalSystem", "reactive_signal", "DataBinding", "bind_to_ui",
    "UpdateEngine", "Observer", "watch_changes", "configure_reactivity"
]