#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Startup script for the Speaker Metadata Manager
"""

import sys
import subprocess
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import pydantic

        print("✓ Dependencies are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing dependencies: {e}")
        print("Installing dependencies...")

        requirements_file = Path(__file__).parent / "requirements.txt"
        if requirements_file.exists():
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                    check=True,
                )
                print("✓ Dependencies installed successfully")
                return True
            except subprocess.CalledProcessError:
                print("✗ Failed to install dependencies")
                return False
        else:
            print("✗ requirements.txt not found")
            return False


def main():
    """Main startup function"""
    print("=" * 60)
    print("Spinorama Speaker Metadata Manager")
    print("=" * 60)

    # Check dependencies
    if not check_dependencies():
        print("\nPlease install the required dependencies and try again.")
        sys.exit(1)

    # Check if we're in the right directory
    project_root = Path(".")
    if not (project_root / "datas").exists():
        print("✗ Could not find datas directory. Please run from the correct location.")
        sys.exit(1)

    print("✓ Project structure validated")

    # Start the server
    print("\nStarting the metadata manager server...")
    print("Open http://localhost:8000 in your browser")
    print("API documentation at http://localhost:8000/docs")
    print("Press Ctrl+C to stop the server")
    print("-" * 60)

    try:
        import uvicorn
        from metadata_server import create_app

        uvicorn.run(create_app(), host="0.0.0.0", port=8000, reload=True, log_level="info")
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\n✗ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
