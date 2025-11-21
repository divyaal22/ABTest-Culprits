# A/B Test Culprits: Comprehensive Guide

## Introduction

When running A/B tests across multiple platforms, inconsistent results are frustrating and concerning. This guide provides a systematic approach to diagnosing and fixing common issues.

## Quick Diagnosis Flowchart

```
Different results across platforms?
│
├─ Check 1: Sample Ratio Mismatch (SRM)
│   ├─ FAIL → CRITICAL: Fix randomization immediately
│   └─ PASS → Continue
│
├─ Check 2: Cross-contamination
│   ├─ FAIL → CRITICAL: Users in both groups
│   └─ PASS → Continue
│
├─ Check 3: Sample Size
│   ├─ FAIL → WARNING: May lack statistical power
│   └─ PASS → Continue
│
├─ Check 4: Data Quality (outliers, bots, duplicates)
│   ├─ FAIL → WARNING: Clean data first
│   └─ PASS → Continue
│
├─ Check 5: Variance Homogeneity
│   ├─ FAIL → INFO: Use Welch's t-test
│   └─ PASS → Continue
│
└─ Check 6: Cross-Platform Homogeneity
    ├─ FAIL → Investigate platform-specific differences
    └─ PASS → Results are legitimately different
```

---

## 1. Randomization Issues

### 1.1 Sample Ratio Mismatch (SRM)

**What it is:** The ratio of users in control vs. treatment differs from the expected ratio (e.g., 50/50).

**Why it matters:** SRM indicates a fundamental problem with randomization that can completely invalidate test results.

**How to detect:**
```python
# Automated check
diagnostics.check_sample_ratio_mismatch('platform_name', expected_ratio=(0.5, 0.5))

# Manual calculation
chi2 = ((n_control - expected_control)^2 / expected_control) +
       ((n_treatment - expected_treatment)^2 / expected_treatment)
p_value = 1 - chi2.cdf(chi2, df=1)
# If p_value < 0.05, you have SRM
```

**Common causes:**
- **Filtering after randomization**: Removing users post-assignment
  ```python
  # WRONG:
  users = assign_variants(all_users)
  users = users[users.country == 'US']  # Changes ratio!

  # RIGHT:
  users = users[users.country == 'US']
  users = assign_variants(users)
  ```

- **Platform-specific eligibility**: Different platforms have different eligibility criteria
  ```python
  # Example: iOS requires version 14+, Android requires version 10+
  # This can create different sample ratios per platform
  ```

- **Data pipeline issues**: Lost events in one variant's tracking
- **Caching**: Cached assignment decisions causing sticky behavior
- **Bot filtering**: Removing bots from one group more than the other

**How to fix:**
1. **Review assignment logic**: Ensure truly random assignment
2. **Filter BEFORE assignment**: Apply eligibility criteria before randomization
3. **Audit data pipeline**: Check for data loss in either variant
4. **Clear caches**: Ensure assignment isn't cached incorrectly
5. **Symmetric bot filtering**: Apply same bot detection to both groups

**Automation:**
```python
# Set up monitoring
from abtest_culprits import ABTestDiagnostics

diagnostics = ABTestDiagnostics()
diagnostics.load_platform_data('web', control, treatment)
result = diagnostics.check_sample_ratio_mismatch('web')

if not result.passed:
    # Alert critical SRM issue
    send_alert(f"SRM detected: {result.message}")
```

---

### 1.2 Cross-Contamination

**What it is:** Users appearing in both control and treatment groups.

**Why it matters:** Violates the fundamental assumption of independent groups.

**How to detect:**
```python
control_users = set(control_data['user_id'])
treatment_users = set(treatment_data['user_id'])
contaminated = control_users & treatment_users
print(f"Contaminated users: {len(contaminated)}")
```

**Common causes:**
- **Multiple devices**: User logs in from different devices
- **Cookie deletion**: User gets reassigned after clearing cookies
- **Cross-platform tracking failure**: Same user not recognized across platforms
- **Session-level assignment**: User gets different assignment per session

**How to fix:**
1. **Use stable user IDs**: Link users across devices/sessions
2. **Persistent assignment**: Store assignments server-side
3. **Deduplication**: Remove contaminated users from analysis
4. **Consistent hashing**: Use deterministic assignment based on user ID

---

## 2. Sample Size Issues

### 2.1 Insufficient Power

**What it is:** Too few samples to reliably detect the effect you're looking for.

**Why it matters:** Leads to false negatives (missing real effects) and unstable results.

**How to calculate required sample size:**
```python
from scipy import stats
import numpy as np

def calculate_sample_size(baseline_mean, mde, std_dev, alpha=0.05, power=0.80):
    """
    Calculate required sample size per group.

    Args:
        baseline_mean: Control group mean
        mde: Minimum Detectable Effect (relative, e.g., 0.01 = 1%)
        std_dev: Standard deviation
        alpha: Significance level
        power: Desired statistical power
    """
    effect_size = (baseline_mean * mde) / std_dev  # Cohen's d
    z_alpha = stats.norm.ppf(1 - alpha/2)
    z_beta = stats.norm.ppf(power)

    n = ((z_alpha + z_beta)**2 * 2 * std_dev**2) / (baseline_mean * mde)**2
    return int(np.ceil(n))

# Example
n_required = calculate_sample_size(
    baseline_mean=100,
    mde=0.01,  # Want to detect 1% change
    std_dev=20,
    power=0.80
)
print(f"Need {n_required:,} samples per group")
```

**Common causes:**
- **Running test too short**: Not enough time to accumulate samples
- **Targeting too small audience**: Limited eligible users
- **Expecting unrealistic effects**: Trying to detect tiny changes
- **High variance metrics**: Noisy metrics need more samples

**How to fix:**
1. **Run longer**: Extend test duration
2. **Expand audience**: Widen eligibility criteria
3. **Adjust MDE**: Be realistic about detectable effects
4. **Use variance reduction**:
   ```python
   # CUPED (Controlled-experiment Using Pre-Experiment Data)
   # Reduces variance by controlling for pre-experiment behavior
   adjusted_metric = metric - theta * pre_metric
   ```
5. **Sequential testing**: Use valid sequential testing methods

---

### 2.2 Unequal Sample Sizes Across Platforms

**What it is:** Dramatically different sample sizes between platforms.

**Why it matters:** Low-traffic platforms may show random noise, not real effects.

**How to detect:**
```python
analyzer = CrossPlatformAnalyzer()
# ... load data ...

culprits = analyzer.identify_likely_culprits()
sample_size_issues = culprits['sample_size']
```

**How to fix:**
1. **Longer runtime for small platforms**: Run test until adequate sample
2. **Different MDE per platform**: Accept larger MDE for small platforms
3. **Stratified analysis**: Don't compare platforms directly if sample sizes differ greatly
4. **Meta-analysis**: Pool platforms using proper statistical methods

---

## 3. Instrumentation Errors

### 3.1 Inconsistent Metric Definitions

**What it is:** Metrics calculated differently across platforms.

**Why it matters:** You're not comparing apples to apples.

**Examples:**
```python
# Web: Revenue per session
web_metric = total_revenue / num_sessions

# Mobile: Revenue per user
mobile_metric = total_revenue / num_users

# These are DIFFERENT metrics!
```

**How to detect:**
1. **Review metric calculation code** across all platforms
2. **Compare distributions**:
   ```python
   print(f"Web mean: {web_data.mean()}")
   print(f"Mobile mean: {mobile_data.mean()}")
   # Should be in same ballpark if same metric
   ```
3. **Check denominators**: Ensure same user base in calculations

**How to fix:**
1. **Standardize definitions**: Document metrics in central location
2. **Shared libraries**: Use common metric calculation code
3. **Validation tests**: Assert metric properties across platforms

---

### 3.2 Data Pipeline Issues

**What it is:** Events lost, duplicated, or delayed in data pipeline.

**Why it matters:** Introduces bias or noise in metrics.

**How to detect:**
```python
# Check temporal consistency
diagnostics.check_temporal_consistency('platform_name')

# Look for gaps in data
daily_counts = data.groupby(data['timestamp'].dt.date).size()
gaps = daily_counts[daily_counts == 0]
print(f"Days with no data: {gaps}")

# Check for duplicates
duplicates = data[data.duplicated(['user_id', 'timestamp', 'event_type'])]
print(f"Duplicate events: {len(duplicates)}")
```

**Common causes:**
- **ETL job failures**: Pipeline outages
- **Clock skew**: Timestamp misalignment
- **Retry logic**: Events sent multiple times
- **Buffer overflows**: High-volume events dropped

**How to fix:**
1. **Monitor pipeline health**: Alert on data gaps
2. **Idempotent processing**: Deduplicate events by unique key
3. **End-to-end tests**: Validate data flow from client to warehouse
4. **Backfill processes**: Handle historical data corrections

---

## 4. Bot and Fraud Traffic

### 4.1 Bot Detection

**What it is:** Automated traffic (bots, scrapers, crawlers) in your A/B test.

**Why it matters:** Bots don't behave like humans and can skew results.

**How to detect:**
```python
# Automated check
diagnostics.check_bot_patterns('platform_name', high_frequency_threshold=100)

# Manual analysis
user_event_counts = data.groupby('user_id').size()
high_frequency_users = user_event_counts[user_event_counts > 100]
print(f"Potential bots: {len(high_frequency_users)}")

# Check user agents
bot_patterns = ['bot', 'crawler', 'spider', 'scraper']
potential_bots = data[data['user_agent'].str.contains('|'.join(bot_patterns), case=False, na=False)]
```

**Characteristics of bot traffic:**
- Very high event frequency
- Perfect periodicity (events every X seconds)
- Suspicious user agents
- Single IP with many users
- Zero variance in behavior
- Unusual hour-of-day patterns

**How to fix:**
1. **Filter at assignment**: Don't assign bots to test
   ```python
   if is_bot(user_agent):
       return None  # Don't assign
   ```
2. **Post-hoc filtering**: Remove bots from analysis
3. **Use bot detection service**: Cloudflare, DataDome, etc.
4. **Behavioral signals**: Captchas, mouse movements, etc.

---

## 5. Statistical Issues

### 5.1 Variance Heterogeneity

**What it is:** Control and treatment groups have different variances.

**Why it matters:** Violates t-test assumptions; can affect p-values.

**How to detect:**
```python
diagnostics.check_variance_homogeneity('platform_name')

# Manual check (Levene's test)
from scipy.stats import levene
statistic, p_value = levene(control_data, treatment_data)
print(f"Levene's test p-value: {p_value}")
# If p < 0.05, variances differ
```

**How to fix:**
```python
# Use Welch's t-test (doesn't assume equal variance)
from scipy.stats import ttest_ind
t_stat, p_value = ttest_ind(treatment, control, equal_var=False)

# Or use non-parametric test
from scipy.stats import mannwhitneyu
statistic, p_value = mannwhitneyu(treatment, control, alternative='two-sided')
```

---

### 5.2 Multiple Comparisons Problem

**What it is:** Testing multiple platforms increases false positive rate.

**Why it matters:** With 4 platforms and α=0.05, probability of at least one false positive is ~18%.

**How to fix:**
```python
# Bonferroni correction
adjusted_alpha = 0.05 / num_platforms

# Or False Discovery Rate (FDR) control
from statsmodels.stats.multitest import multipletests
p_values = [p1, p2, p3, p4]  # p-values from each platform
reject, adjusted_p, _, _ = multipletests(p_values, alpha=0.05, method='fdr_bh')
```

---

### 5.3 Peeking / Early Stopping

**What it is:** Checking results repeatedly and stopping when p < 0.05.

**Why it matters:** Inflates false positive rate dramatically.

**How to fix:**
1. **Pre-specify stopping rule**: Decide sample size in advance
2. **Use sequential testing**: Valid methods like mSPRT, always-valid p-values
3. **Preregistration**: Document test plan before running

---

## 6. Platform-Specific Factors

### 6.1 User Population Differences

**What it is:** Different types of users on each platform.

**Why it matters:** Effect may genuinely differ by user type.

**Example:**
- Web users: Desktop, work hours, high engagement
- Mobile app users: Commute times, quick sessions
- Mobile web users: Older devices, slower connections

**How to handle:**
```python
# Segment analysis
for segment in ['power_users', 'casual_users', 'new_users']:
    segment_data = data[data['segment'] == segment]
    # Analyze separately

# Or use heterogeneous treatment effects analysis
from econml.dml import CausalForestDML
model = CausalForestDML()
model.fit(Y, T, X=user_features, W=controls)
effects = model.effect(X=user_features)
```

**When to worry:**
- ✅ **OK**: Consistent relative lift across platforms, different absolute values
- ⚠️ **Investigate**: Opposite signs of effects
- ❌ **Critical**: One platform violates basic checks (SRM, contamination)

---

### 6.2 Implementation Differences

**What it is:** Feature implemented differently on each platform.

**Examples:**
- Button color slightly different due to platform constraints
- Loading time varies by platform
- Feature placement differs in UI

**How to detect:**
1. **Code review**: Compare implementations
2. **QA testing**: Manual testing on each platform
3. **Instrumentation**: Log feature interaction rates

---

## 7. Automation Strategy

### 7.1 Automated Monitoring

```python
# Set up automated checks
from abtest_culprits import ABTestDiagnostics, CrossPlatformAnalyzer

def monitor_test(test_id, platforms):
    """Run daily on your A/B tests."""
    diagnostics = ABTestDiagnostics()
    analyzer = CrossPlatformAnalyzer()

    critical_issues = []

    for platform in platforms:
        control, treatment = load_test_data(test_id, platform)
        diagnostics.load_platform_data(platform, control, treatment)

        results = diagnostics.run_all_diagnostics(platform)

        # Check for critical issues
        for result in results:
            if result.severity == 'critical' and not result.passed:
                critical_issues.append({
                    'platform': platform,
                    'check': result.check_name,
                    'message': result.message
                })

        # Add to cross-platform analysis
        analyzer.calculate_platform_result(
            platform, control['metric'], treatment['metric']
        )

    # Alert on critical issues
    if critical_issues:
        send_alert(f"Critical A/B test issues in {test_id}", critical_issues)

    # Check cross-platform homogeneity
    is_homogeneous, p_value, interpretation = analyzer.test_homogeneity_of_effects()
    if not is_homogeneous:
        send_notification(f"Heterogeneous effects in {test_id}: {interpretation}")

    # Generate daily report
    report = diagnostics.get_summary()
    save_report(test_id, report)
```

---

### 7.2 Pre-flight Checks

Run these checks BEFORE launching your test:

```python
def pre_launch_checklist(test_config):
    """Validate test configuration before launch."""
    checks = []

    # 1. Sample size calculation
    required_n = calculate_sample_size(
        baseline_mean=test_config['baseline_mean'],
        mde=test_config['mde'],
        std_dev=test_config['std_dev']
    )
    checks.append(f"Need {required_n:,} samples per platform")

    # 2. Metric definition consistency
    for platform in test_config['platforms']:
        metric_code = get_metric_code(platform, test_config['metric'])
        # Compare across platforms
        # ...

    # 3. Randomization logic review
    # Ensure consistent across platforms
    # ...

    # 4. Instrumentation validation
    # Check events are firing correctly
    # ...

    return checks
```

---

## 8. Decision Framework

### When to trust results despite discrepancies

✅ **Trust results if:**
1. All critical checks pass (SRM, no contamination)
2. Sample sizes adequate for all platforms
3. Data quality issues resolved
4. Platform differences explainable by user populations
5. Heterogeneity test shows differences are within expected range

⚠️ **Be cautious if:**
1. Warning-level issues present (outliers, variance differences)
2. Small sample sizes on some platforms
3. Wide confidence intervals
4. Recent implementation changes

❌ **Do NOT trust results if:**
1. SRM detected on any platform
2. Cross-contamination present
3. Major instrumentation issues
4. Opposite effects across platforms without clear explanation
5. Critical data quality issues

---

## 9. Best Practices

### Design Phase
1. ✅ Calculate required sample size upfront
2. ✅ Document metric definitions centrally
3. ✅ Use shared randomization library
4. ✅ Implement consistent instrumentation
5. ✅ Set up automated monitoring

### Implementation Phase
1. ✅ Validate instrumentation before launch
2. ✅ Test on small sample first
3. ✅ Enable real-time dashboards
4. ✅ Set up alerting for critical issues

### Analysis Phase
1. ✅ Run all diagnostic checks
2. ✅ Compare across platforms systematically
3. ✅ Investigate discrepancies before concluding
4. ✅ Document findings and lessons learned
5. ✅ Use appropriate statistical corrections

---

## 10. Resources

### Statistical Tests Reference

| Situation | Recommended Test |
|-----------|------------------|
| Normal distribution, equal variance | Student's t-test |
| Normal distribution, unequal variance | Welch's t-test |
| Non-normal, large sample | t-test (CLT applies) |
| Non-normal, small sample | Mann-Whitney U |
| Binary outcome | Chi-square or Fisher's exact |
| Multiple platforms | Heterogeneity test + corrections |

### Further Reading

- **Trustworthy Online Controlled Experiments** by Kohavi et al.
- **Statistics for Experimenters** by Box, Hunter, Hunter
- **Experimentation Works** by Thomke
- **The Design and Analysis of Computer Experiments** by Santner et al.

### Tools

- **statsmodels**: Python statistical testing library
- **scipy.stats**: Core statistical functions
- **pingouin**: User-friendly statistical package
- **pymc3**: Bayesian A/B testing
