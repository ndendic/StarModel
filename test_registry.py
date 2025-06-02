#!/usr/bin/env python3
"""
Simple test for the State Registry System (Issue #1)

This test verifies that the registry system works correctly with different scopes.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from faststate.registry import StateScope, StateConfig, FastStateRegistry
from faststate.state import State
from fasthtml.common import Request
from unittest.mock import Mock


class TestState(State):
    name: str = "test"
    count: int = 0


def test_state_registry():
    """Test basic state registry functionality."""
    registry = FastStateRegistry()
    
    # Test registration
    config = StateConfig(scope=StateScope.SESSION)
    registry.register(TestState, config)
    
    print("✓ State registration works")
    
    # Test is_state_type
    assert registry.is_state_type(TestState)
    assert not registry.is_state_type(str)
    
    print("✓ State type detection works")
    
    # Test state resolution
    mock_request = Mock(spec=Request)
    mock_request.query_params = {}
    mock_request.path_params = {}
    
    sess = {'session_id': 'test_session'}
    auth = None
    
    state1 = registry.resolve_state(TestState, mock_request, sess, auth)
    state2 = registry.resolve_state(TestState, mock_request, sess, auth)
    
    # Should be the same instance (cached)
    assert state1 is state2
    
    print("✓ State caching works")
    
    # Test different sessions get different instances
    sess2 = {'session_id': 'test_session_2'}
    state3 = registry.resolve_state(TestState, mock_request, sess2, auth)
    
    assert state1 is not state3
    
    print("✓ Session isolation works")


def test_state_scopes():
    """Test different state scopes."""
    registry = FastStateRegistry()
    
    # Global scope
    global_config = StateConfig(scope=StateScope.GLOBAL)
    registry.register(TestState, global_config)
    
    mock_request = Mock(spec=Request)
    mock_request.query_params = {}
    mock_request.path_params = {}
    
    # Different sessions should get same global instance
    sess1 = {'session_id': 'session1'}
    sess2 = {'session_id': 'session2'}
    
    state1 = registry.resolve_state(TestState, mock_request, sess1, None)
    state2 = registry.resolve_state(TestState, mock_request, sess2, None)
    
    assert state1 is state2
    
    print("✓ Global scope works")


def test_authentication_requirement():
    """Test authentication requirements."""
    registry = FastStateRegistry()
    
    # User scope requires auth
    user_config = StateConfig(scope=StateScope.USER, requires_auth=True)
    registry.register(TestState, user_config)
    
    mock_request = Mock(spec=Request)
    mock_request.query_params = {}
    mock_request.path_params = {}
    
    sess = {'session_id': 'test'}
    
    # Should fail without auth
    try:
        registry.resolve_state(TestState, mock_request, sess, None)
        assert False, "Should have raised PermissionError"
    except PermissionError:
        print("✓ Authentication requirement enforced")
    
    # Should work with auth
    state = registry.resolve_state(TestState, mock_request, sess, "user123")
    assert state is not None
    
    print("✓ Authentication works when provided")


if __name__ == "__main__":
    print("Testing FastState Registry System...")
    
    test_state_registry()
    test_state_scopes()
    test_authentication_requirement()
    
    print("\n🎉 All registry tests passed!")
    print("Issue #1 implementation is working correctly.")