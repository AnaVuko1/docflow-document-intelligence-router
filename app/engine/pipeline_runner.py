"""
Core pipeline execution engine.
Reads YAML pipeline definitions and executes steps sequentially.
"""

import asyncio
import yaml
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging
from dataclasses import dataclass

from app.engine.classifier import DocumentClassifier, classifier
from app.engine.extractors import ExtractionConfig, extraction_engine
from app.engine.validators import ValidationRule, ValidationSeverity, validator
from app.engine.transformers import FieldMapping, FormatConversion, transformer
from app.engine.connectors import connector_registry, ConnectorResult
from app.models import Job, ExtractionResult as ExtractionResultModel
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """Result of a pipeline step execution."""
    step_type: str
    step_name: Optional[str] = None
    success: bool = True
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class PipelineRunner:
    """
    Executes pipeline definitions defined in YAML.
    Handles sequential step execution with error handling.
    """
    
    def __init__(self, db_session):
        """
        Initialize pipeline runner.
        
        Args:
            db_session: Database session for storing results
        """
        self.db_session = db_session
        self.classifier = classifier
        self.extraction_engine = extraction_engine
        self.validator = validator
        self.transformer = transformer
    
    async def load_pipeline(self, pipeline_definition: Union[str, Dict]) -> Dict[str, Any]:
        """
        Load pipeline definition from YAML string or dictionary.
        
        Args:
            pipeline_definition: YAML string or parsed dictionary
            
        Returns:
            Parsed pipeline definition
        """
        if isinstance(pipeline_definition, str):
            try:
                pipeline = yaml.safe_load(pipeline_definition)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML: {str(e)}")
        else:
            pipeline = pipeline_definition
        
        # Validate pipeline structure
        required_fields = ["name", "steps"]
        for field in required_fields:
            if field not in pipeline:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate steps
        if not isinstance(pipeline["steps"], list):
            raise ValueError("Steps must be a list")
        
        # Set defaults
        pipeline.setdefault("description", "")
        pipeline.setdefault("version", 1)
        
        return pipeline
    
    async def execute_classify_step(self,
                                   content: str,
                                   config: Dict[str, Any]) -> StepResult:
        """
        Execute classification step.
        
        Args:
            content: Document content
            config: Step configuration
            
        Returns:
            StepResult with classification
        """
        start_time = datetime.now()
        
        try:
            target_types = config.get("target_types")
            if target_types and not isinstance(target_types, list):
                target_types = [target_types]
            
            # Classify document
            classification = self.classifier.classify(content, target_types)
            
            result = StepResult(
                step_type="classify",
                step_name=config.get("name", "Document Classification"),
                success=True,
                output_data={
                    "document_type": classification.document_type,
                    "confidence": classification.confidence,
                    "detected_keywords": classification.detected_keywords,
                    "alternative_types": classification.alternative_types
                },
                metadata={
                    "classifier": "DocumentClassifier",
                    "target_types": target_types
                }
            )
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            result = StepResult(
                step_type="classify",
                step_name=config.get("name", "Document Classification"),
                success=False,
                error_message=f"Classification error: {str(e)}",
                error_details={"exception": str(type(e).__name__)}
            )
        
        result.execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return result
    
    async def execute_extract_step(self,
                                  content: str,
                                  config: Dict[str, Any]) -> StepResult:
        """
        Execute extraction step.
        
        Args:
            content: Document content
            config: Step configuration
            
        Returns:
            StepResult with extracted fields
        """
        start_time = datetime.now()
        
        try:
            strategy = config.get("strategy", "regex")
            fields_config = config.get("fields", [])
            
            # Convert field configurations
            fields = []
            for field_config in fields_config:
                fields.append(ExtractionConfig(
                    name=field_config.get("name"),
                    pattern=field_config.get("pattern"),
                    extractor=field_config.get("extractor"),
                    description=field_config.get("description"),
                    required=field_config.get("required", True),
                    multiple=field_config.get("multiple", False)
                ))
            
            # Extract fields
            extraction_results = self.extraction_engine.extract(content, fields, strategy)
            
            # Format results
            extracted_data = {}
            confidence_scores = {}
            raw_matches = {}
            errors = {}
            
            for field_name, result in extraction_results.items():
                extracted_data[field_name] = result.value
                confidence_scores[field_name] = result.confidence
                raw_matches[field_name] = result.raw_matches
                if result.error:
                    errors[field_name] = result.error
            
            result = StepResult(
                step_type="extract",
                step_name=config.get("name", "Field Extraction"),
                success=True,
                output_data=extracted_data,
                metadata={
                    "strategy": strategy,
                    "fields": [f.name for f in fields],
                    "confidence_scores": confidence_scores,
                    "raw_matches": raw_matches,
                    "errors": errors
                }
            )
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            result = StepResult(
                step_type="extract",
                step_name=config.get("name", "Field Extraction"),
                success=False,
                error_message=f"Extraction error: {str(e)}",
                error_details={"exception": str(type(e).__name__)}
            )
        
        result.execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return result
    
    async def execute_validate_step(self,
                                   data: Dict[str, Any],
                                   config: Dict[str, Any]) -> StepResult:
        """
        Execute validation step.
        
        Args:
            data: Data to validate
            config: Step configuration
            
        Returns:
            StepResult with validation results
        """
        start_time = datetime.now()
        
        try:
            rules_config = config.get("rules", [])
            
            # Convert validation rules
            rules = []
            for rule_config in rules_config:
                severity_str = rule_config.get("severity", "error").lower()
                severity = ValidationSeverity(severity_str)
                
                rules.append(ValidationRule(
                    field=rule_config.get("field"),
                    rule=rule_config.get("rule"),
                    message=rule_config.get("message"),
                    severity=severity
                ))
            
            # Validate data
            validation_summary = self.validator.validate_with_summary(data, rules)
            
            # Check cross-field rules if specified
            cross_field_rules = config.get("cross_field_rules", [])
            cross_field_failures = []
            if cross_field_rules:
                cross_field_failures = self.validator.validate_cross_field(
                    data, cross_field_rules
                )
            
            # Determine overall success
            # Validation passes if there are no errors (warnings are OK)
            validation_passes = validation_summary["error_count"] == 0 and not cross_field_failures
            
            result = StepResult(
                step_type="validate",
                step_name=config.get("name", "Data Validation"),
                success=validation_passes,
                output_data=validation_summary,
                metadata={
                    "rules_count": len(rules),
                    "cross_field_rules_count": len(cross_field_rules),
                    "cross_field_failures": cross_field_failures
                }
            )
            
            if not validation_passes:
                result.error_message = "Validation failed"
                result.error_details = {
                    "validation_errors": validation_summary["failed_validations"],
                    "cross_field_failures": cross_field_failures
                }
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            result = StepResult(
                step_type="validate",
                step_name=config.get("name", "Data Validation"),
                success=False,
                error_message=f"Validation error: {str(e)}",
                error_details={"exception": str(type(e).__name__)}
            )
        
        result.execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return result
    
    async def execute_transform_step(self,
                                    data: Dict[str, Any],
                                    config: Dict[str, Any]) -> StepResult:
        """
        Execute transformation step.
        
        Args:
            data: Data to transform
            config: Step configuration
            
        Returns:
            StepResult with transformed data
        """
        start_time = datetime.now()
        
        try:
            # Get transformation configurations
            mappings = config.get("mappings")
            field_mappings_config = config.get("field_mappings", [])
            formats_config = config.get("formats", [])
            
            # Convert field mappings
            field_mappings = []
            for mapping_config in field_mappings_config:
                field_mappings.append(FieldMapping(
                    source=mapping_config.get("source"),
                    target=mapping_config.get("target"),
                    transform=mapping_config.get("transform"),
                    default=mapping_config.get("default")
                ))
            
            # Convert format conversions
            formats = []
            for format_config in formats_config:
                formats.append(FormatConversion(
                    field=format_config.get("field"),
                    format=format_config.get("format"),
                    params=format_config.get("params")
                ))
            
            # Transform data
            transformation_result = self.transformer.transform(
                data=data,
                mappings=mappings,
                field_mappings=field_mappings,
                formats=formats
            )
            
            result = StepResult(
                step_type="transform",
                step_name=config.get("name", "Data Transformation"),
                success=True,
                output_data=transformation_result.transformed_data,
                metadata={
                    "mappings": mappings,
                    "field_mappings_count": len(field_mappings),
                    "formats_count": len(formats),
                    "errors": transformation_result.errors
                }
            )
            
        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            result = StepResult(
                step_type="transform",
                step_name=config.get("name", "Data Transformation"),
                success=False,
                error_message=f"Transformation error: {str(e)}",
                error_details={"exception": str(type(e).__name__)}
            )
        
        result.execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return result
    
    async def execute_route_step(self,
                                data: Dict[str, Any],
                                config: Dict[str, Any]) -> StepResult:
        """
        Execute routing step.
        
        Args:
            data: Data to route
            config: Step configuration
            
        Returns:
            StepResult with routing results
        """
        start_time = datetime.now()
        
        try:
            destinations = config.get("destinations", [])
            
            if not destinations:
                return StepResult(
                    step_type="route",
                    step_name=config.get("name", "Data Routing"),
                    success=True,
                    output_data={},
                    metadata={"note": "No destinations specified"}
                )
            
            # Send data to all destinations
            connector_results = await connector_registry.send_to_connectors(
                data, destinations
            )
            
            # Check results
            successful = [r for r in connector_results if r.success]
            failed = [r for r in connector_results if not r.success]
            
            overall_success = len(failed) == 0
            
            result = StepResult(
                step_type="route",
                step_name=config.get("name", "Data Routing"),
                success=overall_success,
                output_data={
                    "connector_results": [
                        {
                            "type": destinations[i].get("type") if i < len(destinations) else "unknown",
                            "success": r.success,
                            "output_path": r.output_path,
                            "error_message": r.error_message,
                            "status_code": r.status_code
                        }
                        for i, r in enumerate(connector_results)
                    ]
                },
                metadata={
                    "total_destinations": len(destinations),
                    "successful": len(successful),
                    "failed": len(failed)
                }
            )
            
            if not overall_success:
                result.error_message = f"{len(failed)} connector(s) failed"
                result.error_details = {
                    "failed_connectors": [
                        {
                            "type": destinations[i].get("type") if i < len(destinations) else "unknown",
                            "error": r.error_message
                        }
                        for i, r in enumerate(failed)
                    ]
                }
            
        except Exception as e:
            logger.error(f"Routing failed: {e}")
            result = StepResult(
                step_type="route",
                step_name=config.get("name", "Data Routing"),
                success=False,
                error_message=f"Routing error: {str(e)}",
                error_details={"exception": str(type(e).__name__)}
            )
        
        result.execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return result
    
    async def execute_step(self,
                          step: Dict[str, Any],
                          content: str,
                          current_data: Dict[str, Any]) -> StepResult:
        """
        Execute a single pipeline step.
        
        Args:
            step: Step definition
            content: Document content
            current_data: Current data state
            
        Returns:
            StepResult
        """
        step_type = step.get("type")
        step_config = step.get("config", {})
        step_name = step.get("name", f"{step_type.title()} Step")
        
        if step_type == "classify":
            return await self.execute_classify_step(content, step_config)
        
        elif step_type == "extract":
            return await self.execute_extract_step(content, step_config)
        
        elif step_type == "validate":
            return await self.execute_validate_step(current_data, step_config)
        
        elif step_type == "transform":
            return await self.execute_transform_step(current_data, step_config)
        
        elif step_type == "route":
            return await self.execute_route_step(current_data, step_config)
        
        else:
            return StepResult(
                step_type=step_type,
                step_name=step_name,
                success=False,
                error_message=f"Unknown step type: {step_type}",
                error_details={"step": step}
            )
    
    async def execute_pipeline(self,
                              pipeline_definition: Union[str, Dict],
                              content: str,
                              job_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute complete pipeline.
        
        Args:
            pipeline_definition: Pipeline YAML or dictionary
            content: Document content to process
            job_id: Optional job ID for tracking
            
        Returns:
            Dictionary with execution results
        """
        # Load pipeline
        try:
            pipeline = await self.load_pipeline(pipeline_definition)
        except Exception as e:
            logger.error(f"Failed to load pipeline: {e}")
            raise
        
        pipeline_name = pipeline.get("name", "Unnamed Pipeline")
        steps = pipeline.get("steps", [])
        
        logger.info(f"Executing pipeline: {pipeline_name} with {len(steps)} steps")
        
        # Initialize execution state
        current_data = {}
        step_results = []
        all_successful = True
        error_message = None
        error_step = None
        
        # Execute steps sequentially
        for i, step in enumerate(steps):
            step_type = step.get("type")
            step_name = step.get("name", f"Step {i+1}: {step_type}")
            
            logger.info(f"Executing step {i+1}/{len(steps)}: {step_name}")
            
            # Update job progress if job_id provided
            if job_id:
                await self._update_job_progress(job_id, i + 1, len(steps), step_name)
            
            # Execute step
            try:
                step_result = await self.execute_step(step, content, current_data)
                step_result.step_name = step_name
                step_results.append(step_result)
                
                # Store step result in database
                if job_id:
                    await self._store_step_result(job_id, step_result)
                
                # Update current data if step produced output
                if step_result.success and step_result.output_data:
                    # Merge output data with current data
                    if isinstance(step_result.output_data, dict):
                        current_data.update(step_result.output_data)
                    elif step_type == "classify":
                        # Special handling for classification
                        current_data["document_type"] = step_result.output_data.get("document_type")
                        current_data["classification_confidence"] = step_result.output_data.get("confidence")
                
                # Stop pipeline on critical error
                if not step_result.success:
                    all_successful = False
                    error_message = step_result.error_message
                    error_step = step_name
                    
                    # Check if we should continue despite error
                    continue_on_error = step.get("continue_on_error", False)
                    if not continue_on_error:
                        logger.warning(f"Step failed, stopping pipeline: {error_message}")
                        break
                    else:
                        logger.warning(f"Step failed but continuing: {error_message}")
            
            except Exception as e:
                logger.error(f"Unexpected error in step {step_name}: {e}")
                step_result = StepResult(
                    step_type=step_type,
                    step_name=step_name,
                    success=False,
                    error_message=f"Unexpected error: {str(e)}",
                    error_details={"exception": str(type(e).__name__)}
                )
                step_results.append(step_result)
                
                if job_id:
                    await self._store_step_result(job_id, step_result)
                
                all_successful = False
                error_message = str(e)
                error_step = step_name
                break
        
        # Prepare final result
        result = {
            "pipeline_name": pipeline_name,
            "pipeline_description": pipeline.get("description", ""),
            "success": all_successful,
            "total_steps": len(steps),
            "executed_steps": len(step_results),
            "current_data": current_data,
            "step_results": [
                {
                    "step_type": r.step_type,
                    "step_name": r.step_name,
                    "success": r.success,
                    "execution_time_ms": r.execution_time_ms,
                    "error_message": r.error_message
                }
                for r in step_results
            ],
            "error_message": error_message,
            "error_step": error_step
        }
        
        # Update job with final result if job_id provided
        if job_id:
            await self._update_job_result(job_id, all_successful, current_data, error_message)
        
        logger.info(f"Pipeline execution completed: {'success' if all_successful else 'failed'}")
        return result
    
    async def _update_job_progress(self,
                                  job_id: int,
                                  current_step: int,
                                  total_steps: int,
                                  step_name: str) -> None:
        """Update job progress in database."""
        try:
            async with self.db_session() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.current_step = step_name
                    job.progress = int((current_step / total_steps) * 100)
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to update job progress: {e}")
    
    async def _store_step_result(self,
                                job_id: int,
                                step_result: StepResult) -> None:
        """Store step result in database."""
        try:
            async with self.db_session() as session:
                extraction_result = ExtractionResultModel(
                    job_id=job_id,
                    step_type=step_result.step_type,
                    step_name=step_result.step_name,
                    input_data=None,  # Could store input data if needed
                    output_data=step_result.output_data,
                    execution_time_ms=step_result.execution_time_ms,
                    success=step_result.success,
                    error_message=step_result.error_message,
                    error_details=step_result.error_details
                )
                session.add(extraction_result)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to store step result: {e}")
    
    async def _update_job_result(self,
                                job_id: int,
                                success: bool,
                                data: Dict[str, Any],
                                error_message: Optional[str] = None) -> None:
        """Update job with final result."""
        try:
            async with self.db_session() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.status = "completed" if success else "failed"
                    job.completed_at = datetime.now()
                    
                    # Store extracted data
                    if data:
                        job.extracted_data = data
                    
                    if not success:
                        job.error_message = error_message
                    
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to update job result: {e}")


# Factory function for creating pipeline runners
async def create_pipeline_runner(db_session):
    """Create and return a PipelineRunner instance."""
    return PipelineRunner(db_session)