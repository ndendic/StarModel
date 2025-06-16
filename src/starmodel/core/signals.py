from pydantic._internal._model_construction import ModelMetaclass


class SignalDescriptor:
    """Return `$Model.field` on the class, real value on an instance."""

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name

    def __get__(self, instance, owner):
        #  class access  →  owner is the model class, instance is None
        if instance is None:
            config = getattr(owner, "model_config", {})
            ns = config.get("namespace", owner.__name__)
            use_ns = config.get("use_namespace", False)
            return f"${ns}.{self.field_name}" if use_ns else f"${self.field_name}"

        #  instance access  →  behave like a normal attribute
        return instance.__dict__[self.field_name]

class EventMethodDescriptor:
    """Generate URL strings for @event methods to use with Datastar, but allow direct execution."""
    
    def __init__(self, method_name: str, entity_class_name: str, original_method):
        self.method_name = method_name
        self.entity_class_name = entity_class_name
        self.original_method = original_method
        # Preserve the original event info
        self._event_info = getattr(original_method, '_event_info', None)
    
    def __get__(self, instance, owner):
        """Handle descriptor access - return bound method for instances, self for class access."""
        if instance is None:
            # Accessed on class - return self for URL generation
            return self
        else:
            # Accessed on instance - return bound method for execution
            import functools
            return functools.partial(self.original_method, instance)
    
    def __call__(self, *args, **kwargs):
        """Generate URL strings for Datastar OR execute the original method."""
        # If called with an entity instance as first argument, execute original method
        # Check if first argument is an instance of the entity class
        if args and hasattr(args[0], 'id') and hasattr(args[0], '__class__') and args[0].__class__.__name__ == self.entity_class_name:
            return self.original_method(*args, **kwargs)
        
        # Otherwise, generate URL string for Datastar
        import urllib.parse
        import inspect
        
        # Get HTTP method from event info
        http_method = "get"  # default
        if self._event_info:
            http_method = self._event_info.method.lower()
        
        # Build the path
        path = f"/{self.entity_class_name.lower()}/{self.method_name}"
        
        # Build query parameters from args and kwargs
        params = {}
        
        # Get parameter names from method signature, filtering out FastHTML special params
        if self._event_info and self._event_info.signature:
            sig = self._event_info.signature
            param_names = []
            special_params = {'session', 'auth', 'request', 'htmx', 'scope', 'app', 'datastar'}
            
            for name, param in list(sig.parameters.items())[1:]:  # Skip 'self'
                # Skip FastHTML special parameters that get auto-injected
                if name.lower() not in special_params:
                    # Also skip if annotation indicates it's a special FastHTML type
                    anno = param.annotation
                    if anno != inspect.Parameter.empty:
                        if hasattr(anno, '__name__'):
                            if anno.__name__ in ('Request', 'HtmxHeaders', 'Starlette', 'DatastarPayload'):
                                continue
                    param_names.append(name)
            
            # Add positional arguments mapped to parameter names
            for i, arg in enumerate(args):
                if i < len(param_names):
                    params[param_names[i]] = arg
        
        # Add keyword arguments (filter out None values)
        params.update({k: v for k, v in kwargs.items() if v is not None})
        
        # Build query string
        if params:
            query_string = urllib.parse.urlencode(params, doseq=True)
            return f"@{http_method}('{path}?{query_string}')"
        else:
            return f"@{http_method}('{path}')"


class SignalModelMeta(ModelMetaclass):
    def __init__(cls, name, bases, ns, **kw):
        super().__init__(name, bases, ns, **kw)

        # For each declared field, replace the stub Pydantic left in the
        # class __dict__ with our custom descriptor
        for field_name in cls.model_fields:
            setattr(cls, f"{field_name}_signal", SignalDescriptor(field_name))
        for field_name in cls.model_computed_fields:
            setattr(cls, f"{field_name}_signal", SignalDescriptor(field_name))
        
        # Create URL generator methods for @event decorated methods
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, '_event_info'):
                # Create URL generator method that overrides the original method on the class
                url_generator = EventMethodDescriptor(attr_name, cls.__name__, attr)
                setattr(cls, attr_name, url_generator)
