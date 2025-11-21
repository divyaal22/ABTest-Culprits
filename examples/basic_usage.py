"""
Basic usage example of the A/B Test Diagnostics framework.

This example shows how to:
1. Load A/B test data for multiple platforms
2. Run diagnostic checks
3. Compare results across platforms
4. Generate reports
"""

import pandas as pd
import numpy as np
from abtest_culprits import ABTestDiagnostics, CrossPlatformAnalyzer, DiagnosticReport


def generate_sample_data(n_control=10000, n_treatment=10000, true_lift=0.05, add_issues=False):
    """
    Generate synthetic A/B test data for demonstration.

    Args:
        n_control: Number of control users
        n_treatment: Number of treatment users
        true_lift: True treatment effect (e.g., 0.05 = 5% lift)
        add_issues: Whether to add data quality issues for demonstration

    Returns:
        Tuple of (control_df, treatment_df)
    """
    np.random.seed(42)

    # Generate control data
    control_data = pd.DataFrame({
        'user_id': [f'user_c_{i}' for i in range(n_control)],
        'metric': np.random.normal(100, 20, n_control),
        'timestamp': pd.date_range('2024-01-01', periods=n_control, freq='1min')
    })

    # Generate treatment data with lift
    treatment_mean = 100 * (1 + true_lift)
    treatment_data = pd.DataFrame({
        'user_id': [f'user_t_{i}' for i in range(n_treatment)],
        'metric': np.random.normal(treatment_mean, 20, n_treatment),
        'timestamp': pd.date_range('2024-01-01', periods=n_treatment, freq='1min')
    })

    if add_issues:
        # Add some data quality issues for demonstration

        # 1. Add outliers
        outlier_indices = np.random.choice(len(treatment_data), size=50, replace=False)
        treatment_data.loc[outlier_indices, 'metric'] *= 10

        # 2. Add duplicate users
        duplicate_users = control_data.sample(n=10)
        treatment_data = pd.concat([treatment_data, duplicate_users], ignore_index=True)

        # 3. Add potential bots (high-frequency users)
        bot_user = pd.DataFrame({
            'user_id': ['bot_user_001'] * 200,
            'metric': np.random.normal(treatment_mean, 5, 200),
            'timestamp': pd.date_range('2024-01-01', periods=200, freq='30s')
        })
        treatment_data = pd.concat([treatment_data, bot_user], ignore_index=True)

    return control_data, treatment_data


def main():
    print("=" * 80)
    print("A/B Test Cross-Platform Diagnostics - Basic Example")
    print("=" * 80)
    print()

    # Initialize diagnostics framework
    diagnostics = ABTestDiagnostics(alpha=0.05, power=0.80)

    # Simulate data for multiple platforms
    print("📊 Generating sample data for multiple platforms...")
    print()

    # Platform 1: Web (clean data, positive lift)
    web_control, web_treatment = generate_sample_data(
        n_control=10000, n_treatment=10000, true_lift=0.05, add_issues=False
    )
    diagnostics.load_platform_data('web', web_control, web_treatment,
                                     metric_column='metric', user_id_column='user_id',
                                     timestamp_column='timestamp')

    # Platform 2: iOS (clean data, similar lift)
    ios_control, ios_treatment = generate_sample_data(
        n_control=8000, n_treatment=8000, true_lift=0.048, add_issues=False
    )
    diagnostics.load_platform_data('ios', ios_control, ios_treatment,
                                     metric_column='metric', user_id_column='user_id',
                                     timestamp_column='timestamp')

    # Platform 3: Android (has data quality issues)
    android_control, android_treatment = generate_sample_data(
        n_control=7000, n_treatment=7500, true_lift=0.08, add_issues=True
    )
    diagnostics.load_platform_data('android', android_control, android_treatment,
                                     metric_column='metric', user_id_column='user_id',
                                     timestamp_column='timestamp')

    # Platform 4: Mobile Web (small sample size, negative lift - suspicious!)
    mweb_control, mweb_treatment = generate_sample_data(
        n_control=1500, n_treatment=1500, true_lift=-0.02, add_issues=False
    )
    diagnostics.load_platform_data('mobile_web', mweb_control, mweb_treatment,
                                     metric_column='metric', user_id_column='user_id',
                                     timestamp_column='timestamp')

    # Run diagnostics for all platforms
    print("🔍 Running diagnostic checks for all platforms...")
    print()

    all_results = {}
    for platform in ['web', 'ios', 'android', 'mobile_web']:
        print(f"Analyzing {platform}...")
        results = diagnostics.run_all_diagnostics(
            platform,
            expected_ratio=(0.5, 0.5),
            mde=0.01  # Want to detect 1% lift
        )
        all_results[platform] = results

    # Print platform-specific results
    print()
    print(diagnostics.get_summary())

    # Cross-platform analysis
    print()
    print("=" * 80)
    print("CROSS-PLATFORM ANALYSIS")
    print("=" * 80)
    print()

    analyzer = CrossPlatformAnalyzer(alpha=0.05)

    # Calculate results for each platform
    for platform in ['web', 'ios', 'android', 'mobile_web']:
        platform_data = diagnostics.platforms[platform]
        analyzer.calculate_platform_result(
            platform,
            platform_data['control'][platform_data['metric_column']],
            platform_data['treatment'][platform_data['metric_column']],
            use_welch=True
        )

    # Generate comparison report
    print(analyzer.generate_comparison_report())

    # Statistical test recommendations
    print()
    print("📋 RECOMMENDED STATISTICAL TESTS")
    print("-" * 80)
    print(analyzer.recommend_statistical_test())
    print()

    # Generate reports
    print()
    print("=" * 80)
    print("GENERATING REPORTS")
    print("=" * 80)
    print()

    # HTML Report
    html_report = DiagnosticReport.generate_html_report(all_results, analyzer)
    with open('abtest_diagnostic_report.html', 'w') as f:
        f.write(html_report)
    print("✅ HTML report saved to: abtest_diagnostic_report.html")

    # JSON Report
    json_report = DiagnosticReport.generate_json_report(all_results, analyzer)
    with open('abtest_diagnostic_report.json', 'w') as f:
        f.write(json_report)
    print("✅ JSON report saved to: abtest_diagnostic_report.json")

    # Markdown Report
    md_report = DiagnosticReport.generate_markdown_report(all_results, analyzer)
    with open('abtest_diagnostic_report.md', 'w') as f:
        f.write(md_report)
    print("✅ Markdown report saved to: abtest_diagnostic_report.md")

    print()
    print("=" * 80)
    print("KEY INSIGHTS FROM THIS EXAMPLE")
    print("=" * 80)
    print()
    print("1. Web & iOS show consistent positive lift (~5%) with clean data ✅")
    print("2. Android shows higher lift but has data quality issues:")
    print("   - Outliers detected")
    print("   - Duplicate users")
    print("   - Potential bot traffic")
    print("3. Mobile Web shows opposite effect (negative lift) with small sample")
    print("   - May need more data to reach statistical power")
    print("4. Cross-platform heterogeneity detected - investigate platform differences")
    print()


if __name__ == '__main__':
    main()
