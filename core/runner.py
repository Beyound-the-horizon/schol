import argparse
import sys
import os

try:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Add root project directory to sys.path so package imports work seamlessly
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Scholarship Research Agent Runner with Concurrency Protection"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of scholarships to research and persist per cycle (default: 5)",
    )
    parser.add_argument(
        "--doc-url",
        type=str,
        default=None,
        help="Google Docs URL containing the numbered list of scholarships (optional, defaults to .env SCHOLARSHIP_CATALOG_URL)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass the advisory concurrency lock check (not recommended in production)",
    )

    args = parser.parse_args()

    # Deferred import to allow --help without requiring all packages
    try:
        from core.agents.workflow import run_autonomous_cycle
        from core.tools.db import acquire_run_lock
    except ImportError:
        from agents.workflow import run_autonomous_cycle
        from tools.db import acquire_run_lock

    if args.force:
        summary = run_autonomous_cycle(doc_url=args.doc_url, limit=args.limit)
    else:
        with acquire_run_lock() as acquired:
            if not acquired:
                print(
                    "\n[Runner] [LOCKED] Concurrency Guard: Another agent cycle is currently active in the database. "
                    "Skipping this run cleanly to avoid duplicate execution and Gemini API quota exhaustion."
                )
                sys.exit(0)

            summary = run_autonomous_cycle(doc_url=args.doc_url, limit=args.limit)

    if summary.get("failed", 0) > 0 and summary.get("created", 0) == 0 and summary.get("updated", 0) == 0:
        print("[Runner] Warning: No records were created or updated in this cycle.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
