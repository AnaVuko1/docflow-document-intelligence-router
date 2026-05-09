"""
Output connectors for routing validated data to destinations.
Supports CSV, JSON, SQLite, and webhook connectors.
"""

import csv
import json
import sqlite3
import httpx
import os
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ConnectorResult:
    """Result of connector execution."""
    success: bool
    output_path: Optional[str] = None  # File path, URL, etc.
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    status_code: Optional[int] = None


class BaseConnector(ABC):
    """Base class for all output connectors."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize connector with configuration.
        
        Args:
            config: Connector-specific configuration
        """
        self.config = config
        self.connector_type = self.get_type()
    
    @abstractmethod
    def get_type(self) -> str:
        """Get connector type (csv, json, sqlite, webhook)."""
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to destination."""
        pass
    
    @abstractmethod
    async def send(self, data: Dict[str, Any]) -> ConnectorResult:
        """
        Send data to destination.
        
        Args:
            data: Transformed data to send
            
        Returns:
            ConnectorResult indicating success/failure
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close connection to destination."""
        pass
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()


class CSVConnector(BaseConnector):
    """
    CSV output connector.
    Appends data to CSV file, auto-creates headers if file doesn't exist.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.filename = config.get("filename", "output.csv")
        self.delimiter = config.get("delimiter", ",")
        self.write_header = config.get("write_header", True)
        self.file_path = None
        self.file_handle = None
        self.csv_writer = None
        
        # Ensure output directory exists
        output_dir = settings.csv_output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.file_path = os.path.join(output_dir, self.filename)
    
    def get_type(self) -> str:
        return "csv"
    
    async def connect(self) -> bool:
        """
        Open CSV file for writing.
        Creates file if it doesn't exist.
        """
        try:
            # Check if file exists
            file_exists = os.path.exists(self.file_path)
            
            # Open file in append mode
            self.file_handle = open(self.file_path, 'a', newline='', encoding='utf-8')
            self.csv_writer = csv.DictWriter(
                self.file_handle,
                fieldnames=self.config.get("columns"),
                delimiter=self.delimiter
            )
            
            # Write header if needed
            if not file_exists and self.write_header:
                self.csv_writer.writeheader()
            
            logger.info(f"CSV connector connected to {self.file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect CSV connector: {e}")
            return False
    
    async def send(self, data: Dict[str, Any]) -> ConnectorResult:
        """
        Write data row to CSV file.
        
        Args:
            data: Data dictionary to write
            
        Returns:
            ConnectorResult
        """
        try:
            if not self.csv_writer:
                return ConnectorResult(
                    success=False,
                    error_message="CSV connector not connected"
                )
            
            # Write data row
            self.csv_writer.writerow(data)
            self.file_handle.flush()
            
            logger.debug(f"Written data to CSV: {self.file_path}")
            return ConnectorResult(
                success=True,
                output_path=self.file_path
            )
            
        except Exception as e:
            logger.error(f"Failed to write to CSV: {e}")
            return ConnectorResult(
                success=False,
                error_message=f"CSV write error: {str(e)}"
            )
    
    async def close(self) -> None:
        """Close CSV file."""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None
            self.csv_writer = None
            logger.debug(f"CSV connector closed: {self.file_path}")


class JSONConnector(BaseConnector):
    """
    JSON output connector.
    Appends data to JSON file or writes to new file.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.filename = config.get("filename", "output.json")
        self.mode = config.get("mode", "append")  # append or overwrite
        self.indent = config.get("indent", 2)
        self.file_path = None
        self.data = []
        
        # Ensure output directory exists
        output_dir = settings.json_output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.file_path = os.path.join(output_dir, self.filename)
    
    def get_type(self) -> str:
        return "json"
    
    async def connect(self) -> bool:
        """
        Load existing data if appending.
        """
        try:
            if self.mode == "append" and os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        self.data = existing_data
                    else:
                        self.data = [existing_data]
            
            logger.info(f"JSON connector connected to {self.file_path}")
            return True
            
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in {self.file_path}, starting fresh")
            self.data = []
            return True
        except Exception as e:
            logger.error(f"Failed to connect JSON connector: {e}")
            return False
    
    async def send(self, data: Dict[str, Any]) -> ConnectorResult:
        """
        Append data to JSON file.
        
        Args:
            data: Data dictionary to append
            
        Returns:
            ConnectorResult
        """
        try:
            self.data.append(data)
            
            # Write entire data array to file
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=self.indent, default=str)
            
            logger.debug(f"Appended data to JSON: {self.file_path}")
            return ConnectorResult(
                success=True,
                output_path=self.file_path
            )
            
        except Exception as e:
            logger.error(f"Failed to write to JSON: {e}")
            return ConnectorResult(
                success=False,
                error_message=f"JSON write error: {str(e)}"
            )
    
    async def close(self) -> None:
        """JSON connector cleanup."""
        self.data = []
        logger.debug(f"JSON connector closed: {self.file_path}")


class SQLiteConnector(BaseConnector):
    """
    SQLite output connector.
    Inserts data into database tables.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.database_path = config.get("database", settings.sqlite_output_db)
        self.table = config.get("table", "docflow_output")
        self.create_table = config.get("create_table", True)
        self.connection = None
        
        # Ensure output directory exists
        output_dir = os.path.dirname(self.database_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
    
    def get_type(self) -> str:
        return "sqlite"
    
    async def connect(self) -> bool:
        """
        Connect to SQLite database and ensure table exists.
        """
        try:
            self.connection = sqlite3.connect(self.database_path)
            self.connection.row_factory = sqlite3.Row
            
            if self.create_table:
                self._ensure_table()
            
            logger.info(f"SQLite connector connected to {self.database_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect SQLite connector: {e}")
            return False
    
    def _ensure_table(self) -> None:
        """Create table if it doesn't exist."""
        cursor = self.connection.cursor()
        
        # Get column names from config or use default
        columns = self.config.get("columns")
        if not columns:
            # Default columns based on typical document data
            columns = [
                "id INTEGER PRIMARY KEY AUTOINCREMENT",
                "document_type TEXT",
                "extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "data_json TEXT"
            ]
        
        columns_sql = ", ".join(columns)
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table} (
            {columns_sql}
        )
        """
        
        cursor.execute(create_table_sql)
        self.connection.commit()
        logger.debug(f"Ensured table exists: {self.table}")
    
    async def send(self, data: Dict[str, Any]) -> ConnectorResult:
        """
        Insert data into SQLite table.
        
        Args:
            data: Data dictionary to insert
            
        Returns:
            ConnectorResult
        """
        try:
            if not self.connection:
                return ConnectorResult(
                    success=False,
                    error_message="SQLite connector not connected"
                )
            
            cursor = self.connection.cursor()
            
            # Convert data to JSON for storage
            data_json = json.dumps(data, default=str)
            
            # Insert data
            insert_sql = f"""
            INSERT INTO {self.table} (document_type, data_json)
            VALUES (?, ?)
            """
            
            document_type = data.get("document_type", "unknown")
            cursor.execute(insert_sql, (document_type, data_json))
            self.connection.commit()
            
            row_id = cursor.lastrowid
            logger.debug(f"Inserted data into SQLite (row_id={row_id})")
            
            return ConnectorResult(
                success=True,
                output_path=self.database_path,
                response_data={"row_id": row_id}
            )
            
        except Exception as e:
            logger.error(f"Failed to insert into SQLite: {e}")
            return ConnectorResult(
                success=False,
                error_message=f"SQLite insert error: {str(e)}"
            )
    
    async def close(self) -> None:
        """Close SQLite connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.debug(f"SQLite connector closed: {self.database_path}")


class WebhookConnector(BaseConnector):
    """
    Webhook output connector.
    Sends data via HTTP POST to external URL.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config.get("url")
        self.method = config.get("method", "POST")
        self.headers = config.get("headers", {"Content-Type": "application/json"})
        self.timeout = config.get("timeout", settings.webhook_timeout_seconds)
        self.client = None
        
        if not self.url:
            raise ValueError("Webhook URL is required")
    
    def get_type(self) -> str:
        return "webhook"
    
    async def connect(self) -> bool:
        """
        Initialize HTTP client.
        """
        try:
            self.client = httpx.AsyncClient(timeout=self.timeout)
            logger.info(f"Webhook connector initialized for {self.url}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize webhook connector: {e}")
            return False
    
    async def send(self, data: Dict[str, Any]) -> ConnectorResult:
        """
        Send data to webhook URL.
        
        Args:
            data: Data dictionary to send
            
        Returns:
            ConnectorResult
        """
        try:
            if not self.client:
                return ConnectorResult(
                    success=False,
                    error_message="Webhook connector not connected"
                )
            
            # Send request
            response = await self.client.request(
                method=self.method,
                url=self.url,
                json=data,
                headers=self.headers
            )
            
            # Check response
            response.raise_for_status()
            
            # Parse response if it's JSON
            response_data = None
            if response.headers.get("content-type", "").startswith("application/json"):
                response_data = response.json()
            
            logger.debug(f"Webhook request successful: {response.status_code}")
            return ConnectorResult(
                success=True,
                output_path=self.url,
                response_data=response_data,
                status_code=response.status_code
            )
            
        except httpx.TimeoutException:
            logger.error(f"Webhook request timeout: {self.url}")
            return ConnectorResult(
                success=False,
                error_message="Request timeout",
                status_code=408
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Webhook HTTP error: {e.response.status_code}")
            return ConnectorResult(
                success=False,
                error_message=f"HTTP error: {e.response.status_code}",
                status_code=e.response.status_code
            )
        except Exception as e:
            logger.error(f"Webhook request failed: {e}")
            return ConnectorResult(
                success=False,
                error_message=f"Request failed: {str(e)}"
            )
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.debug(f"Webhook connector closed: {self.url}")


class ConnectorRegistry:
    """
    Registry for managing output connectors.
    """
    
    CONNECTOR_TYPES = {
        "csv": CSVConnector,
        "json": JSONConnector,
        "sqlite": SQLiteConnector,
        "webhook": WebhookConnector,
    }
    
    def __init__(self):
        self.connectors: Dict[str, BaseConnector] = {}
    
    def create_connector(self, 
                        connector_type: str, 
                        config: Dict[str, Any]) -> BaseConnector:
        """
        Create a connector instance.
        
        Args:
            connector_type: Type of connector (csv, json, sqlite, webhook)
            config: Connector configuration
            
        Returns:
            BaseConnector instance
        """
        connector_class = self.CONNECTOR_TYPES.get(connector_type.lower())
        if not connector_class:
            raise ValueError(f"Unknown connector type: {connector_type}")
        
        return connector_class(config)
    
    async def send_to_connectors(self,
                                data: Dict[str, Any],
                                connector_configs: List[Dict[str, Any]]) -> List[ConnectorResult]:
        """
        Send data to multiple connectors.
        
        Args:
            data: Data to send
            connector_configs: List of connector configurations
            
        Returns:
            List of connector results
        """
        results = []
        
        for config in connector_configs:
            connector_type = config.get("type")
            if not connector_type:
                logger.warning("Connector config missing type, skipping")
                continue
            
            try:
                connector = self.create_connector(connector_type, config)
                async with connector:
                    result = await connector.send(data)
                    results.append(result)
                    
            except Exception as e:
                logger.error(f"Failed to process connector {connector_type}: {e}")
                results.append(ConnectorResult(
                    success=False,
                    error_message=f"Connector error: {str(e)}"
                ))
        
        return results


# Global connector registry
connector_registry = ConnectorRegistry()