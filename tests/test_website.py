# -*- coding: utf-8 -*-
#
import unittest

knownMeasurements = [
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


PROD = "https://www.spinorama.org"
DEV = "https://dev.spinorama.org"
COMPARE = "/compare.html"
SIMILAR = "/similar.html"
SCORES = "/scores.html"


class SpinoramaWebsiteTests(unittest.TestCase):

    def setUp(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        # unclear why we need that option but selenium crashes without it
        options.add_argument("--remote-debugging-pipe")
        self.driver = webdriver.Chrome(options=options)

    def tearDown(self):
        self.driver.quit()

    def test_index_smoke(self):
        self.driver.get(DEV)
        title = self.driver.title
        self.assertIn("collection", title)

    def test_index_search_elac(self):
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
        with self.assertRaises(NoSuchElementException):
            gene = self.driver.find_element(by=By.ID, value="Genelec-8361A")
            self.assertIsNone(gene)

    def test_index_search_genelec(self):
        self.driver.get(DEV)
        self.driver.implicitly_wait(2)

        search_box = self.driver.find_element(by=By.ID, value="searchInput")

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
        self.driver.get("{}?{}".format(DEV, "count=10000"))
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

    def test_compare_measurements_without_low_freq(self):
        compare_basic = "speaker0=Genelec+8351A&origin0=Princeton&version0=princeton&measurement=CEA2034&speaker1=Polk+Audio+Legend+L200&origin1=Misc&version1=misc-audioholics"
        self.driver.get("{}/{}?{}".format(DEV, COMPARE, compare_basic))
        self.driver.implicitly_wait(2)

    def test_compare_allgraphs(self):
        compare_basic = "speaker0=Ascend+Acoustics+Sierra+1+V2&origin0=Vendors-Ascend+Acoustics&version0=vendor&speaker1=Neumann+KH+150&origin1=ASR&version1=asr"
        for measurement in knownMeasurements:
            self.driver.get(
                "{}/{}?{}&measurement={}".format(
                    DEV, COMPARE, compare_basic, measurement.replace(" ", "+")
                )
            )
            self.driver.implicitly_wait(2)

    def test_similar_basic(self):
        similar_basic = (
            "speaker0=Ascend+Acoustics+Sierra+1+V2&origin0=Vendors-Ascend+Acoustics&version0=vendor"
        )
        self.driver.get("{}/{}?{}".format(DEV, SIMILAR, similar_basic))
        self.driver.implicitly_wait(2)

    def test_similar_allgraphs(self):
        for measurement in knownMeasurements:
            similar_basic = "speaker0=Ascend+Acoustics+Sierra+1+V2&origin0=Vendors-Ascend+Acoustics&version0=vendor"
            self.driver.get(
                "{}/{}?{}&graphs={}".format(
                    DEV, SIMILAR, similar_basic, measurement.replace(" ", "+")
                )
            )
            self.driver.implicitly_wait(2)

    def test_scores_basic(self):
        scores_basic = "quality=High&sort=score&count=1000"
        self.driver.get("{}/{}?{}".format(DEV, SCORES, scores_basic))
        self.driver.implicitly_wait(2)

    def test_scores_check_filters(self):
        scores_basic = "quality=High&sort=score&count=1000&weightMin=50"
        self.driver.get("{}/{}?{}".format(DEV, SCORES, scores_basic))
        self.driver.implicitly_wait(2)


if __name__ == "__main__":
    unittest.main()
