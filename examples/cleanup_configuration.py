"""
StarModel Cleanup Configuration Examples

This file demonstrates different ways to configure automatic cleanup
for persistence backends without touching main.py.
"""

from starmodel.persistence import MemoryRepo, configure_all_cleanup

# Example 1: Default behavior (no configuration needed)
# MemoryRepo automatically starts cleanup with 5-minute intervals
print("=== Example 1: Default Behavior ===")
repo = MemoryRepo()
print(f"Auto cleanup: {repo._auto_cleanup}")
print(f"Interval: {repo._cleanup_interval}s")

# Example 2: Configure all backends globally
print("\n=== Example 2: Global Configuration ===")
configure_all_cleanup(enabled=True, interval=120)  # 2 minutes
print(f"Updated interval: {repo._cleanup_interval}s")

# Example 3: Configure individual backend
print("\n=== Example 3: Individual Backend Configuration ===")
repo.configure_cleanup(enabled=True, interval=60)  # 1 minute
print(f"Individual interval: {repo._cleanup_interval}s")

# Example 4: Disable cleanup completely
print("\n=== Example 4: Disable Cleanup ===")
repo.configure_cleanup(enabled=False)
print(f"Auto cleanup disabled: {not repo._auto_cleanup}")

# Example 5: Custom persistence backend with cleanup
print("\n=== Example 5: Custom Backend Example ===")

from starmodel.persistence import EntityPersistenceBackend
from typing import Optional

class CustomRepo(EntityPersistenceBackend):
    """Example custom repository with cleanup support."""
    
    def __init__(self, cleanup_interval: int = 600):  # 10 minutes default
        super().__init__()
        self._data = {}
        self._expiry = {}
        
        # Configure custom cleanup interval
        self.configure_cleanup(enabled=True, interval=cleanup_interval)
        self.start_cleanup()
    
    def save_entity_sync(self, entity, ttl: Optional[int] = None) -> bool:
        # Implementation would go here
        return True
    
    def load_entity_sync(self, entity_id: str):
        # Implementation would go here
        return None
    
    def delete_entity_sync(self, entity_id: str) -> bool:
        # Implementation would go here
        return True
    
    def exists_sync(self, entity_id: str) -> bool:
        # Implementation would go here
        return False
    
    def cleanup_expired_sync(self) -> int:
        # Custom cleanup logic would go here
        print("CustomRepo: Running cleanup...")
        return 0

# Create custom repo with 30-second cleanup
custom = CustomRepo(cleanup_interval=30)
print(f"Custom repo interval: {custom._cleanup_interval}s")

print("\n=== Configuration Complete ===")
print("✅ Cleanup is automatically managed by each persistence backend")
print("✅ No manual setup required in main.py")
print("✅ Each backend can have its own cleanup strategy")
print("✅ Global controls available for advanced users")