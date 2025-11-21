# A/B Test Cross-Platform Analysis Framework

## Overview

When running A/B tests across multiple platforms (web, mobile apps, mobile web, etc.), discrepancies in metrics, relative lift, and p-values can indicate underlying issues. This framework helps diagnose and automate the detection of common culprits.

## Common Culprits in Cross-Platform A/B Tests

### 1. **Randomization Issues**
- **Sample Ratio Mismatch (SRM)**: Unequal split between control/treatment groups
- **Biased Assignment**: Non-random user assignment to variants
- **Cross-contamination**: Users experiencing multiple variants
- **Persistent Assignment Issues**: Users switching between variants

### 2. **Sample Size Problems**
- **Insufficient Power**: Too few samples to detect meaningful effects
- **Unequal Distribution**: Imbalanced sample sizes across platforms
- **Early Stopping**: Peeking at results before reaching statistical significance
- **Multiple Comparison Problem**: Not adjusting for testing across multiple platforms

### 3. **Instrumentation Errors**
- **Tracking Inconsistencies**: Different event definitions across platforms
- **Data Pipeline Issues**: Lost or duplicated events
- **Timestamp Misalignment**: Clock skew between platforms
- **Missing Events**: Incomplete tracking implementation
- **Schema Variations**: Different metric calculations per platform

### 4. **Bot and Fraud Traffic**
- **Bot Activity**: Automated traffic skewing results
- **Fraud Patterns**: Malicious actors manipulating metrics
- **Crawler Traffic**: Search engine bots in the data
- **User Agent Spoofing**: Misclassified platform traffic

### 5. **Platform-Specific Factors**
- **User Behavior Differences**: Natural variations between platform users
- **Technical Constraints**: Platform limitations affecting feature delivery
- **Release Timing**: Staggered rollouts across platforms
- **Cache Effects**: Different caching strategies per platform

### 6. **Statistical Issues**
- **Variance Heterogeneity**: Different variance across platforms
- **Non-Normal Distributions**: Violations of t-test assumptions
- **Outliers**: Extreme values affecting results differently per platform
- **Simpson's Paradox**: Confounding variables reversing trends

### 7. **Metric Definition Problems**
- **Inconsistent Calculations**: Different formulas per platform
- **Aggregation Issues**: Time windows or grouping differences
- **Denominator Problems**: Different user bases in calculations

## Diagnostic Techniques

### Automated Checks

1. **Sample Ratio Test (Chi-Square)**
   - Validate 50/50 splits or expected ratios
   - Check for systematic biases in assignment

2. **Sequential Testing**
   - Monitor p-values over time for unusual patterns
   - Detect multiple testing issues

3. **Distribution Analysis**
   - Compare statistical distributions across platforms
   - Identify outliers and anomalies

4. **Instrumentation Validation**
   - Compare event volumes and patterns
   - Detect missing or duplicated events

5. **Bot Detection**
   - Analyze user agent patterns
   - Flag suspicious behavior patterns
   - Identify high-frequency, low-variance users

6. **Power Analysis**
   - Calculate minimum detectable effect
   - Validate sample sizes

7. **Variance Testing**
   - Check homogeneity of variance (Levene's test)
   - Validate t-test assumptions

## Framework Usage

See `examples/` directory for detailed usage examples.

## Installation

```bash
pip install -r requirements.txt
```

## ⚠️ Important: Data Preparation

**The framework requires USER-LEVEL data** (one row per user with aggregated metrics).

If you have **event-level data** (multiple rows per user), you MUST aggregate to user-level first:

```python
from abtest_culprits import prepare_from_events

# Automatically convert event-level to user-level
platform_data = prepare_from_events(
    events_df,
    user_id_column='user_id',
    variant_column='variant',
    metric_column='revenue',
    platform_column='platform',
    aggregation='sum'  # or 'mean', 'count', etc.
)
```

**Why user-level?** Statistical tests assume independent observations. Events from the same user are correlated and violate this assumption, leading to incorrect p-values and conclusions.

📖 **See `docs/DATA_PREPARATION.md` for detailed guidance and examples.**

## Quick Start

```python
from abtest_culprits import ABTestDiagnostics

# Load your A/B test data
diagnostics = ABTestDiagnostics()
diagnostics.load_data('platform_name', control_data, treatment_data)

# Run all diagnostic checks
report = diagnostics.run_all_diagnostics()

# Get actionable recommendations
print(report.get_summary())
```

## Output

The framework generates:
- ✅ **Pass/Fail status** for each diagnostic check
- 📊 **Detailed metrics** for each platform
- 🔍 **Root cause analysis** when issues are detected
- 💡 **Recommendations** for fixing identified problems
- 📈 **Comparison reports** across all platforms

## Contributing

See `CONTRIBUTING.md` for guidelines.

## License

MIT License
