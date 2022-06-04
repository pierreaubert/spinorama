from selenium import webdriver
from selenium.webdriver.common.by import By

PROD = "https://https://pierreaubert.github.io/spinorama"
DEV = "https://spinorama.internet-box.ch"


def test_spinorama_index_smoke(driver, env):

    if env == "prod":
        driver.get(PROD)
    else:
        driver.get(DEV)

    title = driver.title
    assert "collection" in title

    driver.implicitly_wait(0.5)


def test_spinorama_index_search(driver, env):

    if env == "prod":
        driver.get(PROD)
    else:
        driver.get(DEV)

    driver.implicitly_wait(2)

    search_box = driver.find_element(by=By.ID, value="searchInput")

    search_box.clear()
    search_box.send_keys("elac")
    elac = driver.find_element(by=By.ID, value="Elac-Carina-BS243-4")
    assert elac is not None
    assert elac.is_displayed()
    is_hidden = "hidden" in elac.get_attribute("class")
    assert not is_hidden
    gene = driver.find_element(by=By.ID, value="Genelec-8361A")
    assert gene is not None
    is_hidden = "hidden" in gene.get_attribute("class")
    assert is_hidden

    search_box.clear()
    search_box.send_keys("8361A")
    gene = driver.find_element(by=By.ID, value="Genelec-8361A")
    assert gene is not None
    assert not "hidden" in gene.get_attribute("class")

    search_box.clear()
    search_box.send_keys("8361")
    gene = driver.find_element(by=By.ID, value="Genelec-8361A")
    assert gene is not None
    assert not "hidden" in gene.get_attribute("class")


def test_spinorama_compare_two(driver, env):

    COMPARE = "/compare.html?origin0=Vendors-Neumann&measurement=CEA2034&origin1=ErinsAudioCorner&speaker1=Focal+Solo6+Be"

    if env == "prod":
        driver.get(PROD + COMPARE)
    else:
        driver.get(DEV + COMPARE)

    driver.implicitly_wait(2)


if __name__ == "__main__":
    driver = webdriver.Chrome()
    test_spinorama_index_smoke(driver, env="dev")
    test_spinorama_index_search(driver, env="dev")
    test_spinorama_compare_two(driver, env="dev")
    driver.quit()
