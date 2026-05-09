"""Tests for document classifier."""
import pytest
from app.engine.classifier import DocumentClassifier, ClassificationResult


class TestDocumentClassifier:
    """Test document type classification."""
    
    def setup_method(self):
        self.classifier = DocumentClassifier()
    
    def test_classify_invoice(self):
        """Test invoice classification with clear invoice content."""
        content = """INVOICE #INV-2026-001
        Bill To: Acme Corp
        Date: 01/15/2026
        Due Date: 02/15/2026
        Subtotal: $1,200.00
        Tax: $300.00
        Total Due: $1,500.00"""
        
        result = self.classifier.classify(content)
        assert isinstance(result, ClassificationResult)
        assert result.document_type == "invoice"
        assert result.confidence > 0.3
    
    def test_classify_receipt(self):
        """Test receipt classification."""
        content = """RECEIPT #RCPT-001
        Store: Electronics Plus
        Date: 03/15/2026
        Total: $502.51
        Payment Method: Visa
        Thank you for your purchase!"""
        
        result = self.classifier.classify(content)
        assert result.document_type == "receipt"
    
    def test_classify_contract(self):
        """Test contract classification."""
        content = """SERVICE AGREEMENT
        This Agreement is entered into by and between:
        Party A: Provider Inc.
        Party B: Client Corp.
        Effective Date: 01/01/2026
        Governing Law: State of California"""
        
        result = self.classifier.classify(content)
        assert result.document_type == "contract"
    
    def test_classify_empty_content(self):
        """Test empty content returns generic."""
        result = self.classifier.classify("")
        assert result.document_type == "generic"
        assert result.confidence == 1.0
    
    def test_get_supported_types(self):
        """Test getting supported types."""
        types = self.classifier.get_supported_types()
        assert "invoice" in types
        assert "receipt" in types
        assert "contract" in types
        assert "generic" in types
