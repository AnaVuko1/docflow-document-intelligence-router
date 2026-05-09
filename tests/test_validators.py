"""Tests for schema validators."""
import pytest
from app.engine.validators import SchemaValidator


class TestSchemaValidator:
    """Test field validation against business rules."""
    
    def setup_method(self):
        self.validator = SchemaValidator()
    
    def test_required_field_present(self):
        """Test required field validation passes when field exists."""
        data = {"total_amount": "1,500.00", "invoice_number": "INV-001"}
        rules = [{"field": "total_amount", "rule": "required"}]
        result = self.validator.validate(data, rules)
        assert result["valid"] is True
    
    def test_required_field_missing(self):
        """Test required field fails when field is missing."""
        data = {"total_amount": "1,500.00"}
        rules = [{"field": "invoice_number", "rule": "required"}]
        result = self.validator.validate(data, rules)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    def test_value_greater_than(self):
        """Test numeric comparison rule."""
        data = {"total_amount": "1,500.00"}
        rules = [{"field": "total_amount", "rule": "min(0.01)"}]
        result = self.validator.validate(data, rules)
        assert result["valid"] is True
    
    def test_value_not_greater_than(self):
        """Test numeric comparison fails correctly."""
        data = {"total_amount": "0.00"}
        rules = [{"field": "total_amount", "rule": "min(0.01)"}]
        result = self.validator.validate(data, rules)
        assert result["valid"] is False
    
    def test_string_length(self):
        """Test string length validation."""
        data = {"invoice_number": "INV-001"}
        rules = [{"field": "invoice_number", "rule": "min_length(3)"}]
        result = self.validator.validate(data, rules)
        assert result["valid"] is True
    
    def test_string_too_short(self):
        """Test string minimum length fails correctly."""
        data = {"invoice_number": "A"}
        rules = [{"field": "invoice_number", "rule": "min_length(3)"}]
        result = self.validator.validate(data, rules)
        assert result["valid"] is False
    
    def test_multiple_rules(self):
        """Test multiple rules on one field."""
        data = {"total_amount": "1,500.00"}
        rules = [
            {"field": "total_amount", "rule": "required"},
            {"field": "total_amount", "rule": "min(0.01)"}
        ]
        result = self.validator.validate(data, rules)
        assert result["valid"] is True
    
    def test_single_rule_fails_all(self):
        """Test that one failing rule makes whole validation fail."""
        data = {"total_amount": "-50.00", "invoice_number": "INV-001"}
        rules = [
            {"field": "total_amount", "rule": "required"},
            {"field": "total_amount", "rule": "min(0.01)"},
            {"field": "invoice_number", "rule": "required"},
            {"field": "invoice_number", "rule": "min_length(3)"}
        ]
        result = self.validator.validate(data, rules)
        assert result["valid"] is False
        assert len(result["errors"]) >= 1
