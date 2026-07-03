# Windows PowerShell root wrapper forwarding to scripts/cleanup/cleanup.py
uv run python (Join-Path $PSScriptRoot "cleanup\cleanup.py") @args
