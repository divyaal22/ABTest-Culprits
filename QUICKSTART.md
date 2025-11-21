# Quick Start Guide

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd ABTest-Culprits

# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

## Basic Usage

### 1. Load Your Data

```python
import pandas as pd
from abtest_culprits import ABTestDiagnostics, CrossPlatformAnalyzer

# Load your A/B test data
web_control = pd.read_csv('web_control.csv')
web_treatment = pd.read_csv('web_treatment.csv')

# Initialize diagnostics
diagnostics = ABTestDiagnostics(alpha=0.05, power=0.80)

# Load platform data
diagnostics.load_platform_data(
    platform_name='web',
    control_data=web_control,
    treatment_data=web_treatment,
    metric_column='metric',        # Column with metric values
    user_id_column='user_id',      # Column with user IDs
    timestamp_column='timestamp'   # Optional: for temporal checks
)
```

### 2. Run Diagnostics

```python
# Run all diagnostic checks for this platform
results = diagnostics.run_all_diagnostics(
    platform_name='web',
    expected_ratio=(0.5, 0.5),  # Expected control/treatment ratio
    mde=0.01                     # Minimum detectable effect (1%)
)

# Print summary
print(diagnostics.get_summary())
```

### 3. Compare Across Platforms

```python
# Initialize cross-platform analyzer
analyzer = CrossPlatformAnalyzer(alpha=0.05)

# Add platforms
for platform in ['web', 'ios', 'android']:
    platform_data = diagnostics.platforms[platform]
    analyzer.calculate_platform_result(
        platform,
        platform_data['control'][platform_data['metric_column']],
        platform_data['treatment'][platform_data['metric_column']]
    )

# Generate comparison report
print(analyzer.generate_comparison_report())
```

### 4. Generate Reports

```python
from abtest_culprits import DiagnosticReport

# Collect all results
all_results = {
    'web': diagnostics.run_all_diagnostics('web'),
    'ios': diagnostics.run_all_diagnostics('ios'),
    'android': diagnostics.run_all_diagnostics('android')
}

# HTML Report (best for viewing)
html = DiagnosticReport.generate_html_report(all_results, analyzer)
with open('report.html', 'w') as f:
    f.write(html)

# JSON Report (for programmatic use)
json_report = DiagnosticReport.generate_json_report(all_results, analyzer)
with open('report.json', 'w') as f:
    f.write(json_report)

# Markdown Report (for documentation)
md = DiagnosticReport.generate_markdown_report(all_results, analyzer)
with open('report.md', 'w') as f:
    f.write(md)
```

## Run Examples

```bash
# Basic example with synthetic data
cd examples
python basic_usage.py

# Load from CSV example
python load_from_csv.py path/to/your/data.csv
```

## Understanding the Checks

### Critical Checks (Must Pass)
1. **Sample Ratio Mismatch (SRM)** - Validates randomization
2. **Duplicate Users** - Checks for cross-contamination

### Statistical Validity Checks
3. **Minimum Sample Size** - Ensures adequate statistical power
4. **Variance Homogeneity** - Validates t-test assumptions
5. **Normality** - Checks distribution assumptions

### Data Quality Checks
6. **Outliers** - Detects extreme values
7. **Bot Patterns** - Identifies potential automated traffic
8. **Temporal Consistency** - Validates data pipeline health

## Interpreting Results

### ✅ All Checks Pass
Your data is clean and results are trustworthy. Proceed with confidence!

### ⚠️ Warnings Only
Results are likely valid, but review warnings:
- Small sample size → May need more data
- Unequal variance → Use Welch's t-test
- Outliers → Consider robust statistics

### ❌ Critical Failures
**DO NOT TRUST RESULTS** - Fix these first:
- SRM detected → Fix randomization logic
- Cross-contamination → Remove duplicate users
- Major data quality issues → Clean data pipeline

## Common Scenarios

### Scenario 1: Different lifts across platforms

```python
# Check if heterogeneity is expected
is_homogeneous, p_value, interpretation = analyzer.test_homogeneity_of_effects()
print(interpretation)

# Identify likely culprits
culprits = analyzer.identify_likely_culprits()
for category, issues in culprits.items():
    if issues:
        print(f"\n{category}:")
        for issue in issues:
            print(f"  - {issue}")
```

### Scenario 2: One platform shows opposite effect

```python
# Run diagnostics on that specific platform
problem_platform = 'mobile_web'
results = diagnostics.run_all_diagnostics(problem_platform)

# Check for critical issues
critical = [r for r in results if r.severity == 'critical' and not r.passed]
if critical:
    print("Critical issues found:")
    for result in critical:
        print(f"  - {result.check_name}: {result.message}")
        print(f"    {result.recommendation}")
```

### Scenario 3: Automated monitoring

```python
def daily_check(test_id):
    """Run this daily on your active tests."""
    diagnostics = ABTestDiagnostics()

    # Load latest data
    for platform in get_platforms(test_id):
        control, treatment = fetch_data(test_id, platform)
        diagnostics.load_platform_data(platform, control, treatment)

        # Run checks
        results = diagnostics.run_all_diagnostics(platform)

        # Alert on critical issues
        critical = [r for r in results if r.severity == 'critical' and not r.passed]
        if critical:
            send_alert(f"Critical issues in {test_id}/{platform}", critical)

    # Generate daily report
    save_report(test_id, diagnostics.get_summary())
```

## Need Help?

- 📖 **Detailed Guide**: See `docs/CULPRITS_GUIDE.md` for in-depth explanations
- 💡 **Examples**: Check `examples/` directory for more use cases
- 📚 **API Docs**: Coming soon

## Tips

1. **Run diagnostics early**: Check data within first 24 hours of test
2. **Automate monitoring**: Set up daily checks for all running tests
3. **Document everything**: Save reports for every test
4. **Review together**: Have team review cross-platform discrepancies
5. **Iterate**: Use learnings to improve future test designs

## What's Next?

After validating your data:

1. ✅ Confirm all critical checks pass
2. ✅ Investigate any warnings
3. ✅ Run cross-platform comparison
4. ✅ Make decision based on clean, validated data
5. ✅ Document findings and share learnings
