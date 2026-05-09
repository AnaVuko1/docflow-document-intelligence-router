# DocFlow — Document Intelligence Router

**Declarative document pipelines. Define. Route. Transform. Open-source infrastructure for document workflows.**

## 🚀 Core Insight

Document extraction is a solved commodity in 2026 (LlamaParse, Unstructured.io, etc.). The real gap is **ORCHESTRATION** — what happens AFTER extraction: classification, validation, transformation, and routing to destination systems.

DocFlow is the **Zapier for documents**.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DocFlow Pipeline Engine                  │
├─────────────────────────────────────────────────────────────┤
│  Document → Classifier → Extractor → Validator → Transformer │
│                 ↓                                           │
│           Multiple Output Connectors                       │
│                 ↓                                           │
│        CSV │ JSON │ SQLite │ Webhook │ ...                  │
└─────────────────────────────────────────────────────────────┘
```

## ✨ Features

- **Declarative Pipelines**: Define document workflows in clean YAML
- **Smart Classification**: Auto-detect document types (invoice, contract, receipt, etc.)
- **Multiple Extraction Strategies**: Regex, templates, and extensible LLM-based extraction
- **Schema Validation**: Business rules, type checking, and custom validation
- **Data Transformation**: Field mapping, format conversion, and normalization
- **Output Connectors**: Route validated data to CSV, JSON, SQLite, webhooks, and more
- **Web Dashboard**: Monitor pipelines, track jobs, and drill into results

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone and run
git clone https://github.com/docflow-dev/docflow.git
cd docflow
cp .env.example .env  # Optional: configure settings
docker-compose up -d
```

Open http://localhost:8000 to access the dashboard.

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Run database migrations and seed data
python -m alembic upgrade head
python seed_data.py

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📋 API Reference

All endpoints are available at `/api/v1/` with Swagger documentation at `/docs`.

**Core endpoints:**
- `POST /api/v1/pipelines` — Create pipeline definition
- `GET /api/v1/pipelines` — List all pipelines
- `POST /api/v1/pipelines/{id}/run` — Execute pipeline on a document
- `POST /api/v1/documents/upload` — Upload document for processing
- `GET /api/v1/jobs/{id}` — Get job status + results
- `GET /api/v1/dashboard/stats` — Dashboard statistics

## 📁 Pre-built Pipelines

DocFlow comes with three production-ready pipelines:

### 1. Invoice Processing
**File:** `pipelines/invoice_processing.yaml`
Extracts: invoice_number, vendor_name, date, due_date, line_items, subtotal, tax, total

### 2. Contract Intelligence  
**File:** `pipelines/contract_intelligence.yaml`
Extracts: parties, effective_date, expiration_date, contract_value, key_terms, governing_law

### 3. Receipt Scanner
**File:** `pipelines/receipt_scanner.yaml`
Extracts: merchant, date, total, payment_method, tax

Each pipeline includes classification, extraction, validation, transformation, and routing steps.

## 🔧 Pipeline Configuration Example

```yaml
name: "Invoice Processing Pipeline"
description: "Extract and validate invoice data"
steps:
  - type: classify
    config:
      target_types: [invoice, receipt]
  - type: extract
    config:
      strategy: regex
      fields:
        - name: invoice_number
          pattern: "Invoice\\s*#?\\s*([A-Z0-9-]+)"
        - name: total_amount
          pattern: "Total\\s*[:$]\\s*([\\d,]+\\.\\d{2})"
  - type: validate
    config:
      rules:
        - field: total_amount
          rule: "value > 0"
  - type: transform
    config:
      mappings:
        invoice_number: "invoice_id"
        total_amount: "amount"
  - type: route
    config:
      destinations:
        - type: csv
          filename: "invoices_export.csv"
        - type: sqlite
          table: "processed_invoices"
```

## 🧪 Testing

Run the test suite:

```bash
pytest tests/ -v
```

## 🐳 Docker Deployment

Build and run with Docker Compose:

```bash
docker-compose up --build
```

The service will be available at http://localhost:8000 with:
- Web dashboard at `/`
- API documentation at `/docs`
- API endpoints at `/api/v1/*`

## 📊 Dashboard Features

- **Pipeline Overview**: Active pipelines and recent jobs
- **Job Status**: Real-time tracking with timeline visualization
- **Processing Stats**: Success rate, throughput, and error rates
- **Quick Upload**: Direct document processing from the UI
- **Job Drill-down**: View extracted fields, validation errors, and execution logs

## 🔌 Extending DocFlow

### Adding Custom Extractors
Extend the `BaseExtractor` class in `app/engine/extractors.py`

### Creating New Connectors
Implement the `BaseConnector` interface in `app/engine/connectors.py`

### Custom Validation Rules
Add validation functions to `app/engine/validators.py` and reference them in pipeline YAML

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

---

*Built with ❤️ by the DocFlow team | [GitHub](https://github.com/docflow-dev/docflow)*