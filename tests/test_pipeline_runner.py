"""Tests for pipeline runner and YAML pipeline definitions."""
import pytest
import yaml
import os
import re
from pathlib import Path


PIPELINES_DIR = Path(__file__).parent.parent / "pipelines"


class TestPipelineDefinitions:
    """Test the YAML pipeline definitions are valid."""
    
    def test_all_pipeline_files_exist(self):
        """Test all 3 pipeline YAML files exist."""
        files = list(PIPELINES_DIR.glob("*.yaml"))
        assert len(files) == 3, f"Expected 3 pipelines, found {len(files)}"
    
    def test_invoice_pipeline_valid(self):
        """Test invoice pipeline has correct structure."""
        with open(PIPELINES_DIR / "invoice_processing.yaml") as f:
            pipeline = yaml.safe_load(f)
        
        assert pipeline["name"] == "Invoice Processing Pipeline"
        assert len(pipeline["steps"]) >= 5
        assert pipeline["steps"][0]["type"] == "classify"
        assert pipeline["steps"][1]["type"] == "extract"
        assert pipeline["steps"][2]["type"] == "validate"
        assert pipeline["steps"][3]["type"] == "transform"
        assert pipeline["steps"][4]["type"] == "route"
    
    def test_contract_pipeline_valid(self):
        """Test contract pipeline has correct structure."""
        with open(PIPELINES_DIR / "contract_intelligence.yaml") as f:
            pipeline = yaml.safe_load(f)
        
        assert pipeline["name"] == "Contract Intelligence Pipeline"
        assert len(pipeline["steps"]) >= 5
        types = [s["type"] for s in pipeline["steps"]]
        assert "classify" in types
        assert "extract" in types
        assert "validate" in types
    
    def test_receipt_pipeline_valid(self):
        """Test receipt pipeline has correct structure."""
        with open(PIPELINES_DIR / "receipt_scanner.yaml") as f:
            pipeline = yaml.safe_load(f)
        
        assert pipeline["name"] == "Receipt Scanner Pipeline"
        extract_step = pipeline["steps"][1]
        assert extract_step["type"] == "extract"
        assert len(extract_step["config"]["fields"]) >= 5
    
    def test_all_pipelines_have_route(self):
        """Test all pipelines have a route step."""
        for yaml_file in PIPELINES_DIR.glob("*.yaml"):
            with open(yaml_file) as f:
                pipeline = yaml.safe_load(f)
            types = [s["type"] for s in pipeline["steps"]]
            assert "route" in types, f"{yaml_file.name} missing route step"


class TestRegexPatterns:
    """Test regex patterns from pipeline definitions match demo documents."""
    
    DEMO_DIR = Path(__file__).parent.parent / "demo_data"
    
    def test_invoice_regex_match(self):
        """Test invoice regex patterns match demo invoice."""
        with open(PIPELINES_DIR / "invoice_processing.yaml") as f:
            pipeline = yaml.safe_load(f)
        
        with open(self.DEMO_DIR / "sample_invoice.txt") as f:
            content = f.read()
        
        extract_step = pipeline["steps"][1]
        assert extract_step["config"]["strategy"] == "regex"
        
        matches = 0
        for field in extract_step["config"]["fields"]:
            if field.get("required"):
                p = field["pattern"]
                if re.search(p, content, re.IGNORECASE):
                    matches += 1
        
        # At least the required fields should match
        assert matches >= len([f for f in extract_step["config"]["fields"] if f.get("required")])
    
    def test_receipt_regex_match(self):
        """Test receipt regex patterns match demo receipt."""
        with open(PIPELINES_DIR / "receipt_scanner.yaml") as f:
            pipeline = yaml.safe_load(f)
        
        with open(self.DEMO_DIR / "sample_receipt.txt") as f:
            content = f.read()
        
        extract_step = pipeline["steps"][1]
        matches = 0
        for field in extract_step["config"]["fields"]:
            if field.get("required"):
                p = field["pattern"]
                if re.search(p, content, re.IGNORECASE):
                    matches += 1
        
        required = [f for f in extract_step["config"]["fields"] if f.get("required")]
        assert matches == len(required), f"Only {matches}/{len(required)} required fields matched"
    
    def test_contract_regex_match(self):
        """Test contract regex patterns match demo contract."""
        with open(PIPELINES_DIR / "contract_intelligence.yaml") as f:
            pipeline = yaml.safe_load(f)
        
        with open(self.DEMO_DIR / "sample_contract.txt") as f:
            content = f.read()
        
        extract_step = pipeline["steps"][1]
        matches = sum(
            1 for field in extract_step["config"]["fields"]
            if field.get("required") and re.search(field["pattern"], content, re.IGNORECASE)
        )
        
        required = [f for f in extract_step["config"]["fields"] if f.get("required")]
        assert matches == len(required)
