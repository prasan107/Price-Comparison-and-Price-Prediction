# Price Comparison and Price Prediction Engine

An AI-powered web application that compares product prices from Amazon and Flipkart, tracks price history, forecasts future prices, and supports price-drop email alerts.

## Features

- **Price comparison:** Collect product listings from Amazon and Flipkart.
- **Price history:** Store and review historical product prices.
- **Price forecasting:** Use Facebook Prophet to estimate future prices.
- **Deal scoring:** Evaluate products using rule-based deal scoring.
- **Similar products:** Find related products using TF-IDF similarity.
- **Email alerts:** Configure notifications for target prices.
- **Scheduled tasks:** Use Celery and Redis-compatible Memurai for background jobs.
- **Web interface:** Search products and view price trends and forecasts.

## Technology Stack

- **Backend:** Python, FastAPI, Uvicorn
- **Frontend:** React, Vite
- **Database:** PostgreSQL
- **Scraping:** Playwright, BeautifulSoup
- **Forecasting:** Facebook Prophet
- **Similarity:** TF-IDF
- **Background jobs:** Celery, Memurai/Redis
- **Charts:** React chart components

## Project Structure

```text
price-comparison-engine/
|-- api/           # FastAPI application and routes
|-- db/            # Database code
|-- prediction/    # Price forecasting and prediction logic
|-- scrapers/      # Amazon and Flipkart scrapers
|-- services/      # Application services
|-- tasks/         # Celery tasks and notifications
|-- frontend/      # React and Vite application
|-- screenshots/   # Application screenshots
|-- config.py
|-- requirements.txt
|-- .env.example
```

## Prerequisites

Install the following before running the project:

- Python 3.11 or a compatible version supported by the dependencies
- Node.js and npm
- PostgreSQL
- Memurai or Redis
- A Chromium browser installed through Playwright

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/prasan107/Price-Comparison-and-Price-Prediction.git
cd Price-Comparison-and-Price-Prediction
```

### 2. Create a Python environment

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure environment variables

Create a local `.env` file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` with your own PostgreSQL connection details, Redis/Memurai URL, and email settings. Do not commit your real `.env` file.

Required configuration keys:

```text
DATABASE_URL=postgresql://postgres:password@localhost:5432/price_comparison
REDIS_URL=redis://localhost:6379/0
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
ALERT_FROM_EMAIL=your_email@gmail.com
APP_ENV=development
SECRET_KEY=replace-with-a-random-secret
```

Replace the example values with your local configuration. For Gmail, use an app password where required.

### 4. Create the database

Create a PostgreSQL database named `price_comparison` using your preferred PostgreSQL tool. For example:

```bash
psql -U postgres -c "CREATE DATABASE price_comparison;"
```

Ensure the database schema or initialization steps required by the project have been completed before starting the application.

### 5. Start the backend

From the project root:

```bash
uvicorn api.main:app --reload --port 8000
```

The backend should be available at `http://127.0.0.1:8000`.

### 6. Start the frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite in the terminal.

### 7. Run background workers (optional)

With Memurai/Redis running, open separate terminals from the project root.

Celery worker:

```bash
celery -A tasks.celery_app worker --loglevel=info --pool=solo
```

Celery Beat scheduler:

```bash
celery -A tasks.celery_app beat --loglevel=info --schedule=celerybeat-schedule-clean
```

## API

The backend includes search, product, price-history, prediction, and alert functionality. Available routes depend on the route definitions in the `api` package.

When the backend is running, use the FastAPI documentation page at:

`http://127.0.0.1:8000/docs`

## Screenshots

### Product search

![Product search](screenshots/search.png)

### Deal information

![Deal information](screenshots/deal.png)

### Price forecast

![Price forecast](screenshots/forecast.png)

## Notes

- Product availability and prices can change between scraping runs.
- Scraping behavior depends on the source websites and their current access restrictions.
- Forecasts are estimates based on available historical data, not guarantees of future prices.
- Keep credentials and other sensitive configuration in `.env`, not in source control.

## Author

**Prasannaraj S**

- GitHub: [prasan107](https://github.com/prasan107)
- LinkedIn: [prasannaraj-s](https://www.linkedin.com/in/prasannaraj-s)
