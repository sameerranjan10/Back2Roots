#!/usr/bin/env python3
"""
run.py — Convenience script to start the Back2Roots development server.

Usage:
    python run.py              # default: 0.0.0.0:8000, hot-reload
    python run.py --port 9000
    python run.py --prod       # 4 workers, no reload
"""

import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the Back2Roots API server")
    parser.add_argument("--host",   default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port",   default=8000, type=int, help="Bind port (default: 8000)")
    parser.add_argument("--prod",   action="store_true",  help="Production mode (no reload, 4 workers)")
    parser.add_argument("--workers",default=4, type=int,  help="Number of workers in prod mode")
    args = parser.parse_args()

    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", args.host,
        "--port", str(args.port),
    ]

    if args.prod:
        cmd += ["--workers", str(args.workers), "--proxy-headers"]
        print(f"\n🚀  Production mode — {args.workers} workers on {args.host}:{args.port}\n")
    else:
        cmd += ["--reload", "--reload-dir", "app"]
        print(f"\n🔧  Development mode — hot-reload on {args.host}:{args.port}")
        print(f"📖  Swagger UI  →  http://localhost:{args.port}/docs")
        print(f"📖  ReDoc       →  http://localhost:{args.port}/redoc\n")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋  Server stopped.")


if __name__ == "__main__":
    main()
