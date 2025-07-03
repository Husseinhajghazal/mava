import re
import pandas as pd
import time
from selenium import webdriver
from bs4 import BeautifulSoup

url = "https://www.trendyol.com/"

driver = webdriver.Chrome()
driver.get(url + "erkek-sort-x-g2-c119")

time.sleep(2)

for i in range(3):
    driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight - 3500);")
    time.sleep(3)

soup = BeautifulSoup(driver.page_source, 'html.parser')

links = soup.find_all("a", class_="p-card-chldrn-cntnr")
links_list = [url + link.get("href") for link in links]

prices = soup.find_all("div", class_=re.compile("discounted"))
prices_list = [float(price.get_text().replace('TL', '').replace('.', '').replace(',', '.')) for price in prices]

names = soup.find_all("div", class_="p-card-wrppr")
names_list = [name.get("title") for name in names]

df = pd.DataFrame({
    "Adı": names_list,
    "Fiyatı": prices_list,
    "Bağlantı": links_list,
    "Category": "Erkek Şort",
    "Site": "Trendyol"
})
df.drop_duplicates(subset=['Adı']).dropna(subset=['Adı', 'Fiyatı', 'Bağlantı'])
df.to_json("trendyol_mens_shorts.json", orient="records", force_ascii=False, indent=2)