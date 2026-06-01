#!/usr/bin/env python3
"""
Test file for S3 Parquet Comparison Script
Creates sample parquet files and tests comparison functionality.
"""

import os
import sys
from pathlib import Path
import tempfile
import shutil

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def create_test_data():
    """Create sample test data."""
    # Dataset 1 - Original
    data1 = {
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'age': [25, 30, 35, 40, 45],
        'score': [85.5, 90.0, 78.5, 92.0, 88.5],
        'active': [True, True, False, True, True]
    }
    df1 = pd.DataFrame(data1)

    # Dataset 2 - Identical
    df2 = df1.copy()

    # Dataset 3 - Different values
    data3 = {
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'age': [25, 31, 35, 40, 45],  # Bob's age changed
        'score': [85.5, 90.0, 78.5, 92.0, 99.9],  # Eve's score changed
        'active': [True, True, False, True, True]
    }
    df3 = pd.DataFrame(data3)

    # Dataset 4 - Different columns
    data4 = {
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'age': [25, 30, 35, 40, 45],
        'department': ['Sales', 'IT', 'HR', 'IT', 'Sales']  # Different column
    }
    df4 = pd.DataFrame(data4)

    # Dataset 5 - Different shape
    data5 = {
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35],
        'score': [85.5, 90.0, 78.5],
        'active': [True, True, False]
    }
    df5 = pd.DataFrame(data5)

    return df1, df2, df3, df4, df5


def save_parquet_files():
    """Save test parquet files to local test_data directory."""
    test_dir = Path('./test_data')
    test_dir.mkdir(exist_ok=True)

    # Create subdirectories
    (test_dir / 'identical_test' / 'dir1').mkdir(parents=True, exist_ok=True)
    (test_dir / 'identical_test' / 'dir2').mkdir(parents=True, exist_ok=True)
    (test_dir / 'different_values' / 'dir1').mkdir(parents=True, exist_ok=True)
    (test_dir / 'different_values' / 'dir2').mkdir(parents=True, exist_ok=True)
    (test_dir / 'different_columns' / 'dir1').mkdir(parents=True, exist_ok=True)
    (test_dir / 'different_columns' / 'dir2').mkdir(parents=True, exist_ok=True)
    (test_dir / 'different_shape' / 'dir1').mkdir(parents=True, exist_ok=True)
    (test_dir / 'different_shape' / 'dir2').mkdir(parents=True, exist_ok=True)

    df1, df2, df3, df4, df5 = create_test_data()

    # Test 1: Identical files
    df1.to_parquet(test_dir / 'identical_test' / 'dir1' / 'data.parquet', index=False)
    df2.to_parquet(test_dir / 'identical_test' / 'dir2' / 'data.parquet', index=False)

    # Test 2: Different values
    df1.to_parquet(test_dir / 'different_values' / 'dir1' / 'data.parquet', index=False)
    df3.to_parquet(test_dir / 'different_values' / 'dir2' / 'data.parquet', index=False)

    # Test 3: Different columns
    df1.to_parquet(test_dir / 'different_columns' / 'dir1' / 'data.parquet', index=False)
    df4.to_parquet(test_dir / 'different_columns' / 'dir2' / 'data.parquet', index=False)

    # Test 4: Different shape
    df1.to_parquet(test_dir / 'different_shape' / 'dir1' / 'data.parquet', index=False)
    df5.to_parquet(test_dir / 'different_shape' / 'dir2' / 'data.parquet', index=False)

    print("Test data created successfully!")
    print(f"\nTest files saved to: {test_dir.absolute()}")
    print("\nTest scenarios:")
    print("  1. identical_test/     - Two identical parquet files")
    print("  2. different_values/   - Same structure, different values")
    print("  3. different_columns/  - Different column names")
    print("  4. different_shape/    - Different number of rows")


def test_comparison_locally():
    """Test the comparison function locally without S3."""
    # Import the comparison function from main
    sys.path.insert(0, str(Path(__file__).parent))
    from main import compare_dataframes, load_parquet_files

    print("\n" + "=" * 80)
    print("RUNNING LOCAL TESTS")
    print("=" * 80)

    test_dir = Path('./test_data')

    # Test 1: Identical files
    print("\n[TEST 1] Comparing identical files...")
    files1 = [test_dir / 'identical_test' / 'dir1' / 'data.parquet']
    files2 = [test_dir / 'identical_test' / 'dir2' / 'data.parquet']
    df1 = load_parquet_files(files1)
    df2 = load_parquet_files(files2)
    result = compare_dataframes(df1, df2)
    print(f"  Result: {'✓ PASS' if result['identical'] else '✗ FAIL'}")
    assert result['identical'], "Identical files should match"

    # Test 2: Different values
    print("\n[TEST 2] Comparing files with different values...")
    files1 = [test_dir / 'different_values' / 'dir1' / 'data.parquet']
    files2 = [test_dir / 'different_values' / 'dir2' / 'data.parquet']
    df1 = load_parquet_files(files1)
    df2 = load_parquet_files(files2)
    result = compare_dataframes(df1, df2)
    print(f"  Result: {'✓ PASS' if not result['identical'] else '✗ FAIL'}")
    assert not result['identical'], "Different values should not match"
    assert result['shape_match'], "Shapes should match"
    assert result['columns_match'], "Columns should match"

    # Test 3: Different columns
    print("\n[TEST 3] Comparing files with different columns...")
    files1 = [test_dir / 'different_columns' / 'dir1' / 'data.parquet']
    files2 = [test_dir / 'different_columns' / 'dir2' / 'data.parquet']
    df1 = load_parquet_files(files1)
    df2 = load_parquet_files(files2)
    result = compare_dataframes(df1, df2)
    print(f"  Result: {'✓ PASS' if not result['columns_match'] else '✗ FAIL'}")
    assert not result['identical'], "Different columns should not match"
    assert not result['columns_match'], "Columns should not match"

    # Test 4: Different shape
    print("\n[TEST 4] Comparing files with different shapes...")
    files1 = [test_dir / 'different_shape' / 'dir1' / 'data.parquet']
    files2 = [test_dir / 'different_shape' / 'dir2' / 'data.parquet']
    df1 = load_parquet_files(files1)
    df2 = load_parquet_files(files2)
    result = compare_dataframes(df1, df2)
    print(f"  Result: {'✓ PASS' if not result['shape_match'] else '✗ FAIL'}")
    assert not result['identical'], "Different shapes should not match"
    assert not result['shape_match'], "Shapes should not match"

    print("\n" + "=" * 80)
    print("✓ ALL TESTS PASSED")
    print("=" * 80)


def print_sample_data():
    """Print sample data for reference."""
    print("\n" + "=" * 80)
    print("SAMPLE TEST DATA")
    print("=" * 80)

    df1, df2, df3, df4, df5 = create_test_data()

    print("\nDataset 1 (Original):")
    print(df1)

    print("\nDataset 3 (Different Values - Bob's age and Eve's score changed):")
    print(df3)

    print("\nDataset 4 (Different Columns - 'score' and 'active' replaced with 'department'):")
    print(df4)

    print("\nDataset 5 (Different Shape - Only 3 rows):")
    print(df5)


def cleanup_test_data():
    """Remove test data directory."""
    test_dir = Path('./test_data')
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print(f"\nTest data cleaned up: {test_dir}")


def main():
    """Main test function."""
    import argparse

    parser = argparse.ArgumentParser(description='Test S3 Parquet Comparison Script')
    parser.add_argument('--create', action='store_true', help='Create test data files')
    parser.add_argument('--test', action='store_true', help='Run comparison tests')
    parser.add_argument('--show', action='store_true', help='Show sample data')
    parser.add_argument('--cleanup', action='store_true', help='Clean up test data')
    parser.add_argument('--all', action='store_true', help='Create data, run tests, and show results')

    args = parser.parse_args()

    if args.all:
        save_parquet_files()
        print_sample_data()
        test_comparison_locally()
        print("\nTest data kept for inspection. Run with --cleanup to remove.")
    elif args.create:
        save_parquet_files()
    elif args.test:
        test_comparison_locally()
    elif args.show:
        print_sample_data()
    elif args.cleanup:
        cleanup_test_data()
    else:
        parser.print_help()
        print("\nQuick start: python test_compare.py --all")


if __name__ == '__main__':
    main()
