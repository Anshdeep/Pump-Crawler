# Implementation Plan — Crawl Telemetry & History Log

We will implement a complete, robust crawl history logging system to record telemetry metrics (runs count, duration, discovery rates) and present it elegantly in the UI.

## User Review Required

No breaking changes. The Postgres schema will be automatically migrated during database initialization.

---

## Proposed Changes

### 1. Database Layer

#### [MODIFY] [models.py](file:///d:/apps/AI/Pump-Crawler/Compressor/database/models.py)
Create a new SQLAlchemy model `CrawlHistory` representing crawl runs:
```python
class CrawlHistory(Base):
    __tablename__ = "crawl_history"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False)  # "active", "completed", "failed"
    compressor_type = Column(String(100), nullable=True)
    new_manufacturers_count = Column(Integer, default=0)
    new_models_count = Column(Integer, default=0)
    total_specs_enriched = Column(Integer, default=0)
    log_message = Column(Text, nullable=True)
```

---

### 2. Backend Orchestration & APIs

#### [MODIFY] [main.py](file:///d:/apps/AI/Pump-Crawler/Compressor/main.py)
- **Background Orchestrator telemetry Capture**:
  - In `run_crawling_background`, query and store the count of existing `Manufacturer` and `Model` records before the run begins.
  - Insert an initial `CrawlHistory` record with status `"active"`.
  - Upon success, query the counts again, compute the increments (`final - initial`), and update the history row with metrics and status `"completed"`.
  - In case of failure, capture the traceback or error message and set the status to `"failed"`.
- **API Endpoint**:
  - Add `GET /api/crawl/history` to retrieve historical runs ordered by start timestamp.

---

### 3. Frontend Integration

#### [MODIFY] [compressors.js (Store)](file:///d:/apps/AI/Pump-Crawler/Compressor/frontend/src/store/compressors.js)
- Add `crawlHistory` array to state.
- Add Pinia action `fetchCrawlHistory()` to retrieve historical data via the backend API.
- Call this inside `triggerCrawl` and at page startup.

#### [MODIFY] [App.vue](file:///d:/apps/AI/Pump-Crawler/Compressor/frontend/src/App.vue)
- **History log Panel**: Add a card under **Live Crawler Tracker** in the Control Center tab to display the crawl log table.
- **Glassmorphic Data Table**:
  - Columns: Date/Time, target, Duration, Status, New Manufacturers, New Models, Specs Enriched.
  - Render status indicators as chips (`success` for Completed, `warning` for Active, `error` for Failed).

---

## Verification Plan

### Automated Build & DB Init
1. Execute `npm run build` to verify front-end components compilation.
2. Run database initialization `/api/init-db` to create the new `crawl_history` table dynamically in PostgreSQL.

### Manual Verification
1. Navigate to the **Control Center** tab in the browser.
2. Verify that the **Crawl Run History Log** panel appears at the bottom.
3. Click "Start Crawler Pipeline Task".
4. Confirm a new row is added immediately with status `Active`.
5. Upon crawl completion, confirm the status changes to `Completed` and displays the correct count increments (e.g. +3 manufacturers, +5 models).
