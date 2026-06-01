# Industrial Equipment Specs Discovery & RAG Platform — System Documentation

Welcome to the comprehensive technical documentation for the **Industrial Equipment Specs Discovery & RAG Platform**. This document serves as the single source of truth for the platform architecture, relational data models, dynamic configurations, modular packages, and operational flows.

---

## 🔄 1. System Architecture & Operational Flows

The platform is designed as an enterprise-grade, multi-category industrial equipment specifications crawler and retrieval-augmented generation (RAG) catalog. It supports diverse equipment masters (e.g. **Pumps, Compressors, Valves**) and features a decoupled architecture:

*   **Frontend**: Vue 3 + Vuetify 3 (translucent dark glassmorphism styling).
*   **Backend**: FastAPI (Python) + Background Task workers.
*   **Database**: PostgreSQL 18 with `pgvector` nearest-neighbor indexing.
*   **AI Engine**: Google Gemini (Flash series) via the new `google-genai` SDK.

### A. End-to-End Sequence Flow
The diagram below shows the interactions during database initialization, selective manufacturer harvesting, specs compilation, and taxonomy administration.

```mermaid
sequenceDiagram
    autonumber
    participant User as "End User"
    participant FE as "Vue 3 / Vuetify Dashboard"
    participant BE as "FastAPI (Modular Router)"
    participant DB as "PostgreSQL (pump_db)"
    participant AI as "Google Gemini API"

    %% Database Init & Migration
    User->>FE: Click Init PostgreSQL & Settings
    FE->>BE: POST to /api/init-db
    BE->>DB: Apply table rename migrations & append is_approved / is_harvested flags
    BE->>DB: Seed EquipmentMaster ("Compressor", "Pump", "Valve") & system_settings
    DB-->>BE: Seeding and migration completed
    BE-->>FE: Return success snackbar & toast

    %% Taxonomy CRUD
    User->>FE: Navigate to Taxonomy panel & add "Solenoid Valves" under Valve
    FE->>BE: POST to /api/equipment-types {"name": "Solenoid Valves", "master_id": 3}
    BE->>DB: Insert new EquipmentType row
    DB-->>BE: Type created
    BE-->>FE: Re-render dynamic taxonomy tree

    %% Selective Specs Harvesting
    User->>FE: Select "Pump" type, choose specific Manufacturers, toggle unharvested
    FE->>BE: POST to /api/crawl/harvest-specs?manufacturer_ids=[1,2]&only_unharvested=true
    BE-->>FE: Return background job started
    
    Note over BE, AI: Background Specs Harvesting Pipeline
    BE->>DB: Insert CrawlHistory row with status active
    BE->>DB: Query approved / unharvested manufacturers matching IDs
    DB-->>BE: Return Manufacturer profiles
    BE->>AI: Stage 2: Discover Models for target manufacturers
    AI-->>BE: Return model lineups JSON
    
    Note over BE, DB: RAG Two-Tier Deduplication
    BE->>DB: Cosine similarity vector match (similarity >= 0.92)
    DB-->>BE: Return match or None
    alt Model is unique
        BE->>DB: Create new Model record
    else Model is duplicate
        BE->>DB: Skip insert & link cached specs
    end

    BE->>BE: Stage 3: Fetch spec sheets & scrape dynamic tables
    BE->>AI: Extract specs engineering attributes from scraped text
    AI-->>BE: Return TechnicalSpecsSchema structured JSON
    BE->>DB: Save TechnicalAttribute specs JSON & set Model.is_harvested = True
    BE->>DB: Set Manufacturer.is_harvested = True
    BE->>DB: Update CrawlHistory with status completed
    BE-->>User: Update live status tracker & counts
```

---

## 🔒 2. Two-Tier Deduplication Pipeline Flow
To eliminate duplicate `equipment_type + manufacturer + model_name` sheets, the crawler runs a sequential two-tier RAG validation check:

```mermaid
flowchart TD
    A[New Model Discovered] --> B{Tier 1: Exact Name Match?}
    B -->|Yes: Case-insensitive match| C[Flag Duplicate]
    B -->|No exact match| D{Has Vector Embedding?}
    D -->|No embedding| E[Insert New Model]
    D -->|Yes embedding| F{Tier 2: Vector Similarity Match?}
    F -->|Cosine Distance <= 0.08| C
    F -->|Cosine Distance > 0.08| E
    C --> G[Merge Technical Specs & Embeddings]
    C --> H[Update Crawl Logs & Skip Scraping]
```

---

## 📊 3. Relational Database Schema

The platform maps the multi-category industrial taxonomy using a structured 3-level hierarchy linked directly to global manufacturer directories and technical specifications.

```mermaid
erDiagram
    system_settings {
        string key PK
        text value
        string value_type
        text description
    }
    equipment_master ||--o{ equipment_type : has_many
    equipment_type ||--o{ equipment_subtypes : has_many
    equipment_type ||--o{ models : categorizes
    equipment_subtypes ||--o{ models : subcategorizes
    manufacturers ||--o{ models : manufactures
    models ||--|| technical_attributes : has_specs

    equipment_master {
        int id PK
        string name UK
        text description
    }
    equipment_type {
        int id PK
        int equipment_master_id FK
        string name UK
        text description
    }
    equipment_subtypes {
        int id PK
        int type_id FK
        string name
    }
    manufacturers {
        int id PK
        string name UK
        string country
        string website
        int founded_year
        text description
        boolean is_approved
        boolean is_harvested
    }
    models {
        int id PK
        int equipment_master_id FK
        int equipment_type_id FK
        int equipment_subtype_id FK
        int manufacturer_id FK
        string model_name
        string series
        text product_url
        boolean is_approved
        boolean is_harvested
        array embedding
    }
    technical_attributes {
        int model_id PK
        jsonb attributes
        timestamp updated_at
    }
    crawl_history {
        int id PK
        timestamp started_at
        timestamp completed_at
        string status
        string compressor_type
        int new_manufacturers_count
        int new_models_count
        int total_specs_enriched
        text log_message
    }
```

### Core Tables & Descriptions

#### 1. `system_settings`
Stores dynamic crawler quotas, Gemini model versions, and vector thresholds live inside PostgreSQL.
*   `key` (`String(100)`, Primary Key): Setting key name (e.g. `MAX_MODELS_PER_MANUFACTURER`).
*   `value` (`Text`, Not Null): Setting value saved as string.
*   `value_type` (`String(50)`): Type indicator (`int`, `float`, `bool`, `str`) for auto-type-casting.
*   `description` (`Text`): Helper descriptions.

#### 2. `equipment_master`
Stores high-level master equipment classifications.
*   `id` (`Integer`, Primary Key, Autoincrement)
*   `name` (`String(100)`, Unique, Not Null): e.g. `"Compressor"`, `"Pump"`, `"Valve"`.
*   `description` (`Text`, Nullable)

#### 3. `equipment_type` (Formerly `compressor_types`)
Stores specific equipment product categories under a master.
*   `equipment_master_id` (`Integer`, Foreign Key referencing `equipment_master.id` on delete `CASCADE`, Not Null)
*   `name` (`String(100)`, Unique, Indexed, Not Null): e.g. `"Air Compressors"`, `"Centrifugal Pumps"`.

#### 4. `equipment_subtypes` (Formerly `compressor_subtypes`)
Stores divisions and architectures under a type category.
*   `type_id` (`Integer`, Foreign Key referencing `equipment_type.id` on delete `CASCADE`, Not Null)
*   `name` (`String(100)`, Not Null): e.g. `"Scroll"`, `"Screw"`, `"Plunger"`.

#### 5. `manufacturers`
Stores global manufacturer directories.
*   `is_approved` (`Boolean`, Not Null, Default `False`): Toggle to grant crawling permission.
*   `is_harvested` (`Boolean`, Not Null, Default `False`): True if Stage 2 (model discovery) has run.

#### 6. `models`
Tracks specific commercial manufactured model lines.
*   `equipment_master_id` (`Integer`, FK referencing `equipment_master.id`)
*   `equipment_type_id` (`Integer`, FK referencing `equipment_type.id`)
*   `equipment_subtype_id` (`Integer`, FK referencing `equipment_subtypes.id`)
*   `is_approved` (`Boolean`, Default `False`): Model-level approval for frontend specs grid display.
*   `is_harvested` (`Boolean`, Default `False`): True if Stage 3 (specifications enrichment) has run.

---

## 📁 4. Modular Codebase Package Layout

To maximize maintainability and scalability, the backend was decoupled from the 760-line main script into an API router structure:

*   `main.py`: Thin CLI parser and server boot wrapper.
*   `api/router.py`: Unified registry combining all domain routing nodes.
*   `api/system.py`: Relational settings CRUD and database schema health controllers.
*   `api/taxonomy.py`: Transactional Master, Type, and Subtype taxonomy CRUD endpoints and nested tree mappings.
*   `api/manufacturers.py`: Manufacturer directory listings and website approvals.
*   `api/models.py`: Specs catalog lists, sliding drawers details, and model-level catalog approvals.
*   `api/crawler.py`: Background thread pipeline triggers and history logs.
*   `utils/crawler_orchestrator.py`: Progress state telemetry manager and background crawl handlers.
*   `tests/test_integration.py`: Fully modularized integration test package.

---

## 💻 5. Operational Commands & Logs

Use these PowerShell commands on Windows to manage, build, run, and verify the application:

### A. Run API Server & Client
```powershell
# 1. Start the backend API server reloading continuously on port 8000
python main.py --server >> backend.log 2>&1

# 2. Run the Vue 3 Vite development server on port 5173
cd frontend
npm run dev

# 3. Monitor backend uvicorn and play crawler logs in real-time
Get-Content backend.log -Wait -Tail 50
```

### B. Run the Modular Verification Suite
```powershell
# Execute the self-contained ASCII-safe database, CRUD, settings, and RAG vector test suite
python tests/test_integration.py
```

### C. Compile production Frontend Assets
```powershell
# Run Vite production asset pipeline to verify syntax safety and minification
cd frontend
npm run build
```
