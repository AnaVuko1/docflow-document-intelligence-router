"""Connector routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.engine.connectors import ConnectorRegistry

router = APIRouter()


@router.get("/connectors")
async def list_connectors(db: AsyncSession = Depends(get_db)):
    try:
        registry = ConnectorRegistry()
        connectors = registry.list_connectors()
        return {"connectors": connectors, "total": len(connectors)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connectors/{connector_type}")
async def get_connector_info(connector_type: str, db: AsyncSession = Depends(get_db)):
    try:
        registry = ConnectorRegistry()
        info = registry.get_connector_info(connector_type)
        if not info:
            raise HTTPException(status_code=404, detail=f"Connector {connector_type} not found")
        return info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
