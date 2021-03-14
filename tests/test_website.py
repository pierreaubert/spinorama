import unittest
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from docopt import docopt
from selenium import webdriver
from selenium.webdriver.common.keys import Keys


class CORSRequestHandler(SimpleHTTPRequestHandler):
    """ Generate CORS headers """

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        return super(CORSRequestHandler, self).end_headers()


class SpinoramaTest(unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Chrome()
        self.ip = "172.0.0.2"
        self.port = 8000
        self.url = "http://{}:{}/docs".format(self.ip, self.port)
        self.httpd = HTTPServer((ip, port), CORSRequestHandler)
        self.httpd.serve_forever()

    def tearDown(self):
        pass

    def test_smoke(self):
        driver = self.driver
        driver.get(self.url)
        self.assertIn("Spinorama", driver.title)

    def test_search_in_python_org(self):
        driver = self.driver
        driver.get("http://www.python.org")
        self.assertIn("Python", driver.title)
        elem = driver.find_element_by_name("q")
        elem.send_keys("pycon")
        elem.send_keys(Keys.RETURN)
        assert "No results found." not in driver.page_source

    def tearDown(self):
        self.driver.close()


if __name__ == "__main__":
    unittest.main()
