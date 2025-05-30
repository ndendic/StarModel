#!/usr/bin/env python3
"""
Test for the Authentication System (Issue #2)

This test verifies that the authentication and authorization decorators work correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from faststate.auth import (
    requires_auth, AuthenticationError, AuthorizationError,
    set_current_auth, set_user_permissions, set_user_roles, set_user_id,
    clear_auth_context, has_permission, has_role, is_authenticated
)
from faststate.state import ReactiveState


class TestState(ReactiveState):
    name: str = "test"
    user_id: str = ""
    
    @requires_auth()
    def authenticated_method(self):
        return "success"
    
    @requires_auth(permissions=['admin'])
    def admin_method(self):
        return "admin_success"
    
    @requires_auth(roles=['manager'])
    def manager_method(self):
        return "manager_success"
    
    @requires_auth(owner_only=True)
    def owner_method(self):
        return "owner_success"
    
    @requires_auth(permissions=['edit'], owner_only=True)
    def combined_method(self):
        return "combined_success"


def test_authentication_required():
    """Test that authentication is required when specified."""
    print("Testing authentication requirement...")
    
    state = TestState()
    
    # Clear auth context
    clear_auth_context()
    
    # Should fail without authentication
    try:
        state.authenticated_method()
        assert False, "Should have raised AuthenticationError"
    except AuthenticationError:
        print("✓ AuthenticationError raised correctly")
    
    # Should work with authentication
    set_current_auth("user123")
    result = state.authenticated_method()
    assert result == "success"
    print("✓ Method works with authentication")


def test_permission_checking():
    """Test permission-based authorization."""
    print("\nTesting permission checking...")
    
    state = TestState()
    
    # Set auth but no permissions
    set_current_auth("user123")
    set_user_permissions([])
    
    # Should fail without required permission
    try:
        state.admin_method()
        assert False, "Should have raised AuthorizationError"
    except AuthorizationError:
        print("✓ AuthorizationError raised for missing permission")
    
    # Should work with required permission
    set_user_permissions(['admin'])
    result = state.admin_method()
    assert result == "admin_success"
    print("✓ Method works with required permission")


def test_role_checking():
    """Test role-based authorization."""
    print("\nTesting role checking...")
    
    state = TestState()
    
    # Set auth but no roles
    set_current_auth("user123")
    set_user_roles([])
    
    # Should fail without required role
    try:
        state.manager_method()
        assert False, "Should have raised AuthorizationError"
    except AuthorizationError:
        print("✓ AuthorizationError raised for missing role")
    
    # Should work with required role
    set_user_roles(['manager'])
    result = state.manager_method()
    assert result == "manager_success"
    print("✓ Method works with required role")


def test_owner_only():
    """Test owner-only access control."""
    print("\nTesting owner-only access...")
    
    state = TestState()
    state.user_id = "user456"  # Set owner
    
    # Set different user
    set_current_auth("user123")
    set_user_id("user123")
    
    # Should fail for non-owner
    try:
        state.owner_method()
        assert False, "Should have raised AuthorizationError"
    except AuthorizationError:
        print("✓ AuthorizationError raised for non-owner")
    
    # Should work for owner
    set_user_id("user456")
    result = state.owner_method()
    assert result == "owner_success"
    print("✓ Method works for owner")


def test_combined_requirements():
    """Test combined permission and owner requirements."""
    print("\nTesting combined requirements...")
    
    state = TestState()
    state.user_id = "user123"
    
    set_current_auth("user123")
    set_user_id("user123")
    set_user_permissions([])
    
    # Should fail without permission even if owner
    try:
        state.combined_method()
        assert False, "Should have raised AuthorizationError"
    except AuthorizationError:
        print("✓ AuthorizationError raised for missing permission")
    
    # Should work with both permission and ownership
    set_user_permissions(['edit'])
    result = state.combined_method()
    assert result == "combined_success"
    print("✓ Method works with combined requirements")


def test_utility_functions():
    """Test utility functions."""
    print("\nTesting utility functions...")
    
    clear_auth_context()
    
    # Test unauthenticated state
    assert not is_authenticated()
    assert not has_permission('test')
    assert not has_role('test')
    print("✓ Utility functions work for unauthenticated state")
    
    # Test authenticated state
    set_current_auth("user123")
    set_user_permissions(['read', 'write'])
    set_user_roles(['user', 'editor'])
    
    assert is_authenticated()
    assert has_permission('read')
    assert has_permission('write')
    assert not has_permission('admin')
    assert has_role('user')
    assert has_role('editor')
    assert not has_role('admin')
    print("✓ Utility functions work for authenticated state")


if __name__ == "__main__":
    print("Testing FastState Authentication System...")
    
    test_authentication_required()
    test_permission_checking()
    test_role_checking()
    test_owner_only()
    test_combined_requirements()
    test_utility_functions()
    
    print("\n🎉 All authentication tests passed!")
    print("Issue #2 implementation is working correctly.")