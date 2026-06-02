#!/usr/bin/env python3
"""
Small admin / ops script to repair (clean) corrupted chat history files for a user.

Usage examples (run from repo root):

    # List what would be cleaned for a user
    python scripts/repair_user_chat_history.py --user-id 42 --dry-run

    # Actually clean .bad files (and optionally the main file if broken)
    python scripts/repair_user_chat_history.py --user-id 42

    # Also force-delete the main history.json
    python scripts/repair_user_chat_history.py --user-id 42 --reset-main

    # By email (looks up the user id via the local DB if available)
    python scripts/repair_user_chat_history.py --email silvio-test-0602@osijek.ai
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Try to import the real manager (best fidelity when run with PYTHONPATH=src)
try:
    sys.path.insert(0, "src")
    from user_context import chat_history_manager
    HAS_MANAGER = True
except Exception:
    HAS_MANAGER = False
    chat_history_manager = None


def find_bad_files(storage_path: Path, user_id: str) -> list[Path]:
    return sorted(storage_path.glob(f"{user_id}.bad*.json"))


def is_main_file_corrupted(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
        return False
    except Exception:
        return True


def repair(user_id: str, storage_path: Path | None = None, reset_main: bool = False, dry_run: bool = False) -> dict:
    if storage_path is None:
        if HAS_MANAGER:
            storage_path = chat_history_manager.storage_path
        else:
            storage_path = Path("data/chat_history")

    storage_path.mkdir(parents=True, exist_ok=True)
    main_path = storage_path / f"{user_id}.json"

    bad_files = find_bad_files(storage_path, user_id)
    cleaned = []

    for bf in bad_files:
        if dry_run:
            cleaned.append(str(bf))
        else:
            try:
                bf.unlink()
                cleaned.append(str(bf))
            except Exception as e:
                print(f"WARNING: could not delete {bf}: {e}", file=sys.stderr)

    main_deleted = False
    if reset_main and is_main_file_corrupted(main_path):
        if dry_run:
            main_deleted = True
            cleaned.append(str(main_path))
        else:
            try:
                main_path.unlink()
                main_deleted = True
                cleaned.append(str(main_path))
            except Exception as e:
                print(f"WARNING: could not delete main {main_path}: {e}", file=sys.stderr)

    return {
        "user_id": user_id,
        "storage_path": str(storage_path),
        "cleaned_files": cleaned,
        "main_file_deleted": main_deleted,
        "dry_run": dry_run,
    }


def main():
    parser = argparse.ArgumentParser(description="Repair / clean corrupted chat history files for one user.")
    parser.add_argument("--user-id", help="Numeric user id (preferred)")
    parser.add_argument("--email", help="User email (will try to resolve to id if local DB is available)")
    parser.add_argument("--reset-main", action="store_true", help="Also delete the main history file if it is unreadable")
    parser.add_argument("--dry-run", action="store_true", help="Only list what would be deleted, do not actually delete")
    parser.add_argument("--storage-path", help="Override the chat_history storage directory (default: data/chat_history)")
    args = parser.parse_args()

    if not args.user_id and not args.email:
        parser.error("You must provide either --user-id or --email")

    user_id = args.user_id

    if not user_id and args.email:
        # Best-effort lookup from local DB
        try:
            sys.path.insert(0, "src")
            from database import get_db
            from models.user import User
            db = next(get_db())
            user = db.query(User).filter(User.email == args.email).first()
            if user:
                user_id = str(user.id)
                print(f"Resolved email {args.email} -> user_id {user_id}")
            else:
                print(f"ERROR: No user found with email {args.email}", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"ERROR: Could not resolve email to user_id ({e}). Please use --user-id instead.", file=sys.stderr)
            sys.exit(1)

    storage = Path(args.storage_path) if args.storage_path else None

    result = repair(user_id, storage_path=storage, reset_main=args.reset_main, dry_run=args.dry_run)

    action = "Would clean" if args.dry_run else "Cleaned"
    print(f"{action} for user {result['user_id']}:")
    if result["cleaned_files"]:
        for f in result["cleaned_files"]:
            print(f"  - {f}")
    else:
        print("  (nothing to clean)")

    if result["main_file_deleted"]:
        print("  - main history file was also removed (was corrupted)")

    print(f"\nStorage: {result['storage_path']}")
    if args.dry_run:
        print("\n(This was a dry-run. Re-run without --dry-run to actually delete the files.)")


if __name__ == "__main__":
    main()
