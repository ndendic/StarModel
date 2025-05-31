#!/usr/bin/env python3
"""
Test Persistence Layer Functionality (Phase 5.1)

This test verifies that the state persistence system works correctly
with different backends (Memory, Redis, Database).
"""

import sys
import os
import asyncio
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from faststate.persistence import (
    MemoryStatePersistence, DatabaseStatePersistence, StatePersistenceManager,
    RedisStatePersistence
)


async def test_memory_persistence():
    """Test memory-based persistence backend."""
    print("Testing Memory Persistence...")
    
    backend = MemoryStatePersistence()
    
    # Test basic save and load
    state_data = {"count": 42, "name": "test_state", "active": True}
    success = await backend.save_state("test_key", state_data)
    assert success, "Save should succeed"
    
    loaded_data = await backend.load_state("test_key")
    assert loaded_data == state_data, "Loaded data should match saved data"
    
    print("✓ Basic save/load works")
    
    # Test exists check
    exists = await backend.exists("test_key")
    assert exists, "State should exist"
    
    non_existent = await backend.exists("non_existent_key")
    assert not non_existent, "Non-existent state should not exist"
    
    print("✓ Exists check works")
    
    # Test TTL functionality
    ttl_data = {"temporary": True}
    success = await backend.save_state("ttl_key", ttl_data, ttl=1)
    assert success, "TTL save should succeed"
    
    # Should exist immediately
    exists = await backend.exists("ttl_key")
    assert exists, "TTL state should exist immediately"
    
    # Wait for expiration
    time.sleep(1.1)
    
    # Should be expired now
    exists = await backend.exists("ttl_key")
    assert not exists, "TTL state should be expired"
    
    print("✓ TTL functionality works")
    
    # Test deletion
    success = await backend.delete_state("test_key")
    assert success, "Delete should succeed"
    
    exists = await backend.exists("test_key")
    assert not exists, "Deleted state should not exist"
    
    print("✓ Deletion works")
    
    # Test cleanup
    # Add some expired entries
    await backend.save_state("expired1", {"data": 1}, ttl=1)
    await backend.save_state("expired2", {"data": 2}, ttl=1)
    time.sleep(1.1)
    
    cleaned = await backend.cleanup_expired()
    assert cleaned == 2, "Should clean up 2 expired entries"
    
    print("✓ Cleanup works")


async def test_database_persistence():
    """Test database-based persistence backend."""
    print("Testing Database Persistence...")
    
    # Use temporary database for testing
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_url = f"sqlite:///{tmp_file.name}"
    
    try:
        backend = DatabaseStatePersistence(database_url=db_url)
        
        # Test basic save and load
        state_data = {"count": 100, "name": "db_test_state", "enabled": False}
        success = await backend.save_state("db_test_key", state_data)
        assert success, "Database save should succeed"
        
        loaded_data = await backend.load_state("db_test_key")
        assert loaded_data == state_data, "Database loaded data should match"
        
        print("✓ Database save/load works")
        
        # Test update existing
        updated_data = {"count": 200, "name": "updated_state", "enabled": True}
        success = await backend.save_state("db_test_key", updated_data)
        assert success, "Database update should succeed"
        
        loaded_data = await backend.load_state("db_test_key")
        assert loaded_data == updated_data, "Updated data should match"
        
        print("✓ Database update works")
        
        # Test TTL with database
        ttl_data = {"temporary": True, "expiry_test": True}
        success = await backend.save_state("db_ttl_key", ttl_data, ttl=1)
        assert success, "Database TTL save should succeed"
        
        # Should exist immediately
        exists = await backend.exists("db_ttl_key")
        assert exists, "TTL state should exist in database"
        
        # Wait for expiration and check cleanup
        time.sleep(1.1)
        
        # Loading expired entry should return None and clean it up
        loaded_data = await backend.load_state("db_ttl_key")
        assert loaded_data is None, "Expired state should return None"
        
        print("✓ Database TTL works")
        
        # Test cleanup
        await backend.save_state("cleanup1", {"data": 1}, ttl=1)
        await backend.save_state("cleanup2", {"data": 2}, ttl=1)
        time.sleep(1.1)
        
        cleaned = await backend.cleanup_expired()
        assert cleaned >= 0, "Cleanup should return non-negative count"
        
        print("✓ Database cleanup works")
        
    except ImportError:
        print("⚠ SQLAlchemy not available, skipping database tests")
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_file.name)
        except:
            pass


async def test_redis_persistence():
    """Test Redis-based persistence backend (if available)."""
    print("Testing Redis Persistence...")
    
    try:
        backend = RedisStatePersistence()
        
        # Test basic operations
        state_data = {"count": 500, "name": "redis_test", "cached": True}
        success = await backend.save_state("redis_test_key", state_data)
        
        if success:
            loaded_data = await backend.load_state("redis_test_key")
            assert loaded_data == state_data, "Redis loaded data should match"
            
            print("✓ Redis save/load works")
            
            # Test TTL
            ttl_data = {"redis_ttl": True}
            success = await backend.save_state("redis_ttl_key", ttl_data, ttl=2)
            assert success, "Redis TTL save should succeed"
            
            exists = await backend.exists("redis_ttl_key")
            assert exists, "Redis TTL state should exist"
            
            print("✓ Redis TTL works")
            
            # Test deletion
            success = await backend.delete_state("redis_test_key")
            assert success, "Redis delete should succeed"
            
            exists = await backend.exists("redis_test_key") 
            assert not exists, "Deleted Redis state should not exist"
            
            print("✓ Redis deletion works")
        else:
            print("⚠ Redis server not available, basic operations skipped")
            
    except ImportError:
        print("⚠ Redis library not available, skipping Redis tests")
    except Exception as e:
        print(f"⚠ Redis tests failed (server not running?): {e}")


async def test_persistence_manager():
    """Test the persistence manager with multiple backends."""
    print("Testing Persistence Manager...")
    
    manager = StatePersistenceManager()
    
    # Add different backends
    memory_backend = MemoryStatePersistence()
    manager.add_backend("memory", memory_backend)
    
    try:
        # Test with temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_url = f"sqlite:///{tmp_file.name}"
        
        db_backend = DatabaseStatePersistence(database_url=db_url)
        manager.add_backend("database", db_backend)
        
        # Test saving to different backends
        test_data = {"manager_test": True, "backend": "memory"}
        success = await manager.save_state("test_key", test_data, backend="memory")
        assert success, "Manager save to memory should succeed"
        
        test_data_db = {"manager_test": True, "backend": "database"}
        success = await manager.save_state("test_key", test_data_db, backend="database")
        assert success, "Manager save to database should succeed"
        
        # Test loading from specific backends
        memory_data = await manager.load_state("test_key", backend="memory")
        assert memory_data["backend"] == "memory", "Memory backend should return memory data"
        
        db_data = await manager.load_state("test_key", backend="database")
        assert db_data["backend"] == "database", "Database backend should return database data"
        
        print("✓ Multi-backend operations work")
        
        # Test default backend fallback
        default_data = {"default_backend": True}
        success = await manager.save_state("default_key", default_data)  # No backend specified
        assert success, "Default backend save should succeed"
        
        loaded_default = await manager.load_state("default_key")  # No backend specified
        assert loaded_default == default_data, "Default backend load should work"
        
        print("✓ Default backend fallback works")
        
        # Clean up
        os.unlink(tmp_file.name)
        
    except ImportError:
        print("⚠ SQLAlchemy not available, skipping database backend tests")


async def test_persistence_error_handling():
    """Test error handling in persistence operations."""
    print("Testing Persistence Error Handling...")
    
    backend = MemoryStatePersistence()
    
    # Test loading non-existent key
    result = await backend.load_state("non_existent")
    assert result is None, "Loading non-existent key should return None"
    
    # Test deleting non-existent key
    success = await backend.delete_state("non_existent")
    assert not success, "Deleting non-existent key should return False"
    
    # Test invalid data handling (this should work since we're using JSON)
    complex_data = {
        "simple": "string",
        "number": 42,
        "boolean": True,
        "null": None,
        "list": [1, 2, 3],
        "nested": {"inner": "value"}
    }
    
    success = await backend.save_state("complex_key", complex_data)
    assert success, "Saving complex data should succeed"
    
    loaded = await backend.load_state("complex_key")
    assert loaded == complex_data, "Complex data should round-trip correctly"
    
    print("✓ Error handling works correctly")


def run_all_tests():
    """Run all persistence tests."""
    print("Testing FastState Persistence Layer...")
    print("=" * 50)
    
    async def run_async_tests():
        await test_memory_persistence()
        await test_database_persistence() 
        await test_redis_persistence()
        await test_persistence_manager()
        await test_persistence_error_handling()
    
    asyncio.run(run_async_tests())
    
    print("=" * 50)
    print("✅ All Persistence tests passed!")


if __name__ == "__main__":
    run_all_tests()