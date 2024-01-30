# -*- coding: utf-8 -*-
#
import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions


PROD = "https://www.spinorama.org"
DEV = "https://dev.spinorama.org"
COMPARE = "/compare.html"


class SpinoramaWebsiteTests(unittest.TestCase):
    def setUp(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        # unclear why we need that option but selenium crashes without it
        options.add_argument('--remote-debugging-pipe')
        self.driver = webdriver.Chrome(options=options)

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

        search_box.clear()
        search_box.send_keys("elac")
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

    def test_filters_brand(self):
        self.driver.get(DEV)
        self.driver.implicitly_wait(2)

        WebDriverWait(self.driver, 1).until(
            expected_conditions.element_to_be_clickable((By.ID, "filters-dropdown"))
        ).click()

        WebDriverWait(self.driver, 1).until(
            expected_conditions.element_to_be_clickable((By.ID, "selectBrand"))
        ).click()

        brand_box = Select(self.driver.find_element(by=By.ID, value="selectBrand"))

        brand_box.select_by_value("Elac")

        elac = self.driver.find_element(by=By.ID, value="Elac-Carina-BS243-4")
        self.assertIsNotNone(elac)
        self.assertTrue(elac.is_displayed())
        is_hidden = "hidden" in elac.get_attribute("class")
        self.assertFalse(is_hidden)

    def test_filters_price(self):
        self.driver.get(DEV)
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

        a306 = self.driver.find_element(by=By.ID, value="Thomann-Swissonic-A306")
        self.assertIsNotNone(a306)
        self.assertTrue(a306.is_displayed())
        is_hidden = "hidden" in a306.get_attribute("class")
        self.assertFalse(is_hidden)

    def test_compare_basic(self):
        compare_basic = "speaker0=Ascend+Acoustics+Sierra+1+V2&origin0=Vendors-Ascend+Acoustics&version0=vendor&speaker1=Neumann+KH+150&origin1=ASR&version1=asr&measurement=CEA2034"
        self.driver.get("{}/{}?{}".format(DEV, COMPARE, compare_basic))
        self.driver.implicitly_wait(2)


if __name__ == "__main__":
    unittest.main()
