# A/B Test Cross-Platform Checklist

Use this checklist when investigating discrepancies across platforms.

## Phase 1: Critical Checks (Stop if any fail)

### Randomization
- [ ] **Sample Ratio Mismatch (SRM)**
  - [ ] Run chi-square test for each platform
  - [ ] p-value > 0.05 for all platforms?
  - [ ] If FAIL: Investigate randomization logic immediately
  - [ ] Check: Filtering applied BEFORE or AFTER assignment?

- [ ] **Cross-Contamination**
  - [ ] Users appear in only ONE group?
  - [ ] Check overlap: `len(control_users & treatment_users) == 0`
  - [ ] If FAIL: Review user ID tracking and assignment persistence

### Data Integrity
- [ ] **Duplicate Events**
  - [ ] No duplicate (user_id, timestamp, event) tuples?
  - [ ] Deduplication logic consistent across platforms?
  - [ ] If FAIL: Fix data pipeline idempotency

## Phase 2: Statistical Validity

### Sample Size
- [ ] **Power Analysis**
  - [ ] Calculate required N for desired MDE
  - [ ] Each platform has ≥ required N?
  - [ ] If NO: Run longer or adjust MDE expectations
  - [ ] Formula: n = 2(z_α/2 + z_β)²σ² / δ²

- [ ] **Sample Size Balance Across Platforms**
  - [ ] Smallest platform ≥ 50% of median sample size?
  - [ ] If NO: Consider separate analysis timeline

### Variance
- [ ] **Variance Homogeneity** (Levene's test)
  - [ ] p-value > 0.05 for each platform?
  - [ ] Variance ratio < 2x between control/treatment?
  - [ ] If FAIL: Use Welch's t-test instead of Student's t-test

- [ ] **Variance Across Platforms**
  - [ ] Similar standard deviations across platforms?
  - [ ] If NO: Investigate platform-specific noise sources

### Distribution
- [ ] **Normality** (Shapiro-Wilk or visual inspection)
  - [ ] Distributions approximately normal?
  - [ ] Skewness < 2, Kurtosis < 7?
  - [ ] If NO + small sample: Consider Mann-Whitney U test

## Phase 3: Data Quality

### Outliers
- [ ] **Outlier Detection**
  - [ ] Outliers < 5% of data?
  - [ ] Similar outlier % in control and treatment?
  - [ ] Outliers explainable (e.g., whale users)?
  - [ ] If >5%: Investigate bots, data issues, or winsorize

### Bot Traffic
- [ ] **High-Frequency Users**
  - [ ] Users with >100 events < 2% of total?
  - [ ] User agent analysis shows normal distribution?
  - [ ] Behavioral patterns look human?
  - [ ] If FAIL: Apply bot filtering or use bot detection service

### Temporal Consistency
- [ ] **Data Pipeline Health**
  - [ ] No days with zero data?
  - [ ] Coefficient of variation < 0.5 for daily means?
  - [ ] No sudden spikes/drops in event volume?
  - [ ] If FAIL: Investigate ETL job failures or data quality issues

## Phase 4: Cross-Platform Comparison

### Effect Consistency
- [ ] **Homogeneity of Effects** (Q statistic)
  - [ ] p-value > 0.05?
  - [ ] If FAIL: Effects genuinely differ by platform
  - [ ] Document why (user population, implementation, etc.)

- [ ] **Effect Direction**
  - [ ] All platforms show same direction (+/- lift)?
  - [ ] If NO: CRITICAL - Investigate immediately
  - [ ] Check: Feature implementation, metric calculation

### Metric Consistency
- [ ] **Metric Definition**
  - [ ] Same metric formula across all platforms?
  - [ ] Same denominator (per user, per session, etc.)?
  - [ ] Same data types and rounding?
  - [ ] If NO: Standardize definitions

- [ ] **Metric Distribution**
  - [ ] Control group means similar across platforms?
  - [ ] If NO: May indicate different user populations (OK)
  - [ ] Or may indicate metric calculation bug (NOT OK)

## Phase 5: Implementation Validation

### Feature Parity
- [ ] **Code Review**
  - [ ] Feature code reviewed across all platforms?
  - [ ] Same business logic?
  - [ ] Same user experience?
  - [ ] Any platform-specific constraints?

- [ ] **QA Testing**
  - [ ] Manual testing completed on all platforms?
  - [ ] Feature works as expected?
  - [ ] Screenshots/videos compared?

### Instrumentation
- [ ] **Event Tracking**
  - [ ] Same events tracked on all platforms?
  - [ ] Event properties consistent?
  - [ ] No platform-specific filtering in tracking?
  - [ ] End-to-end test validates data flow?

- [ ] **Assignment Tracking**
  - [ ] Assignment logged consistently?
  - [ ] Assignment time and exposure time tracked?
  - [ ] Assignment persistent across sessions?

## Phase 6: Environmental Factors

### User Populations
- [ ] **Demographic Analysis**
  - [ ] User demographics similar across platforms?
  - [ ] New vs. returning user mix consistent?
  - [ ] Geographic distribution similar?

- [ ] **Behavior Baseline**
  - [ ] Pre-experiment metrics similar?
  - [ ] Platform-specific usage patterns documented?
  - [ ] User journeys understood per platform?

### External Factors
- [ ] **Timing**
  - [ ] Test launched simultaneously on all platforms?
  - [ ] If NO: Document stagger and account for time-based effects
  - [ ] Any holidays/events during test period?

- [ ] **Technical Factors**
  - [ ] No major releases during test?
  - [ ] No outages or performance issues?
  - [ ] No marketing campaigns targeting specific platforms?

## Phase 7: Statistical Corrections

### Multiple Comparisons
- [ ] **Bonferroni Correction**
  - [ ] If testing K platforms: α' = α / K
  - [ ] Or use FDR (False Discovery Rate) control

### Sequential Testing
- [ ] **Peeking Problem**
  - [ ] Pre-specified stopping rule?
  - [ ] Or using valid sequential testing method?
  - [ ] Not stopping just because p < 0.05?

## Decision Matrix

| Scenario | Action |
|----------|--------|
| All checks pass ✅ | Trust results, proceed with decision |
| Only warnings ⚠️ | Trust results with caveats, document warnings |
| Critical failures ❌ | DO NOT TRUST - Fix issues and re-run |
| Opposite effects by platform 🔄 | INVESTIGATE - Don't make decision yet |
| High heterogeneity 📊 | Analyze platforms separately |

## Automated Checks

```python
# Minimal automation script
from abtest_culprits import ABTestDiagnostics, CrossPlatformAnalyzer

def check_test(platforms_data):
    """
    platforms_data: dict of {platform_name: (control_df, treatment_df)}
    """
    diagnostics = ABTestDiagnostics()
    analyzer = CrossPlatformAnalyzer()

    critical_issues = []

    for platform, (control, treatment) in platforms_data.items():
        # Load data
        diagnostics.load_platform_data(platform, control, treatment)

        # Run checks
        results = diagnostics.run_all_diagnostics(platform)

        # Collect critical issues
        for r in results:
            if r.severity == 'critical' and not r.passed:
                critical_issues.append(f"{platform}: {r.check_name}")

        # Add to analyzer
        analyzer.calculate_platform_result(
            platform, control['metric'], treatment['metric']
        )

    # Check heterogeneity
    is_homogeneous, _, _ = analyzer.test_homogeneity_of_effects()

    # Generate checklist status
    status = {
        'critical_issues': critical_issues,
        'is_homogeneous': is_homogeneous,
        'can_proceed': len(critical_issues) == 0
    }

    return status
```

## Sign-Off Template

```
A/B Test: [Test Name]
Date: [Date]
Platforms: [List]

CHECKLIST STATUS:
✅ Critical checks passed
✅ Statistical validity confirmed
✅ Data quality acceptable
⚠️ Minor warnings: [List]
✅ Cross-platform consistency validated
✅ Implementation verified

RECOMMENDATION: [Proceed / Investigate further / Re-run]

Reviewed by: [Name]
Date: [Date]
```

## Common Issues and Solutions

| Issue | Quick Fix |
|-------|-----------|
| SRM detected | Check filtering logic; review data pipeline |
| Opposite effects | Review feature implementation; check metric calculation |
| High variance | Filter bots; remove outliers; increase sample size |
| Small sample | Run test longer; expand audience |
| Missing data | Check ETL jobs; review tracking code |
| Duplicates | Add deduplication logic; check idempotency |

## Resources

- **Full Guide**: `docs/CULPRITS_GUIDE.md`
- **Quick Start**: `QUICKSTART.md`
- **Examples**: `examples/`

---

**Remember**: When in doubt, investigate. It's better to delay a decision than to make one based on faulty data.
