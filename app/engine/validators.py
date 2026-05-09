"""
Schema validator with rule-based validation for extracted data.
Supports type validation, range checks, pattern matching, and custom business rules.
"""

import re
import json
from typing import List, Dict, Any, Optional, Union, Callable
from datetime import datetime
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationRule:
    """Validation rule definition."""
    field: str
    rule: str  # Python expression or function name
    message: Optional[str] = None
    severity: ValidationSeverity = ValidationSeverity.ERROR
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "field": self.field,
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity.value
        }


@dataclass
class ValidationResult:
    """Result of validation for a single field."""
    valid: bool
    field: str
    rule: str
    message: Optional[str] = None
    severity: ValidationSeverity = ValidationSeverity.ERROR
    actual_value: Any = None
    expected_value: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "field": self.field,
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity.value,
            "actual_value": str(self.actual_value) if self.actual_value is not None else None,
            "expected_value": str(self.expected_value) if self.expected_value is not None else None
        }


class SchemaValidator:
    """
    Validator for extracted data with support for:
    - Type validation (string, number, date, email, etc.)
    - Range validation (min/max)
    - Pattern validation (regex)
    - Custom business rules
    - Cross-field validation
    """
    
    # Built-in validation functions
    BUILTIN_VALIDATORS = {
        # Type validators
        "is_string": lambda x: isinstance(x, str),
        "is_number": lambda x: isinstance(x, (int, float, Decimal)) or (isinstance(x, str) and x.replace('.', '', 1).replace(',', '').isdigit()),
        "is_integer": lambda x: isinstance(x, int) or (isinstance(x, str) and x.replace(',', '').isdigit()),
        "is_float": lambda x: isinstance(x, float) or (isinstance(x, str) and self._is_float_string(x)),
        "is_boolean": lambda x: isinstance(x, bool) or str(x).lower() in ['true', 'false', 'yes', 'no', '1', '0'],
        "is_date": lambda x, fmt=None: self._is_date_string(x, fmt),
        "is_email": lambda x: isinstance(x, str) and re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', x),
        "is_url": lambda x: isinstance(x, str) and re.match(r'^https?://[^\s/$.?#].[^\s]*$', x),
        
        # Range validators
        "min": lambda x, min_val: self._as_number(x) >= min_val,
        "max": lambda x, max_val: self._as_number(x) <= max_val,
        "between": lambda x, min_val, max_val: min_val <= self._as_number(x) <= max_val,
        
        # Length validators (for strings, lists)
        "min_length": lambda x, length: len(str(x)) >= length,
        "max_length": lambda x, length: len(str(x)) <= length,
        "exact_length": lambda x, length: len(str(x)) == length,
        
        # Pattern validators
        "matches_pattern": lambda x, pattern: bool(re.match(pattern, str(x))),
        "contains": lambda x, substring: substring in str(x),
        "starts_with": lambda x, prefix: str(x).startswith(prefix),
        "ends_with": lambda x, suffix: str(x).endswith(suffix),
        
        # Business rule validators
        "required": lambda x: x is not None and str(x).strip() != '',
        "not_empty": lambda x: x is not None and str(x).strip() != '',
        "in_list": lambda x, *items: str(x) in items,
        "not_in_list": lambda x, *items: str(x) not in items,
        
        # Numeric validators
        "positive": lambda x: self._as_number(x) > 0,
        "negative": lambda x: self._as_number(x) < 0,
        "non_negative": lambda x: self._as_number(x) >= 0,
        "non_positive": lambda x: self._as_number(x) <= 0,
        
        # Date validators
        "after_date": lambda x, date_str, fmt=None: self._parse_date(x, fmt) > self._parse_date(date_str, fmt),
        "before_date": lambda x, date_str, fmt=None: self._parse_date(x, fmt) < self._parse_date(date_str, fmt),
        "between_dates": lambda x, start_str, end_str, fmt=None: self._parse_date(start_str, fmt) <= self._parse_date(x, fmt) <= self._parse_date(end_str, fmt),
    }
    
    def __init__(self):
        """Initialize validator with built-in functions."""
        # Rebuild validators with proper self-binding
        self.validators = {
            # Type validators
            "is_string": lambda x: isinstance(x, str),
            "is_number": lambda x: isinstance(x, (int, float, Decimal)) or (isinstance(x, str) and x.replace('.', '', 1).replace(',', '').isdigit()),
            "is_integer": lambda x: isinstance(x, int) or (isinstance(x, str) and x.replace(',', '').isdigit()),
            "is_float": lambda x: isinstance(x, float) or (isinstance(x, str) and self._is_float_string(x)),
            "is_boolean": lambda x: isinstance(x, bool) or str(x).lower() in ['true', 'false', 'yes', 'no', '1', '0'],
            "is_date": lambda x, fmt=None: self._is_date_string(x, fmt),
            "is_email": lambda x: isinstance(x, str) and re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', x),
            "is_url": lambda x: isinstance(x, str) and re.match(r'^https?://[^\s/$.?#].[^\s]*$', x),
            # Range validators
            "min": lambda x, min_val: self._as_number(x) >= min_val,
            "max": lambda x, max_val: self._as_number(x) <= max_val,
            "between": lambda x, min_val, max_val: min_val <= self._as_number(x) <= max_val,
            # Length validators
            "min_length": lambda x, length: len(str(x)) >= length,
            "max_length": lambda x, length: len(str(x)) <= length,
            "exact_length": lambda x, length: len(str(x)) == length,
            # Presence validators
            "required": lambda x: x is not None and (not isinstance(x, str) or x.strip() != ""),
            "not_empty": lambda x: x is not None and (not isinstance(x, str) or x.strip() != ""),
            "nullable": lambda x: True,
            # Pattern validators
            "pattern": lambda x, pattern: isinstance(x, str) and bool(re.search(pattern, x)),
            "email": lambda x: isinstance(x, str) and bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', x)),
            # Date validators
            "after_date": lambda x, date_str, fmt=None: self._parse_date(x, fmt) > self._parse_date(date_str, fmt),
            "before_date": lambda x, date_str, fmt=None: self._parse_date(x, fmt) < self._parse_date(date_str, fmt),
            "between_dates": lambda x, start_str, end_str, fmt=None: self._parse_date(start_str, fmt) <= self._parse_date(x, fmt) <= self._parse_date(end_str, fmt),
        }
        self.custom_validators: Dict[str, Callable] = {}
    
    def _as_number(self, value: Any) -> float:
        """Convert value to number for numeric validation."""
        if isinstance(value, (int, float, Decimal)):
            return float(value)
        
        if isinstance(value, str):
            # Remove commas and currency symbols
            clean = value.replace(',', '').replace('$', '').replace('€', '').replace('£', '')
            try:
                return float(clean)
            except ValueError:
                raise ValueError(f"Cannot convert '{value}' to number")
        
        raise ValueError(f"Cannot convert {type(value).__name__} to number")
    
    def _is_float_string(self, value: str) -> bool:
        """Check if string can be converted to float."""
        try:
            clean = value.replace(',', '').replace('$', '').replace('€', '').replace('£', '')
            float(clean)
            return True
        except ValueError:
            return False
    
    def _is_date_string(self, value: Any, fmt: Optional[str] = None) -> bool:
        """Check if string is a valid date."""
        if not isinstance(value, str):
            return False
        
        date_formats = [
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
            "%d-%m-%Y", "%m-%d-%Y",
            "%Y/%m/%d", "%d.%m.%Y", "%m.%d.%Y",
            "%b %d, %Y", "%d %b %Y", "%B %d, %Y", "%d %B %Y",
        ]
        
        if fmt:
            date_formats = [fmt] + date_formats
        
        for date_format in date_formats:
            try:
                datetime.strptime(value.strip(), date_format)
                return True
            except ValueError:
                continue
        
        return False
    
    def _parse_date(self, value: Any, fmt: Optional[str] = None) -> datetime:
        """Parse date string to datetime object."""
        if isinstance(value, datetime):
            return value
        
        if not isinstance(value, str):
            raise ValueError(f"Cannot parse date from {type(value).__name__}")
        
        date_formats = [
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
            "%d-%m-%Y", "%m-%d-%Y",
            "%Y/%m/%d", "%d.%m.%Y", "%m.%d.%Y",
            "%b %d, %Y", "%d %b %Y", "%B %d, %Y", "%d %B %Y",
        ]
        
        if fmt:
            date_formats = [fmt] + date_formats
        
        for date_format in date_formats:
            try:
                return datetime.strptime(value.strip(), date_format)
            except ValueError:
                continue
        
        raise ValueError(f"Cannot parse date: {value}")
    
    def register_custom_validator(self, name: str, validator: Callable) -> None:
        """Register a custom validation function."""
        self.custom_validators[name] = validator
        logger.info(f"Registered custom validator: {name}")
    
    def _parse_rule(self, rule_str: str) -> tuple[str, list]:
        """Parse rule string into function name and arguments."""
        # Remove whitespace and split
        rule_str = rule_str.strip()
        
        if '(' in rule_str and rule_str.endswith(')'):
            # Function call with arguments: func(arg1, arg2)
            func_name = rule_str[:rule_str.index('(')].strip()
            args_str = rule_str[rule_str.index('(')+1:-1]
            
            # Parse arguments (simple comma separation, no nested parentheses)
            args = []
            for arg in args_str.split(','):
                arg = arg.strip()
                if arg:
                    # Try to parse as number
                    if arg.replace('.', '', 1).replace('-', '', 1).isdigit():
                        if '.' in arg:
                            args.append(float(arg))
                        else:
                            args.append(int(arg))
                    elif arg.lower() in ['true', 'false']:
                        args.append(arg.lower() == 'true')
                    elif arg.startswith('"') and arg.endswith('"'):
                        args.append(arg[1:-1])
                    elif arg.startswith("'") and arg.endswith("'"):
                        args.append(arg[1:-1])
                    else:
                        args.append(arg)
            
            return func_name, args
        
        else:
            # Simple rule name without arguments
            return rule_str, []
    
    def validate_field(self, 
                      field_name: str, 
                      value: Any, 
                      rule: ValidationRule) -> ValidationResult:
        """
        Validate a single field against a rule.
        
        Args:
            field_name: Name of the field
            value: Field value to validate
            rule: Validation rule to apply
            
        Returns:
            ValidationResult indicating success/failure
        """
        try:
            # Parse rule string
            func_name, args = self._parse_rule(rule.rule)
            
            # Get validator function
            validator = self.custom_validators.get(func_name) or self.validators.get(func_name)
            if not validator:
                return ValidationResult(
                    valid=False,
                    field=field_name,
                    rule=rule.rule,
                    message=f"Unknown validation function: {func_name}",
                    severity=rule.severity,
                    actual_value=value
                )
            
            # Apply validator
            try:
                # Handle special case for required/not_empty
                if func_name in ['required', 'not_empty']:
                    is_valid = validator(value)
                else:
                    # Check if value is None or empty for non-required fields
                    if value is None or (isinstance(value, str) and not value.strip()):
                        return ValidationResult(
                            valid=True,  # Non-required fields pass validation when empty
                            field=field_name,
                            rule=rule.rule,
                            message=f"Field is empty, skipping validation",
                            severity=ValidationSeverity.INFO,
                            actual_value=value
                        )
                    
                    # Apply validator with arguments
                    is_valid = validator(value, *args)
                
                if not is_valid:
                    return ValidationResult(
                        valid=False,
                        field=field_name,
                        rule=rule.rule,
                        message=rule.message or f"Validation failed: {rule.rule}",
                        severity=rule.severity,
                        actual_value=value
                    )
                
                return ValidationResult(
                    valid=True,
                    field=field_name,
                    rule=rule.rule,
                    message=None,
                    severity=rule.severity,
                    actual_value=value
                )
                
            except Exception as e:
                logger.error(f"Error applying validator {func_name}: {e}")
                return ValidationResult(
                    valid=False,
                    field=field_name,
                    rule=rule.rule,
                    message=f"Validation error: {str(e)}",
                    severity=rule.severity,
                    actual_value=value
                )
                
        except Exception as e:
            logger.error(f"Error parsing rule '{rule.rule}': {e}")
            return ValidationResult(
                valid=False,
                field=field_name,
                rule=rule.rule,
                message=f"Invalid rule format: {str(e)}",
                severity=rule.severity,
                actual_value=value
            )
    
    def validate(self, 
                 data: Dict[str, Any], 
                 rules: List[Any]) -> Dict[str, Any]:
        """
        Validate data against multiple rules.
        
        Args:
            data: Dictionary of field names to values
            rules: List of validation rules (dicts or ValidationRule objects)
            
        Returns:
            Dict with 'valid' (bool) and 'errors' (list of dicts)
        """
        results = []
        
        for rule_raw in rules:
            # Accept both dicts and ValidationRule objects
            if isinstance(rule_raw, dict):
                rule = ValidationRule(**rule_raw)
            else:
                rule = rule_raw
            
            field_name = rule.field
            
            # Check if field exists in data
            if field_name not in data:
                if rule.rule == "required":
                    # Required field missing
                    results.append(ValidationResult(
                        valid=False,
                        field=field_name,
                        rule=rule.rule,
                        message=rule.message or f"Required field '{field_name}' is missing",
                        severity=rule.severity,
                        actual_value=None
                    ))
                else:
                    # Non-required field missing, skip validation
                    results.append(ValidationResult(
                        valid=True,
                        field=field_name,
                        rule=rule.rule,
                        message=f"Field '{field_name}' not found, skipping validation",
                        severity=ValidationSeverity.INFO,
                        actual_value=None
                    ))
                continue
            
            # Validate field
            value = data[field_name]
            result = self.validate_field(field_name, value, rule)
            results.append(result)
        
        # Build summary dict
        all_valid = all(r.valid for r in results)
        errors = [
            {
                "field": r.field,
                "rule": r.rule,
                "message": r.message,
                "actual_value": r.actual_value
            }
            for r in results if not r.valid
        ]
        return {"valid": all_valid, "errors": errors, "details": results}
    
    def validate_with_summary(self,
                             data: Dict[str, Any],
                             rules: List[ValidationRule]) -> Dict[str, Any]:
        """
        Validate data and return summary statistics.
        
        Args:
            data: Dictionary of field names to values
            rules: List of validation rules
            
        Returns:
            Dictionary with validation summary
        """
        results = self.validate(data, rules)
        
        # Count by severity and validity
        error_count = sum(1 for r in results if r.severity == ValidationSeverity.ERROR and not r.valid)
        warning_count = sum(1 for r in results if r.severity == ValidationSeverity.WARNING and not r.valid)
        info_count = sum(1 for r in results if r.severity == ValidationSeverity.INFO and not r.valid)
        
        # Overall validity (passes if no errors)
        overall_valid = error_count == 0
        
        # Failed validations
        failed = [r.to_dict() for r in results if not r.valid]
        
        # Group by field
        field_results = {}
        for result in results:
            if result.field not in field_results:
                field_results[result.field] = []
            field_results[result.field].append(result.to_dict())
        
        return {
            "valid": overall_valid,
            "error_count": error_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "total_rules": len(rules),
            "passed_rules": sum(1 for r in results if r.valid),
            "failed_validations": failed,
            "field_results": field_results,
            "all_results": [r.to_dict() for r in results]
        }
    
    def validate_cross_field(self,
                            data: Dict[str, Any],
                            cross_field_rules: List[str]) -> List[Dict[str, Any]]:
        """
        Validate cross-field relationships.
        
        Args:
            data: Dictionary of field names to values
            cross_field_rules: List of rule strings like "field1 + field2 == total"
            
        Returns:
            List of validation failures
        """
        failures = []
        
        # Prepare context for eval
        context = {
            "data": data,
            "float": float,
            "int": int,
            "str": str,
            "len": len,
            "sum": sum,
            "min": min,
            "max": max,
        }
        
        for rule_str in cross_field_rules:
            try:
                # Evaluate rule
                result = eval(rule_str, {"__builtins__": {}}, context)
                
                if not result:
                    failures.append({
                        "rule": rule_str,
                        "message": f"Cross-field validation failed: {rule_str}",
                        "data": data
                    })
                    
            except Exception as e:
                failures.append({
                    "rule": rule_str,
                    "message": f"Error evaluating cross-field rule: {str(e)}",
                    "error": str(e)
                })
        
        return failures


# Global validator instance
validator = SchemaValidator()