#!/usr/bin/env python3
"""
Script to run Alembic database migrations.

Usage:
    python scripts/run_migrations.py [upgrade|downgrade|current|history]
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from alembic import command
from alembic.config import Config

from app.config import settings


def run_migrations(command_name: str = "upgrade", revision: str = "head") -> None:
    """
    Run Alembic migrations.
    
    Args:
        command_name: Migration command (upgrade, downgrade, current, history)
        revision: Target revision (default: "head" for upgrade)
    """
    # Get Alembic config
    alembic_cfg = Config("alembic.ini")
    
    # Set database URL
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    
    print(f"Running migration: {command_name} {revision}")
    print(f"Database URL: {database_url.split('@')[1] if '@' in database_url else 'configured'}")
    
    if command_name == "upgrade":
        command.upgrade(alembic_cfg, revision)
        print(f"✓ Migration upgraded to {revision}")
    elif command_name == "downgrade":
        command.downgrade(alembic_cfg, revision)
        print(f"✓ Migration downgraded to {revision}")
    elif command_name == "current":
        command.current(alembic_cfg)
    elif command_name == "history":
        command.history(alembic_cfg)
    else:
        print(f"Unknown command: {command_name}")
        print("Available commands: upgrade, downgrade, current, history")
        sys.exit(1)


if __name__ == "__main__":
    command_name = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    revision = sys.argv[2] if len(sys.argv) > 2 else "head"
    
    try:
        run_migrations(command_name, revision)
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        sys.exit(1)

