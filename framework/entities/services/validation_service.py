"""
Validation Service - Entity Validation Operations

✅ Clean Validation Interface:
This service handles entity validation through dependency injection,
providing flexible validation strategies without coupling entities to specific validation libraries.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Callable, TYPE_CHECKING
import inspect

if TYPE_CHECKING:
    from ..lifecycle.entity import Entity


class ValidationError(Exception):
    """Raised when entity validation fails"""
    
    def __init__(self, message: str, field: str = None, errors: Dict[str, List[str]] = None):
        super().__init__(message)
        self.field = field
        self.errors = errors or {}


class ValidationService(ABC):
    """
    Abstract interface for entity validation.
    
    This service is injected into entities to handle validation concerns,
    keeping business logic separate from validation implementation details.
    """
    
    @abstractmethod
    def validate_entity(self, entity: 'Entity') -> bool:
        """Validate an entire entity"""
        pass
    
    @abstractmethod
    def validate_field(self, entity: 'Entity', field_name: str, value: Any) -> bool:
        """Validate a specific field"""
        pass
    
    @abstractmethod
    def get_validation_errors(self, entity: 'Entity') -> Dict[str, List[str]]:
        """Get all validation errors for an entity"""
        pass
    
    @abstractmethod
    def add_validator(self, entity_class: Type['Entity'], field_name: str, validator: Callable):
        """Add a custom validator for a field"""
        pass
    
    @abstractmethod
    def setup_entity_validation(self, entity_class: Type['Entity']):
        """Set up validation for an entity class"""
        pass


class EntityValidationService(ValidationService):
    """
    Default implementation of validation service with comprehensive validation capabilities.
    
    This service provides field-level and entity-level validation with custom validator support.
    """
    
    def __init__(self):
        self._custom_validators: Dict[Type, Dict[str, List[Callable]]] = {}
        self._validation_cache: Dict[str, Any] = {}
    
    def validate_entity(self, entity: 'Entity') -> bool:
        """Validate an entire entity"""
        errors = self.get_validation_errors(entity)
        
        if errors:
            error_messages = []
            for field, field_errors in errors.items():
                error_messages.extend([f"{field}: {error}" for error in field_errors])
            
            raise ValidationError(
                f"Entity validation failed: {', '.join(error_messages)}",
                errors=errors
            )
        
        return True
    
    def validate_field(self, entity: 'Entity', field_name: str, value: Any) -> bool:
        """Validate a specific field"""
        errors = []
        
        # Get field info from model if available
        if hasattr(entity.__class__, 'model_fields'):
            field_info = entity.__class__.model_fields.get(field_name)
            if field_info:
                # Basic type validation
                if hasattr(field_info, 'annotation'):
                    expected_type = field_info.annotation
                    if not self._check_type(value, expected_type):
                        errors.append(f"Expected {expected_type}, got {type(value)}")
        
        # Run custom validators
        entity_class = type(entity)
        if entity_class in self._custom_validators:
            if field_name in self._custom_validators[entity_class]:
                for validator in self._custom_validators[entity_class][field_name]:
                    try:
                        if not validator(value):
                            errors.append(f"Custom validation failed for {field_name}")
                    except Exception as e:
                        errors.append(f"Validation error: {str(e)}")
        
        if errors:
            raise ValidationError(
                f"Field validation failed for {field_name}: {', '.join(errors)}",
                field=field_name,
                errors={field_name: errors}
            )
        
        return True
    
    def get_validation_errors(self, entity: 'Entity') -> Dict[str, List[str]]:
        """Get all validation errors for an entity"""
        errors = {}
        
        # Validate all fields
        if hasattr(entity.__class__, 'model_fields'):
            for field_name in entity.__class__.model_fields:
                try:
                    value = getattr(entity, field_name, None)
                    self.validate_field(entity, field_name, value)
                except ValidationError as e:
                    if e.errors:
                        errors.update(e.errors)
                    else:
                        errors[field_name] = [str(e)]
        
        # Run entity-level validators
        entity_class = type(entity)
        if entity_class in self._custom_validators:
            if '__entity__' in self._custom_validators[entity_class]:
                for validator in self._custom_validators[entity_class]['__entity__']:
                    try:
                        if not validator(entity):
                            errors.setdefault('__entity__', []).append("Entity-level validation failed")
                    except Exception as e:
                        errors.setdefault('__entity__', []).append(f"Validation error: {str(e)}")
        
        return errors
    
    def add_validator(self, entity_class: Type['Entity'], field_name: str, validator: Callable):
        """Add a custom validator for a field"""
        if entity_class not in self._custom_validators:
            self._custom_validators[entity_class] = {}
        
        if field_name not in self._custom_validators[entity_class]:
            self._custom_validators[entity_class][field_name] = []
        
        self._custom_validators[entity_class][field_name].append(validator)
    
    def add_entity_validator(self, entity_class: Type['Entity'], validator: Callable):
        """Add a validator for the entire entity"""
        self.add_validator(entity_class, '__entity__', validator)
    
    def setup_entity_validation(self, entity_class: Type['Entity']):
        """Set up validation for an entity class"""
        # For now, validation is set up through add_validator
        # In the future, this could analyze decorators or annotations
        pass
    
    def _check_type(self, value: Any, expected_type: Type) -> bool:
        """Check if value matches expected type"""
        try:
            # Handle Optional types
            if hasattr(expected_type, '__origin__'):
                if expected_type.__origin__ is type(None):
                    return value is None
                elif expected_type.__origin__ is type(Union):
                    # Handle Union types (like Optional)
                    args = getattr(expected_type, '__args__', ())
                    return any(isinstance(value, arg) for arg in args if arg is not type(None))
            
            # Basic type check
            return isinstance(value, expected_type)
        except:
            # If type checking fails, assume it's valid
            return True


class SimpleValidationService(ValidationService):
    """
    Simple validation service for testing and minimal deployments.
    
    This implementation provides basic validation without complex type checking
    or custom validator support.
    """
    
    def validate_entity(self, entity: 'Entity') -> bool:
        """Simple entity validation"""
        # Check required fields if using Pydantic
        if hasattr(entity, 'model_validate'):
            try:
                # Pydantic validation
                if hasattr(entity, 'model_dump'):
                    data = entity.model_dump()
                    entity.__class__.model_validate(data)
                return True
            except Exception as e:
                raise ValidationError(f"Entity validation failed: {str(e)}")
        
        return True
    
    def validate_field(self, entity: 'Entity', field_name: str, value: Any) -> bool:
        """Simple field validation"""
        # Basic checks
        if value is None:
            # Check if field is required
            if hasattr(entity.__class__, 'model_fields'):
                field_info = entity.__class__.model_fields.get(field_name)
                if field_info and hasattr(field_info, 'is_required') and field_info.is_required():
                    raise ValidationError(f"Field {field_name} is required")
        
        return True
    
    def get_validation_errors(self, entity: 'Entity') -> Dict[str, List[str]]:
        """Get validation errors"""
        try:
            self.validate_entity(entity)
            return {}
        except ValidationError as e:
            if e.errors:
                return e.errors
            else:
                return {'__entity__': [str(e)]}
    
    def add_validator(self, entity_class: Type['Entity'], field_name: str, validator: Callable):
        """Add validator (not implemented in simple version)"""
        pass
    
    def setup_entity_validation(self, entity_class: Type['Entity']):
        """Simple validation setup"""
        pass


# Validation decorators and helpers
def validator(field_name: str):
    """Decorator to mark a method as a field validator"""
    def decorator(func):
        func._is_validator = True
        func._validates_field = field_name
        return func
    return decorator


def entity_validator(func):
    """Decorator to mark a method as an entity-level validator"""
    func._is_entity_validator = True
    return func


# Export main components
__all__ = [
    "ValidationService", "EntityValidationService", "SimpleValidationService",
    "ValidationError", "validator", "entity_validator"
]