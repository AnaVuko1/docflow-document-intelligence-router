"""Job routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Job, Document, Pipeline

router = APIRouter()


@router.get("/jobs")
async def list_jobs(skip: int = Query(0), limit: int = Query(100),
                     status_filter: str = Query(None),
                     db: AsyncSession = Depends(get_db)):
    try:
        query = select(Job)
        if status_filter:
            query = query.where(Job.status == status_filter)
        
        count_result = await db.execute(select(Job))
        total = len(count_result.scalars().all())
        
        query = query.offset(skip).limit(limit).order_by(Job.created_at.desc())
        result = await db.execute(query)
        jobs = result.scalars().all()
        
        items = [{"id": j.id, "document_id": j.document_id, "pipeline_id": j.pipeline_id,
                  "status": j.status, "error_message": j.error_message,
                  "created_at": str(j.created_at) if j.created_at else None,
                  "completed_at": str(j.completed_at) if j.completed_at else None}
                 for j in jobs]
        return {"items": items, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    try:
        job = await db.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        return {"id": job.id, "document_id": job.document_id, "pipeline_id": job.pipeline_id,
                "status": job.status, "error_message": job.error_message,
                "created_at": str(job.created_at) if job.created_at else None,
                "completed_at": str(job.completed_at) if job.completed_at else None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
