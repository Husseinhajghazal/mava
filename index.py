import requests
import re
import pandas as pd
import time
from selenium import webdriver
from bs4 import BeautifulSoup


def scrape_trendyol():
    url = "https://www.trendyol.com/"
    r = requests.get(url + "erkek-sort-x-g2-c119")
    soup = BeautifulSoup(r.text, 'html.parser')

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
    return df.drop_duplicates(subset=['Adı']).dropna(subset=['Adı', 'Fiyatı', 'Bağlantı'])


def scrape_migros(driver):
    url = "https://www.migros.com.tr"
    driver.get(url + "/telefon-c-2add")
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    links = soup.find_all("a", class_="product-name")
    links_list = []
    names_list = []
    for link in links:
        product_link = link.get("href")
        links_list.append(url + product_link)
        names_list.append(link.get_text())

    prices = soup.find_all("div", class_="price-container")
    prices_list = []
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

    df = pd.DataFrame({
        "Adı": names_list,
        "Fiyatı": prices_list,
        "Bağlantı": links_list,
        "Category": "Telefon",
        "Site": "Migros"
    })
    return df.drop_duplicates(subset=['Adı']).dropna(subset=['Adı', 'Fiyatı', 'Bağlantı'])


def scrape_hepsiburada(driver):
    url = "https://www.hepsiburada.com"
    driver.get(url + "/erkek-sortlar-c-60000754")
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    links = soup.find_all("a", class_=re.compile("productCardLink"))
    links_list = [url + link.get("href") for link in links]
    names_list = [link.get("title") for link in links]

    prices = soup.find_all("div", class_=re.compile("price-module_finalPrice"))
    prices_list = [float(price.get_text().replace('TL', '').replace('.', '').replace(',', '.')) for price in prices]

    df = pd.DataFrame({
        "Adı": names_list,
        "Fiyatı": prices_list,
        "Bağlantı": links_list,
        "Category": "Erkek Şort",
        "Site": "Hepsiburada"
    })
    return df.drop_duplicates(subset=['Adı']).dropna(subset=['Adı', 'Fiyatı', 'Bağlantı'])


def main():
    all_data = []
    all_data.append(scrape_trendyol())
    driver = webdriver.Chrome()
    try:
        all_data.append(scrape_migros(driver))
        all_data.append(scrape_hepsiburada(driver))
    finally:
        driver.quit()
    df = pd.concat(all_data, ignore_index=True)
    df.to_json("data.json", orient="records", force_ascii=False, indent=2)


if __name__ == "__main__":
    main()