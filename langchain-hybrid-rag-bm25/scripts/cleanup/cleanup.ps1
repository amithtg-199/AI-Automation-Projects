# Windows PowerShell entrypoint for unified system and database cleanup
uv run python (Join-Path $PSScriptRoot "cleanup.py") @args
