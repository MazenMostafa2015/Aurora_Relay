# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Aurora Relay desktop backend."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

project_root = Path(SPECPATH).resolve().parents[1]
backend_root = project_root / "backend"

hiddenimports = []
for package in ("app", "fastapi", "uvicorn", "sqlalchemy", "pydantic", "mcp_servers"):
    try:
        hiddenimports.extend(collect_submodules(package))
    except Exception:
        pass

analysis = Analysis(
    [str(backend_root / "run.py")],
    pathex=[str(project_root), str(backend_root)],
    binaries=[],
    datas=[
        (str(project_root / "mcp_servers" / "config.json"), "mcp_servers"),
        (str(project_root / "alembic.ini"), "."),
    ],
    hiddenimports=hiddenimports + [
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.ext.asyncio",
        "aiosqlite",
        "asyncpg",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.websockets_impl",
    ],
    hookspath=[str(Path(SPECPATH) / "hooks")],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "pytest"],
    noarchive=False,
)

pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="aurora-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
