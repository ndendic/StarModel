#!/usr/bin/env python3
"""
Test that the counter page async generators work correctly after the FastHTML integration improvements.
"""

from fasthtml.common import *
from app.pages.counter import CounterState

def test_counter_state_rendering():
    """Test that CounterState renders correctly (not as generator object)."""
    print("Testing CounterState rendering...")
    
    # Create a counter state instance
    counter = CounterState()
    
    # Test __ft__ method returns proper content
    result = counter.__ft__()
    print(f"__ft__ result type: {type(result)}")
    print(f"__ft__ result: {result}")
    
    # Should be a tuple with a div, not a generator
    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    assert len(result) > 0, "Result should not be empty"
    
    # Convert to XML to see the actual output
    xml_output = to_xml(result)
    print(f"XML output preview: {xml_output[:200]}...")
    
    # Should contain data-signals, not generator object string
    assert "data-signals" in xml_output, "Should contain data-signals"
    assert "<generator object" not in xml_output, "Should not contain generator object strings"
    assert "CounterState" in xml_output, "Should contain class name in output"
    
    print("✅ CounterState renders correctly!")

def test_counter_async_methods():
    """Test that async generator methods work correctly."""
    print("\nTesting CounterState async methods...")
    
    # Test original methods are preserved
    assert hasattr(CounterState, '_original_methods'), "Should have original methods"
    
    orig_increment = CounterState._original_methods.get('increment')
    assert orig_increment is not None, "Should have original increment method"
    
    print(f"Original increment method: {orig_increment}")
    print(f"Is coroutine function: {inspect.iscoroutinefunction(orig_increment)}")
    
    # Test URL generator works
    url = CounterState.increment(5, "TestUser")
    print(f"URL generator: {url}")
    assert "amount=5" in url
    assert "user=TestUser" in url
    
    print("✅ CounterState async methods work correctly!")

def test_fasthtml_parameter_injection():
    """Test that the improved parameter injection would work."""
    print("\nTesting FastHTML parameter injection compatibility...")
    
    # Get the original increment method
    orig_increment = CounterState._original_methods.get('increment')
    sig = inspect.signature(orig_increment)
    params = list(sig.parameters.keys())
    
    print(f"increment method parameters: {params}")
    
    # Should have self, amount, user parameters
    assert 'self' in params
    assert 'amount' in params  
    assert 'user' in params
    
    # This demonstrates the method signature is preserved for FastHTML processing
    print("✅ Method signatures compatible with FastHTML parameter injection!")

def main():
    """Run all tests."""
    print("🧪 Testing Counter Page Fix")
    print("=" * 40)
    
    test_counter_state_rendering()
    test_counter_async_methods()
    test_fasthtml_parameter_injection()
    
    print("\n🎉 All counter page tests passed!")
    print("\nKey fixes verified:")
    print("✅ CounterState.__ft__() returns proper content (not generator)")
    print("✅ Async generator methods are preserved for route handlers")
    print("✅ URL generators work correctly for async methods")
    print("✅ Method signatures are preserved for FastHTML parameter injection")
    print("✅ Counter page should now render objects correctly instead of generator strings")

if __name__ == "__main__":
    import inspect
    main()