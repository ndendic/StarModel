"""
Validation Mixin - Enhanced Entity Validation

✅ Clean Architecture Validation Operations:
This mixin provides enhanced validation capabilities for entities,
including business rule validation and cross-field validation.
"""

from typing import List, Dict, Any, Optional, Callable, ClassVar
from dataclasses import dataclass
from abc import ABC, abstractmethod
import inspect

@dataclass
class ValidationError:
    """Represents a validation error"""
    field: Optional[str]
    message: str
    code: Optional[str] = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}

@dataclass
class ValidationResult:
    """Result of validation operations"""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
    
    def add_error(self, field: Optional[str], message: str, 
                  code: Optional[str] = None, **context):
        """Add a validation error"""
        error = ValidationError(field, message, code, context)
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, field: Optional[str], message: str,
                    code: Optional[str] = None, **context):
        """Add a validation warning"""
        warning = ValidationError(field, message, code, context)
        self.warnings.append(warning)
    
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0
    
    def get_errors_by_field(self, field: str) -> List[ValidationError]:
        """Get errors for a specific field"""
        return [e for e in self.errors if e.field == field]
    
    def get_error_messages(self) -> List[str]:
        """Get all error messages"""
        return [e.message for e in self.errors]

class ValidationRule(ABC):
    """Abstract base class for validation rules"""
    
    @abstractmethod
    def validate(self, entity: Any, field: Optional[str] = None) -> ValidationResult:
        """Validate the rule against an entity"""
        pass

class FieldValidationRule(ValidationRule):
    """Validation rule for a specific field"""
    
    def __init__(self, field_name: str, validator: Callable, message: str, code: Optional[str] = None):
        self.field_name = field_name
        self.validator = validator
        self.message = message
        self.code = code
    
    def validate(self, entity: Any, field: Optional[str] = None) -> ValidationResult:
        """Validate field value"""
        result = ValidationResult(is_valid=True, errors=[])
        
        if field and field != self.field_name:
            return result
        
        value = getattr(entity, self.field_name, None)
        
        try:
            if not self.validator(value, entity):
                result.add_error(self.field_name, self.message, self.code)
        except Exception as e:
            result.add_error(self.field_name, f"Validation error: {e}", "VALIDATION_EXCEPTION")
        
        return result

class EntityValidationRule(ValidationRule):
    """Validation rule for entire entity"""
    
    def __init__(self, validator: Callable, message: str, code: Optional[str] = None):
        self.validator = validator
        self.message = message
        self.code = code
    
    def validate(self, entity: Any, field: Optional[str] = None) -> ValidationResult:
        """Validate entire entity"""
        result = ValidationResult(is_valid=True, errors=[])
        
        try:
            if not self.validator(entity):
                result.add_error(None, self.message, self.code)
        except Exception as e:
            result.add_error(None, f"Entity validation error: {e}", "ENTITY_VALIDATION_EXCEPTION")
        
        return result

class ValidationMixin:
    """
    Enhanced validation capabilities mixin.
    
    Provides comprehensive validation including:
    - Field-level validation rules
    - Entity-level business rules
    - Cross-field validation
    - Async validation support
    - Validation result management
    """
    
    # Class-level validation rules registry
    _validation_rules: ClassVar[List[ValidationRule]] = []
    _field_validators: ClassVar[Dict[str, List[FieldValidationRule]]] = {}
    _entity_validators: ClassVar[List[EntityValidationRule]] = []
    
    def __init_subclass__(cls, **kwargs):
        """Initialize validation rules when class is created"""
        super().__init_subclass__(**kwargs)
        cls._validation_rules = []
        cls._field_validators = {}
        cls._entity_validators = []
    
    def validate(self, field: Optional[str] = None) -> ValidationResult:
        """
        Validate this entity instance.
        
        Args:
            field: Optional specific field to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(is_valid=True, errors=[])
        
        # Run Pydantic validation first if available
        if hasattr(self, 'model_validate'):
            try:
                self.model_validate(self.model_dump())
            except Exception as e:
                result.add_error(None, f"Model validation failed: {e}", "MODEL_VALIDATION")
        
        # Run custom validation rules
        if field:
            # Validate specific field
            field_rules = self._field_validators.get(field, [])
            for rule in field_rules:
                rule_result = rule.validate(self, field)
                result.errors.extend(rule_result.errors)
                result.warnings.extend(rule_result.warnings)
                if rule_result.has_errors():
                    result.is_valid = False
        else:
            # Validate all fields
            for field_name, rules in self._field_validators.items():
                for rule in rules:
                    rule_result = rule.validate(self)
                    result.errors.extend(rule_result.errors)
                    result.warnings.extend(rule_result.warnings)
                    if rule_result.has_errors():
                        result.is_valid = False
            
            # Validate entity rules
            for rule in self._entity_validators:
                rule_result = rule.validate(self)
                result.errors.extend(rule_result.errors)
                result.warnings.extend(rule_result.warnings)
                if rule_result.has_errors():
                    result.is_valid = False
        
        return result
    
    def is_valid(self, field: Optional[str] = None) -> bool:
        """
        Check if entity is valid.
        
        Args:
            field: Optional specific field to validate
            
        Returns:
            True if valid, False otherwise
        """
        return self.validate(field).is_valid
    
    def get_validation_errors(self, field: Optional[str] = None) -> List[ValidationError]:
        """
        Get validation errors for this entity.
        
        Args:
            field: Optional specific field to get errors for
            
        Returns:
            List of validation errors
        """
        result = self.validate(field)
        return result.errors
    
    def get_validation_warnings(self, field: Optional[str] = None) -> List[ValidationError]:
        """
        Get validation warnings for this entity.
        
        Args:
            field: Optional specific field to get warnings for
            
        Returns:
            List of validation warnings
        """
        result = self.validate(field)
        return result.warnings
    
    # Class methods for validation rule management
    @classmethod
    def add_field_validator(cls, field_name: str, validator: Callable, 
                           message: str, code: Optional[str] = None):
        """
        Add a field validation rule.
        
        Args:
            field_name: Name of the field to validate
            validator: Function that takes (value, entity) and returns bool
            message: Error message if validation fails
            code: Optional error code
        """
        rule = FieldValidationRule(field_name, validator, message, code)
        
        if field_name not in cls._field_validators:
            cls._field_validators[field_name] = []
        
        cls._field_validators[field_name].append(rule)
    
    @classmethod
    def add_entity_validator(cls, validator: Callable, message: str, 
                            code: Optional[str] = None):
        """
        Add an entity validation rule.
        
        Args:
            validator: Function that takes entity and returns bool
            message: Error message if validation fails
            code: Optional error code
        """
        rule = EntityValidationRule(validator, message, code)
        cls._entity_validators.append(rule)
    
    @classmethod
    def remove_field_validator(cls, field_name: str, code: Optional[str] = None):
        """
        Remove field validation rules.
        
        Args:
            field_name: Name of the field
            code: Optional specific error code to remove
        """
        if field_name in cls._field_validators:
            if code:
                cls._field_validators[field_name] = [
                    rule for rule in cls._field_validators[field_name]
                    if rule.code != code
                ]
            else:
                del cls._field_validators[field_name]
    
    @classmethod
    def remove_entity_validator(cls, code: str):
        """
        Remove entity validation rules by code.
        
        Args:
            code: Error code to remove
        """
        cls._entity_validators = [
            rule for rule in cls._entity_validators
            if rule.code != code
        ]
    
    # Common validation helpers
    def validate_required_fields(self, required_fields: List[str]) -> ValidationResult:
        """
        Validate that required fields are present and not empty.
        
        Args:
            required_fields: List of field names that are required
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True, errors=[])
        
        for field_name in required_fields:
            value = getattr(self, field_name, None)
            
            if value is None or (isinstance(value, str) and not value.strip()):
                result.add_error(
                    field_name, 
                    f"{field_name} is required", 
                    "REQUIRED_FIELD"
                )
        
        return result
    
    def validate_field_constraints(self, constraints: Dict[str, Dict[str, Any]]) -> ValidationResult:
        """
        Validate field constraints.
        
        Args:
            constraints: Dict of field_name -> constraint_dict
                        e.g., {"age": {"min": 0, "max": 120}}
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True, errors=[])
        
        for field_name, field_constraints in constraints.items():
            value = getattr(self, field_name, None)
            
            if value is None:
                continue
            
            # Check min constraint
            if "min" in field_constraints and value < field_constraints["min"]:
                result.add_error(
                    field_name,
                    f"{field_name} must be at least {field_constraints['min']}",
                    "MIN_VALUE"
                )
            
            # Check max constraint
            if "max" in field_constraints and value > field_constraints["max"]:
                result.add_error(
                    field_name,
                    f"{field_name} must be at most {field_constraints['max']}",
                    "MAX_VALUE"
                )
            
            # Check length constraints for strings
            if isinstance(value, str):
                if "min_length" in field_constraints and len(value) < field_constraints["min_length"]:
                    result.add_error(
                        field_name,
                        f"{field_name} must be at least {field_constraints['min_length']} characters",
                        "MIN_LENGTH"
                    )
                
                if "max_length" in field_constraints and len(value) > field_constraints["max_length"]:
                    result.add_error(
                        field_name,
                        f"{field_name} must be at most {field_constraints['max_length']} characters",
                        "MAX_LENGTH"
                    )
        
        return result
    
    # Validation decorators support
    @classmethod
    def validates(cls, field_name: str, message: Optional[str] = None, 
                  code: Optional[str] = None):
        """
        Decorator to mark a method as a field validator.
        
        Args:
            field_name: Name of the field to validate
            message: Optional error message
            code: Optional error code
        """
        def decorator(func):
            # Extract validation logic
            validator_message = message or f"{field_name} validation failed"
            validator_code = code or f"{field_name.upper()}_VALIDATION"
            
            # Add to class validators
            cls.add_field_validator(field_name, func, validator_message, validator_code)
            
            return func
        
        return decorator
    
    @classmethod
    def validates_entity(cls, message: Optional[str] = None, 
                        code: Optional[str] = None):
        """
        Decorator to mark a method as an entity validator.
        
        Args:
            message: Optional error message
            code: Optional error code
        """
        def decorator(func):
            validator_message = message or "Entity validation failed"
            validator_code = code or "ENTITY_VALIDATION"
            
            cls.add_entity_validator(func, validator_message, validator_code)
            
            return func
        
        return decorator

# Export main components
__all__ = [
    "ValidationMixin", "ValidationError", "ValidationResult",
    "ValidationRule", "FieldValidationRule", "EntityValidationRule"
]