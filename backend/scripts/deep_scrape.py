import os, re, requests, openai
import sys
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
    """
    Estimates the number of tokens in a given message.
    Used for tracking OpenAI API token usage.
    """
    return len(msg) // 4

def extract_first_url(text):
    """
    Extracts the first URL found in a given text string.
    Uses a regular expression to find HTTP or HTTPS links.
    """
    match = re.search(r"https?://[^\s)\]]+", text)
    return match.group(0) if match else ""

#  AI prompt
def ai_prompt(prompt, log_label=""):
    """
    Sends a prompt to the OpenAI API and returns the AI's response.
    Tracks total token usage for API calls.
    """
    global TOTAL_TOKENS
    TOTAL_TOKENS += estimate_tokens(prompt)
    print(f"\n[AI PROMPT -- {log_label}]\n{prompt[:500]}...\n")

    res = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    response = res.choices[0].message.content.strip() # type: ignore

    print(f"\n[AI RESPONSE -- {log_label}]\n{response}\n{'─'*80}")
    return response


#  AI chooses best next link
def ai_pick_best_link(current_url, links, full_text, year="2024"):
    """
    Uses AI to select the best link from a list to navigate towards an annual report PDF.
    Considers the current URL, available links, and page text.
    """
    prompt = f"""
You are helping locate the official annual report PDF for the year {year}.
Only choose annual reports, not quarterly.

The current page is: {current_url}

Here are the visible links on the page:
{chr(10).join(links)}

Here is the full page content (all headings, buttons, paragraphs):
{full_text[:12000]}

Which link or element would you click next to get closer to downloading the annual report PDF? Return a single full URL.
"""
    return ai_prompt(prompt)

# Load and parse page with Playwright
def scan_page(url):
    """
    Loads a web page using Playwright and extracts all links and visible text.
    Includes fallbacks for sitemap and search functionality.
    """
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


#  Download pdf
def download_pdf(url, year=None, ticker="UNKNOWN", downloaded_pdfs=None):
    """
    Downloads a PDF from the given URL and saves it to the PDF_FOLDER.
    Handles existing files, invalid PDF content, and download errors.
    """
    if downloaded_pdfs is None:
        downloaded_pdfs = []
    ticker = ticker.upper()
    year = str(year) if year else "unknown"
    fname = f"{ticker}_{year}.pdf"
    fpath = os.path.join(PDF_FOLDER, fname)

    if os.path.exists(fpath):
        print(f"[SKIP] Already downloaded: {fname}")
        if fname not in downloaded_pdfs:
            downloaded_pdfs.append(fname)
        return True

    print(f"[ DOWNLOAD] {url}")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(fpath, "wb") as f:
            f.write(r.content)

        with open(fpath, "rb") as f:
            if not f.read(4) == b'%PDF':
                print(f"[INVALID FILE] Not a real PDF. Removing: {fname}")
                os.remove(fpath)
                return False

        print(f"[ SAVED] {fname}")
        if fname not in downloaded_pdfs:
            downloaded_pdfs.append(fname)
        return True
    except Exception as e:
        print(f"[ DOWNLOAD ERROR] {e}")
        return False

#  Recursively use AI to navigate
def recursive_ai_nav(start_url, year="2024", ticker="UNKNOWN", depth=0, visited=None, downloaded_pdfs=None):
    """
    Recursively navigates web pages using AI to find and download annual report PDFs.
    Explores links until a PDF is found or max depth is reached.
    """
    if visited is None:
        visited = set()
    if downloaded_pdfs is None:
        downloaded_pdfs = []

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
        if download_pdf(pdf_links[0], year, ticker, downloaded_pdfs):
            return pdf_links[0], current_url

    next_url = ai_pick_best_link(current_url, links, text, year)
    if not next_url or next_url in visited:
        print("[ No better link found.]")
        return None, current_url
    if next_url.endswith(".pdf") or "download" in next_url or "asset" in next_url:
        if download_pdf(next_url, year, ticker, downloaded_pdfs):
            return next_url, current_url
        else:
            return None, current_url
    return recursive_ai_nav(next_url, year, ticker, depth + 1, visited, downloaded_pdfs)

# Try previous years using recursive AI fallback
def try_other_years(from_url, ticker, from_year=2023, downloaded_pdfs=None):
    """
    Attempts to find and download annual reports for previous years using recursive AI fallback.
    """
    if downloaded_pdfs is None:
        downloaded_pdfs = []
    current_base = from_url
    for y in range(from_year, 2014, -1):
        print(f"\n[ AI BACKTRACE] Attempting to find report for {y}")
        result_url, new_base = recursive_ai_nav(current_base, str(y), ticker, downloaded_pdfs=downloaded_pdfs)
        if result_url:
            current_base = new_base
        else:
            print(f"[ Could not find report for {y}]")

#  Get IR URL using AI
def find_ir_url_via_ai(ticker):
    """
    Uses AI to find the official investor relations (IR) URL for a given company ticker.
    """
    prompt = f"""Find the official investor relations or annual reports page for European company '{ticker}'. Return the best direct URL."""
    return ai_prompt(prompt)

#  define globally
downloaded_years = []

#   Main 
def scrapeticker(ticker, missed_years):
    """
    Main function for deep scraping missed annual reports for a given ticker.
    It attempts to find and download PDFs for specified missed years.
    """
    print(f"\n🔍 Deep scraping missed reports for {ticker}: {missed_years}")
    ir_url = extract_first_url(ai_prompt(f"Return official annual report or IR page for '{ticker}'"))
    downloaded_years.clear()

    company_name = ticker 

    for year in missed_years:
        recursive_ai_nav(ir_url, year, ticker)

    still_missing = [y for y in missed_years if f"{ticker}_{y}.pdf" not in downloaded_years]

    return {
        "name": company_name,
        "ticker": ticker,
        "ir_url": ir_url,
        "downloaded_years": sorted([
            int(f.split("_")[1].replace(".pdf", ""))
            for f in downloaded_years if f.startswith(ticker)
        ]),
        "missed_years": still_missing
    }
 
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 deep_scrape.py <TICKER> <missed_years_comma_separated>")
        sys.exit(1)
    ticker = sys.argv[1].upper()
    missed = list(map(int, sys.argv[2].split(",")))
    print(scrapeticker(ticker, missed))