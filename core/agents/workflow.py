import time
from typing import Any

try:
    from core.tools.catalog_reader import fetch_curated_scholarships
    from core.tools.db import select_daily_batch
    from core.agents.researcher import research_scholarship
    from core.agents.structurer import structure_scholarship
    from core.agents.writer import write_scholarship
except ImportError:
    from tools.catalog_reader import fetch_curated_scholarships
    from tools.db import select_daily_batch
    from agents.researcher import research_scholarship
    from agents.structurer import structure_scholarship
    from agents.writer import write_scholarship


def run_autonomous_cycle(doc_url: str | None = None, limit: int = 5) -> dict[str, Any]:
    """
    Executes a complete autonomous batch cycle:
    1. Fetches the live curated numbered list from the online Google Doc.
    2. Selects up to `limit` scholarships (prioritizing new entries, then oldest verified).
    3. Iterates through each scholarship:
       Researcher (Gemini + Search) ➔ Structurer (Schema + Pydantic) ➔ Writer (Supabase).
    4. Provides fault-isolated execution with a complete audit summary.
    """
    print("\n=======================================================")
    print("[START] Starting Autonomous Scholarship Research Cycle")
    print("=======================================================\n")

    # Read live online catalog
    catalog = fetch_curated_scholarships(doc_url=doc_url)
    print(f"[CATALOG] Loaded {len(catalog)} total scholarships from curated registry.")

    # Queue selection & deduplication
    batch = select_daily_batch(catalog, limit=limit)
    if not batch:
        print("[QUEUE] No eligible candidates to process today.")
        return {"status": "idle", "message": "Queue is empty."}

    print(f"[TARGETS] Selected today's batch of {len(batch)} scholarships:")
    for idx, item in enumerate(batch, 1):
        status_label = "NEW" if item["is_new"] else f"REFRESH (last: {item['last_verified_at']})"
        print(f"  {idx}. {item['target_name']} [{status_label}]")

    print("\n-------------------------------------------------------")

    results = []
    created_count = 0
    updated_count = 0
    failed_count = 0

    # Execute pipeline per scholarship with fault isolation
    for idx, target in enumerate(batch, 1):
        target_name = target["target_name"]
        print(f"\n[{idx}/{len(batch)}] Processing: {target_name}...")

        try:
            # 1. Researcher Agent
            print("  [1/3 Researcher] Searching live web for official details...")
            research_data = research_scholarship(target_name)
            sources_found = len(research_data.get("sources", []))
            print(f"        Found {sources_found} grounded sources.")

            # 2. Structurer Agent
            print("  [2/3 Structurer] Extracting schema and validating Pydantic constraints...")
            structured_record = structure_scholarship(research_data)
            if not structured_record:
                print("        [FAILED] Validation failed: insufficient verified data.")
                failed_count += 1
                results.append({"name": target_name, "status": "validation_failed"})
                continue

            # 3. Writer Agent
            print(f"  [3/3 Writer] Persisting '{structured_record.name}' to Supabase...")
            write_result = write_scholarship(structured_record)
            write_status = write_result.get("status")

            if write_status == "created":
                created_count += 1
                print(f"        [SUCCESS] Created new row (ID: {write_result.get('id')}).")
            elif write_status == "updated":
                updated_count += 1
                print(f"        [SUCCESS] Refreshed existing row (ID: {write_result.get('id')}).")
            else:
                failed_count += 1
                print(f"        [REJECTED] Save rejected: {write_result.get('reason')}")

            results.append({
                "name": target_name,
                "status": write_status,
                "db_id": write_result.get("id"),
                "official_url": write_result.get("official_url"),
            })

            
            if idx < len(batch):
                time.sleep(2)

        except Exception as e:
            failed_count += 1
            print(f"  [ERROR] Error processing '{target_name}': {type(e).__name__}: {e}")
            results.append({"name": target_name, "status": "error", "error": str(e)})

    summary = {
        "total_catalog": len(catalog),
        "batch_size": len(batch),
        "created": created_count,
        "updated": updated_count,
        "failed": failed_count,
        "details": results,
    }

    print("\n=======================================================")
    print("[COMPLETED] Autonomous Cycle Completed!")
    print(f"Summary: {created_count} Created, {updated_count} Updated, {failed_count} Failed/Rejected.")
    print("=======================================================\n")

    return summary
