#!/usr/bin/env python3
"""
Unified Cross-Platform Cleanup Script
Detects OS (Windows, Linux, macOS) and executes system artifact cleanup,
Docker pruning, and database purges (Postgres & Qdrant).
"""

import os
import sys
import shutil
import platform
import subprocess
import glob

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from scripts.logger import get_logger
from scripts.config import config

logger = get_logger("unified_cleanup")


def get_os_type() -> str:
    """Detect operating system (Windows, Linux, Darwin)."""
    os_name = platform.system()
    logger.info(f"[OS Detection] Detected Operating System: {os_name}")
    return os_name


def clean_system_artifacts(project_root: str, os_type: str):
    logger.info("--- 1. Starting System Artifact Cleanup ---")
    removed_dirs = 0
    removed_files = 0

    # 1. Clean __pycache__ directories
    for pyc_dir in glob.glob(os.path.join(project_root, "**", "__pycache__"), recursive=True):
        try:
            shutil.rmtree(pyc_dir)
            removed_dirs += 1
        except Exception as e:
            logger.warning(f"Could not remove cache dir {pyc_dir}: {e}")

    # 2. Clean temporary test CSV files in logs directory
    logs_dir = os.path.join(project_root, "logs")
    if os.path.exists(logs_dir):
        for temp_file in glob.glob(os.path.join(logs_dir, "testset_*.csv")):
            try:
                os.remove(temp_file)
                removed_files += 1
            except Exception:
                pass

    logger.info(f"Local files cleaned: Removed {removed_dirs} __pycache__ dirs and {removed_files} temp CSV files.")

    # 3. Docker build cache and dangling image pruning
    logger.info(f"Invoking Docker prune commands on {os_type}...")
    shell_flag = True if os_type == "Windows" else False
    try:
        subprocess.run(["docker", "builder", "prune", "-f"], shell=shell_flag, check=False)
        subprocess.run(["docker", "image", "prune", "-f"], shell=shell_flag, check=False)
        logger.info("Docker build cache and dangling image cleanup executed successfully.")
    except Exception as e:
        logger.warning(f"Docker cleanup command failed (Docker CLI might not be running): {e}")


def clean_databases(target_project: str = None):
    logger.info(f"--- 2. Starting Database Purge (Target: {target_project or 'ALL PROJECTS'}) ---")
    
    # Postgres
    try:
        import psycopg2
        logger.info(f"Connecting to Postgres at {config.POSTGRES_HOST}:{config.POSTGRES_PORT}...")
        conn = psycopg2.connect(config.get_pg_dsn(), connect_timeout=3)
        conn.autocommit = True
        cur = conn.cursor()
        if target_project:
            cur.execute("DELETE FROM projects WHERE project_name = %s;", (target_project,))
            logger.info(f"Postgres rows for project '{target_project}' deleted successfully!")
        else:
            cur.execute("TRUNCATE TABLE parent_chunks, documents, projects, versions CASCADE;")
            logger.info("All Postgres tables truncated successfully!")
        cur.close()
        conn.close()
    except Exception as e:
        logger.warning(f"Postgres cleanup skipped or failed (is container running?): {e}")

    # Qdrant
    try:
        from qdrant_client import QdrantClient
        logger.info(f"Connecting to Qdrant at {config.QDRANT_HOST}:{config.QDRANT_PORT}...")
        client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT, timeout=3.0)
        if target_project:
            try:
                client.delete_collection(target_project)
                logger.info(f"Qdrant collection '{target_project}' deleted!")
            except Exception as e:
                logger.warning(f"Qdrant collection deletion info: {e}")
        else:
            collections = client.get_collections().collections
            for c in collections:
                try:
                    client.delete_collection(c.name)
                    logger.info(f"Qdrant collection '{c.name}' deleted!")
                except Exception as e:
                    logger.warning(f"Error deleting collection '{c.name}': {e}")
        logger.info("Qdrant cleanup completed!")
    except Exception as e:
        logger.warning(f"Qdrant cleanup skipped or failed: {e}")


def main():
    os_type = get_os_type()
    args = sys.argv[1:]

    do_system = "--system" in args or not args or "--all" in args
    do_db = "--db" in args or not args or "--all" in args

    # Extract target project name if passed with --db
    target_proj = None
    if "--db" in args:
        db_idx = args.index("--db")
        if db_idx + 1 < len(args) and not args[db_idx + 1].startswith("--"):
            target_proj = args[db_idx + 1]

    if not do_system and not do_db:
        do_system = True
        do_db = True

    if do_system:
        clean_system_artifacts(PROJECT_ROOT, os_type)

    if do_db:
        clean_databases(target_proj if not ("--all" in args) else None)

    logger.info("--- Unified Cleanup Completed ---")


if __name__ == "__main__":
    main()
