# Health Data Sync

A modularized Streamlit application for syncing health data from Garmin to Google Sheets and exporting Cronometer data via a Go backend.

## Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/)
- (For Cronometer Sync) [Go](https://go.dev/dl/)

## Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd health_data_app
```

### 2. Environment Setup

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

*(Note: If you are on Windows and don't have `pip` installed, run `python -m ensurepip` first.)*

## Authentication & Configuration

To protect your privacy, local secrets, credentials, and token files are **ignored by Git** and should never be committed.

### Required Files (Not in Git)
- `credentials.json`: Your Google OAuth Desktop Client file.
- `tokens/`: Directory containing `google_token.json` and Garmin authentication tokens.
- `data/`: Local storage for your reports and sleep summaries.

### Initial Configuration
1. Obtain your `credentials.json` from the [Google Cloud Console](https://console.cloud.google.com/).
2. Place it in the project root: `python/health_data_app/credentials.json`.
3. Start the app (see below) and use the **Settings** tab to point the app to your local folders for data and Go projects.
4. Complete the Google Auth flow within the **Settings** tab to generate your `tokens/google_token.json`.

## Run the Application

**macOS / Linux:**
```bash
source .venv/bin/activate
streamlit run app.py
```

**Windows:**
```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

The app will launch at `http://localhost:8501`.

## Security Note

All sensitive data, environment files, and local workspaces are strictly excluded from version control via `.gitignore`. 
- **NEVER** commit `credentials.json`, the `tokens/` folder, or any `.env` files.
- If you accidentally commit a secret, rotate your API keys immediately.
