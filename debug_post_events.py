#!/usr/bin/env python3
"""
Debug script to examine event metadata for POST vs GET methods.
This will help identify why POST routes aren't being registered correctly.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.pages.counter import CounterEntity

def debug_event_info():
    """Debug the event metadata for different methods."""
    
    print("=== DEBUG: Event Metadata Analysis ===\n")
    
    # Get the CounterEntity class
    counter_class = CounterEntity
    
    print(f"CounterEntity class: {counter_class}")
    print(f"CounterEntity MRO: {counter_class.__mro__}")
    print()
    
    # Check if _event_info exists
    if hasattr(counter_class, '_event_info'):
        print(f"_event_info found: {counter_class._event_info}")
        print(f"_event_info type: {type(counter_class._event_info)}")
        print()
    else:
        print("❌ _event_info not found on CounterEntity")
        print()
    
    # Check individual methods
    methods_to_check = ['increment', 'decrement', 'reset']
    
    for method_name in methods_to_check:
        print(f"--- Checking method: {method_name} ---")
        
        if hasattr(counter_class, method_name):
            method = getattr(counter_class, method_name)
            print(f"Method found: {method}")
            print(f"Method type: {type(method)}")
            
            # Check for event metadata on the method itself
            if hasattr(method, '_event_info'):
                print(f"Method _event_info: {method._event_info}")
            else:
                print("❌ No _event_info on method")
                
            # Check for other event-related attributes
            for attr in ['_event_method', '_event_path', '_event_selector']:
                if hasattr(method, attr):
                    print(f"Method {attr}: {getattr(method, attr)}")
                    
            print()
        else:
            print(f"❌ Method {method_name} not found")
            print()
    
    # Check the class-level _event_info in detail
    if hasattr(counter_class, '_event_info'):
        event_info = counter_class._event_info
        print("=== DETAILED _event_info ANALYSIS ===")
        
        for method_name, info in event_info.items():
            print(f"\n{method_name}:")
            print(f"  Full info: {info}")
            if isinstance(info, dict):
                for key, value in info.items():
                    print(f"    {key}: {value}")
            print()
    
    # Test method signature analysis
    print("=== METHOD SIGNATURE ANALYSIS ===")
    
    for method_name in methods_to_check:
        if hasattr(counter_class, method_name):
            method = getattr(counter_class, method_name)
            print(f"\n{method_name} signature analysis:")
            print(f"  Method: {method}")
            print(f"  __name__: {getattr(method, '__name__', 'NO NAME')}")
            print(f"  __doc__: {getattr(method, '__doc__', 'NO DOC')}")
            
            # Check if it's a coroutine
            import asyncio
            print(f"  Is coroutine: {asyncio.iscoroutinefunction(method)}")
            
            # Check annotations
            if hasattr(method, '__annotations__'):
                print(f"  Annotations: {method.__annotations__}")
            
            # Check parameters
            import inspect
            try:
                sig = inspect.signature(method)
                print(f"  Parameters: {list(sig.parameters.keys())}")
                for param_name, param in sig.parameters.items():
                    print(f"    {param_name}: {param}")
            except Exception as e:
                print(f"  Error getting signature: {e}")

if __name__ == "__main__":
    debug_event_info()