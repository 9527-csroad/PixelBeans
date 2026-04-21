"""Root-level shim so `python cli.py ...` works from the project root.

Actual implementation lives in `pixelbeans.cli`.
"""
from pixelbeans.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
