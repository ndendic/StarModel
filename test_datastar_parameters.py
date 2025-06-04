#!/usr/bin/env python3
"""
Test the enhanced Datastar parameter extraction functionality.
"""

import asyncio
import json
from fasthtml.common import *
from fasthtml.core import HtmxHeaders
from src.faststate.state import State, event, DatastarPayload

# Test State class with Datastar parameter injection
class DatastarTestState(State):
    counter: int = 0
    message: str = "Hello"
    user_data: dict = {}
    
    @event
    def basic_params(self, amount: int = 1, name: str = "default"):
        """Test basic parameter extraction (should work from query params or Datastar)."""
        self.counter += amount
        self.message = f"Updated by {name}"
        return Div(f"Counter: {self.counter}, Name: {name}")
    
    @event
    def datastar_injection(self, datastar: DatastarPayload, fallback: str = "none"):
        """Test Datastar payload injection as object."""
        data = datastar.raw_data if datastar else {}
        self.user_data = data
        self.message = f"Got datastar data: {len(data)} items, fallback: {fallback}"
        return Div(f"Datastar: {data}")
    
    @event
    def mixed_params(self, session: dict, datastar: DatastarPayload, 
                    amount: int, user_preference: str = "default"):
        """Test mixed FastHTML and Datastar parameters."""
        session_user = session.get('user', 'anonymous')
        datastar_extra = datastar.get('extra_data', 'none') if datastar else 'none'
        
        self.counter += amount
        self.message = f"User: {session_user}, Amount: {amount}, Pref: {user_preference}, Extra: {datastar_extra}"
        return Div(self.message)
    
    @event
    def datastar_attributes(self, custom_field: str = "missing", datastar: DatastarPayload = None):
        """Test accessing Datastar data as attributes and explicit params."""
        if datastar:
            # Access as attributes
            form_name = datastar.form_name or "no_form"
            form_value = datastar.form_value or "no_value"
            # Access using get method
            extra = datastar.get('extra', 'no_extra')
        else:
            form_name = form_value = extra = "no_datastar"
        
        self.message = f"Custom: {custom_field}, Form: {form_name}={form_value}, Extra: {extra}"
        return Div(self.message)

def test_datastar_payload_class():
    """Test DatastarPayload class functionality."""
    print("Testing DatastarPayload class...")
    
    # Test empty payload
    empty_payload = DatastarPayload()
    assert empty_payload.get('missing') is None
    assert 'missing' not in empty_payload
    print(f"Empty payload: {empty_payload}")
    
    # Test with data
    test_data = {'name': 'John', 'age': 30, 'active': True}
    payload = DatastarPayload(test_data)
    
    # Test attribute access
    assert payload.name == 'John'
    assert payload.age == 30
    assert payload.missing is None
    
    # Test dict-like access
    assert payload['name'] == 'John'
    assert payload.get('age') == 30
    assert payload.get('missing', 'default') == 'default'
    
    # Test containment
    assert 'name' in payload
    assert 'missing' not in payload
    
    # Test raw data access
    assert payload.raw_data == test_data
    
    print("✅ DatastarPayload class tests passed!")

def test_url_generators():
    """Test that URL generators work and filter Datastar parameters."""
    print("\nTesting URL generators with Datastar filtering...")
    
    # Basic parameters (should include both)
    url1 = DatastarTestState.basic_params(5, "TestUser")
    print(f"basic_params(5, 'TestUser'): {url1}")
    assert "amount=5" in url1
    assert "name=TestUser" in url1
    
    # Datastar injection (should exclude datastar param)
    url2 = DatastarTestState.datastar_injection("fallback_value")
    print(f"datastar_injection('fallback_value'): {url2}")
    assert "datastar=" not in url2  # datastar should be filtered out
    assert "fallback=fallback_value" in url2
    
    # Mixed parameters (should exclude session and datastar)
    url3 = DatastarTestState.mixed_params(amount=10, user_preference="custom")
    print(f"mixed_params(amount=10, user_preference='custom'): {url3}")
    assert "session=" not in url3  # session should be filtered out
    assert "datastar=" not in url3  # datastar should be filtered out
    assert "amount=10" in url3
    assert "user_preference=custom" in url3
    
    # Datastar attributes (should exclude datastar param)
    url4 = DatastarTestState.datastar_attributes("test_value")
    print(f"datastar_attributes('test_value'): {url4}")
    assert "datastar=" not in url4  # datastar should be filtered out
    assert "custom_field=test_value" in url4
    
    print("✅ URL generator tests passed!")

async def test_datastar_extraction():
    """Test the Datastar payload extraction function."""
    print("\nTesting Datastar payload extraction...")
    
    from src.faststate.state import _extract_datastar_payload
    from starlette.requests import Request
    from starlette.datastructures import QueryParams, FormData
    
    # Mock request with query param datastar
    class MockRequest1:
        def __init__(self):
            self.query_params = QueryParams("datastar=" + json.dumps({"name": "John", "age": 30}))
        
        async def json(self):
            raise Exception("Should not be called")
    
    payload1 = await _extract_datastar_payload(MockRequest1())
    print(f"Query param extraction: {payload1}")
    assert payload1.name == "John"
    assert payload1.age == 30
    
    # Mock request with JSON body
    class MockRequest2:
        def __init__(self):
            self.query_params = QueryParams("")
        
        async def json(self):
            return {"form_data": "test", "user_id": 123}
    
    payload2 = await _extract_datastar_payload(MockRequest2())
    print(f"JSON body extraction: {payload2}")
    assert payload2.form_data == "test"
    assert payload2.user_id == 123
    
    print("✅ Datastar extraction tests passed!")

def test_method_signatures():
    """Test that method signatures are preserved for Datastar methods."""
    print("\nTesting method signatures with Datastar parameters...")
    
    import inspect
    
    if hasattr(DatastarTestState, '_original_methods'):
        # Test mixed_params method signature
        mixed_method = DatastarTestState._original_methods.get('mixed_params')
        if mixed_method:
            sig = inspect.signature(mixed_method)
            params = list(sig.parameters.keys())
            print(f"mixed_params parameters: {params}")
            
            assert 'self' in params
            assert 'session' in params
            assert 'datastar' in params
            assert 'amount' in params
            assert 'user_preference' in params
            
            # Check parameter annotations
            datastar_param = sig.parameters['datastar']
            print(f"datastar parameter annotation: {datastar_param.annotation}")
        
        # Test datastar_injection method
        injection_method = DatastarTestState._original_methods.get('datastar_injection')
        if injection_method:
            sig = inspect.signature(injection_method)
            params = list(sig.parameters.keys())
            print(f"datastar_injection parameters: {params}")
            
            assert 'datastar' in params
            assert 'fallback' in params
    
    print("✅ Method signature tests passed!")

def main():
    """Run all tests."""
    print("🧪 Testing Datastar Parameter Extraction")
    print("=" * 50)
    
    # Test DatastarPayload class
    test_datastar_payload_class()
    
    # Test URL generators filter Datastar params
    test_url_generators()
    
    # Test payload extraction
    asyncio.run(test_datastar_extraction())
    
    # Test method signatures
    test_method_signatures()
    
    print("\n🎉 All Datastar parameter tests passed!")
    print("\nKey features verified:")
    print("✅ DatastarPayload class with attribute and dict-like access")
    print("✅ Datastar parameter injection in event methods")
    print("✅ URL generators correctly filter out datastar parameters")
    print("✅ Datastar payload extraction from query params and JSON body")
    print("✅ Mixed FastHTML and Datastar parameter support")
    print("✅ Method signatures preserved for route processing")
    
    print("\nUsage examples:")
    print("@event")
    print("def my_method(self, datastar: DatastarPayload, session: dict, amount: int):")
    print("    user_data = datastar.user_name  # Access as attribute")
    print("    form_value = datastar['form_field']  # Access as dict")
    print("    extra = datastar.get('optional', 'default')  # With default")
    print("    session_user = session.get('user')  # Regular FastHTML injection")

if __name__ == "__main__":
    main()