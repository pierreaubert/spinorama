#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test signal handling and command line parsing in metadata start module
"""

import argparse
import os
import signal
import sys
import unittest
from unittest.mock import patch, Mock, call
import subprocess
from pathlib import Path

# Add parent directory to path to import metadata module
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from metadata import start


class TestMetadataModule(unittest.TestCase):
    """Test signal handling and command line parsing in metadata start module"""

    @patch("metadata.start.sys.exit")
    @patch("metadata.start.child_processes")
    def test_signal_handler(self, mock_child_processes, mock_exit):
        """Test that the signal handler properly terminates child processes"""
        # Setup mock processes
        mock_proc1 = Mock()
        mock_proc1.poll.return_value = None  # Process is running
        mock_proc1.pid = 12345

        mock_proc2 = Mock()
        mock_proc2.poll.return_value = 0  # Process has already exited
        mock_proc2.pid = 54321

        mock_proc3 = Mock()
        mock_proc3.poll.return_value = None  # Process is running
        mock_proc3.pid = 98765
        # Make this one time out and need to be killed
        mock_proc3.wait.side_effect = subprocess.TimeoutExpired("cmd", 2)

        # Set up our mock child processes list
        mock_child_processes.__iter__.return_value = [mock_proc1, mock_proc2, mock_proc3]

        # Call the signal handler
        start.signal_handler(signal.SIGTERM, None)

        # Verify process termination was attempted only for running processes
        mock_proc1.terminate.assert_called_once()
        mock_proc1.wait.assert_called_once_with(timeout=2)
        self.assertFalse(mock_proc2.terminate.called)

        # Verify that killing occurs for the process that timed out
        mock_proc3.terminate.assert_called_once()
        mock_proc3.kill.assert_called_once()

        # Verify system exit was called
        mock_exit.assert_called_once_with(0)

    @patch("metadata.start.signal.signal")
    def test_register_signal_handlers(self, mock_signal):
        """Test that signal handlers are registered for all required signals"""
        # Call the register function
        start.register_signal_handlers()

        # Verify signal handlers were registered for the required signals
        expected_calls = [
            call(signal.SIGTERM, start.signal_handler),
            call(signal.SIGINT, start.signal_handler),
        ]

        # On Unix-like systems, these signals should also be registered
        if hasattr(signal, "SIGHUP"):
            expected_calls.append(call(signal.SIGHUP, start.signal_handler))
        if hasattr(signal, "SIGQUIT"):
            expected_calls.append(call(signal.SIGQUIT, start.signal_handler))

        mock_signal.assert_has_calls(expected_calls, any_order=True)

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_default(self, mock_parse_args):
        """Test that command line arguments are parsed correctly with defaults"""
        # Setup mock args with default values
        mock_args = Mock()
        mock_args.ip = "0.0.0.0"
        mock_args.port = 8000
        mock_parse_args.return_value = mock_args

        # Call the parse function
        args = start.parse_args()

        # Verify defaults were used
        self.assertEqual(args["ip"], "0.0.0.0")
        self.assertEqual(args["port"], 8000)

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_custom(self, mock_parse_args):
        """Test that command line arguments are parsed correctly with custom values"""
        # Setup mock args with custom values
        mock_args = Mock()
        mock_args.ip = "127.0.0.1"
        mock_args.port = 9000
        mock_parse_args.return_value = mock_args

        # Call the parse function
        args = start.parse_args()

        # Verify custom values were used
        self.assertEqual(args["ip"], "127.0.0.1")
        self.assertEqual(args["port"], 9000)

    def test_main_uses_cmd_args(self):
        """Test that main function uses command line arguments for server config"""
        # Patch parse_args to return custom IP and port
        with (
            patch("metadata.start.parse_args") as mock_parse_args,
            patch("metadata.start.run_server") as mock_run_server,
            patch("metadata.start.check_dependencies", return_value=True),
            patch("metadata.start.register_signal_handlers"),
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.print"),
        ):
            # Setup custom IP and port values
            mock_parse_args.return_value = {"ip": "127.0.0.1", "port": 8080}

            # Call main function
            start.main()

            # Verify run_server was called with our custom IP and port
            mock_run_server.assert_called_once_with("127.0.0.1", 8080)

    def test_run_server(self):
        """Test that run_server calls uvicorn.run with the correct arguments"""
        # Check if uvicorn is available first and skip if not
        try:
            import uvicorn  # noqa: F401
        except ImportError:
            self.skipTest("uvicorn not available, skipping test")
            return

        # Since uvicorn is available, create the patch and run the test
        with patch("uvicorn.run") as mock_uvicorn_run, patch("builtins.print"), patch("sys.exit"):
            # Call run_server with custom IP and port
            start.run_server("192.168.1.100", 9000)

            # Verify uvicorn.run was called with correct arguments
            mock_uvicorn_run.assert_called_once()
            args, kwargs = mock_uvicorn_run.call_args

            self.assertEqual(args[0], "metadata.server:create_app")
            self.assertEqual(kwargs.get("host"), "192.168.1.100")
            self.assertEqual(kwargs.get("port"), 9000)
            self.assertEqual(kwargs.get("reload"), True)
            self.assertEqual(kwargs.get("log_level"), "info")


if __name__ == "__main__":
    unittest.main()
