const {Builder} = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');

const service = new chrome.ServiceBuilder('/home/pierre/bin/selenium/chromedriver');
const driver = new
Builder().forBrowser('chrome').setChromeService(service).build();

(async function openChromeTest() {
  try {
    let options = new chrome.Options();
    let driver = await new Builder()
	.setChromeOptions(options)
	.forBrowser('chrome')
	.build();
    await driver.get('https://www.google.com');
    await driver.quit();
  }
  catch (error) {
    console.log(error)
  }
})();
