#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Startup script for the Speaker Metadata Manager
"""

import argparse
import os
import signal
import sys
import subprocess
from pathlib import Path
from typing import List, Optional, Any, Dict, Tuple


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


# Store child processes to clean up on termination
child_processes: List[subprocess.Popen] = []


def parse_args() -> Dict[str, Any]:
    """Parse command line arguments.

    Returns:
        Dictionary with parsed command line arguments
    """
    parser = argparse.ArgumentParser(description="Spinorama Speaker Metadata Manager")

    parser.add_argument(
        "--ip",
        type=str,
        default="0.0.0.0",
        help="IP address to bind the server to (default: 0.0.0.0)",
    )

    parser.add_argument(
        "--port", type=int, default=8000, help="Port to run the server on (default: 8000)"
    )

    return vars(parser.parse_args())


def signal_handler(sig: int, frame: Any) -> None:
    """Handle termination signals to gracefully shutdown the application.

    Args:
        sig: Signal number
        frame: Current stack frame
    """
    signal_name = signal.Signals(sig).name if hasattr(signal, "Signals") else str(sig)
    print(f"\nReceived termination signal {signal_name} ({sig})")

    # Cleanup any spawned child processes
    for proc in child_processes:
        if proc.poll() is None:  # If process is still running
            print(f"Terminating child process with PID {proc.pid}")
            try:
                proc.terminate()
                # Give it a moment to terminate gracefully
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    print(f"Process {proc.pid} did not terminate in time, killing...")
                    proc.kill()
            except Exception as e:
                print(f"Error while terminating process {proc.pid}: {e}")

    print("Shutdown complete.")
    sys.exit(0)


def register_signal_handlers() -> None:
    """Register signal handlers for graceful shutdown."""
    # Register for common termination signals
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    signal.signal(signal.SIGINT, signal_handler)  # Interrupt from keyboard (Ctrl+C)

    # On Unix-like systems, register additional signals
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, signal_handler)  # Terminal closed
    if hasattr(signal, "SIGQUIT"):
        signal.signal(signal.SIGQUIT, signal_handler)  # Quit signal


def run_server(ip_address: str, port: int) -> None:
    """Run the server with the specified IP address and port.

    This function is separated from main() to make it more testable.

    Args:
        ip_address: IP address to bind the server to
        port: Port to run the server on
    """
    try:
        import uvicorn
        from metadata.server import create_app

        # Using run() in non-blocking way to allow signal handlers to work properly
        uvicorn.run(
            "metadata.server:create_app", host=ip_address, port=port, reload=True, log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\n✗ Error starting server: {e}")
        sys.exit(1)


def main() -> None:
    """Main startup function"""
    print("=" * 60)
    print("Spinorama Speaker Metadata Manager")
    print("=" * 60)

    # Parse command line arguments
    args = parse_args()
    ip_address = args["ip"]
    port = args["port"]

    # Register signal handlers
    register_signal_handlers()

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
    print(
        f"Open http://{ip_address if ip_address != '0.0.0.0' else 'localhost'}:{port} in your browser"
    )
    print(
        f"API documentation at http://{ip_address if ip_address != '0.0.0.0' else 'localhost'}:{port}/docs"
    )
    print("Press Ctrl+C to stop the server")
    print("-" * 60)

    # Run the server
    run_server(ip_address, port)


if __name__ == "__main__":
    main()
