#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
import unittest
import threading
import http.server
import socketserver
import os
import socket
import sys
import time
import urllib.request
import urllib.error

known_measurements = [
    "CEA2034",
    "On Axis",
    "Estimated In-Room Response",
    "Early Reflections",
    "Horizontal Reflections",
    "Vertical Reflections",
    "SPL Horizontal",
    "SPL Horizontal Normalized",
    "SPL Vertical",
    "SPL Vertical Normalized",
    "SPL Horizontal Contour",
    "SPL Horizontal Contour Normalized",
    "SPL Vertical Contour",
    "SPL Vertical Contour Normalized",
    "SPL Horizontal Contour 3D",
    "SPL Horizontal Contour Normalized 3D",
    "SPL Vertical Contour 3D",
    "SPL Vertical Contour Normalized 3D",
    "SPL Horizontal Globe",
    "SPL Horizontal Globe Normalized",
    "SPL Vertical Globe",
    "SPL Vertical Globe Normalized",
    "SPL Horizontal Radar",
    "SPL Vertical Radar",
]

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service


PROD = "https://www.spinorama.org"
COMPARE = "/compare.html"
SIMILAR = "/similar.html"
SCORES = "/scores.html"

# The built JS in dist/ hardcodes urlSite to http://localhost:8080,
# so the test server must use the same port for metadata fetches to work.
DEV_PORT = 8080


@unittest.skipIf(
    sys.platform == "darwin",
    "chromedriver-based selenium tests are disabled on macOS",
)
class SpinoramaWebsiteTests(unittest.TestCase):
    server = None
    server_thread = None
    DEV = None

    @classmethod
    def _port_is_serving(cls):
        """Check if port 8080 is already serving HTTP content."""
        try:
            urllib.request.urlopen(f"http://localhost:{DEV_PORT}/", timeout=2)
            return True
        except (urllib.error.URLError, OSError):
            return False

    @classmethod
    def setUpClass(cls):
        """Start HTTP server before all tests, or reuse existing one on port 8080."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dist_dir = os.path.join(project_root, "dist")

        if not os.path.exists(dist_dir):
            raise RuntimeError(f"dist directory not found at {dist_dir}")

        cls.DEV = f"http://localhost:{DEV_PORT}"

        # If port 8080 is already serving (e.g. dev server), reuse it
        if cls._port_is_serving():
            cls.server = None
            cls.server_thread = None
            return

        # Change to dist directory for serving
        os.chdir(dist_dir)

        Handler = http.server.SimpleHTTPRequestHandler

        class ReuseAddrTCPServer(socketserver.TCPServer):
            allow_reuse_address = True

        try:
            cls.server = ReuseAddrTCPServer(("localhost", DEV_PORT), Handler)
        except OSError as e:
            raise unittest.SkipTest(
                f"Port {DEV_PORT} is in use but not serving HTTP. "
                f"Stop the process or run the dev server: {e}"
            )

        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        """Stop HTTP server after all tests (only if we started it)."""
        if cls.server:
            cls.server.shutdown()
            cls.server.server_close()
        if cls.server_thread:
            cls.server_thread.join(timeout=1)

    def setUp(self):
        service = Service()
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        # unclear why we need that option but selenium crashes without it
        # options.add_argument("--remote-debugging-pipe")
        self.driver = webdriver.Chrome(service=service, options=options)

    def tearDown(self):
        self.driver.quit()

    def test_index_smoke(self):
        self.driver.get(self.DEV)
        title = self.driver.title
        self.assertIn("collection", title)

    def test_index_search_elac(self):
        self.driver.get("{}/{}".format(self.DEV, "?search=Elac"))

        # Wait for the Elac speaker to appear
        elac = WebDriverWait(self.driver, 10).until(
            expected_conditions.presence_of_element_located((By.ID, "Elac-Carina-BS243-4"))
        )
        self.assertIsNotNone(elac)

        with self.assertRaises(NoSuchElementException):
            genelec = self.driver.find_element(by=By.ID, value="Genelec-8361A")

        with self.assertRaises(NoSuchElementException):
            revel = self.driver.find_element(by=By.ID, value="Revel-F35")

    def test_index_search_elac_menu(self):
        self.driver.get(self.DEV)
        self.driver.implicitly_wait(2)

        search_box = self.driver.find_element(by=By.ID, value="searchInput")

        search_box.clear()
        search_box.send_keys("elac")
        search_box.clear()
        search_box.send_keys("elac")

        self.assertIsNotNone(search_box)

    def test_index_search_genelec(self):
        self.driver.get("{}/{}".format(self.DEV, "?search=Genelec"))

        # Wait for the Genelec speaker to appear
        genelec = WebDriverWait(self.driver, 10).until(
            expected_conditions.presence_of_element_located((By.ID, "Genelec-8361A"))
        )
        self.assertIsNotNone(genelec)

        with self.assertRaises(NoSuchElementException):
            self.driver.find_element(by=By.ID, value="Elac-Carina-BS243-4")

    def test_filters_brand(self):
        self.driver.get("{}?{}".format(self.DEV, "page=1&count=100&brand=Elac"))

        # Wait for the Elac speaker to appear
        elac = WebDriverWait(self.driver, 10).until(
            expected_conditions.presence_of_element_located((By.ID, "Elac-Carina-BS243-4"))
        )
        self.assertIsNotNone(elac)
        self.assertTrue(elac.is_displayed())

    def test_filters_brand_menu(self):
        self.driver.get("{}?{}".format(self.DEV, "page=1&count=100"))
        self.driver.implicitly_wait(3)

        WebDriverWait(self.driver, 1).until(
            expected_conditions.element_to_be_clickable((By.ID, "filters-dropdown"))
        ).click()

        WebDriverWait(self.driver, 1).until(
            expected_conditions.element_to_be_clickable((By.ID, "selectBrand"))
        ).click()

        select_brand = self.driver.find_element(by=By.ID, value="selectBrand")
        brand_box = Select(select_brand)
        brand_box.select_by_value("Elac")
        self.assertIsNotNone(brand_box)

    def test_filters_price(self):
        self.driver.get("{}?{}".format(self.DEV, "count=10000&priceMin=120&priceMax=200"))

        # Wait for the Thomann speaker to appear
        a306 = WebDriverWait(self.driver, 10).until(
            expected_conditions.presence_of_element_located((By.ID, "Thomann-Swissonic-A306"))
        )
        self.assertIsNotNone(a306)
        self.assertTrue(a306.is_displayed())

    def test_filters_price_menu(self):
        self.driver.get("{}?{}".format(self.DEV, "count=10000"))
        self.driver.implicitly_wait(2)

        WebDriverWait(self.driver, 1).until(
            expected_conditions.element_to_be_clickable((By.ID, "filters-dropdown"))
        ).click()

        WebDriverWait(self.driver, 1).until(
            expected_conditions.element_to_be_clickable((By.ID, "inputPriceMin"))
        ).click()
        price_min = self.driver.find_element(by=By.ID, value="inputPriceMin")
        price_min.send_keys("120")

        WebDriverWait(self.driver, 1).until(
            expected_conditions.element_to_be_clickable((By.ID, "inputPriceMax"))
        ).click()
        price_max = self.driver.find_element(by=By.ID, value="inputPriceMax")
        price_max.send_keys("200")

        self.assertIsNotNone(price_min)
        self.assertIsNotNone(price_max)

    def test_compare_basic(self):
        compare_basic = "speaker0=Ascend+Acoustics+Sierra+1+V2&origin0=Vendors-Ascend+Acoustics&version0=vendor&speaker1=Neumann+KH+150&origin1=ASR&version1=asr&measurement=CEA2034"
        self.driver.get("{}/{}?{}".format(self.DEV, COMPARE, compare_basic))
        self.driver.implicitly_wait(2)

    def test_compare_measurements_without_low_freq(self):
        compare_basic = "speaker0=Genelec+8351A&origin0=Princeton&version0=princeton&measurement=CEA2034&speaker1=Polk+Audio+Legend+L200&origin1=Misc&version1=misc-audioholics"
        self.driver.get("{}/{}?{}".format(self.DEV, COMPARE, compare_basic))
        self.driver.implicitly_wait(2)

    def test_compare_allgraphs(self):
        compare_basic = "speaker0=Ascend+Acoustics+Sierra+1+V2&origin0=Vendors-Ascend+Acoustics&version0=vendor&speaker1=Neumann+KH+150&origin1=ASR&version1=asr"
        for measurement in known_measurements:
            self.driver.get(
                "{}/{}?{}&measurement={}".format(
                    self.DEV, COMPARE, compare_basic, measurement.replace(" ", "+")
                )
            )
            self.driver.implicitly_wait(2)

    def test_similar_basic(self):
        similar_basic = (
            "speaker0=Ascend+Acoustics+Sierra+1+V2&origin0=Vendors-Ascend+Acoustics&version0=vendor"
        )
        self.driver.get("{}/{}?{}".format(self.DEV, SIMILAR, similar_basic))
        self.driver.implicitly_wait(2)

    def test_similar_allgraphs(self):
        for measurement in known_measurements:
            similar_basic = "speaker0=Ascend+Acoustics+Sierra+1+V2&origin0=Vendors-Ascend+Acoustics&version0=vendor"
            self.driver.get(
                "{}/{}?{}&graphs={}".format(
                    self.DEV, SIMILAR, similar_basic, measurement.replace(" ", "+")
                )
            )
            self.driver.implicitly_wait(2)

    def test_scores_basic(self):
        scores_basic = "quality=High&sort=score&count=1000"
        self.driver.get("{}/{}?{}".format(self.DEV, SCORES, scores_basic))
        self.driver.implicitly_wait(2)

    def test_scores_check_filters(self):
        scores_basic = "quality=High&sort=score&count=1000&weightMin=50"
        self.driver.get("{}/{}?{}".format(self.DEV, SCORES, scores_basic))
        self.driver.implicitly_wait(2)


if __name__ == "__main__":
    unittest.main()
