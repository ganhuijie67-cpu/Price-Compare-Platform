# Backend

`backend` is the FastAPI service for the Price Compare Platform.

## Technology baseline

```text
Web framework: FastAPI
Python:        3.12
Runtime deps:  requirements.txt
Dev deps:      requirements-dev.txt
```

The backend is pinned to Python 3.12 for a consistent local and deployment
baseline. The `.python-version` file records that version for Python version
managers that read it.

## First install on Windows PowerShell

Run these commands from the project root:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

If `py -3.12` is unavailable, install Python 3.12 first and rerun the setup.
If PowerShell blocks `Activate.ps1`, you can still install with the virtual
environment interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` installs the runtime dependencies too because it includes
`requirements.txt`.

If you only need the dependencies required to run the API service, use:

```powershell
python -m pip install -r requirements.txt
```

## First install on macOS or Linux

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## Verify the install

```powershell
python -c "import fastapi; print(fastapi.__version__)"
```

## Run the API locally

```powershell
fastapi dev app/main.py
```

Health check endpoints:

```text
GET /api/v1/health
GET /health
```

The `/api/v1/health` path is the versioned API route used by the frontend.
`/health` is a short local alias.

Mock compare endpoint:

```text
POST /api/v1/compare
```

Example request body:

```json
{
  "query": "iPhone 17 Pro 256GB 国行"
}
```

Current Mock data source:

```text
../mock_data/platform_products/compare_mock.json
```

The compare service also uses `app/tools/product_parse.py` to add a minimal
`normalized_product` object to the response.
It then uses `app/tools/product_match.py` to add `match_score`,
`match_reasons`, and `is_match` to each Mock item.
