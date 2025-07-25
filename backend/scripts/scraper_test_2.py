import os, sys, re, time
import requests, openai
from urllib.parse import urljoin
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

#  Load API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# pdf folder
PDF_FOLDER = os.path.join(os.path.dirname(__file__), "../pdfs")
os.makedirs(PDF_FOLDER, exist_ok=True)

#  Token tracking
TOTAL_TOKENS = 0

def estimate_tokens(msg):
    return len(msg) // 4

def extract_first_url(text):
    match = re.search(r"https?://[^\s)\]]+", text)
    return match.group(0) if match else ""

#  AI prompt

def ai_prompt(prompt):
    global TOTAL_TOKENS
    TOTAL_TOKENS += estimate_tokens(prompt)
    print(f"\n[ AI PROMPT]\n{prompt[:300]}...")
    res = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content.strip() # type: ignore

#  AI chooses best next link

def ai_pick_best_link(current_url, links, page_text, year="2024"):
    prompt = f"""You are helping locate the official annual report PDF for the year {year}.
Only choose annual reports, not quarterly.

The current page is: {current_url}

Here are the visible links:\n{chr(10).join(links)}

Visible page text:\n{page_text[:3000]}

Which link is the best next step? Only return one full URL."""
    return ai_prompt(prompt)

# Load and parse page with Playwright

def scan_page(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(url, timeout=60000)
            page.wait_for_timeout(4000)
        except Exception as e:
            print(f"[ ERROR] Failed to load: {url}\n{e}")
            browser.close()
            return [], ""

        anchors = page.query_selector_all("a[href]")
        links = []
        for a in anchors:
            href = a.get_attribute("href")
            if href:
                if href.startswith("http"):
                    links.append(href)
                else:
                    links.append(urljoin(page.url, href))

        text = page.inner_text("body")

        #try sitemap if no good links found
        sitemap_link = page.query_selector("a:has-text('Sitemap')")
        if sitemap_link:
            try:
                print("[🗺️ SITEMAP] Navigating to Sitemap")
                sitemap_url = sitemap_link.get_attribute("href")
                if not sitemap_url.startswith("http"): # type: ignore
                    sitemap_url = urljoin(url, sitemap_url)
                return scan_page(sitemap_url)
            except Exception as e:
                print(f"[⚠️ SITEMAP FAIL] {e}")

        #fallback2 try site search
        try:
            search_button = page.query_selector("button[aria-label='Search'], button:has-text('Search')")
            if search_button:
                print("[🔎 SEARCH] Clicking search button")
                search_button.click()
                page.wait_for_timeout(1500)
                input_box = page.query_selector("input[type='search'], input[type='text']")
                if input_box:
                    print("[🔎 SEARCH] Typing 'annual report 2024'")
                    input_box.fill("annual report 2024")
                    input_box.press("Enter")
                    page.wait_for_timeout(4000)
        except Exception as e:
            print(f"[⚠️ SEARCH FAIL] {e}")

        anchors = page.query_selector_all("a[href]")
        links = []
        for a in anchors:
            href = a.get_attribute("href")
            if href:
                if href.startswith("http"):
                    links.append(href)
                else:
                    links.append(urljoin(page.url, href))

        text = page.inner_text("body")
        browser.close()
        return list(set(links)), text

#  download pdf

def download_pdf(url, year=None, ticker="UNKNOWN"):
    ticker = ticker.upper()
    year = str(year) if year else "unknown"
    fname = f"{ticker}_{year}.pdf"
    fpath = os.path.join(PDF_FOLDER, fname)

    if os.path.exists(fpath):
        print(f"[SKIP] Already downloaded: {fname}")
        return True

    print(f"[ DOWNLOAD] {url}")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(fpath, "wb") as f:
            f.write(r.content)

        with open(fpath, "rb") as f:
            if not f.read(4) == b'%PDF':
                print(f"[ INVALID FILE] Not a real PDF. Removing: {fname}")
                os.remove(fpath)
                return False

        print(f"[ SAVED] {fname}")
        return True
    except Exception as e:
        print(f"[ DOWNLOAD ERROR] {e}")
        return False

#  Recursively use AI to navigate

def recursive_ai_nav(start_url, year="2024", ticker="UNKNOWN", depth=0, visited=None):
    if visited is None:
        visited = set()
    if depth > 8:
        print("[ ] Max depth reached.")
        return None
    if start_url in visited:
        return None
    visited.add(start_url)

    links, text = scan_page(start_url)
    pdf_links = [l for l in links if (
        (".pdf" in l.lower() or "download" in l.lower() or "asset" in l.lower()) and
        year in l and
        not l.endswith("/")
    )]
    if pdf_links:
        print(f"[ PDF LINK FOUND] {pdf_links[0]}")
        if download_pdf(pdf_links[0], year, ticker):
            return pdf_links[0]

    next_url = ai_pick_best_link(start_url, links, text, year)
    if not next_url or next_url in visited:
        print("[ No better link found.]")
        return None
    if next_url.endswith(".pdf") or "download" in next_url or "asset" in next_url:
        download_pdf(next_url, year, ticker)
        return next_url
    return recursive_ai_nav(next_url, year, ticker, depth + 1, visited)

# Try previous years using pattern match

def try_other_years(base_url_2024, ticker, from_year=2023):
    for y in range(from_year, 2014, -1):
        guess_url = re.sub(r"20\d{2}", str(y), base_url_2024)
        print(f"[TRY] {guess_url}")
        download_pdf(guess_url, y, ticker)

#  Get IR URL using AI

def find_ir_url_via_ai(ticker):
    prompt = f"""Find the official investor relations or annual reports page for European company '{ticker}'. Return the best direct URL."""
    return ai_prompt(prompt)

# Main

def scrapeticker(ticker):
    print(f"\n🔍 Scraping 10-year annual reports for: {ticker}")
    start_url = extract_first_url(find_ir_url_via_ai(ticker))
    print(f"[IR URL] {start_url}")

    pdf_2024 = recursive_ai_nav(start_url, "2024", ticker)
    if pdf_2024:
        try_other_years(pdf_2024, ticker, from_year=2023)
    else:
        print("[ Could not locate 2024 report]")

    print(f"\n Done. Tokens used: {TOTAL_TOKENS}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 quick scrape.py <TICKER>")
        sys.exit(1)
    scrapeticker(sys.argv[1].upper())