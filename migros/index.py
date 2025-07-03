import pandas as pd
import time
from selenium import webdriver
from bs4 import BeautifulSoup

links_list = []
names_list = []
prices_list = []

driver = webdriver.Chrome()
url = "https://www.migros.com.tr"

i = 1
while True:
    page_url = url + f"/telefon-c-2add?sayfa={i}"
    driver.get(page_url)

    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    links = soup.find_all("a", class_="product-name")
    if not links:
        break
    for link in links:
        product_link = link.get("href")
        links_list.append(url + product_link)
        names_list.append(link.get_text())

    prices = soup.find_all("div", class_="price-container")
    for price in prices:
        discounted = price.find("div", class_="sale-price")
        if discounted:
            price_text = discounted.get_text(strip=True)
        else:
            regular = price.find("div", class_="price")
            if regular:
                price_text = regular.get_text(strip=True)
            else:
                continue
        price_cleaned = price_text.replace("TL", "").replace(".", "").replace(",", ".")
        try:
            prices_list.append(float(price_cleaned))
        except ValueError:
            continue

    i += 1

df = pd.DataFrame({
    "Adı": names_list,
    "Fiyatı": prices_list,
    "Bağlantı": links_list,
    "Category": "Telefon",
    "Site": "Migros"
})
df.drop_duplicates(subset=['Adı', 'Bağlantı']).dropna(subset=['Adı', 'Fiyatı', 'Bağlantı'])
df.to_json("migros_telefons.json", orient="records", force_ascii=False, indent=2)