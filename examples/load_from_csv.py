"""
Example: Loading A/B test data from CSV files.

This example shows how to load real A/B test data from CSV files
and run the diagnostic framework.

Expected CSV format:
- user_id: unique identifier for each user
- variant: 'control' or 'treatment'
- metric: the metric value being measured
- platform: platform identifier (e.g., 'web', 'ios', 'android')
- timestamp: (optional) event timestamp
"""

import pandas as pd
from abtest_culprits import ABTestDiagnostics, CrossPlatformAnalyzer, DiagnosticReport


def load_and_diagnose(csv_path: str, output_dir: str = '.'):
    """
    Load A/B test data from CSV and run diagnostics.

    Args:
        csv_path: Path to CSV file with A/B test data
        output_dir: Directory to save reports

    CSV should have columns: user_id, variant, metric, platform, timestamp (optional)
    """
    print(f"Loading data from {csv_path}...")

    # Load data
    df = pd.read_csv(csv_path)

    # Validate required columns
    required_cols = ['user_id', 'variant', 'metric', 'platform']
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    print(f"Loaded {len(df):,} rows")
    print(f"Platforms: {df['platform'].unique()}")
    print(f"Variants: {df['variant'].unique()}")
    print()

    # Initialize diagnostics
    diagnostics = ABTestDiagnostics(alpha=0.05, power=0.80)
    analyzer = CrossPlatformAnalyzer(alpha=0.05)

    # Process each platform
    all_results = {}
    platforms = df['platform'].unique()

    for platform in platforms:
        print(f"Processing platform: {platform}")

        # Filter data for this platform
        platform_data = df[df['platform'] == platform]

        # Split into control and treatment
        control_data = platform_data[platform_data['variant'] == 'control']
        treatment_data = platform_data[platform_data['variant'] == 'treatment']

        print(f"  Control: {len(control_data):,} users")
        print(f"  Treatment: {len(treatment_data):,} users")

        # Load into diagnostics framework
        timestamp_col = 'timestamp' if 'timestamp' in df.columns else None
        diagnostics.load_platform_data(
            platform,
            control_data,
            treatment_data,
            metric_column='metric',
            user_id_column='user_id',
            timestamp_column=timestamp_col
        )

        # Run diagnostics
        results = diagnostics.run_all_diagnostics(
            platform,
            expected_ratio=(0.5, 0.5),
            mde=0.01
        )
        all_results[platform] = results

        # Add to cross-platform analyzer
        analyzer.calculate_platform_result(
            platform,
            control_data['metric'],
            treatment_data['metric'],
            use_welch=True
        )

        print()

    # Print summary
    print(diagnostics.get_summary())
    print()
    print(analyzer.generate_comparison_report())

    # Generate reports
    print(f"Generating reports in {output_dir}/...")

    html_report = DiagnosticReport.generate_html_report(all_results, analyzer)
    with open(f'{output_dir}/diagnostic_report.html', 'w') as f:
        f.write(html_report)
    print(f"✅ HTML report: {output_dir}/diagnostic_report.html")

    json_report = DiagnosticReport.generate_json_report(all_results, analyzer)
    with open(f'{output_dir}/diagnostic_report.json', 'w') as f:
        f.write(json_report)
    print(f"✅ JSON report: {output_dir}/diagnostic_report.json")

    md_report = DiagnosticReport.generate_markdown_report(all_results, analyzer)
    with open(f'{output_dir}/diagnostic_report.md', 'w') as f:
        f.write(md_report)
    print(f"✅ Markdown report: {output_dir}/diagnostic_report.md")

    return diagnostics, analyzer


def create_sample_csv(output_path: str = 'sample_abtest_data.csv'):
    """
    Create a sample CSV file for demonstration purposes.

    Args:
        output_path: Where to save the sample CSV
    """
    import numpy as np

    np.random.seed(42)

    data = []

    platforms = ['web', 'ios', 'android', 'mobile_web']
    base_samples = [5000, 4000, 3500, 2000]

    for platform, n_base in zip(platforms, base_samples):
        # Control group
        for i in range(n_base):
            data.append({
                'user_id': f'{platform}_user_c_{i}',
                'variant': 'control',
                'metric': np.random.normal(100, 20),
                'platform': platform,
                'timestamp': pd.Timestamp('2024-01-01') + pd.Timedelta(minutes=i)
            })

        # Treatment group
        lift = 0.05 if platform != 'mobile_web' else -0.02
        for i in range(n_base):
            data.append({
                'user_id': f'{platform}_user_t_{i}',
                'variant': 'treatment',
                'metric': np.random.normal(100 * (1 + lift), 20),
                'platform': platform,
                'timestamp': pd.Timestamp('2024-01-01') + pd.Timedelta(minutes=i)
            })

    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"Sample CSV created at: {output_path}")
    return output_path


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        # Use provided CSV path
        csv_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
    else:
        # Create and use sample data
        print("No CSV provided. Creating sample data...")
        csv_path = create_sample_csv()
        output_dir = '.'
        print()

    # Run diagnostics
    load_and_diagnose(csv_path, output_dir)
