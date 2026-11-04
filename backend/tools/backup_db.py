"""Back up the Compose database and optionally verify a disposable restore.

Run from any directory with ``python backend/tools/backup_db.py --verify``.
The archive stays on the host in the git-ignored ``backups`` directory.
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
BACKUPS = ROOT / "backups"
IDENTIFIER = re.compile(r"[a-z_][a-z0-9_]*\Z")


def docker_binary() -> str:
    found = shutil.which("docker")
    if found:
        return found
    if os.name == "nt":
        candidate = Path.home() / "AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe"
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError("No se encontró Docker CLI. Inicia Docker Desktop y revisa PATH.")


def run(docker: str, *args: str, capture: bool = False) -> str:
    result = subprocess.run(
        [docker, *args], cwd=ROOT, check=True,
        stdout=subprocess.PIPE if capture else None,
        text=capture,
    )
    return result.stdout.strip() if capture else ""


def db_command(docker: str, user: str, database: str, sql: str) -> str:
    return run(
        docker, "compose", "exec", "-T", "db", "psql", "-X", "-v", "ON_ERROR_STOP=1",
        "-U", user, "-d", database, "-Atqc", sql, capture=True,
    )


def container_settings(docker: str) -> tuple[str, str]:
    user = run(docker, "compose", "exec", "-T", "db", "printenv", "POSTGRES_USER", capture=True)
    database = run(docker, "compose", "exec", "-T", "db", "printenv", "POSTGRES_DB", capture=True)
    if not IDENTIFIER.fullmatch(user) or not IDENTIFIER.fullmatch(database):
        raise RuntimeError("El usuario o nombre de base requiere un identificador SQL simple.")
    return user, database


def create_backup(docker: str, user: str, database: str) -> Path:
    BACKUPS.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = BACKUPS / f"gridwatch-{stamp}-{uuid4().hex[:8]}.dump"
    temporary = target.with_suffix(".dump.part")
    try:
        with temporary.open("wb") as archive:
            subprocess.run(
                [docker, "compose", "exec", "-T", "db", "pg_dump", "-U", user,
                 "-d", database, "-Fc", "--no-owner", "--no-acl"],
                cwd=ROOT, stdout=archive, check=True,
            )
        if temporary.stat().st_size == 0:
            raise RuntimeError("pg_dump produjo un archivo vacío.")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    with target.open("rb") as saved:
        digest = hashlib.file_digest(saved, "sha256").hexdigest()
    print(f"Copia: {target} ({target.stat().st_size} bytes; SHA-256 {digest})")
    return target


def verify_restore(docker: str, user: str, database: str, archive: Path) -> None:
    if not archive.is_file() or archive.stat().st_size == 0:
        raise RuntimeError("El archivo de respaldo no existe o está vacío.")
    # Every destructive operation below targets only this freshly generated name.
    temporary_db = f"gridwatch_restore_{uuid4().hex[:12]}"
    container = run(docker, "compose", "ps", "-q", "db", capture=True)
    if not container or not re.fullmatch(r"[a-f0-9]{12,64}", container):
        raise RuntimeError("No se encontró un contenedor de base de datos en ejecución.")
    container_archive = f"/tmp/{temporary_db}.dump"
    copied = False
    created = False
    try:
        run(docker, "cp", str(archive), f"{container}:{container_archive}")
        copied = True
        db_command(docker, user, "postgres", f"CREATE DATABASE {temporary_db}")
        created = True
        db_command(docker, user, temporary_db, "CREATE EXTENSION IF NOT EXISTS timescaledb")
        db_command(docker, user, temporary_db, "SELECT timescaledb_pre_restore()")
        run(
            docker, "compose", "exec", "-T", "db", "pg_restore", "--exit-on-error",
            "--no-owner", "--no-acl", "-U", user, "-d", temporary_db,
            container_archive,
        )
        db_command(docker, user, temporary_db, "SELECT timescaledb_post_restore()")
        restored = int(db_command(docker, user, temporary_db, "SELECT count(*) FROM measurements"))
        live = int(db_command(docker, user, database, "SELECT count(*) FROM measurements"))
        hypertables = int(db_command(
            docker, user, temporary_db,
            "SELECT count(*) FROM timescaledb_information.hypertables "
            "WHERE hypertable_schema = 'public' AND hypertable_name = 'measurements'",
        ))
        if restored <= 0 or restored > live or hypertables != 1:
            raise RuntimeError(
                f"Validación fallida: restauradas={restored}, originales={live}, "
                f"hipertablas={hypertables}"
            )
        for table in ("users", "installations", "equipment", "alert_rules", "alert_events", "audit_events"):
            saved_count = int(db_command(docker, user, temporary_db, f"SELECT count(*) FROM {table}"))
            live_count = int(db_command(docker, user, database, f"SELECT count(*) FROM {table}"))
            if saved_count > live_count or (table in {"users", "installations", "equipment"} and saved_count == 0):
                raise RuntimeError(f"Validación fallida para {table}: restauradas={saved_count}, originales={live_count}")
        old_rows = "SELECT count(*) FROM measurements WHERE measured_at < now() - INTERVAL '35 days'"
        recent_rows = "SELECT count(*) FROM measurements WHERE measured_at >= now() - INTERVAL '31 days'"
        old_before = int(db_command(docker, user, temporary_db, old_rows))
        recent_before = int(db_command(docker, user, temporary_db, recent_rows))
        db_command(
            docker, user, temporary_db,
            "INSERT INTO measurements (equipment_id, measured_at, voltage_l1_v) "
            "SELECT id, now() - INTERVAL '70 days', 220 FROM equipment LIMIT 1",
        )
        if int(db_command(docker, user, temporary_db, old_rows)) != old_before + 1:
            raise RuntimeError("No se pudo preparar la medición antigua de prueba.")
        db_command(docker, user, temporary_db, "SELECT public.gridwatch_apply_measurement_retention()")
        if (int(db_command(docker, user, temporary_db, old_rows)) > old_before
                or int(db_command(docker, user, temporary_db, recent_rows)) != recent_before):
            raise RuntimeError("La retención no eliminó la lectura antigua o afectó lecturas recientes.")
        print(f"Restauración correcta: {restored} mediciones, tablas de negocio y retención aislada verificadas.")
    finally:
        if created:
            if not re.fullmatch(r"gridwatch_restore_[a-f0-9]{12}", temporary_db):
                raise RuntimeError("Nombre de base temporal no válido; se omite la limpieza.")
            db_command(docker, user, "postgres", f"DROP DATABASE {temporary_db} WITH (FORCE)")
        if copied:
            run(docker, "exec", container, "rm", "--", container_archive)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="restaurar en una base temporal y comparar")
    args = parser.parse_args()
    try:
        docker = docker_binary()
        user, database = container_settings(docker)
        archive = create_backup(docker, user, database)
        if args.verify:
            verify_restore(docker, user, database, archive)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Error de respaldo: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
