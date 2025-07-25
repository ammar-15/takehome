# Takehome Project for Fiscal.ai

[Live](https://takehome-rho.vercel.app/)

This project consists of a frontend application and a backend API, designed to scrape, parse, and structure financial data for companies.

## Project Setup (Local)

To set up and run this project locally, follow these steps:

### 1. Clone the Repository

```bash
git clone <repository_url>
cd takehome
```

### 2. Backend Setup

The backend is built with Python (FastAPI) and TypeScript (Node.js for scraping/parsing utilities).

Navigate to the `backend` directory:

```bash
cd backend
```

Install Node.js dependencies:

```bash
npm install
```

**Environment Variables:**
Create a `.env` file in the `backend` directory and add your OpenAI API key:

```
OPENAI_API_KEY=your_openai_api_key_here
```

**Run the Backend:**

To start the backend API server:

```bash
npm run dev
```

The backend will typically run on `http://localhost:3001`.

### 3. Frontend Setup

The frontend is a React application built with Vite.

Navigate to the `frontend` directory:

```bash
cd frontend
```

Install Node.js dependencies:

```bash
npm install
```

**Run the Frontend:**

To start the frontend development server (it will run on port 5172 as configured):

```bash
npm run dev -- --port 5172
```

The frontend will be accessible at `http://localhost:5172`.

## Application Overview

### Frontend

The frontend provides a user interface to interact with the financial data. Its primary function is to display a searchable table of company financial information, fetched from the backend API. It uses shadcn/ui components for a modern look and feel.

### Backend

The backend serves two main purposes:

1.  **Automated Data Pipeline:**
    The core functionality is exposed via an API endpoint in `main.py`. When you provide a company ticker to this endpoint, the backend orchestrates a complete data pipeline:
    *   **Scraping:** It attempts to scrape annual report PDFs using `quick_scrape.py`. If `quick_scrape.py` fails or misses some PDFs, `deep_scrape.py` is used as a fallback to locate and download the remaining reports.
    *   **Parsing:** Once PDFs are downloaded, `parser.py` processes each PDF to extract structured financial data.
    *   **Structuring & Storage:** The extracted data is then passed to `structure.py`, which organizes it into a consistent JSON format (prioritizing data from newer reports for historical years) and saves it into a SQLite database.

    You can trigger this pipeline by making a GET request to `/scrape/{ticker}` (e.g., `http://localhost:3001/scrape/ASML`).

2.  **Individual Data Processing & Testing:**
    For development, testing, or specific data processing needs, you can also run the individual components of the pipeline directly:
    *   **Scraping:** Use `scrape_test.py` or `scrape_test_2.py` to download PDFs for a given ticker. `scrape_test_2.py` is a quick scraper and `scrape_test.py` is a deep scraper. these files can be run by `python3 filename.py ticker`
    *   **Parsing:** Use `parser_test.py` to parse individual PDF files from the `pdfs` directory.
    *   **Structuring:** Use `structure_test.py` to process parsed data and save it to the database.

    These individual scripts are typically found in the `backend/scripts` directory and can be run using `python3 filename.py`   from the `backend` directory.
