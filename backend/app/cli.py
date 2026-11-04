"""Interactive setup commands for a new GridWatch database."""

import argparse
import secrets
import sys
from getpass import getpass

import sqlalchemy as sa
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import User
from app.db.demo_seed import seed_demo
from app.db.session import get_engine
from app.modules.audit import record_audit
from app.modules.auth import UserCreate


def create_initial_admin(session: Session, *, email: str, full_name: str, password: str) -> User:
    """Bootstrap exactly one administrator in an empty users table."""
    if session.scalar(sa.select(User.id).limit(1)) is not None:
        raise RuntimeError("The first administrator can only be created in an empty users table")
    payload = UserCreate(email=email, full_name=full_name, password=password, role="admin")
    user = User(
        email=str(payload.email).lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role="admin",
    )
    session.add(user)
    session.flush()
    record_audit(session, actor_id=user.id, action="user.bootstrapped", entity_type="user", entity_id=user.id)
    session.commit()
    session.refresh(user)
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description="GridWatch setup commands")
    subcommands = parser.add_subparsers(dest="command", required=True)
    create_admin = subcommands.add_parser("create-admin", help="Create the first administrator")
    create_admin.add_argument("--email", required=True)
    create_admin.add_argument("--name", required=True)
    password_source = create_admin.add_mutually_exclusive_group()
    password_source.add_argument(
        "--generate-password",
        action="store_true",
        help="Generate a strong password and print it once after creating the administrator",
    )
    password_source.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read the initial password from standard input for automated setup",
    )
    subcommands.add_parser("seed-demo", help="Create simulated demo installations, equipment and rules")
    args = parser.parse_args()

    if args.command == "seed-demo":
        try:
            with Session(get_engine()) as session:
                seed_demo(session)
        except RuntimeError as exc:
            parser.error(str(exc))
        print("Demo installations, equipment and alert rules created")
        return

    if args.command == "create-admin":
        if args.generate_password:
            password = secrets.token_urlsafe(24)
        elif args.password_stdin:
            password = sys.stdin.readline().rstrip("\r\n")
            if not password:
                parser.error("Expected a password on standard input")
        else:
            password = getpass("Administrator password (12 characters minimum): ")
            if password != getpass("Confirm password: "):
                parser.error("Passwords do not match")
        try:
            with Session(get_engine()) as session:
                user = create_initial_admin(
                    session, email=args.email, full_name=args.name, password=password
                )
        except (RuntimeError, ValidationError) as exc:
            parser.error(str(exc))
        print(f"Administrator created: {user.email}")
        if args.generate_password:
            print(f"Generated password (save it now): {password}")


if __name__ == "__main__":
    main()
