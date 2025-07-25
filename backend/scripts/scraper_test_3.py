import os, sys, re, time
import requests, openai
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

#  Load API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# PDF folder
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

def scan_page(page, url, allowed_domain=None):
    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(3000)

        current_domain = urlparse(page.url).netloc
        allowed_domain = allowed_domain or current_domain

        #AGE GATE handling
        try:
            day_input = page.query_selector("select[name*='day'], input[name*='day']")
            month_input = page.query_selector("select[name*='month'], input[name*='month']")
            year_input = page.query_selector("select[name*='year'], input[name*='year']")
            submit_btn = page.query_selector("button[type='submit'], button:has-text('Enter'), input[type='submit']")

            if day_input and month_input and year_input:
                print("[🔓 AGE GATE] Filling in date: 01 01 2000")
                try:
                    if "select" in str(day_input): day_input.select_option("1")
                    else: day_input.fill("01")
                except: pass
                try:
                    if "select" in str(month_input): month_input.select_option("1")
                    else: month_input.fill("01")
                except: pass
                try:
                    if "select" in str(year_input): year_input.select_option("2000")
                    else: year_input.fill("2000")
                except: pass
                if submit_btn:
                    print("[🚪 AGE GATE] Submitting form")
                    old_url = page.url
                    submit_btn.click()
                    page.wait_for_timeout(2000)

                    if page.url != old_url:
                        print(f"[ URL changed] Now at {page.url}")
                    else:
                        print("[ℹ️ No URL change after submit (likely JS-driven age gate)]")

                    #   Prevent domain hijack
                    new_domain = urlparse(page.url).netloc
                    if allowed_domain not in new_domain:
                        print(f"[⚠️ REDIRECTED] {new_domain} is outside allowed domain ({allowed_domain}), going back.")
                        page.go_back()
                        page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[⚠️ AGE GATE ERROR] {e}")

        # Extract all links on the current page
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

        # fheck for sitemap link
        try:
            sitemap_link = page.query_selector("a:has-text('Sitemap')")
            if sitemap_link:
                print("[🗺️ SITEMAP] Navigating to Sitemap")
                sitemap_url = sitemap_link.get_attribute("href")
                if not sitemap_url.startswith("http"):
                    sitemap_url = urljoin(page.url, sitemap_url)
                page.goto(sitemap_url)
                page.wait_for_timeout(2000)
                anchors = page.query_selector_all("a[href]")
                links = [a.get_attribute("href") for a in anchors if a.get_attribute("href")]
                text = page.inner_text("body")
                return list(set(links)), text
        except Exception as e:
            print(f"[⚠️ SITEMAP FAIL] {e}")

        # try search option
        try:
            search_btn = page.query_selector("button[aria-label='Search'], button:has-text('Search')")
            if search_btn:
                print("[🔎 SEARCH] Clicking search button")
                search_btn.click()
                page.wait_for_timeout(1500)
                input_box = page.query_selector("input[type='search'], input[type='text']")
                if input_box:
                    print("[🔎 SEARCH] Typing 'annual report 2024'")
                    input_box.fill("annual report 2024")
                    input_box.press("Enter")
                    page.wait_for_timeout(4000)
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
                    return list(set(links)), text
        except Exception as e:
            print(f"[⚠️ SEARCH FAIL] {e}")

        return list(set(links)), text

    except Exception as e:
        print(f"[ PAGE LOAD ERROR] {e}")
        return [], ""

    
#  Download pdf

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

def recursive_ai_nav(page, start_url, year="2024", ticker="UNKNOWN", depth=0, visited=None, allowed_domain=None):
    if visited is None:
        visited = set()
    if depth > 8 or start_url in visited:
        return None
    visited.add(start_url)

    if not allowed_domain:
        allowed_domain = urlparse(start_url).netloc

    links, text = scan_page(page, start_url, allowed_domain)

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
    if "age-gate" in next_url:
        print(f"[ SKIPPING AGE GATE LOOP] {next_url}")
        return None
    if not next_url or next_url in visited:
        print("[ No better link found.]")
        return None

    if urlparse(next_url).netloc != allowed_domain:
        print(f"[ BLOCKED DOMAIN] {next_url} is outside {allowed_domain}")
        return None

    if next_url.endswith(".pdf") or "download" in next_url or "asset" in next_url:
        download_pdf(next_url, year, ticker)
        return next_url

    return recursive_ai_nav(page, next_url, year, ticker, depth + 1, visited, allowed_domain)


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

# pdfs Main function

def scrapeticker(ticker):
    print(f"\n🔍 Scraping 10-year annual reports for: {ticker}")
    start_url = extract_first_url(find_ir_url_via_ai(ticker))
    print(f"[IR URL] {start_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        pdf_2024 = recursive_ai_nav(page, start_url, "2024", ticker)
        if pdf_2024:
            try_other_years(pdf_2024, ticker, from_year=2023)
        else:
            print("[ Could not locate 2024 report]")

        browser.close()

    print(f"\n Done. Tokens used: {TOTAL_TOKENS}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scrapper_3.py <TICKER>")
        sys.exit(1)
    scrapeticker(sys.argv[1].upper())