import unittest
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class CORSRequestHandler(SimpleHTTPRequestHandler):
    """ Generate CORS headers """

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        return super(CORSRequestHandler, self).end_headers()


class SpinoramaTest(unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Firefox()
        self.ip = "172.0.0.1"
        self.port = 8888
        self.url = "http://{}:{}/docs".format(self.ip, self.port)
        self.url = "https://pierreaubert.github.io/spinorama"
        # self.httpd = HTTPServer((self.ip, self.port), CORSRequestHandler)
        # print("server started on {}".format(self.url))
        # self.httpd.serve_forever()

    def test_index(self):
        driver = self.driver
        driver.get(self.url)
        self.assertIn("8341A", driver.page_source)
        search = driver.find_element_by_id("searchInput")
        # exact search
        search.send_keys("genelec")
        search.send_keys(Keys.RETURN)
        try:
            wait = WebDriverWait(driver, 10)
            found = wait.until(
                EC.visibility_of_element_located((By.ID, "Genelec-8341A"))
            )
            notfound = wait.until(
                EC.invisibility_of_element_located((By.ID, "KEF-LS50"))
            )
        finally:
            pass

    def test_eqs(self):
        driver = self.driver
        driver.get("{}/eqs.html".format(self.url))
        self.assertIn("8341A", driver.page_source)
        search = driver.find_element_by_id("searchInput")
        # exact search
        search.send_keys("genelec")
        search.send_keys(Keys.RETURN)
        try:
            wait = WebDriverWait(driver, 10)
            found = wait.until(
                EC.visibility_of_element_located((By.ID, "Genelec-8341A"))
            )
            notfound = wait.until(
                EC.invisibility_of_element_located((By.ID, "KEF-LS50"))
            )
        finally:
            pass

    def tearDown(self):
        self.driver.close()


if __name__ == "__main__":
    unittest.main()
