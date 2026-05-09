"""
Data transformer for field mapping and format conversion.
Supports field renaming, type conversion, and complex transformations.
"""

import re
import json
from typing import List, Dict, Any, Optional, Union, Callable
from datetime import datetime
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class FieldMapping:
    """Field mapping configuration."""
    source: str
    target: str
    transform: Optional[str] = None  # Transformation function name
    default: Optional[Any] = None  # Default value if source is missing


@dataclass
class FormatConversion:
    """Format conversion specification."""
    field: str
    format: str  # date, float, integer, boolean, string, uppercase, lowercase, trim
    params: Optional[Dict[str, Any]] = None  # Format-specific parameters


@dataclass
class TransformationResult:
    """Result of data transformation."""
    transformed_data: Dict[str, Any]
    applied_transformations: List[Dict[str, Any]]
    errors: Dict[str, str]


class DataTransformer:
    """
    Data transformer for field mapping and format conversion.
    """
    
    # Built-in transformation functions
    BUILTIN_TRANSFORMERS = {
        # Type converters
        "to_string": lambda x: str(x) if x is not None else None,
        "to_integer": lambda x: int(float(str(x).replace(',', ''))) if x is not None and str(x).strip() else None,
        "to_float": lambda x: float(str(x).replace(',', '')) if x is not None and str(x).strip() else None,
        "to_boolean": lambda x: str(x).lower() in ['true', 'yes', '1', 'on'] if x is not None else None,
        "to_decimal": lambda x: Decimal(str(x).replace(',', '')) if x is not None and str(x).strip() else None,
        
        # String transformers
        "uppercase": lambda x: str(x).upper() if x is not None else None,
        "lowercase": lambda x: str(x).lower() if x is not None else None,
        "trim": lambda x: str(x).strip() if x is not None else None,
        "capitalize": lambda x: str(x).capitalize() if x is not None else None,
        "title_case": lambda x: str(x).title() if x is not None else None,
        
        # Numeric transformers
        "round": lambda x, decimals=2: round(float(str(x).replace(',', '')), decimals) if x is not None and str(x).strip() else None,
        "abs": lambda x: abs(float(str(x).replace(',', ''))) if x is not None and str(x).strip() else None,
        "add": lambda x, value: float(str(x).replace(',', '')) + float(value) if x is not None and str(x).strip() else None,
        "subtract": lambda x, value: float(str(x).replace(',', '')) - float(value) if x is not None and str(x).strip() else None,
        "multiply": lambda x, value: float(str(x).replace(',', '')) * float(value) if x is not None and str(x).strip() else None,
        "divide": lambda x, value: float(str(x).replace(',', '')) / float(value) if x is not None and str(x).strip() and float(value) != 0 else None,
        
        # Date transformers
        "parse_date": lambda x, fmt=None: DataTransformer._parse_date_string(x, fmt) if x is not None else None,
        "format_date": lambda x, fmt="%Y-%m-%d": x.strftime(fmt) if isinstance(x, datetime) else None,
        "extract_year": lambda x: x.year if isinstance(x, datetime) else None,
        "extract_month": lambda x: x.month if isinstance(x, datetime) else None,
        "extract_day": lambda x: x.day if isinstance(x, datetime) else None,
        
        # String manipulation
        "replace": lambda x, old, new: str(x).replace(old, new) if x is not None else None,
        "remove": lambda x, substring: str(x).replace(substring, '') if x is not None else None,
        "extract_numbers": lambda x: ''.join(filter(str.isdigit, str(x))) if x is not None else None,
        "extract_letters": lambda x: ''.join(filter(str.isalpha, str(x))) if x is not None else None,
        "left": lambda x, length: str(x)[:length] if x is not None else None,
        "right": lambda x, length: str(x)[-length:] if x is not None else None,
        "substring": lambda x, start, end: str(x)[start:end] if x is not None else None,
        
        # Conditional transformers
        "if_empty": lambda x, default: default if not x or not str(x).strip() else x,
        "if_null": lambda x, default: default if x is None else x,
        
        # Business logic transformers
        "add_tax": lambda x, rate=0.1: float(str(x).replace(',', '')) * (1 + float(rate)) if x is not None and str(x).strip() else None,
        "calculate_discount": lambda x, rate=0.1: float(str(x).replace(',', '')) * (1 - float(rate)) if x is not None and str(x).strip() else None,
        "calculate_total": lambda x, *args: sum(float(str(v).replace(',', '')) for v in [x] + list(args) if v is not None and str(v).strip()),
    }
    
    @staticmethod
    def _parse_date_string(date_str: Any, fmt: Optional[str] = None) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str or not isinstance(date_str, str):
            return None
        
        date_formats = [
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
            "%d-%m-%Y", "%m-%d-%Y",
            "%Y/%m/%d", "%d.%m.%Y", "%m.%d.%Y",
            "%b %d, %Y", "%d %b %Y", "%B %d, %Y", "%d %B %Y",
            "%m/%d/%y", "%d/%m/%y", "%y-%m-%d",
        ]
        
        if fmt:
            date_formats = [fmt] + date_formats
        
        for date_format in date_formats:
            try:
                return datetime.strptime(date_str.strip(), date_format)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date string: {date_str}")
        return None
    
    def __init__(self):
        """Initialize transformer with built-in functions."""
        self.transformers = self.BUILTIN_TRANSFORMERS.copy()
        self.custom_transformers: Dict[str, Callable] = {}
    
    def register_custom_transformer(self, name: str, transformer: Callable) -> None:
        """Register a custom transformation function."""
        self.custom_transformers[name] = transformer
        logger.info(f"Registered custom transformer: {name}")
    
    def _parse_transform(self, transform_str: str) -> tuple[str, list, dict]:
        """Parse transform string into function name and arguments."""
        transform_str = transform_str.strip()
        
        if '(' in transform_str and transform_str.endswith(')'):
            # Function call with arguments: func(arg1, arg2, key=value)
            func_name = transform_str[:transform_str.index('(')].strip()
            args_str = transform_str[transform_str.index('(')+1:-1]
            
            # Parse positional and keyword arguments
            args = []
            kwargs = {}
            
            # Simple parsing (doesn't handle nested parentheses)
            parts = []
            current_part = []
            paren_depth = 0
            
            for char in args_str:
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                elif char == ',' and paren_depth == 0:
                    parts.append(''.join(current_part).strip())
                    current_part = []
                    continue
                current_part.append(char)
            
            if current_part:
                parts.append(''.join(current_part).strip())
            
            for part in parts:
                if '=' in part:
                    # Keyword argument
                    key, value = part.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Parse value
                    if value.lower() in ['true', 'false']:
                        kwargs[key] = value.lower() == 'true'
                    elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                        if '.' in value:
                            kwargs[key] = float(value)
                        else:
                            kwargs[key] = int(value)
                    elif value.startswith('"') and value.endswith('"'):
                        kwargs[key] = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        kwargs[key] = value[1:-1]
                    else:
                        kwargs[key] = value
                else:
                    # Positional argument
                    value = part.strip()
                    
                    if value.lower() in ['true', 'false']:
                        args.append(value.lower() == 'true')
                    elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                        if '.' in value:
                            args.append(float(value))
                        else:
                            args.append(int(value))
                    elif value.startswith('"') and value.endswith('"'):
                        args.append(value[1:-1])
                    elif value.startswith("'") and value.endswith("'"):
                        args.append(value[1:-1])
                    else:
                        args.append(value)
            
            return func_name, args, kwargs
        
        else:
            # Simple function name without arguments
            return transform_str, [], {}
    
    def apply_simple_mappings(self,
                             data: Dict[str, Any],
                             mappings: Dict[str, str]) -> Dict[str, Any]:
        """
        Apply simple field renaming mappings.
        
        Args:
            data: Input data dictionary
            mappings: Dictionary mapping source field names to target field names
            
        Returns:
            Transformed data dictionary
        """
        transformed = {}
        applied = []
        
        for source, target in mappings.items():
            if source in data:
                transformed[target] = data[source]
                applied.append({
                    "type": "rename",
                    "source": source,
                    "target": target,
                    "value": data[source]
                })
            else:
                # Source field not found, keep target as None
                transformed[target] = None
                applied.append({
                    "type": "rename",
                    "source": source,
                    "target": target,
                    "value": None,
                    "note": "Source field not found"
                })
        
        # Copy any unmapped fields
        for key, value in data.items():
            if key not in mappings:
                transformed[key] = value
        
        return transformed
    
    def apply_field_mappings(self,
                            data: Dict[str, Any],
                            field_mappings: List[FieldMapping]) -> Dict[str, Any]:
        """
        Apply complex field mappings with transformations.
        
        Args:
            data: Input data dictionary
            field_mappings: List of field mapping configurations
            
        Returns:
            Transformed data dictionary
        """
        transformed = data.copy()
        applied = []
        errors = {}
        
        for mapping in field_mappings:
            source_value = None
            
            # Get source value
            if mapping.source in data:
                source_value = data[mapping.source]
            elif mapping.default is not None:
                source_value = mapping.default
                applied.append({
                    "type": "default",
                    "source": mapping.source,
                    "target": mapping.target,
                    "value": source_value,
                    "note": "Using default value"
                })
            else:
                # Source not found and no default
                transformed[mapping.target] = None
                errors[mapping.target] = f"Source field '{mapping.source}' not found"
                continue
            
            # Apply transformation if specified
            if mapping.transform:
                try:
                    func_name, args, kwargs = self._parse_transform(mapping.transform)
                    
                    # Get transformer function
                    transformer = self.custom_transformers.get(func_name) or self.transformers.get(func_name)
                    if not transformer:
                        raise ValueError(f"Unknown transformer function: {func_name}")
                    
                    # Apply transformer
                    if source_value is not None:
                        transformed_value = transformer(source_value, *args, **kwargs)
                    else:
                        transformed_value = None
                    
                    applied.append({
                        "type": "transform",
                        "source": mapping.source,
                        "target": mapping.target,
                        "transform": mapping.transform,
                        "original_value": source_value,
                        "transformed_value": transformed_value
                    })
                    
                    transformed[mapping.target] = transformed_value
                    
                except Exception as e:
                    transformed[mapping.target] = source_value
                    errors[mapping.target] = f"Transformation error: {str(e)}"
                    applied.append({
                        "type": "transform_error",
                        "source": mapping.source,
                        "target": mapping.target,
                        "transform": mapping.transform,
                        "error": str(e),
                        "value": source_value
                    })
            else:
                # Simple copy
                transformed[mapping.target] = source_value
                applied.append({
                    "type": "copy",
                    "source": mapping.source,
                    "target": mapping.target,
                    "value": source_value
                })
        
        return transformed
    
    def apply_format_conversions(self,
                                data: Dict[str, Any],
                                formats: List[FormatConversion]) -> Dict[str, Any]:
        """
        Apply format conversions to fields.
        
        Args:
            data: Input data dictionary
            formats: List of format conversion specifications
            
        Returns:
            Transformed data dictionary
        """
        transformed = data.copy()
        applied = []
        
        for fmt in formats:
            if fmt.field not in transformed:
                continue
            
            value = transformed[fmt.field]
            if value is None:
                continue
            
            params = fmt.params or {}
            
            try:
                if fmt.format == "date":
                    # Parse date string
                    date_format = params.get("format")
                    output_format = params.get("output_format", "%Y-%m-%d")
                    
                    if isinstance(value, str):
                        dt = self._parse_date_string(value, date_format)
                        if dt:
                            transformed[fmt.field] = dt.strftime(output_format)
                            applied.append({
                                "field": fmt.field,
                                "format": "date",
                                "original": value,
                                "transformed": transformed[fmt.field]
                            })
                
                elif fmt.format == "float":
                    # Convert to float
                    transformed[fmt.field] = float(str(value).replace(',', ''))
                    applied.append({
                        "field": fmt.field,
                        "format": "float",
                        "original": value,
                        "transformed": transformed[fmt.field]
                    })
                
                elif fmt.format == "integer":
                    # Convert to integer
                    transformed[fmt.field] = int(float(str(value).replace(',', '')))
                    applied.append({
                        "field": fmt.field,
                        "format": "integer",
                        "original": value,
                        "transformed": transformed[fmt.field]
                    })
                
                elif fmt.format == "boolean":
                    # Convert to boolean
                    str_val = str(value).lower()
                    transformed[fmt.field] = str_val in ['true', 'yes', '1', 'on']
                    applied.append({
                        "field": fmt.field,
                        "format": "boolean",
                        "original": value,
                        "transformed": transformed[fmt.field]
                    })
                
                elif fmt.format == "string":
                    # Convert to string
                    transformed[fmt.field] = str(value)
                    applied.append({
                        "field": fmt.field,
                        "format": "string",
                        "original": value,
                        "transformed": transformed[fmt.field]
                    })
                
                elif fmt.format == "uppercase":
                    # Convert to uppercase
                    transformed[fmt.field] = str(value).upper()
                    applied.append({
                        "field": fmt.field,
                        "format": "uppercase",
                        "original": value,
                        "transformed": transformed[fmt.field]
                    })
                
                elif fmt.format == "lowercase":
                    # Convert to lowercase
                    transformed[fmt.field] = str(value).lower()
                    applied.append({
                        "field": fmt.field,
                        "format": "lowercase",
                        "original": value,
                        "transformed": transformed[fmt.field]
                    })
                
                elif fmt.format == "trim":
                    # Trim whitespace
                    transformed[fmt.field] = str(value).strip()
                    applied.append({
                        "field": fmt.field,
                        "format": "trim",
                        "original": value,
                        "transformed": transformed[fmt.field]
                    })
                
                else:
                    logger.warning(f"Unknown format: {fmt.format}")
                    
            except Exception as e:
                logger.error(f"Error applying format {fmt.format} to field {fmt.field}: {e}")
                # Keep original value on error
        
        return transformed
    
    def transform(self,
                  data: Dict[str, Any],
                  mappings: Optional[Dict[str, str]] = None,
                  field_mappings: Optional[List[FieldMapping]] = None,
                  formats: Optional[List[FormatConversion]] = None) -> TransformationResult:
        """
        Apply all transformations to data.
        
        Args:
            data: Input data dictionary
            mappings: Simple field renaming mappings
            field_mappings: Complex field mappings with transformations
            formats: Format conversion specifications
            
        Returns:
            TransformationResult with transformed data and metadata
        """
        transformed = data.copy()
        applied_transformations = []
        errors = {}
        
        # Apply simple mappings first
        if mappings:
            result = self.apply_simple_mappings(transformed, mappings)
            # Merge results
            transformed.update(result)
            # Note: apply_simple_mappings doesn't return applied transformations
        
        # Apply complex field mappings
        if field_mappings:
            result = self.apply_field_mappings(transformed, field_mappings)
            # We need to track applied transformations from this method
            # For now, we'll just update the data
            transformed.update(result)
        
        # Apply format conversions
        if formats:
            result = self.apply_format_conversions(transformed, formats)
            transformed.update(result)
        
        return TransformationResult(
            transformed_data=transformed,
            applied_transformations=applied_transformations,
            errors=errors
        )


# Global transformer instance
transformer = DataTransformer()