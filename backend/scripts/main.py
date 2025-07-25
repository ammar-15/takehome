from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .quick_scrape import scrapeticker as quick_scrape
from .deep_scrape import scrapeticker as deep_scrape
from .parser import parsed_pdf
from .structure import save_to_db, load_from_db
import logging
import traceback
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL")
PDF_DIR = os.path.join(os.path.dirname(__file__), "../pdfs")
COMPANY_TABLE_PATH = os.path.join(os.path.dirname(__file__), "../company_table.json")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5172",
        "https://takehome-rho.vercel.app"
        ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

class ScrapeError(Exception):
    """Custom exception for scraping errors."""
    def __init__(self, message: str):
        """
        Initializes the ScrapeError with a given message.
        """
        self.message = message
        super().__init__(self.message)

class DataParseError(Exception):
    """Custom exception for data parsing errors."""
    def __init__(self, message: str):
        """
        Initializes the DataParseError with a given message.
        """
        self.message = message
        super().__init__(self.message)

class FileSaveError(Exception):
    """Custom exception for file saving errors."""
    def __init__(self, message: str):
        """
        Initializes the FileSaveError with a given message.
        """
        self.message = message
        super().__init__(self.message)



def save_company_info(company_name, ticker, ir_url):
    """
    Saves or updates company information (name, ticker, IR URL) to a JSON file.
    """
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

@app.get("/metadata/{ticker}")
def get_metadata(ticker: str):
    """
    Retrieves metadata for a given company ticker.
    Returns company name, ticker, and investor relations URL if found.
    """
    data = get_company_info(ticker)
    if data:
        return data
    return {"error": f"Metadata for ticker '{ticker}' not found."}

def get_company_info(ticker):
    """
    Retrieves company information for a given ticker from the JSON file.
    """
    if os.path.exists(COMPANY_TABLE_PATH):
        with open(COMPANY_TABLE_PATH, 'r') as f:
            data = json.load(f)
        return data.get(ticker)
    return None

# Set up logging configuration
logging.basicConfig(level=logging.INFO)


@app.get("/scrape/{ticker}")
def run_pipeline(ticker: str):
    """
    Runs the full data pipeline for a given company ticker, including scraping, parsing, and structuring.
    """
    print(f"[START] Running pipeline for ticker: {ticker}")

    failed_tickers = []

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

    # Quick Scrape
    try:
        result = quick_scrape(ticker)
        company_name, ir_url = result["name"], result["ir_url"]
        downloaded_years = result["downloaded_years"]
        missed_years = result["missed_years"]
        save_company_info(company_name, ticker, ir_url)
    except (ConnectionError, TimeoutError) as e:
        logging.warning(f"[NETWORK ISSUE] {ticker} - {e}")
    except ScrapeError as e:
        logging.error(f"[SCRAPE ERROR] {ticker} - {e}")
    except Exception as e:
        logging.critical(f"[UNKNOWN ERROR] {ticker} - {e}")
        traceback.print_exc() 
        failed_tickers.append(ticker)  

    # Deep Scrape if quick scrape fails
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
        except ScrapeError as e:
            logging.error(f"[SCRAPE ERROR] {ticker} - {e}")
        except Exception as e:
            logging.critical(f"[UNKNOWN ERROR] {ticker} - {e}")
            traceback.print_exc()  
            failed_tickers.append(ticker)

    if not downloaded_years:
        return {"error": "No pdfs were successfully downloaded."}

    # Find the downloaded pdfs
    pdfs_after = set(os.listdir(PDF_DIR))
    new_pdfs = sorted(list(pdfs_after - pdfs_before), reverse=True)

    print(f"[PARSER] New pdfs to process: {new_pdfs}")

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

        except DataParseError as e:
            logging.error(f"[DATA ERROR] {ticker} - {e}")
        except FileSaveError as e:
            logging.error(f"[FILE SAVE ERROR] {ticker} - {e}")
        except Exception as e:
            logging.critical(f"[UNKNOWN ERROR] {ticker} - {e}")
            traceback.print_exc()  
            failed_tickers.append(ticker)  

    print(f"[DONE] Pipeline complete for {ticker}")
    return {"company": ticker, "results": load_from_db(ticker)}
