"""Document routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Document, Job

router = APIRouter()

UPLOAD_DIR = "/tmp/docflow_uploads"
import os
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/documents")
async def list_documents(skip: int = Query(0), limit: int = Query(100),
                          db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Document).offset(skip).limit(limit).order_by(Document.uploaded_at.desc()))
        docs = result.scalars().all()
        count_result = await db.execute(select(Document))
        total = len(count_result.scalars().all())
        items = [{"id": d.id, "filename": d.filename, "original_filename": d.original_filename,
                  "file_size": d.file_size, "mime_type": d.mime_type, "status": d.status,
                  "uploaded_at": str(d.uploaded_at) if d.uploaded_at else None}
                 for d in docs]
        return {"items": items, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(None), content: str = Form(None),
                           db: AsyncSession = Depends(get_db)):
    try:
        if file:
            raw = await file.read()
            text = raw.decode("utf-8", errors="replace")
            doc = Document(filename=file.filename, original_filename=file.filename,
                          file_path=f"{UPLOAD_DIR}/{file.filename}", content=text,
                          file_size=len(raw), mime_type=file.content_type or "text/plain",
                          status="uploaded")
        elif content:
            doc = Document(filename="text_input.txt", original_filename="text_input.txt",
                          file_path=f"{UPLOAD_DIR}/text_input.txt", content=content,
                          file_size=len(content), mime_type="text/plain", status="uploaded")
        else:
            raise HTTPException(status_code=400, detail="File or content required")
        
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        return {"id": doc.id, "filename": doc.filename, "status": doc.status,
                "uploaded_at": str(doc.uploaded_at) if doc.uploaded_at else None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}")
async def get_document(document_id: int, db: AsyncSession = Depends(get_db)):
    try:
        doc = await db.get(Document, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        return {"id": doc.id, "filename": doc.filename, "content": doc.content,
                "mime_type": doc.mime_type, "status": doc.status,
                "uploaded_at": str(doc.uploaded_at) if doc.uploaded_at else None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
