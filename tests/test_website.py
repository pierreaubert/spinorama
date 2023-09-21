# -*- coding: utf-8 -*-
#
import platform
import os
import unittest

import pytest

from selenium import webdriver
from selenium.webdriver.common.by import By


PROD = "https://www.spinorama.org"
DEV = "https://dev.spinorama.org"
COMPARE = "/compare.html?origin0=Vendors-Neumann&measurement=CEA2034&origin1=ErinsAudioCorner&speaker1=Focal+Solo6+Be"


def systemcheck():
    current_os = os.getenv("OSTYPE")
    current_display = os.getenv("DISPLAY")

    if current_display is None or len(current_display) == 0:
        return False
    
    if (
        platform.system() == "Linux" or (current_os is not None and current_os == "linux-gnu")
    ): 
        return False

    if (
        platform.system() == "darwin22.0"
    ):
        return False

    return True


@pytest.mark.skipif(not systemcheck(), reason="headless")
class SpinoramaWebsiteTests(unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Chrome()

    def tearDown(self):
        self.driver.quit()

    def test_index_smoke(self):
        self.driver.get(DEV)
        title = self.driver.title
        self.assertIn("collection", title)

    def test_index_search(self):
        self.driver.get(DEV)
        self.driver.implicitly_wait(2)

        search_box = self.driver.find_element(by=By.ID, value="searchInput")

        search_box.clear()
        search_box.send_keys("elac")
        elac = self.driver.find_element(by=By.ID, value="Elac-Carina-BS243-4")
        self.assertIsNotNone(elac)
        self.assertTrue(elac.is_displayed())
        is_hidden = "hidden" in elac.get_attribute("class")
        self.assertFalse(is_hidden)
        gene = self.driver.find_element(by=By.ID, value="Genelec-8361A")
        self.assertIsNotNone(gene)
        is_hidden = "hidden" in gene.get_attribute("class")
        self.assertTrue(is_hidden)

        search_box.clear()
        search_box.send_keys("8361A")
        gene = self.driver.find_element(by=By.ID, value="Genelec-8361A")
        self.assertIsNotNone(gene)
        self.assertNotIn("hidden", gene.get_attribute("class"))

        search_box.clear()
        search_box.send_keys("8361")
        gene = self.driver.find_element(by=By.ID, value="Genelec-8361A")
        self.assertIsNotNone(gene)
        self.assertNotIn("hidden", gene.get_attribute("class"))


if __name__ == "__main__":
    if systemcheck():
        unittest.main()
