import time
from datetime import datetime
from sqlalchemy.orm import Session
import database.connection as connection
import database.crud as crud
from database.models import Model, EquipmentType, Manufacturer, TechnicalAttribute, CrawlHistory, EquipmentMaster

import stages.stage1_manufacturers as stage1
import stages.stage2_models        as stage2
import stages.stage3_attributes    as stage3

# ── Global Crawler Progress State ──────────────────────────────────────────

CRAWL_PROGRESS = {
    "active": False,
    "compressor_type": None,  # Keep category name compatible with frontend
    "stage": "idle",
    "percent": 0,
    "status_msg": "System idle",
    "started_at": None,
    "completed_at": None,
    "discovered_manufacturers": 0,
    "discovered_models": 0,
    "enriched_records": 0,
}

def _update_progress(stage: str, percent: int, msg: str, **kwargs):
    global CRAWL_PROGRESS
    CRAWL_PROGRESS["stage"] = stage
    CRAWL_PROGRESS["percent"] = percent
    CRAWL_PROGRESS["status_msg"] = msg
    for k, v in kwargs.items():
        CRAWL_PROGRESS[k] = v

# ── Global Cancellation State ──────────────────────────────────────────────
_CRAWL_STOP_REQUESTED = False

def request_crawl_stop():
    global _CRAWL_STOP_REQUESTED
    _CRAWL_STOP_REQUESTED = True
    print("[System] Crawl stop request received. Hailing active crawlers...")

def check_cancel():
    global _CRAWL_STOP_REQUESTED
    if _CRAWL_STOP_REQUESTED:
        raise InterruptedError("Crawl stopped by user request.")


# ── Dynamic Setting Loader Helper ──────────────────────────────────────────

def _get_db_settings():
    """Retrieve runtime crawler configurations from system_settings table."""
    db = next(connection.get_db())
    try:
        max_mfrs = crud.get_setting_typed(db, "MAX_MANUFACTURERS_PER_TYPE", 3)
        max_models = crud.get_setting_typed(db, "MAX_MODELS_PER_MANUFACTURER", 5)
        delay = crud.get_setting_typed(db, "REQUEST_DELAY_SECONDS", 4.0)
        cache_on = crud.get_setting_typed(db, "CACHE_ENABLED", True)
        model_name = crud.get_setting(db, "GEMINI_MODEL", "gemini-2.5-flash")
        similarity = crud.get_setting_typed(db, "RAG_SIMILARITY_THRESHOLD", 0.92)
        return {
            "max_mfrs": max_mfrs,
            "max_models": max_models,
            "delay": delay,
            "cache_on": cache_on,
            "model_name": model_name,
            "similarity": similarity
        }
    finally:
        db.close()

# ── Background Process Operations ──────────────────────────────────────────

def run_manufacturer_discovery_background(
    equipment_master_id: int | None,
    equipment_type_id: int | None,
    no_cache: bool
):
    """Stage 1: Discover manufacturers for a given equipment master/type (or all types)."""
    global CRAWL_PROGRESS, _CRAWL_STOP_REQUESTED
    _CRAWL_STOP_REQUESTED = False
    
    CRAWL_PROGRESS["active"] = True
    CRAWL_PROGRESS["started_at"] = datetime.now().isoformat()
    CRAWL_PROGRESS["completed_at"] = None
    CRAWL_PROGRESS["discovered_manufacturers"] = 0
    CRAWL_PROGRESS["discovered_models"] = 0
    CRAWL_PROGRESS["enriched_records"] = 0

    db = next(connection.get_db())
    
    # Resolve display name for progress tracking
    target_name = "All Categories"
    if equipment_type_id:
        etype = db.query(EquipmentType).filter(EquipmentType.id == equipment_type_id).first()
        if etype:
            target_name = etype.name
    elif equipment_master_id:
        master = db.query(EquipmentMaster).filter(EquipmentMaster.id == equipment_master_id).first()
        if master:
            target_name = f"All {master.name} types"
    CRAWL_PROGRESS["compressor_type"] = target_name

    history_record = CrawlHistory(
        started_at=datetime.now(),
        status="active",
        compressor_type=target_name,
        log_message="Manufacturer discovery background task started (Stage 1)."
    )
    db.add(history_record)
    db.commit()
    db.refresh(history_record)

    initial_mfrs = db.query(Manufacturer).count()

    try:
        # Load configurable database settings
        settings = _get_db_settings()
        import config
        config.CACHE_ENABLED = False if no_cache else settings["cache_on"]
        
        # Pull only the equipment types belonging to the requested master/type.
        # Always apply master filter first so a stale type_id can't pull in
        # types from a different master category (e.g. Compressor when Pump is selected).
        query_etypes = db.query(EquipmentType)
        if equipment_master_id:
            query_etypes = query_etypes.filter(EquipmentType.equipment_master_id == equipment_master_id)
        if equipment_type_id:
            query_etypes = query_etypes.filter(EquipmentType.id == equipment_type_id)
        etype_objs = query_etypes.all()

        # Fallback: if a specific type_id was given but returned nothing (stale selection),
        # drop the type filter and crawl all types under the selected master instead.
        if not etype_objs and equipment_type_id and equipment_master_id:
            print(f"[WARN] type_id={equipment_type_id} not found under master_id={equipment_master_id}. "
                  f"Falling back to all types under master_id={equipment_master_id}.")
            etype_objs = db.query(EquipmentType).filter(
                EquipmentType.equipment_master_id == equipment_master_id
            ).all()
        
        if not etype_objs:
            raise ValueError(
                f"No equipment types found for master_id={equipment_master_id}, type_id={equipment_type_id}. "
                "Go to the Taxonomy tab and ensure equipment types exist under this master category."
            )

        # Assemble list of category dicts mimicking compressors.json
        compressors_list = []
        for et in etype_objs:
            subtypes = [sub.name for sub in et.subtypes]
            compressors_list.append({
                "id": et.id,
                "type": et.name,
                "equipment_master_id": et.equipment_master_id,
                "subtypes": subtypes,
                "applications": ["Industrial processing"]
            })

        # ── Stage 1 Run ──
        _update_progress("Stage 1: Manufacturers", 50, f"Discovering manufacturers for {[c['type'] for c in compressors_list]}")
        
        # Override config limits
        import config
        config.MAX_MANUFACTURERS_PER_TYPE = settings["max_mfrs"]
        
        mfrs_data = stage1.run(compressors_list, db=db, check_cancel=check_cancel)
        total_mfrs = sum(len(v) for v in mfrs_data.values())

        CRAWL_PROGRESS["completed_at"] = datetime.now().isoformat()
        _update_progress(
            "Completed", 
            100, 
            f"Successfully discovered {total_mfrs} manufacturers for validation!",
            discovered_manufacturers=total_mfrs
        )

        final_mfrs = db.query(Manufacturer).count()
        history_record.status = "completed"
        history_record.completed_at = datetime.now()
        history_record.new_manufacturers_count = max(0, final_mfrs - initial_mfrs)
        history_record.log_message = f"Discovery complete. Found {history_record.new_manufacturers_count} new manufacturer profiles."
        db.commit()

    except Exception as e:
        print(f"[BG Discovery Error] {e}")
        is_stopped = isinstance(e, InterruptedError) or "stopped by user" in str(e).lower()
        if is_stopped:
            _update_progress("Stopped", CRAWL_PROGRESS["percent"], "Crawl stopped by user request.")
            history_record.status = "stopped"
            history_record.completed_at = datetime.now()
            history_record.log_message = "Crawl stopped by user request."
        else:
            _update_progress("Failed", 0, f"Error occurred: {str(e)}")
            history_record.status = "failed"
            history_record.completed_at = datetime.now()
            history_record.log_message = f"Error: {str(e)}"
        db.commit()
    finally:
        CRAWL_PROGRESS["active"] = False
        db.close()


def run_model_discovery_background(
    manufacturer_ids: list[int] | None, 
    only_unharvested: bool, 
    no_cache: bool,
    equipment_master_id: int | None = None,
    equipment_type_id: int | None = None,
    equipment_subtype_id: int | None = None
):
    """Stage 2: Run model lineup discovery on approved manufacturers."""
    global CRAWL_PROGRESS, _CRAWL_STOP_REQUESTED
    _CRAWL_STOP_REQUESTED = False

    CRAWL_PROGRESS["active"] = True
    CRAWL_PROGRESS["compressor_type"] = "Approved Manufacturers"
    CRAWL_PROGRESS["started_at"] = datetime.now().isoformat()
    CRAWL_PROGRESS["completed_at"] = None
    CRAWL_PROGRESS["discovered_manufacturers"] = 0
    CRAWL_PROGRESS["discovered_models"] = 0
    CRAWL_PROGRESS["enriched_records"] = 0

    db = next(connection.get_db())

    history_record = CrawlHistory(
        started_at=datetime.now(),
        status="active",
        compressor_type="Approved Manufacturers",
        log_message="Approved model lineup discovery background task started (Stage 2)."
    )
    db.add(history_record)
    db.commit()
    db.refresh(history_record)

    initial_models = db.query(Model).count()

    try:
        # Load settings
        settings = _get_db_settings()
        import config
        config.CACHE_ENABLED = False if no_cache else settings["cache_on"]
        config.MAX_MODELS_PER_MANUFACTURER = settings["max_models"]
        
        # Load all approved manufacturers from PostgreSQL
        mfr_query = db.query(Manufacturer).filter(Manufacturer.is_approved == True)
        if manufacturer_ids:
            mfr_query = mfr_query.filter(Manufacturer.id.in_(manufacturer_ids))
        if only_unharvested:
            mfr_query = mfr_query.filter(Manufacturer.is_harvested == False)
            
        # Apply category filters to filter manufacturers that are associated with models in this category
        if equipment_master_id or equipment_type_id or equipment_subtype_id:
            mfr_sub = db.query(Model.manufacturer_id)
            if equipment_master_id:
                mfr_sub = mfr_sub.filter(Model.equipment_master_id == equipment_master_id)
            if equipment_type_id:
                mfr_sub = mfr_sub.filter(Model.equipment_type_id == equipment_type_id)
            if equipment_subtype_id:
                mfr_sub = mfr_sub.filter(Model.equipment_subtype_id == equipment_subtype_id)
            mfr_query = mfr_query.filter(Manufacturer.id.in_(mfr_sub))
            
        mfr_objs = mfr_query.all()
        if not mfr_objs:
            raise ValueError("No approved/selected manufacturers to crawl! Verify approvals in the Manufacturers tab.")

        CRAWL_PROGRESS["discovered_manufacturers"] = len(mfr_objs)
        print(f"[BG Model Discovery] Targeting {len(mfr_objs)} manufacturers.")

        # Reconstruct manufacturers_data structure expected by Stage 2
        manufacturers_data = {}
        for mfr in mfr_objs:
            # Query only equipment types that match the filter parameters
            et_query = db.query(EquipmentType)
            if equipment_type_id:
                et_query = et_query.filter(EquipmentType.id == equipment_type_id)
            elif equipment_master_id:
                et_query = et_query.filter(EquipmentType.equipment_master_id == equipment_master_id)
            all_types = et_query.all()
            
            for et in all_types:
                manufacturers_data.setdefault(et.name, []).append({
                    "id": mfr.id,
                    "name": mfr.name,
                    "country": mfr.country,
                    "website": mfr.website,
                    "description": mfr.description
                })
        
        _update_progress("Stage 2: Model Search", 50, f"Searching product model lineups for {len(mfr_objs)} targeted manufacturers")
        stage2.run(manufacturers_data, db=db, check_cancel=check_cancel, equipment_subtype_id=equipment_subtype_id)
        time.sleep(1)

        final_models = db.query(Model).count()
        new_models = max(0, final_models - initial_models)

        CRAWL_PROGRESS["completed_at"] = datetime.now().isoformat()
        _update_progress(
            "Completed", 
            100, 
            f"Lineup discovery complete: successfully discovered {new_models} models!",
            discovered_models=new_models
        )

        history_record.status = "completed"
        history_record.completed_at = datetime.now()
        history_record.new_manufacturers_count = 0
        history_record.new_models_count = new_models
        history_record.log_message = f"Lineup discovery complete. Found {new_models} new models."
        db.commit()

    except Exception as e:
        print(f"[BG Model Discovery Error] {e}")
        is_stopped = isinstance(e, InterruptedError) or "stopped by user" in str(e).lower()
        if is_stopped:
            _update_progress("Stopped", CRAWL_PROGRESS["percent"], "Crawl stopped by user request.")
            history_record.status = "stopped"
            history_record.completed_at = datetime.now()
            history_record.log_message = "Crawl stopped by user request."
        else:
            _update_progress("Failed", 0, f"Error occurred: {str(e)}")
            history_record.status = "failed"
            history_record.completed_at = datetime.now()
            history_record.log_message = f"Error: {str(e)}"
        db.commit()
    finally:
        CRAWL_PROGRESS["active"] = False
        db.close()


def run_specs_harvester_background(
    manufacturer_ids: list[int] | None, 
    only_unharvested: bool, 
    no_cache: bool,
    model_ids: list[int] | None = None,
    deep_crawl: bool = False,
    equipment_master_id: int | None = None,
    equipment_type_id: int | None = None,
    equipment_subtype_id: int | None = None,
    target_approved_only: bool = True
):
    """Stages 2 & 3: Run model discovery and specs extraction on approved manufacturers."""
    global CRAWL_PROGRESS, _CRAWL_STOP_REQUESTED
    _CRAWL_STOP_REQUESTED = False

    CRAWL_PROGRESS["active"] = True
    CRAWL_PROGRESS["compressor_type"] = "Approved Manufacturers"
    CRAWL_PROGRESS["started_at"] = datetime.now().isoformat()
    CRAWL_PROGRESS["completed_at"] = None
    CRAWL_PROGRESS["discovered_manufacturers"] = 0
    CRAWL_PROGRESS["discovered_models"] = 0
    CRAWL_PROGRESS["enriched_records"] = 0

    db = next(connection.get_db())

    history_record = CrawlHistory(
        started_at=datetime.now(),
        status="active",
        compressor_type="Approved Manufacturers",
        log_message="Approved specifications harvester background task started (Stages 2 & 3)."
    )
    db.add(history_record)
    db.commit()
    db.refresh(history_record)

    initial_models = db.query(Model).count()

    try:
        # Load settings
        settings = _get_db_settings()
        import config
        config.CACHE_ENABLED = False if no_cache else settings["cache_on"]
        config.MAX_MODELS_PER_MANUFACTURER = settings["max_models"]
        
        if model_ids:
            # Bypass manufacturer queries and load the targeted models directly
            model_query = db.query(Model).filter(Model.id.in_(model_ids))
            if only_unharvested:
                model_query = model_query.filter(Model.is_harvested == False)
            model_objs = model_query.all()
            
            # Extract manufacturers from these models
            mfr_objs = list({mo.manufacturer for mo in model_objs if mo.manufacturer})
            mfr_ids_list = [m.id for m in mfr_objs]
            deep_crawl = False
        else:
            # Load all approved manufacturers from PostgreSQL
            mfr_query = db.query(Manufacturer).filter(Manufacturer.is_approved == True)
            if manufacturer_ids:
                mfr_query = mfr_query.filter(Manufacturer.id.in_(manufacturer_ids))
            if only_unharvested:
                mfr_query = mfr_query.filter(Manufacturer.is_harvested == False)
                
            # Apply category filters to filter manufacturers that are associated with models in this category
            if equipment_master_id or equipment_type_id or equipment_subtype_id:
                mfr_sub = db.query(Model.manufacturer_id)
                if equipment_master_id:
                    mfr_sub = mfr_sub.filter(Model.equipment_master_id == equipment_master_id)
                if equipment_type_id:
                    mfr_sub = mfr_sub.filter(Model.equipment_type_id == equipment_type_id)
                if equipment_subtype_id:
                    mfr_sub = mfr_sub.filter(Model.equipment_subtype_id == equipment_subtype_id)
                mfr_query = mfr_query.filter(Manufacturer.id.in_(mfr_sub))
                
            mfr_objs = mfr_query.all()
            if not mfr_objs:
                raise ValueError("No approved/selected manufacturers to crawl! Verify approvals in the Manufacturers tab.")
            mfr_ids_list = [m.id for m in mfr_objs]

        # Coerce deep_crawl to strict boolean in case of string serialization
        if isinstance(deep_crawl, str):
            deep_crawl = deep_crawl.lower() in ("true", "1", "yes")
        else:
            deep_crawl = bool(deep_crawl)

        CRAWL_PROGRESS["discovered_manufacturers"] = len(mfr_objs)
        print(f"[BG Harvester] Targeting {len(mfr_objs)} manufacturers. deep_crawl={deep_crawl}")

        # ── Stage 2: Discover Lineups (Optional) ──
        if deep_crawl:
            # Reconstruct manufacturers_data structure expected by Stage 2
            manufacturers_data = {}
            for mfr in mfr_objs:
                # Query only equipment types that match the filter parameters
                et_query = db.query(EquipmentType)
                if equipment_type_id:
                    et_query = et_query.filter(EquipmentType.id == equipment_type_id)
                elif equipment_master_id:
                    et_query = et_query.filter(EquipmentType.equipment_master_id == equipment_master_id)
                all_types = et_query.all()
                
                for et in all_types:
                    manufacturers_data.setdefault(et.name, []).append({
                        "id": mfr.id,
                        "name": mfr.name,
                        "country": mfr.country,
                        "website": mfr.website,
                        "description": mfr.description
                    })
            
            _update_progress("Stage 2: Model Search", 35, f"Searching product model lineups for {len(mfr_objs)} targeted manufacturers")
            stage2.run(manufacturers_data, db=db, check_cancel=check_cancel, equipment_subtype_id=equipment_subtype_id)
            time.sleep(1)

        # ── Stage 3: Specs Extraction ──
        # Resolve target model_objs to crawl if not already resolved
        if not model_ids:
            model_query = db.query(Model).filter(
                Model.manufacturer_id.in_(mfr_ids_list)
            )
            if target_approved_only:
                model_query = model_query.filter(Model.is_approved == True)
            
            # Exclude placeholder models
            model_query = model_query.filter(Model.model_name != "TEMP_PLACEHOLDER")

            if only_unharvested:
                model_query = model_query.filter(Model.is_harvested == False)
            if equipment_master_id:
                model_query = model_query.filter(Model.equipment_master_id == equipment_master_id)
            if equipment_type_id:
                model_query = model_query.filter(Model.equipment_type_id == equipment_type_id)
            if equipment_subtype_id:
                model_query = model_query.filter(Model.equipment_subtype_id == equipment_subtype_id)
            model_objs = model_query.all()

        if not model_objs:
            msg = "No target models found to harvest specs for."
            if target_approved_only:
                msg = "No approved models to harvest specs for. Approve discovered models in the Catalog, or disable 'Approved Models Only'."
            
            _update_progress("Completed", 100, msg)
            history_record.status = "completed"
            history_record.completed_at = datetime.now()
            history_record.new_manufacturers_count = 0
            history_record.new_models_count = max(0, db.query(Model).count() - initial_models)
            history_record.total_specs_enriched = 0
            history_record.log_message = msg
            db.commit()
            return

        CRAWL_PROGRESS["discovered_models"] = len(model_objs)

        # Reconstruct models_data structure expected by Stage 3
        models_data = {}
        for mo in model_objs:
            mfr_name = mo.manufacturer.name
            ctype_name = mo.equipment_type.name
            
            if mfr_name not in models_data:
                models_data[mfr_name] = {
                    "compressor_type": ctype_name,
                    "manufacturer_info": {
                        "id": mo.manufacturer.id,
                        "name": mfr_name,
                        "country": mo.manufacturer.country,
                        "website": mo.manufacturer.website,
                        "description": mo.manufacturer.description
                    },
                    "models": []
                }
            
            models_data[mfr_name]["models"].append({
                "model_id": mo.id,
                "model_name": mo.model_name,
                "series": mo.series,
                "product_url": mo.product_url
            })

        _update_progress("Stage 3: Attributes", 75, f"Extracting spec attributes sheets for {len(model_objs)} models")
        final_records = stage3.run(models_data, db=db, check_cancel=check_cancel)
        with_attrs = sum(1 for r in final_records if r.get("attributes"))

        # Flag parent manufacturers as harvested in DB
        crawled_mfr_ids = {mo.manufacturer_id for mo in model_objs}
        for mfr_id in crawled_mfr_ids:
            mfr = db.query(Manufacturer).filter(Manufacturer.id == mfr_id).first()
            if mfr:
                mfr.is_harvested = True
        db.commit()

        CRAWL_PROGRESS["completed_at"] = datetime.now().isoformat()
        _update_progress(
            "Completed", 
            100, 
            f"Enriched specifications catalog: successfully compiled {with_attrs} spec sheets!",
            enriched_records=with_attrs
        )

        final_models = db.query(Model).count()
        history_record.status = "completed"
        history_record.completed_at = datetime.now()
        history_record.new_manufacturers_count = 0
        history_record.new_models_count = max(0, final_models - initial_models)
        history_record.total_specs_enriched = with_attrs
        history_record.log_message = f"Specs harvesting compiled successfully. Discovered {history_record.new_models_count} new models."
        db.commit()

    except Exception as e:
        print(f"[BG Harvester Error] {e}")
        is_stopped = isinstance(e, InterruptedError) or "stopped by user" in str(e).lower()
        if is_stopped:
            _update_progress("Stopped", CRAWL_PROGRESS["percent"], "Crawl stopped by user request.")
            history_record.status = "stopped"
            history_record.completed_at = datetime.now()
            history_record.log_message = "Crawl stopped by user request."
        else:
            _update_progress("Failed", 0, f"Error occurred: {str(e)}")
            history_record.status = "failed"
            history_record.completed_at = datetime.now()
            history_record.log_message = f"Error: {str(e)}"
        db.commit()
    finally:
        CRAWL_PROGRESS["active"] = False
        db.close()
