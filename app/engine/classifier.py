"""
Document classifier for automatic document type detection.
Supports keyword-based classification with confidence scoring.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class DocumentType(Enum):
    """Supported document types."""
    INVOICE = "invoice"
    RECEIPT = "receipt"
    CONTRACT = "contract"
    BANK_STATEMENT = "bank_statement"
    REPORT = "report"
    RESUME = "resume"
    GENERIC = "generic"


@dataclass
class ClassificationResult:
    """Classification result with confidence."""
    document_type: str
    confidence: float  # 0-1
    detected_keywords: List[str]
    alternative_types: List[Dict[str, Any]]  # Other possible types with confidences


class DocumentClassifier:
    """
    Smart document classifier with keyword-based and pattern-based detection.
    """
    
    # Keyword patterns for different document types
    PATTERNS = {
        DocumentType.INVOICE: {
            "keywords": [
                "invoice", "invoice number", "bill to", "ship to", 
                "total due", "subtotal", "tax", "payment terms",
                "invoice date", "due date", "amount", "balance"
            ],
            "regex_patterns": [
                r"invoice\s*#?\s*[A-Z0-9\-]+",
                r"invoice\s+date\s*[:]?\s*\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}",
                r"total\s+(?:due|amount)\s*[$]?\s*[\d,]+\.?\d{0,2}",
            ]
        },
        DocumentType.RECEIPT: {
            "keywords": [
                "receipt", "thank you", "purchase", "merchant",
                "store", "transaction", "payment method", "card",
                "cash", "change", "receipt number", "tax"
            ],
            "regex_patterns": [
                r"receipt\s*#?\s*[\d]+",
                r"total\s*[:$]?\s*[\d,]+\.\d{2}",
                r"payment\s+method\s*[:]?\s*\w+",
                r"change\s*[:$]?\s*[\d,]+\.\d{2}",
            ]
        },
        DocumentType.CONTRACT: {
            "keywords": [
                "contract", "agreement", "parties", "effective date",
                "expiration date", "terms", "conditions", "obligations",
                "indemnification", "governing law", "jurisdiction",
                "signature", "witness", "notary"
            ],
            "regex_patterns": [
                r"this\s+(?:agreement|contract)\s+is",
                r"effective\s+date\s*[:]?\s*\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}",
                r"party\s+(?:a|b)\s*[:]",
                r"governing\s+law\s*[:]",
            ]
        },
        DocumentType.BANK_STATEMENT: {
            "keywords": [
                "bank statement", "account number", "statement period",
                "opening balance", "closing balance", "transactions",
                "deposit", "withdrawal", "balance forward", "account summary"
            ],
            "regex_patterns": [
                r"account\s+number\s*[:]?\s*[\d\-]+",
                r"statement\s+period\s*[:]?\s*\w+\s+\d{1,2}\s*[,]?\s*\d{4}",
                r"opening\s+balance\s*[:$]?\s*[\d,]+\.\d{2}",
                r"closing\s+balance\s*[:$]?\s*[\d,]+\.\d{2}",
            ]
        },
        DocumentType.REPORT: {
            "keywords": [
                "report", "summary", "findings", "conclusions",
                "recommendations", "executive summary", "introduction",
                "methodology", "results", "analysis", "appendix"
            ],
            "regex_patterns": [
                r"report\s+(?:title|name)\s*[:]",
                r"executive\s+summary",
                r"table\s+of\s+contents",
                r"references?|bibliography",
            ]
        },
        DocumentType.RESUME: {
            "keywords": [
                "resume", "cv", "curriculum vitae", "work experience",
                "education", "skills", "certifications", "references",
                "objective", "summary", "contact information"
            ],
            "regex_patterns": [
                r"work\s+experience",
                r"education\s*[:]",
                r"skills\s*[:]",
                r"references?\s*[:]",
                r"phone\s*[:]?\s*[\d\-\(\)\s]+",
                r"email\s*[:]?\s*[\w\.\-]+@[\w\.\-]+",
            ]
        },
    }
    
    # Default weights for different detection methods
    KEYWORD_WEIGHT = 0.6
    REGEX_WEIGHT = 0.3
    STRUCTURE_WEIGHT = 0.1
    
    def __init__(self):
        """Initialize the classifier."""
        self._compile_regex_patterns()
    
    def _compile_regex_patterns(self) -> None:
        """Compile all regex patterns for performance."""
        self.compiled_patterns = {}
        for doc_type, patterns in self.PATTERNS.items():
            compiled = []
            for pattern in patterns.get("regex_patterns", []):
                try:
                    compiled.append(re.compile(pattern, re.IGNORECASE))
                except re.error:
                    # Skip invalid patterns
                    continue
            self.compiled_patterns[doc_type] = compiled
    
    def classify(self, 
                 content: str, 
                 candidate_types: Optional[List[str]] = None) -> ClassificationResult:
        """
        Classify document content and return the most likely type.
        
        Args:
            content: Document text content (lowercased for better matching)
            candidate_types: Optional list of candidate document types to consider
            
        Returns:
            ClassificationResult with type, confidence, and keywords
        """
        if not content or not content.strip():
            return ClassificationResult(
                document_type=DocumentType.GENERIC.value,
                confidence=1.0,
                detected_keywords=[],
                alternative_types=[]
            )
        
        content_lower = content.lower()
        
        # Filter document types if candidates are provided
        doc_types_to_check = list(DocumentType)
        if candidate_types:
            doc_types_to_check = [
                dt for dt in DocumentType 
                if dt.value in [c.lower() for c in candidate_types]
            ]
        
        scores = {}
        keyword_matches = {}
        
        # Calculate scores for each document type
        for doc_type in doc_types_to_check:
            if doc_type == DocumentType.GENERIC:
                continue
                
            pattern_info = self.PATTERNS.get(doc_type)
            if not pattern_info:
                continue
            
            # Keyword matching score
            keyword_score = 0
            matched_keywords = []
            for keyword in pattern_info.get("keywords", []):
                keyword_lower = keyword.lower()
                # Count occurrences
                count = content_lower.count(keyword_lower)
                if count > 0:
                    matched_keywords.append(keyword)
                    # More occurrences = higher score (capped)
                    keyword_score += min(count * 0.1, 0.5)
            
            # Regex pattern matching score
            regex_score = 0
            compiled_patterns = self.compiled_patterns.get(doc_type, [])
            for pattern in compiled_patterns:
                if pattern.search(content_lower):
                    regex_score += 0.2  # Each matching pattern adds value
            
            # Structure detection (simplified)
            structure_score = 0
            lines = content.split('\n')
            non_empty_lines = [line.strip() for line in lines if line.strip()]
            
            # Check for common structures
            if doc_type == DocumentType.INVOICE:
                # Invoices often have "Invoice #", "Date", "Total" on separate lines
                invoice_keywords = ["invoice", "date", "total"]
                if any(keyword in content_lower for keyword in invoice_keywords):
                    structure_score += 0.1
            
            elif doc_type == DocumentType.RECEIPT:
                # Receipts often have "Receipt", "Date", "Total", "Change"
                receipt_keywords = ["receipt", "date", "total", "change", "payment"]
                if any(keyword in content_lower for keyword in receipt_keywords):
                    structure_score += 0.1
            
            elif doc_type == DocumentType.CONTRACT:
                # Contracts often have sections like "1. Parties", "2. Term"
                section_patterns = [r"\d+\.\s+\w+", r"article\s+\d+", r"section\s+\d+"]
                for line in non_empty_lines[:10]:  # Check first 10 lines
                    for pattern in section_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            structure_score += 0.05
                            break
            
            # Weighted total score (normalized to 0-1)
            total_score = (
                min(keyword_score, 1.0) * self.KEYWORD_WEIGHT +
                min(regex_score, 1.0) * self.REGEX_WEIGHT +
                min(structure_score, 1.0) * self.STRUCTURE_WEIGHT
            )
            
            scores[doc_type.value] = total_score
            keyword_matches[doc_type.value] = matched_keywords
        
        # If no type scores high enough, return generic
        if not scores or max(scores.values()) < 0.3:
            return ClassificationResult(
                document_type=DocumentType.GENERIC.value,
                confidence=1.0,
                detected_keywords=[],
                alternative_types=[]
            )
        
        # Sort by score descending
        sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Get best match
        best_type, best_score = sorted_types[0]
        
        # Prepare alternative types (skip generic)
        alternative_types = []
        for doc_type, score in sorted_types[1:]:
            if score > 0.1:  # Only include if score is meaningful
                alternative_types.append({
                    "document_type": doc_type,
                    "confidence": score,
                    "keywords": keyword_matches.get(doc_type, [])
                })
        
        return ClassificationResult(
            document_type=best_type,
            confidence=min(best_score, 1.0),  # Cap at 1.0
            detected_keywords=keyword_matches.get(best_type, []),
            alternative_types=alternative_types
        )
    
    def classify_batch(self, 
                      contents: List[str],
                      candidate_types: Optional[List[str]] = None) -> List[ClassificationResult]:
        """
        Classify multiple documents.
        
        Args:
            contents: List of document contents
            candidate_types: Optional list of candidate document types
            
        Returns:
            List of ClassificationResult objects
        """
        return [self.classify(content, candidate_types) for content in contents]
    
    def get_supported_types(self) -> List[str]:
        """Get list of supported document types."""
        return [dt.value for dt in DocumentType]


# Singleton instance for convenient use
classifier = DocumentClassifier()