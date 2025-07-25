from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .quick_scrape import scrapeticker as quick_scrape
from .deep_scrape import scrapeticker as deep_scrape
from .parser import parsed_pdf
from .structure import save_to_db, load_from_db
import os
import json

PDF_DIR = os.path.join(os.path.dirname(__file__), "../pdfs")
COMPANY_TABLE_PATH = os.path.join(os.path.dirname(__file__), "../company_table.json")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://takehome-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

def save_company_info(company_name, ticker, ir_url):
    if os.path.exists(COMPANY_TABLE_PATH):
        with open(COMPANY_TABLE_PATH, 'r') as f:
            data = json.load(f)
    else:
        data = {}

    data[ticker] = {
        "name": company_name,
        "ticker": ticker,
        "investor_relations_url": ir_url
    }

    with open(COMPANY_TABLE_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def get_company_info(ticker):
    if os.path.exists(COMPANY_TABLE_PATH):
        with open(COMPANY_TABLE_PATH, 'r') as f:
            data = json.load(f)
        return data.get(ticker)
    return None

@app.get("/scrape/{ticker}")
def run_pipeline(ticker: str):
    print(f"[START] Running pipeline for ticker: {ticker}")

    db_data = load_from_db(ticker)
    if db_data:
        print(f"[CACHE HIT] Returning saved data for {ticker}")
        return {"company": ticker, "results": db_data}

    print(f"[CACHE MISS] No data found for {ticker}. Starting scrape...")

    pdfs_before = set(os.listdir(PDF_DIR))
    company_name = ticker
    ir_url = ""
    downloaded_years = []
    missed_years = []

    #  Quick Scrape
    try:
        result = quick_scrape(ticker)
        company_name, ir_url = result["name"], result["ir_url"]
        downloaded_years = result["downloaded_years"]
        missed_years = result["missed_years"]
        save_company_info(company_name, ticker, ir_url)
    except Exception as e:
        print(f"[ QUICK SCRAPE FAILED] {e}")

    #  Deep Scrape if quick scrape fails
    expected_years = list(range(2015, 2025))
    if sorted(downloaded_years) == expected_years:
        print(f"[ QUICK SCRAPE COMPLETE] 10  pdfs downloaded. No deep scrape needed.")
    elif missed_years:
        print(f"[Missing years: {missed_years}] Trying deep scrape...")
        try:
            result = deep_scrape(ticker, missed_years)
            downloaded_years += result["downloaded_years"]
            missed_years = result["missed_years"]
            ir_url = result["ir_url"]
            company_name = result["name"]
            save_company_info(company_name, ticker, ir_url)
        except Exception as e:
            print(f"[ DEEP SCRAPE FAILED] {e}")

    if not downloaded_years:
        return {"error": "No  pdfs were successfully downloaded."}

    #  Find the downloaded pdfs
    pdfs_after = set(os.listdir(PDF_DIR))
    new_pdfs = sorted(list(pdfs_after - pdfs_before), reverse=True) 

    print(f"[PARSER] New  pdfs to process: {new_pdfs}")

    for pdf_file in new_pdfs:
        try:
            year = int(pdf_file.split("_")[1].replace(".pdf", ""))
            pdf_path = os.path.join(PDF_DIR, pdf_file)

            print(f"[PARSER] Parsing {pdf_file}...")
            parsed_output = parsed_pdf(pdf_path)

            structured_data = {
                "company": company_name,
                "ticker": ticker,
                "ir_url": ir_url,
                "data": parsed_output
            }

            print(f"[STRUCTURE] Structuring and saving data for {company_name} {year}")
            save_to_db(company_name, structured_data)

        except Exception as e:
            print(f"[ ERROR] Failed to process {pdf_file}: {e}")
            continue

    print(f"[ DONE] Pipeline complete for {ticker}")
    return {"company": ticker, "results": load_from_db(ticker)}
