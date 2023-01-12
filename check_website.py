# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import unittest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# class CORSRequestHandler(SimpleHTTPRequestHandler):
#    """ Generate CORS headers """
#
#    def end_headers(self):
#        self.send_header("Access-Control-Allow-Origin", "*")
#        self.send_header("Access-Control-Allow-Methods", "GET")
#        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
#        return super(CORSRequestHandler, self).end_headers()


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
            # expect found
            _ = wait.until(EC.visibility_of_element_located((By.ID, "Genelec-8341A")))
            # expect notfound
            _ = wait.until(EC.invisibility_of_element_located((By.ID, "KEF-LS50")))
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
            # expect found
            _ = wait.until(EC.visibility_of_element_located((By.ID, "Genelec-8341A")))
            # expect notfound
            _ = wait.until(EC.invisibility_of_element_located((By.ID, "KEF-LS50")))
        finally:
            pass

    def tearDown(self):
        self.driver.close()


if __name__ == "__main__":
    unittest.main()
