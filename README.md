# RaaS Parquet Compare

S3 Parquet File Comparison Tool - Downloads and compares parquet files from two S3 directories.

## Features

- Downloads parquet files from two S3 directories
- Stores files in local `./temp_download/` directory with datetime stamps
- Compares all rows, columns, and data using pandas
- Shows detailed differences when files don't match
- Keeps downloaded files for inspection (stored in `./temp_download/`)
- Supports AWS credentials via environment variables

## Installation

```bash
# Install dependencies
uv sync

# Or using pip
pip install -r requirements.txt
```

## Configuration

### AWS Credentials (REQUIRED)

You must set AWS credentials via environment variables before running the script:

```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_SESSION_TOKEN=your-session-token  # Optional, for temporary credentials
```

### .env file (Optional)

You can optionally create a `.env` file for bucket and region configuration:

```env
S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1  # Optional, defaults to us-east-1
```

Note: AWS credentials must be set via environment variables, not in the .env file.

## Usage

```bash
# Set AWS credentials first (REQUIRED)
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=xyz...
export AWS_SESSION_TOKEN=IQo...  # Optional, for temporary credentials

# Basic usage
uv run python main.py data/source1/ data/source2/

# Override bucket from command line
uv run python main.py dir1/ dir2/ --bucket my-bucket

# Use specific region
uv run python main.py dir1/ dir2/ --region us-west-2

# Full example with all options
uv run python main.py data/v1/ data/v2/ --bucket prod-data --region us-west-2

# Show help
uv run python main.py --help
```

## Output

The script will display:
- Download progress for both directories
- Shape and columns of each dataset
- Comparison results:
  - ✓ FILES ARE IDENTICAL (if all data matches)
  - ✗ FILES ARE DIFFERENT (with detailed differences)
    - Shape mismatch
    - Column differences
    - Data differences with sample rows
- Location of downloaded files in `./temp_download/YYYYMMDD_HHMMSS/`

Downloaded files are preserved for manual inspection and can be deleted when no longer needed.

## Example

```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=xyz...
export AWS_SESSION_TOKEN=IQo...  # If using temporary credentials

# Run comparison
uv run python main.py raas/prod/2024-01-01/ raas/staging/2024-01-01/ --bucket my-data-bucket
```

## Project Structure

```
.
├── main.py              # Main comparison script
├── pyproject.toml       # Project dependencies (uv)
├── .env                 # Configuration file (not in git)
├── .gitignore          # Git ignore patterns
└── README.md           # This file
```

## Requirements

- Python >= 3.12
- boto3 >= 1.26.0
- pandas >= 2.0.0
- pyarrow >= 12.0.0
- python-dotenv >= 1.0.0
