"""
Extraction engine with multiple strategies: regex, template, and LLM-based extraction.
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExtractionConfig:
    """Configuration for field extraction."""
    name: str
    pattern: Optional[str] = None  # For regex extraction
    extractor: Optional[str] = None  # For template/LLM extraction
    description: Optional[str] = None
    required: bool = True
    multiple: bool = False  # Whether to extract multiple values


@dataclass
class ExtractionResult:
    """Result of field extraction."""
    value: Any
    confidence: float = 1.0
    raw_matches: List[str] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.raw_matches is None:
            self.raw_matches = []


class BaseExtractor(ABC):
    """Base class for all extractors."""
    
    @abstractmethod
    def extract(self, 
                content: str, 
                fields: List[ExtractionConfig]) -> Dict[str, ExtractionResult]:
        """Extract fields from content."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get extractor name."""
        pass


class RegexExtractor(BaseExtractor):
    """
    Regex-based field extractor.
    Supports named groups and multiple matches.
    """
    
    def __init__(self):
        self._compiled_patterns: Dict[str, re.Pattern] = {}
    
    def get_name(self) -> str:
        return "regex"
    
    def _compile_pattern(self, pattern: str) -> re.Pattern:
        """Compile regex pattern with caching."""
        if pattern not in self._compiled_patterns:
            try:
                self._compiled_patterns[pattern] = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            except re.error as e:
                logger.error(f"Invalid regex pattern '{pattern}': {e}")
                raise ValueError(f"Invalid regex pattern: {pattern}") from e
        return self._compiled_patterns[pattern]
    
    def extract(self, 
                content: str, 
                fields: List[ExtractionConfig]) -> Dict[str, ExtractionResult]:
        """
        Extract fields using regex patterns.
        
        Args:
            content: Text content to extract from
            fields: List of field configurations
            
        Returns:
            Dictionary mapping field name to ExtractionResult
        """
        results = {}
        
        for field_config in fields:
            if not field_config.pattern:
                results[field_config.name] = ExtractionResult(
                    value=None,
                    confidence=0.0,
                    raw_matches=[],
                    error="No regex pattern provided"
                )
                continue
            
            try:
                pattern = self._compile_pattern(field_config.pattern)
                matches = pattern.findall(content)
                
                if not matches:
                    results[field_config.name] = ExtractionResult(
                        value=None,
                        confidence=0.0,
                        raw_matches=[],
                        error="No matches found" if field_config.required else None
                    )
                    continue
                
                # Handle different match formats
                if isinstance(matches[0], tuple):
                    # Multiple capture groups - take first non-empty group from each match
                    extracted = []
                    for match_tuple in matches:
                        for group in match_tuple:
                            if group and str(group).strip():
                                extracted.append(str(group).strip())
                                break
                    if not extracted:
                        # If no non-empty groups, use first group from first match
                        extracted = [str(matches[0][0]).strip()] if matches[0] else []
                else:
                    # Single capture group or full match
                    extracted = [str(match).strip() for match in matches if str(match).strip()]
                
                # Determine value based on multiplicity
                if field_config.multiple:
                    value = extracted
                    confidence = min(len(extracted) / max(len(matches), 1), 1.0)
                else:
                    value = extracted[0] if extracted else None
                    confidence = 1.0 if value else 0.0
                
                results[field_config.name] = ExtractionResult(
                    value=value,
                    confidence=confidence,
                    raw_matches=extracted
                )
                
            except Exception as e:
                logger.error(f"Error extracting field '{field_config.name}': {e}")
                results[field_config.name] = ExtractionResult(
                    value=None,
                    confidence=0.0,
                    raw_matches=[],
                    error=f"Extraction error: {str(e)}"
                )
        
        return results


class TemplateExtractor(BaseExtractor):
    """
    Template-based extractor for known document formats.
    Uses predefined field mappings and extraction rules.
    """
    
    def __init__(self):
        self.templates: Dict[str, Dict[str, Any]] = {
            "invoice": {
                "invoice_number": {
                    "patterns": [
                        r"Invoice\s*#?\s*([A-Z0-9\-]+)",
                        r"INV-\s*(\d+)",
                        r"Bill\s+Number\s*[:]?\s*(\S+)"
                    ],
                    "default": None
                },
                "date": {
                    "patterns": [
                        r"Date\s*[:]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
                        r"Invoice\s+Date\s*[:]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})"
                    ],
                    "default": None
                },
                "total": {
                    "patterns": [
                        r"Total\s+(?:Due|Amount)\s*[$]?\s*([\d,]+\.?\d{0,2})",
                        r"Amount\s+Due\s*[$]?\s*([\d,]+\.?\d{0,2})"
                    ],
                    "default": None
                }
            },
            "receipt": {
                "merchant": {
                    "patterns": [
                        r"Merchant\s*[:]?\s*(.+)",
                        r"Store\s*[:]?\s*(.+)",
                        r"From\s*[:]?\s*(.+)"
                    ],
                    "default": None
                },
                "date": {
                    "patterns": [
                        r"Date\s*[:]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
                        r"Transaction\s+Date\s*[:]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})"
                    ],
                    "default": None
                },
                "total": {
                    "patterns": [
                        r"Total\s*[:$]?\s*([\d,]+\.\d{2})",
                        r"Amount\s*[:$]?\s*([\d,]+\.\d{2})"
                    ],
                    "default": None
                }
            },
            "contract": {
                "parties": {
                    "patterns": [
                        r"Party\s+A\s*[:]?\s*(.+)",
                        r"Between\s+(.+)\s+and",
                        r"THIS AGREEMENT is made between\s+(.+)"
                    ],
                    "default": [],
                    "multiple": True
                },
                "effective_date": {
                    "patterns": [
                        r"Effective\s+Date\s*[:]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
                        r"Date\s+of\s+Agreement\s*[:]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})"
                    ],
                    "default": None
                }
            }
        }
    
    def get_name(self) -> str:
        return "template"
    
    def extract(self, 
                content: str, 
                fields: List[ExtractionConfig]) -> Dict[str, ExtractionResult]:
        """
        Extract fields using template-based extraction.
        
        Args:
            content: Text content to extract from
            fields: List of field configurations
            
        Returns:
            Dictionary mapping field name to ExtractionResult
        """
        results = {}
        
        for field_config in fields:
            if not field_config.extractor:
                results[field_config.name] = ExtractionResult(
                    value=None,
                    confidence=0.0,
                    raw_matches=[],
                    error="No extractor template specified"
                )
                continue
            
            # Parse extractor format: "template:invoice:invoice_number" or just "invoice"
            parts = field_config.extractor.split(":")
            if len(parts) == 3 and parts[0] == "template":
                template_name = parts[1]
                field_key = parts[2]
            elif len(parts) == 1:
                template_name = parts[0]
                field_key = field_config.name
            else:
                results[field_config.name] = ExtractionResult(
                    value=None,
                    confidence=0.0,
                    raw_matches=[],
                    error=f"Invalid extractor format: {field_config.extractor}"
                )
                continue
            
            # Get template
            template = self.templates.get(template_name)
            if not template:
                results[field_config.name] = ExtractionResult(
                    value=None,
                    confidence=0.0,
                    raw_matches=[],
                    error=f"Unknown template: {template_name}"
                )
                continue
            
            # Get field definition from template
            field_def = template.get(field_key)
            if not field_def:
                results[field_config.name] = ExtractionResult(
                    value=None,
                    confidence=0.0,
                    raw_matches=[],
                    error=f"Field '{field_key}' not found in template '{template_name}'"
                )
                continue
            
            # Try patterns in order
            extracted = []
            raw_matches = []
            
            patterns = field_def.get("patterns", [])
            for pattern_str in patterns:
                try:
                    pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
                    matches = pattern.findall(content)
                    
                    if matches:
                        if isinstance(matches[0], tuple):
                            # Multiple capture groups
                            for match_tuple in matches:
                                for group in match_tuple:
                                    if group and str(group).strip():
                                        extracted.append(str(group).strip())
                                        raw_matches.append(str(group).strip())
                                        break
                        else:
                            # Simple matches
                            for match in matches:
                                if match and str(match).strip():
                                    extracted.append(str(match).strip())
                                    raw_matches.append(str(match).strip())
                        
                        if extracted:
                            break  # Stop at first successful pattern
                except re.error as e:
                    logger.warning(f"Invalid pattern in template: {pattern_str}")
                    continue
            
            # Determine value
            if extracted:
                if field_def.get("multiple", False) or field_config.multiple:
                    value = extracted
                    confidence = min(len(extracted) / 5, 1.0)  # Cap confidence
                else:
                    value = extracted[0]
                    confidence = 1.0
            else:
                value = field_def.get("default")
                confidence = 0.3 if value is not None else 0.0
            
            results[field_config.name] = ExtractionResult(
                value=value,
                confidence=confidence,
                raw_matches=raw_matches,
                error=None if value is not None else "No matches found"
            )
        
        return results


class LLMExtractor(BaseExtractor):
    """
    LLM-based extractor for complex documents.
    Note: This is a placeholder implementation - in production,
    you would integrate with an actual LLM API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.available = api_key is not None
    
    def get_name(self) -> str:
        return "llm"
    
    def extract(self, 
                content: str, 
                fields: List[ExtractionConfig]) -> Dict[str, ExtractionResult]:
        """
        Extract fields using LLM (placeholder implementation).
        
        In a real implementation, this would:
        1. Create a structured prompt with the fields to extract
        2. Call an LLM API (OpenAI, Anthropic, etc.)
        3. Parse the JSON response
        4. Return extracted values with confidence scores
        
        For now, this returns placeholder values for demonstration.
        """
        if not self.available:
            # Return empty results with errors
            return {
                field.name: ExtractionResult(
                    value=None,
                    confidence=0.0,
                    raw_matches=[],
                    error="LLM extractor not configured (no API key)"
                )
                for field in fields
            }
        
        results = {}
        
        # Placeholder: Simple keyword search for demonstration
        content_lower = content.lower()
        
        for field_config in fields:
            # Try to find the field name in content
            field_name_lower = field_config.name.lower()
            
            if field_name_lower in content_lower:
                # Find the value after the field name
                lines = content.split('\n')
                value = None
                
                for line in lines:
                    line_lower = line.lower()
                    if field_name_lower in line_lower:
                        # Extract value after colon or equals
                        parts = line.split(':', 1)
                        if len(parts) > 1:
                            value = parts[1].strip()
                        else:
                            # Try to extract numbers or specific patterns
                            numbers = re.findall(r'[\d,]+\.?\d*', line)
                            if numbers:
                                value = numbers[0]
                        
                        if value:
                            break
                
                results[field_config.name] = ExtractionResult(
                    value=value,
                    confidence=0.7 if value else 0.3,
                    raw_matches=[value] if value else [],
                    error=None if value else "Field found but value not extracted"
                )
            else:
                results[field_config.name] = ExtractionResult(
                    value=None,
                    confidence=0.0,
                    raw_matches=[],
                    error="Field not found in content"
                )
        
        return results


class ExtractionEngine:
    """
    Main extraction engine that routes to appropriate extractor based on strategy.
    """
    
    EXTRACTORS = {
        "regex": RegexExtractor,
        "template": TemplateExtractor,
        "llm": LLMExtractor,
    }
    
    def __init__(self):
        self.extractors: Dict[str, BaseExtractor] = {}
    
    def get_extractor(self, strategy: str) -> BaseExtractor:
        """Get or create extractor for given strategy."""
        if strategy not in self.extractors:
            extractor_class = self.EXTRACTORS.get(strategy)
            if not extractor_class:
                raise ValueError(f"Unknown extraction strategy: {strategy}")
            self.extractors[strategy] = extractor_class()
        return self.extractors[strategy]
    
    def extract(self,
                content: str,
                fields: List[ExtractionConfig],
                strategy: str = "regex") -> Dict[str, ExtractionResult]:
        """
        Extract fields from content using specified strategy.
        
        Args:
            content: Text content to extract from
            fields: List of field configurations
            strategy: Extraction strategy (regex, template, llm)
            
        Returns:
            Dictionary mapping field name to ExtractionResult
        """
        extractor = self.get_extractor(strategy)
        return extractor.extract(content, fields)
    
    def extract_with_fallback(self,
                             content: str,
                             fields: List[ExtractionConfig],
                             strategies: List[str] = None) -> Dict[str, ExtractionResult]:
        """
        Extract fields using multiple strategies with fallback.
        
        Args:
            content: Text content to extract from
            fields: List of field configurations
            strategies: Ordered list of strategies to try
            
        Returns:
            Dictionary with best results from all strategies
        """
        if strategies is None:
            strategies = ["regex", "template", "llm"]
        
        all_results = []
        
        for strategy in strategies:
            try:
                results = self.extract(content, fields, strategy)
                all_results.append((strategy, results))
            except Exception as e:
                logger.warning(f"Strategy '{strategy}' failed: {e}")
                continue
        
        if not all_results:
            raise ValueError("All extraction strategies failed")
        
        # Merge results, preferring higher confidence
        merged = {}
        for field_config in fields:
            field_name = field_config.name
            best_result = None
            best_confidence = -1
            
            for strategy, results in all_results:
                result = results.get(field_name)
                if result and result.confidence > best_confidence:
                    best_confidence = result.confidence
                    best_result = result
            
            if best_result:
                merged[field_name] = best_result
            else:
                merged[field_name] = ExtractionResult(
                    value=None,
                    confidence=0.0,
                    raw_matches=[],
                    error="All extraction strategies failed for this field"
                )
        
        return merged


# Global extraction engine instance
extraction_engine = ExtractionEngine()