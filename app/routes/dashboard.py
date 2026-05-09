"""Dashboard routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Pipeline, Job, Document

router = APIRouter()


@router.get("/dashboard/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    try:
        # Pipeline count
        pipelines_result = await db.execute(select(Pipeline).where(Pipeline.is_active == True))
        pipeline_count = len(pipelines_result.scalars().all())
        
        # Job stats
        jobs_result = await db.execute(select(Job))
        all_jobs = jobs_result.scalars().all()
        total_jobs = len(all_jobs)
        completed_jobs = sum(1 for j in all_jobs if j.status == "completed")
        failed_jobs = sum(1 for j in all_jobs if j.status == "failed")
        
        # Document stats
        docs_result = await db.execute(select(Document))
        docs = docs_result.scalars().all()
        
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        return {
            "pipeline_count": pipeline_count,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "running_jobs": total_jobs - completed_jobs - failed_jobs,
            "total_documents": len(docs),
            "success_rate": round(success_rate, 1),
            "uptime_hours": 1.0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/pipelines")
async def get_pipeline_overview(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Pipeline))
        pipelines = result.scalars().all()
        
        items = []
        for p in pipelines:
            jobs_result = await db.execute(
                select(Job).where(Job.pipeline_id == p.id)
            )
            pipeline_jobs = jobs_result.scalars().all()
            
            items.append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "is_active": p.is_active,
                "total_jobs": len(pipeline_jobs),
                "completed_jobs": sum(1 for j in pipeline_jobs if j.status == "completed"),
                "failed_jobs": sum(1 for j in pipeline_jobs if j.status == "failed")
            })
        
        return {"items": items, "total": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/recent-activity")
async def get_recent_activity(limit: int = Query(10, ge=1, le=100),
                               db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Job).order_by(Job.created_at.desc()).limit(limit)
        )
        jobs = result.scalars().all()
        
        items = [{
            "id": j.id,
            "status": j.status,
            "pipeline_id": j.pipeline_id,
            "document_id": j.document_id,
            "created_at": str(j.created_at) if j.created_at else None,
            "completed_at": str(j.completed_at) if j.completed_at else None,
            "error_message": j.error_message
        } for j in jobs]
        
        return {"items": items, "total": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/system-health")
async def get_system_health(db: AsyncSession = Depends(get_db)):
    try:
        pipelines_result = await db.execute(select(Pipeline))
        pipelines = pipelines_result.scalars().all()
        active_pipelines = sum(1 for p in pipelines if p.is_active)
        
        jobs_result = await db.execute(select(Job))
        jobs = jobs_result.scalars().all()
        failed_24h = sum(1 for j in jobs if j.status == "failed" and 
                        j.created_at and j.created_at > datetime.utcnow() - timedelta(hours=24))
        
        return {
            "status": "healthy" if failed_24h == 0 else "degraded",
            "active_pipelines": active_pipelines,
            "recent_failures": failed_24h,
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
