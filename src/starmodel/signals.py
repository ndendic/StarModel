
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

class SignalModelMeta(ModelMetaclass):
    def __init__(cls, name, bases, ns, **kw):
        super().__init__(name, bases, ns, **kw)

        # For each declared field, replace the stub Pydantic left in the
        # class __dict__ with our custom descriptor
        for field_name in cls.model_fields:
            setattr(cls, f"{field_name}_signal", SignalDescriptor(field_name))
        for field_name in cls.model_computed_fields:
            setattr(cls, f"{field_name}_signal", SignalDescriptor(field_name))

