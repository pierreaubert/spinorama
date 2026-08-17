from email.message import Message
from http.server import SimpleHTTPRequestHandler
import unittest
from unittest.mock import Mock, patch

from scripts.debug_server import CORSRequestHandler


class DebugServerTests(unittest.TestCase):
    def test_cors_preflight(self):
        handler = object.__new__(CORSRequestHandler)
        handler.headers = Message()
        handler.headers["Origin"] = "http://localhost:5173"
        handler.headers["Access-Control-Request-Method"] = "GET"
        handler.headers["Access-Control-Request-Headers"] = "content-type"
        handler.send_header = Mock()
        handler.send_response = Mock()

        with patch.object(SimpleHTTPRequestHandler, "end_headers"):
            handler.do_OPTIONS()

        handler.send_response.assert_called_once_with(204)
        sent_headers = {call.args[0]: call.args[1] for call in handler.send_header.call_args_list}
        self.assertEqual(
            sent_headers["Access-Control-Allow-Origin"], "http://localhost:5173"
        )
        self.assertIn("GET", sent_headers["Access-Control-Allow-Methods"])
        self.assertIn("OPTIONS", sent_headers["Access-Control-Allow-Methods"])
        self.assertEqual(sent_headers["Access-Control-Allow-Headers"], "content-type")


if __name__ == "__main__":
    unittest.main()
