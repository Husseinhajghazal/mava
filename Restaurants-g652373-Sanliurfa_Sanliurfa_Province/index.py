import os
import json
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import re

# --- Constants and Mappings ---
turkish_months = {
    "Oca": "01", "Şub": "02", "Mar": "03", "Nis": "04",
    "May": "05", "Haz": "06", "Tem": "07", "Ağu": "08",
    "Eyl": "09", "Eki": "10", "Kas": "11", "Ara": "12"
}
travel_types = {
    "Çiftler": "Couple", "Aile": "Family", "Yalnız": "Solo",
    "İşletme": "Business", "Arkadaşlar": "Friends",
}

# --- Restaurants to Skip ---
SKIP_RESTAURANTS = {}

# --- Utility Functions ---
def convert_turkish_date(date_str):
    """Convert Turkish month-year string to MM.YYYY format."""
    try:
        month_str, year = date_str.split()
        month = turkish_months.get(month_str)
        return f"{month}.{year}" if month else ""
    except ValueError:
        return ""

def fetch_html(url, api_key):
    """Fetch HTML content using the webscraping API."""
    resp = requests.get("https://api.webscrapingapi.com/v2", params={
        "api_key": api_key,
        "url": url,
        "render_js": "true"
    })
    if resp.status_code == 200:
        return BeautifulSoup(resp.text, 'html.parser')
    raise Exception(f"Failed to fetch {url} ({resp.status_code})")

def fetch_html_with_retry(url, api_key, max_retries=10):
    """Fetch HTML content with retry logic."""
    for attempt in range(1, max_retries + 1):
        try:
            return fetch_html(url, api_key)
        except Exception as e:
            print(f"    Fetch attempt {attempt} failed: {e}")
            if attempt == max_retries:
                print(f"    Giving up on this page after {max_retries} attempts.")
                return None

def extract_reviews(soup, restaurant_name):
    """Extract reviews from the soup for a given restaurant."""
    reviews = []
    reviews_container = soup.select_one('div.LMGCx.f.e')
    if not reviews_container:
        return reviews
    for review in reviews_container.select('div.JVaPo.Gi.kQjeB'):
        user_tag = review.select_one('a.BMQDV._F.Gv.wSSLS.SwZTJ.FGwzt.ukgoS')
        user_name = user_tag.get_text(strip=True) if user_tag else ""
        user_profile_link = (
            "https://www.tripadvisor.com.tr" + user_tag.get('href') if user_tag else ""
        )
        rating_tag = review.select_one('svg.evwcZ')
        paths = rating_tag.select("path") if rating_tag else []
        rate = sum(1 for p in paths if "a9.983" not in p.get("d", ""))
        visit_info_tag = review.select('div.biGQs._P.fiohW.ezezH')
        visit_date = ""
        travel_type = ""
        if visit_info_tag and len(visit_info_tag) > 0:
            try:
                visit_date = visit_info_tag[0].get_text(strip=True)
            except Exception:
                visit_date = ""
        if visit_info_tag and len(visit_info_tag) > 1:
            try:
                travel_type = visit_info_tag[1].get_text(strip=True)
            except Exception:
                travel_type = ""
        title_tag = review.select_one('a.BMQDV._F.Gv.wSSLS.SwZTJ.FGwzt.ukgoS')
        review_title = title_tag.get_text(strip=True) if title_tag else ""
        text_tag = review.select_one('span._d._c')
        review_text = text_tag.get_text(strip=True) if text_tag else ""
        other_ratings = review.select('div.biGQs._P.fiohW.biKBZ.navcl')
        value_rating = service_rating = food_rating = atmosphere_rating = 0
        if len(other_ratings) > 3:
            try:
                value_rating = int(other_ratings[0].get_text(strip=True).split(",")[0])
                service_rating = int(other_ratings[1].get_text(strip=True).split(",")[0])
                food_rating = int(other_ratings[2].get_text(strip=True).split(",")[0])
                atmosphere_rating = int(other_ratings[3].get_text(strip=True).split(",")[0])
            except Exception:
                pass
        helpful_tag = review.select_one('span.biGQs._P.navcl')
        try:
            helpful_vote_count = int(helpful_tag.get_text(strip=True).split()[0]) if helpful_tag else 0
        except Exception:
            helpful_vote_count = 0
        reviews.append({
            "restaurant_name": restaurant_name,
            "user_name": user_name,
            "user_profile_link": user_profile_link,
            "rating": rate,
            "visit_date": visit_date,
            "travel_type": travel_type,
            "review_title": review_title,
            "review_text": review_text,
            "value_rating": value_rating,
            "service_rating": service_rating,
            "food_rating": food_rating,
            "atmosphere_rating": atmosphere_rating,
            "helpful_vote_count": helpful_vote_count
        })
    return reviews

def get_next_page_url(soup, current_page):
    """Get the URL for the next page of reviews."""
    next_page_links = soup.select('a.BrOJk.u.j.z._F._S.wSSLS.tIqAi.unMkR.xtNBb')
    if not next_page_links:
        return None
    idx = 1 if current_page > 0 and len(next_page_links) > 1 else 0
    next_link = next_page_links[idx].get('href')
    if not next_link:
        return None
    return "https://www.tripadvisor.com.tr" + next_link

def extract_total_reviews(soup):
    """Extract the total number of reviews from the soup."""
    reviews_text = soup.select_one('div.biGQs._P.fiohW.kSNRl.KeZJf')
    if not reviews_text:
        return 0
    try:
        return int(reviews_text.get_text(strip=True).split()[2].replace('.', '').replace("(", '').replace(")", ''))
    except Exception:
        return 0

def safe_filename(name):
    # Remove invalid characters for Windows and Unix
    name = re.sub(r'[\\/:*?"<>|]', '', name)
    return name

# --- Main Scraping Logic ---
def main():
    load_dotenv()
    api_key = os.getenv("WEBSCRAPING_API_KEY")
    reviews_dir = Path("Reviews")
    reviews_dir.mkdir(exist_ok=True)
    directory = Path.cwd()
    folder_name = directory.name
    files_count = sum(1 for f in directory.iterdir() if f.is_file() and f.suffix == ".json" and not f.name.startswith("Reviews"))

    for file_number in range(0, files_count, 30):
        file_path = directory / f"{folder_name}_page_{file_number}.json"
        if not file_path.exists():
            continue
        with open(file_path, 'r', encoding='utf-8') as file:
            restaurants = json.load(file)

        for restaurant in restaurants:
            restaurant_name = restaurant.get("name", "restaurant")
            if restaurant_name in SKIP_RESTAURANTS:
                print(f"Skipping restaurant: {restaurant_name}")
                continue
            link = restaurant.get("link")
            print(f"Scraping reviews for: {restaurant_name}")
            # --- Retry fetching the first page ---
            soup = fetch_html_with_retry(link, api_key)
            if soup is None:
                print(f"  Could not fetch first page for {restaurant_name}, skipping.")
                continue
            # --- Retry extracting total reviews ---
            for attempt in range(10):
                total_reviews = extract_total_reviews(soup)
                if total_reviews is not None:
                    break
                print(f"    Failed to extract review count (attempt {attempt+1}), retrying fetch...")
                soup = fetch_html_with_retry(link, api_key)
                if soup is None:
                    break
            reviews_data = []
            if total_reviews > 0:
                review_pages = total_reviews // 15 + 1
                for i in range(review_pages):
                    print(f"  Page {i+1}/{review_pages}")
                    # --- Retry extracting reviews and refetch page if not found ---
                    for attempt in range(10):
                        try:
                            page_reviews = extract_reviews(soup, restaurant_name)
                            if page_reviews:
                                reviews_data.extend(page_reviews)
                                break
                            else:
                                print(f"    Reviews component not found (attempt {attempt+1}), retrying fetch...")
                                soup = fetch_html_with_retry(link if i == 0 else get_next_page_url(soup, i-1), api_key)
                        except Exception as e:
                            print(f"    Failed to extract reviews (attempt {attempt+1}): {e}")
                            if attempt == 9:
                                print("    Skipping this page after 10 failed attempts.")
                    else:
                        print(f"    Skipping restaurant {restaurant_name} after 10 failed attempts to extract reviews on page {i+1}.")
                        break
                    next_page_url = get_next_page_url(soup, i)
                    if not next_page_url:
                        print("  No more pages to scrape.")
                        break
                    # --- Retry fetching next page ---
                    soup = fetch_html_with_retry(next_page_url, api_key)
                    if soup is None:
                        print(f"  Failed to fetch next page after retries. Stopping further pages for this restaurant.")
                        break
            # Save reviews
            out_path = reviews_dir / f"{safe_filename(restaurant_name)}.json"
            pd.DataFrame(reviews_data).to_json(out_path, orient="records", force_ascii=False, indent=2)
            print(f"Saved {len(reviews_data)} reviews to {out_path}")

if __name__ == "__main__":
    main()
