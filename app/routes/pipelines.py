"""Pipeline routes."""
import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Pipeline

router = APIRouter()


@router.get("/pipelines")
async def list_pipelines(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    try:
        query = select(Pipeline)
        if active_only:
            query = query.where(Pipeline.is_active == True)
        
        count_result = await db.execute(select(Pipeline))
        total = len(count_result.scalars().all())
        
        query = query.offset(skip).limit(limit).order_by(Pipeline.created_at.desc())
        result = await db.execute(query)
        pipelines = result.scalars().all()
        
        items = [{"id": p.id, "name": p.name, "description": p.description,
                  "version": p.version, "is_active": p.is_active,
                  "definition": p.definition,
                  "created_at": str(p.created_at) if p.created_at else None}
                 for p in pipelines]
        
        return {"items": items, "total": total, "page": skip // limit + 1 if limit else 1,
                "size": limit}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: int, db: AsyncSession = Depends(get_db)):
    try:
        pipeline = await db.get(Pipeline, pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")
        return {"id": pipeline.id, "name": pipeline.name, "description": pipeline.description,
                "version": pipeline.version, "is_active": pipeline.is_active,
                "definition": pipeline.definition,
                "created_at": str(pipeline.created_at) if pipeline.created_at else None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipelines", status_code=status.HTTP_201_CREATED)
async def create_pipeline(definition: dict, db: AsyncSession = Depends(get_db)):
    try:
        if not isinstance(definition, dict):
            raise HTTPException(status_code=400, detail="Definition must be a dict")
        if "name" not in definition:
            raise HTTPException(status_code=400, detail="'name' is required")
        if "steps" not in definition:
            raise HTTPException(status_code=400, detail="'steps' is required")
        
        pipeline = Pipeline(
            name=definition["name"],
            description=definition.get("description", ""),
            version=definition.get("version", 1),
            definition=definition,
            is_active=True
        )
        db.add(pipeline)
        await db.commit()
        await db.refresh(pipeline)
        return {"id": pipeline.id, "name": pipeline.name, "description": pipeline.description,
                "version": pipeline.version, "is_active": pipeline.is_active,
                "created_at": str(pipeline.created_at) if pipeline.created_at else None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
