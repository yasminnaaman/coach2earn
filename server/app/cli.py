"""Trusted operator commands for one-time account bootstrap operations."""

from __future__ import annotations

import argparse
from getpass import getpass
import sys

from app.core.config import get_settings
from app.core.security import ensure_authentication_configured
from app.db.session import SessionLocal
from app.services.auth import AccountWorkflowError, bootstrap_admin


def _bootstrap_admin(email_argument: str | None) -> int:
    try:
        ensure_authentication_configured(get_settings())
    except Exception:
        print("JWT_SECRET_KEY must be configured before admin bootstrap.", file=sys.stderr)
        return 2

    with SessionLocal() as db:
        if db.bind is None or db.bind.dialect.name != "postgresql":
            print("Admin bootstrap is only supported against PostgreSQL.", file=sys.stderr)
            return 2

    if not sys.stdin.isatty() or not sys.stderr.isatty():
        print("Run admin bootstrap from an interactive terminal to keep password input hidden.", file=sys.stderr)
        return 2

    email = email_argument or input("Initial admin email: ").strip()
    password = getpass("Initial admin password (input hidden): ")
    confirmation = getpass("Confirm password (input hidden): ")
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 2

    try:
        with SessionLocal() as db:
            bootstrap_admin(db, email, password)
    except AccountWorkflowError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        # Do not print exception details: database driver messages may contain
        # connection metadata, and this command never needs to echo credentials.
        print("Admin bootstrap failed. Check server configuration and database health.", file=sys.stderr)
        return 1

    print("Initial admin account created.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    bootstrap = commands.add_parser("bootstrap-admin", help="Create the first admin account once")
    bootstrap.add_argument("--email", help="Admin email (password is always prompted interactively)")
    arguments, unexpected = parser.parse_known_args()
    if unexpected:
        print(
            "Unexpected arguments. Passwords are prompted interactively and must not be passed on the command line.",
            file=sys.stderr,
        )
        return 2

    if arguments.command == "bootstrap-admin":
        return _bootstrap_admin(arguments.email)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
