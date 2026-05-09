"""
Seed data generator for DocFlow.
Creates sample pipeline definitions, uploads demo documents,
and runs processing jobs for the dashboard demo.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import AsyncSessionLocal, engine, Base
from app.models import Pipeline, Document, Job, ExtractionResult
import yaml


async def create_tables():
    """Create database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_pipelines():
    """Load YAML pipeline definitions into database."""
    pipelines_dir = Path(__file__).parent / "pipelines"
    
    async with AsyncSessionLocal() as db:
        for yaml_file in sorted(pipelines_dir.glob("*.yaml")):
            with open(yaml_file) as f:
                pipeline_yaml = yaml.safe_load(f)
            
            pipeline = Pipeline(
                name=pipeline_yaml["name"],
                description=pipeline_yaml.get("description", ""),
                version=int(pipeline_yaml.get("version", "1.0")),
                definition=pipeline_yaml,
                is_active=True
            )
            db.add(pipeline)
        
        await db.commit()
        print(f"✅ Seeded {len(list(pipelines_dir.glob('*.yaml')))} pipelines")


async def seed_documents_and_jobs():
    """Upload demo documents and create processing jobs."""
    demo_dir = Path(__file__).parent / "demo_data"
    
    doc_mapping = {
        "sample_invoice.txt": "invoice_processing",
        "sample_contract.txt": "contract_intelligence",
        "sample_receipt.txt": "receipt_scanner"
    }
    
    async with AsyncSessionLocal() as db:
        # Get pipelines
        from sqlalchemy import select
        pipelines_result = await db.execute(select(Pipeline))
        pipelines = {p.name.lower().replace(" ", "_").replace("pipeline", "").strip("_"): p 
                     for p in pipelines_result.scalars().all()}
        
        job_count = 0
        for filename, pipeline_key in doc_mapping.items():
            filepath = demo_dir / filename
            if not filepath.exists():
                print(f"⚠️  Demo file not found: {filename}")
                continue
            
            with open(filepath) as f:
                content = f.read()
            
            # Create document record
            doc = Document(
                filename=filename,
                original_filename=filename,
                file_path=str(filepath),
                content=content,
                file_size=len(content),
                mime_type="text/plain",
                status="uploaded"
            )
            db.add(doc)
            await db.flush()
            
            # Find matching pipeline
            pipeline = pipelines.get(pipeline_key)
            if pipeline:
                # Create job
                job = Job(
                    document_id=doc.id,
                    pipeline_id=pipeline.id,
                    status="completed",
                    created_at=datetime.utcnow() - timedelta(hours=job_count),
                    completed_at=datetime.utcnow() - timedelta(hours=job_count, minutes=-2)
                )
                db.add(job)
                job_count += 1
        
        await db.commit()
        print(f"✅ Seeded {job_count} documents with processing jobs")
        
        # Create a few more historical jobs for the dashboard
        from sqlalchemy import select as sel
        docs_result = await db.execute(sel(Document))
        docs = docs_result.scalars().all()
        pipes_result = await db.execute(sel(Pipeline))
        all_pipes = pipes_result.scalars().all()
        
        if docs and all_pipes:
            statuses = ["completed", "completed", "completed", "failed", "completed"]
            for i, status in enumerate(statuses):
                job = Job(
                    document_id=docs[i % len(docs)].id,
                    pipeline_id=all_pipes[i % len(all_pipes)].id,
                    status=status,
                    created_at=datetime.utcnow() - timedelta(days=i + 1),
                    completed_at=datetime.utcnow() - timedelta(days=i + 1, minutes=-3)
                )
                db.add(job)
            await db.commit()
            print(f"✅ Added {len(statuses)} historical jobs")


async def main():
    """Run seed data generation."""
    print("🌱 Seeding DocFlow database...")
    
    await create_tables()
    await seed_pipelines()
    await seed_documents_and_jobs()
    
    print("✅ Seed complete! Run 'python app/main.py' to start DocFlow.")
    print("   Visit http://localhost:8000 for the dashboard.")
    print("   API docs at http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())
