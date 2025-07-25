import os
from playwright.sync_api import sync_playwright
import openai
import requests
from dotenv import load_dotenv
load_dotenv()


openai.api_key = os.getenv("OPENAI_API_KEY")
PDF_FOLDER = os.path.join(os.path.dirname(__file__), "../pdfs")

def find_ir_url(ticker: str) -> str:
    prompt = f"Return the official investor relations website URL of the European company with ticker '{ticker}' in plain text only (no formatting)."
    response = openai.ChatCompletion.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}],
)
    print(f"[OPENAI] Finding IR URL for {ticker}")
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("No content returned from OpenAI API.")
    return content.strip()

def download_pdf(pdf_url: str, file_path: str):
    response = requests.get(pdf_url)
    response.raise_for_status()
    with open(file_path, "wb") as f:
        f.write(response.content)

def scrape_pdf(ticker: str):
    ir_url = find_ir_url(ticker)
    company_name = ir_url.split("//")[-1].split(".")[0]
    print(f"[SCRAPER] Visiting: {ir_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(ir_url, timeout=60000)

        links = page.query_selector_all("a")
        for link in links:
            try:
                text = (link.inner_text() or "").lower()
                href = link.get_attribute("href")

                if href and "2024" in text and "annual" in text and href.endswith(".pdf"):
                    pdf_url = href if href.startswith("http") else f"{ir_url.rstrip('/')}/{href.lstrip('/')}"
                    print(f"[SCRAPER] Trying PDF link: {pdf_url}")
                    file_path = os.path.join(PDF_FOLDER, f"{company_name}_2024.pdf")
                    print(f"[SCRAPER] Saved PDF to: {file_path}")
                    download_pdf(pdf_url, file_path)
                    browser.close()
                    return company_name, file_path

            except Exception as e:
                continue  # silently skip broken links

        browser.close()
        raise Exception("PDF not found.")
