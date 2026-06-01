#!/usr/bin/env python3
"""
S3 Parquet File Comparison Script
Downloads parquet files from two S3 directories and compares them.

Usage:
    python raas_compare_script.py <s3_dir1> <s3_dir2>

Example:
    python raas_compare_script.py data/source1/ data/source2/
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import tempfile
import shutil
import argparse

import boto3
import pandas as pd
from dotenv import load_dotenv
from botocore.exceptions import ClientError


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Compare parquet files from two S3 directories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py data/source1/ data/source2/
  python main.py s3://bucket/dir1/ dir2/ --bucket my-bucket
        """
    )

    parser.add_argument('dir1', help='First S3 directory path (prefix)')
    parser.add_argument('dir2', help='Second S3 directory path (prefix)')
    parser.add_argument('--bucket', help='S3 bucket name (overrides .env file)')
    parser.add_argument('--region', help='AWS region (overrides .env file)')

    return parser.parse_args()


def load_config(args):
    """Load configuration from .env file and command-line arguments."""
    script_dir = Path(__file__).parent
    env_path = script_dir / '.env'

    if env_path.exists():
        load_dotenv(env_path)

    # Command-line args override .env values
    config = {
        'bucket': args.bucket or os.getenv('S3_BUCKET'),
        'dir1': args.dir1,
        'dir2': args.dir2,
        'aws_region': args.region or os.getenv('AWS_REGION', 'us-east-1'),
    }

    # Validate required fields
    if not config['bucket']:
        print("Error: S3 bucket must be specified either via --bucket flag or S3_BUCKET in .env file")
        sys.exit(1)

    return config


def create_temp_directory():
    """Create a local temporary directory with datetime stamp."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    temp_dir = Path('./temp_download') / timestamp
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_s3_client(region='us-east-1'):
    """Create and return an S3 client using environment variables."""
    # Check for AWS credentials in environment variables
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_session_token = os.getenv('AWS_SESSION_TOKEN')

    if not aws_access_key or not aws_secret_key:
        print("Error: AWS credentials not found in environment variables")
        print("Please set the following environment variables:")
        print("  export AWS_ACCESS_KEY_ID=your-key")
        print("  export AWS_SECRET_ACCESS_KEY=your-secret")
        print("  export AWS_SESSION_TOKEN=your-token  # Optional")
        sys.exit(1)

    session_kwargs = {
        'region_name': region,
        'aws_access_key_id': aws_access_key,
        'aws_secret_access_key': aws_secret_key,
    }

    if aws_session_token:
        session_kwargs['aws_session_token'] = aws_session_token

    session = boto3.Session(**session_kwargs)
    return session.client('s3')


def download_s3_files(s3_client, bucket, prefix, local_dir):
    """Download all parquet files from S3 prefix to local directory."""
    local_path = Path(local_dir)
    local_path.mkdir(parents=True, exist_ok=True)

    downloaded_files = []

    try:
        # List objects in the S3 prefix
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

        for page in pages:
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']

                # Skip directories and non-parquet files
                if key.endswith('/'):
                    continue
                if not key.lower().endswith('.parquet'):
                    continue

                # Create local file path
                file_name = Path(key).name
                local_file = local_path / file_name

                print(f"  Downloading: s3://{bucket}/{key}")
                s3_client.download_file(bucket, key, str(local_file))
                downloaded_files.append(local_file)

        return downloaded_files

    except ClientError as e:
        print(f"Error downloading from S3: {e}")
        sys.exit(1)


def load_parquet_files(file_list):
    """Load and concatenate multiple parquet files into a single DataFrame."""
    if not file_list:
        return None

    dataframes = []
    for file_path in file_list:
        print(f"  Loading: {file_path.name}")
        df = pd.read_parquet(file_path)
        dataframes.append(df)

    if len(dataframes) == 1:
        return dataframes[0]
    else:
        return pd.concat(dataframes, ignore_index=True)


def compare_dataframes(df1, df2):
    """Compare two DataFrames and return detailed comparison results."""
    results = {
        'identical': False,
        'shape_match': False,
        'columns_match': False,
        'data_match': False,
        'differences': []
    }

    # Check shapes
    if df1.shape != df2.shape:
        results['differences'].append(
            f"Shape mismatch: DF1 {df1.shape} vs DF2 {df2.shape}"
        )
    else:
        results['shape_match'] = True

    # Check columns
    df1_cols = set(df1.columns)
    df2_cols = set(df2.columns)

    if df1_cols != df2_cols:
        missing_in_df2 = df1_cols - df2_cols
        missing_in_df1 = df2_cols - df1_cols

        if missing_in_df2:
            results['differences'].append(
                f"Columns in DF1 but not in DF2: {missing_in_df2}"
            )
        if missing_in_df1:
            results['differences'].append(
                f"Columns in DF2 but not in DF1: {missing_in_df1}"
            )
    else:
        results['columns_match'] = True

    # If shapes and columns match, compare data
    if results['shape_match'] and results['columns_match']:
        # Sort both dataframes by all columns for consistent comparison
        df1_sorted = df1.sort_values(by=list(df1.columns)).reset_index(drop=True)
        df2_sorted = df2.sort_values(by=list(df2.columns)).reset_index(drop=True)

        try:
            # Compare values
            comparison = df1_sorted.equals(df2_sorted)

            if comparison:
                results['data_match'] = True
                results['identical'] = True
            else:
                # Find differences
                diff_mask = df1_sorted != df2_sorted
                diff_count = diff_mask.sum().sum()
                results['differences'].append(
                    f"Data mismatch: {diff_count} cell(s) differ"
                )

                # Show sample of differences (first 5)
                for col in df1_sorted.columns:
                    col_diffs = diff_mask[col]
                    if col_diffs.any():
                        diff_rows = col_diffs[col_diffs].index[:5].tolist()
                        results['differences'].append(
                            f"Column '{col}' differs at rows: {diff_rows} (showing first 5)"
                        )

                        for row_idx in diff_rows[:2]:  # Show values for first 2 rows
                            val1 = df1_sorted.loc[row_idx, col]
                            val2 = df2_sorted.loc[row_idx, col]
                            results['differences'].append(
                                f"  Row {row_idx}: {val1} != {val2}"
                            )

        except Exception as e:
            results['differences'].append(f"Error comparing data: {e}")

    return results


def main():
    """Main execution function."""
    print("=" * 80)
    print("S3 Parquet File Comparison Script")
    print("=" * 80)

    # Parse arguments and load configuration
    print("\n[1/5] Loading configuration...")
    args = parse_arguments()
    config = load_config(args)
    print(f"  Bucket: {config['bucket']}")
    print(f"  Directory 1: {config['dir1']}")
    print(f"  Directory 2: {config['dir2']}")

    # Create temp directory
    print("\n[2/5] Creating temporary directory...")
    temp_dir = create_temp_directory()
    print(f"  Temp directory: {temp_dir}")

    dir1_local = temp_dir / 'dir1'
    dir2_local = temp_dir / 'dir2'

    try:
        # Initialize S3 client
        print("\n[3/5] Connecting to S3...")
        s3_client = get_s3_client(config['aws_region'])

        # Download files from both directories
        print("\n[4/5] Downloading files...")
        print(f"\nDownloading from Directory 1: {config['dir1']}")
        files1 = download_s3_files(s3_client, config['bucket'], config['dir1'], dir1_local)
        print(f"  Downloaded {len(files1)} file(s)")


        print(f"\nDownloading from Directory 2: {config['dir2']}")
        files2 = download_s3_files(s3_client, config['bucket'], config['dir2'], dir2_local)
        print(f"  Downloaded {len(files2)} file(s)")

        if not files1:
            print(f"\nError: No parquet files found in {config['dir1']}")
            return

        if not files2:
            print(f"\nError: No parquet files found in {config['dir2']}")
            return

        # Load and combine parquet files
        print("\n[5/5] Loading and comparing data...")
        print("\nLoading Directory 1 files:")
        df1 = load_parquet_files(files1)
        print(f"  Shape: {df1.shape}")
        print(f"  Columns: {list(df1.columns)}")

        print("\nLoading Directory 2 files:")
        df2 = load_parquet_files(files2)
        print(f"  Shape: {df2.shape}")
        print(f"  Columns: {list(df2.columns)}")

        # Compare dataframes
        print("\nComparing dataframes...")
        results = compare_dataframes(df1, df2)

        # Print results
        print("\n" + "=" * 80)
        print("COMPARISON RESULTS")
        print("=" * 80)

        if results['identical']:
            print("\n✓ FILES ARE IDENTICAL")
            print("  All rows, columns, and data match perfectly.")
        else:
            print("\n✗ FILES ARE DIFFERENT")
            print(f"\n  Shape Match: {'✓' if results['shape_match'] else '✗'}")
            print(f"  Columns Match: {'✓' if results['columns_match'] else '✗'}")
            print(f"  Data Match: {'✓' if results['data_match'] else '✗'}")

            if results['differences']:
                print("\n  Differences found:")
                for diff in results['differences']:
                    print(f"    - {diff}")

        print("\n" + "=" * 80)

    finally:
        # Keep files in local temp_download directory for inspection
        print(f"\nDownloaded files are kept in: {temp_dir}")
        print("You can inspect or delete them manually.")
        print("Done.")


if __name__ == '__main__':
    main()
