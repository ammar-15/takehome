import os, re, requests, openai
import sys
from urllib.parse import urljoin
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
def ai_prompt(prompt, log_label=""):
    global TOTAL_TOKENS
    TOTAL_TOKENS += estimate_tokens(prompt)
    print(f"\n[ AI PROMPT — {log_label}]\n{prompt[:500]}...\n")

    res = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    response = res.choices[0].message.content.strip()

    print(f"\n [AI RESPONSE — {log_label}]\n{response}\n{'─'*80}")
    return response


#  AI chooses best next link
def ai_pick_best_link(current_url, links, full_text, year="2024"):
    prompt = f"""
You are helping locate the official annual report PDF for the year {year}.
Only choose annual reports, not quarterly.

The current page is: {current_url}

Here are the visible links on the page:
{chr(10).join(links)}

Here is the full page content (all headings, buttons, paragraphs):
{full_text[:12000]}

Which link or element would you click next to get closer to downloading the annual report PDF? Return a single full URL only.
"""
    return ai_prompt(prompt)

# Load and parse page with Playwright
def scan_page(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(url, timeout=60000)
            page.wait_for_selector("body", timeout=10000)
        except Exception as e:
            print(f"[ ERROR] Failed to load: {url}\n{e}")
            browser.close()
            return [], "", url

        # Wait a bit more for JS-heavy sites
        page.wait_for_timeout(3000)

        anchors = page.query_selector_all("a[href]")
        buttons = page.query_selector_all("button")
        headings = page.query_selector_all("h1, h2, h3, h4, h5, h6")
        paragraphs = page.query_selector_all("p, span, div")

        links = []
        for a in anchors:
            href = a.get_attribute("href")
            if href:
                links.append(href if href.startswith("http") else urljoin(page.url, href))

        # Gather all visible text content
        content = []
        for el in headings + buttons + paragraphs:
            try:
                txt = el.inner_text().strip()
                if txt:
                    content.append(txt)
            except:
                continue

        full_text = "\n".join(content)
        browser.close()
        return list(set(links)), full_text, url


#  Download PDF
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
        return None, start_url
    if start_url in visited:
        return None, start_url
    visited.add(start_url)

    links, text, current_url = scan_page(start_url)
    pdf_links = [l for l in links if (
        (".pdf" in l.lower() or "download" in l.lower() or "asset" in l.lower()) and
        year in l and
        not l.endswith("/")
    )]
    if pdf_links:
        print(f"[ PDF LINK FOUND] {pdf_links[0]}")
        if download_pdf(pdf_links[0], year, ticker):
            return pdf_links[0], current_url

    next_url = ai_pick_best_link(current_url, links, text, year)
    if not next_url or next_url in visited:
        print("[ No better link found.]")
        return None, current_url
    if next_url.endswith(".pdf") or "download" in next_url or "asset" in next_url:
        if download_pdf(next_url, year, ticker):
            return next_url, current_url
        else:
            return None, current_url
    return recursive_ai_nav(next_url, year, ticker, depth + 1, visited)

# Try previous years using recursive AI fallback
def try_other_years(from_url, ticker, from_year=2023):
    current_base = from_url
    for y in range(from_year, 2014, -1):
        print(f"\n[ AI BACKTRACE] Attempting to find report for {y}")
        result_url, new_base = recursive_ai_nav(current_base, str(y), ticker)
        if result_url:
            current_base = new_base
        else:
            print(f"[ Could not find report for {y}]")

#  Get IR URL using AI
def find_ir_url_via_ai(ticker):
    prompt = f"""Find the official investor relations or annual reports page for European company '{ticker}'. Return the best direct URL."""
    return ai_prompt(prompt)

#   Main function
def scrapeticker(ticker):
    print(f"\n🔍 Scraping 10-year annual reports for: {ticker}")
    start_url = extract_first_url(find_ir_url_via_ai(ticker))
    print(f"[IR URL] {start_url}")

    pdf_2024, base_url = recursive_ai_nav(start_url, "2024", ticker)
    if pdf_2024:
        try_other_years(base_url, ticker, from_year=2023)
    else:
        print("[ Could not locate 2024 report]")

    print(f"\n Done. Tokens used: {TOTAL_TOKENS}")

 
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scraper_test.py <TICKER>")
        sys.exit(1)
    scrapeticker(sys.argv[1].upper())
