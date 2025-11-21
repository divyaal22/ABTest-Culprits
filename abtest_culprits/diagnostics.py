"""
Core diagnostic functions for A/B test validation.
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import warnings


@dataclass
class DiagnosticResult:
    """Result of a single diagnostic check."""
    check_name: str
    passed: bool
    severity: str  # 'critical', 'warning', 'info'
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""


class ABTestDiagnostics:
    """
    Automated diagnostic framework for A/B test validation.

    Performs comprehensive checks to identify common issues in A/B tests:
    - Randomization problems
    - Sample size issues
    - Instrumentation errors
    - Bot traffic
    - Statistical assumption violations
    """

    def __init__(self, alpha: float = 0.05, power: float = 0.80):
        """
        Initialize diagnostics framework.

        Args:
            alpha: Significance level for statistical tests (default: 0.05)
            power: Desired statistical power (default: 0.80)
        """
        self.alpha = alpha
        self.power = power
        self.platforms: Dict[str, Dict] = {}
        self.results: List[DiagnosticResult] = []

    def load_platform_data(
        self,
        platform_name: str,
        control_data: pd.DataFrame,
        treatment_data: pd.DataFrame,
        metric_column: str = 'metric',
        user_id_column: str = 'user_id',
        timestamp_column: Optional[str] = None
    ):
        """
        Load A/B test data for a specific platform.

        Args:
            platform_name: Name of the platform (e.g., 'web', 'ios', 'android')
            control_data: DataFrame with control group data
            treatment_data: DataFrame with treatment group data
            metric_column: Name of the column containing the metric values
            user_id_column: Name of the column containing user IDs
            timestamp_column: Optional column containing timestamps
        """
        self.platforms[platform_name] = {
            'control': control_data,
            'treatment': treatment_data,
            'metric_column': metric_column,
            'user_id_column': user_id_column,
            'timestamp_column': timestamp_column
        }

    def check_sample_ratio_mismatch(
        self,
        platform_name: str,
        expected_ratio: Tuple[float, float] = (0.5, 0.5)
    ) -> DiagnosticResult:
        """
        Check for Sample Ratio Mismatch (SRM) using Chi-Square test.

        SRM indicates randomization issues that can invalidate test results.

        Args:
            platform_name: Platform to check
            expected_ratio: Expected (control, treatment) ratio

        Returns:
            DiagnosticResult with SRM check status
        """
        data = self.platforms[platform_name]
        n_control = len(data['control'])
        n_treatment = len(data['treatment'])
        n_total = n_control + n_treatment

        expected_control = n_total * expected_ratio[0]
        expected_treatment = n_total * expected_ratio[1]

        # Chi-square test
        chi2_stat = (
            ((n_control - expected_control) ** 2 / expected_control) +
            ((n_treatment - expected_treatment) ** 2 / expected_treatment)
        )
        p_value = 1 - stats.chi2.cdf(chi2_stat, df=1)

        passed = p_value > self.alpha
        actual_ratio = n_control / n_total if n_total > 0 else 0

        return DiagnosticResult(
            check_name="Sample Ratio Mismatch (SRM)",
            passed=passed,
            severity='critical' if not passed else 'info',
            message=f"{'✅ PASS' if passed else '❌ FAIL'}: Sample ratio check (p={p_value:.4f})",
            details={
                'platform': platform_name,
                'n_control': n_control,
                'n_treatment': n_treatment,
                'actual_ratio': actual_ratio,
                'expected_ratio': expected_ratio[0],
                'chi2_statistic': chi2_stat,
                'p_value': p_value
            },
            recommendation=(
                "✓ Sample ratio is as expected." if passed else
                "⚠️ Sample ratio mismatch detected! Check randomization logic, "
                "data pipeline, and filtering. This is a critical issue that can "
                "invalidate all test results."
            )
        )

    def check_minimum_sample_size(
        self,
        platform_name: str,
        minimum_detectable_effect: float = 0.01,  # 1% relative change
        baseline_mean: Optional[float] = None
    ) -> DiagnosticResult:
        """
        Check if sample size is sufficient for desired power.

        Args:
            platform_name: Platform to check
            minimum_detectable_effect: Smallest effect size to detect (relative)
            baseline_mean: Baseline metric mean (if None, uses control mean)

        Returns:
            DiagnosticResult with sample size adequacy check
        """
        data = self.platforms[platform_name]
        control_values = data['control'][data['metric_column']]

        if baseline_mean is None:
            baseline_mean = control_values.mean()

        pooled_std = np.std(control_values, ddof=1)

        # Effect size in standard deviations (Cohen's d)
        effect_size = (baseline_mean * minimum_detectable_effect) / pooled_std

        # Calculate required sample size per group
        z_alpha = stats.norm.ppf(1 - self.alpha / 2)
        z_beta = stats.norm.ppf(self.power)

        required_n = ((z_alpha + z_beta) ** 2 * 2 * (pooled_std ** 2)) / ((baseline_mean * minimum_detectable_effect) ** 2)
        required_n = int(np.ceil(required_n))

        actual_n = min(len(data['control']), len(data['treatment']))
        passed = actual_n >= required_n

        return DiagnosticResult(
            check_name="Minimum Sample Size",
            passed=passed,
            severity='warning' if not passed else 'info',
            message=f"{'✅ PASS' if passed else '⚠️ WARNING'}: Sample size check",
            details={
                'platform': platform_name,
                'actual_sample_size': actual_n,
                'required_sample_size': required_n,
                'power': self.power,
                'mde': minimum_detectable_effect,
                'effect_size_d': effect_size
            },
            recommendation=(
                f"✓ Sample size ({actual_n:,}) is sufficient." if passed else
                f"⚠️ Sample size ({actual_n:,}) may be insufficient. "
                f"Need {required_n:,} samples per group to detect {minimum_detectable_effect*100}% "
                f"change with {self.power*100}% power. Consider running test longer or "
                f"adjusting MDE expectations."
            )
        )

    def check_variance_homogeneity(self, platform_name: str) -> DiagnosticResult:
        """
        Check if variances are equal between control and treatment (Levene's test).

        Unequal variances can affect t-test validity.

        Args:
            platform_name: Platform to check

        Returns:
            DiagnosticResult with variance homogeneity check
        """
        data = self.platforms[platform_name]
        control_values = data['control'][data['metric_column']].dropna()
        treatment_values = data['treatment'][data['metric_column']].dropna()

        # Levene's test (more robust than F-test)
        statistic, p_value = stats.levene(control_values, treatment_values)

        passed = p_value > self.alpha

        control_var = np.var(control_values, ddof=1)
        treatment_var = np.var(treatment_values, ddof=1)
        variance_ratio = max(control_var, treatment_var) / min(control_var, treatment_var) if min(control_var, treatment_var) > 0 else np.inf

        return DiagnosticResult(
            check_name="Variance Homogeneity",
            passed=passed,
            severity='warning' if not passed else 'info',
            message=f"{'✅ PASS' if passed else '⚠️ WARNING'}: Variance homogeneity (p={p_value:.4f})",
            details={
                'platform': platform_name,
                'control_variance': control_var,
                'treatment_variance': treatment_var,
                'variance_ratio': variance_ratio,
                'levene_statistic': statistic,
                'p_value': p_value
            },
            recommendation=(
                "✓ Variances are homogeneous." if passed else
                f"⚠️ Variances differ significantly (ratio: {variance_ratio:.2f}x). "
                "Consider using Welch's t-test instead of Student's t-test, or "
                "investigate if different user segments are affecting one variant more."
            )
        )

    def check_normality(self, platform_name: str, sample_size: int = 5000) -> DiagnosticResult:
        """
        Check if metric distributions are approximately normal.

        Uses Shapiro-Wilk test on a sample for computational efficiency.

        Args:
            platform_name: Platform to check
            sample_size: Max samples to test (for performance)

        Returns:
            DiagnosticResult with normality check
        """
        data = self.platforms[platform_name]
        control_values = data['control'][data['metric_column']].dropna()
        treatment_values = data['treatment'][data['metric_column']].dropna()

        # Sample for performance if dataset is large
        if len(control_values) > sample_size:
            control_sample = control_values.sample(n=sample_size, random_state=42)
        else:
            control_sample = control_values

        if len(treatment_values) > sample_size:
            treatment_sample = treatment_values.sample(n=sample_size, random_state=42)
        else:
            treatment_sample = treatment_values

        # Shapiro-Wilk test
        _, p_control = stats.shapiro(control_sample)
        _, p_treatment = stats.shapiro(treatment_sample)

        passed = p_control > self.alpha and p_treatment > self.alpha

        # Calculate skewness and kurtosis as additional indicators
        control_skew = stats.skew(control_values)
        treatment_skew = stats.skew(treatment_values)
        control_kurt = stats.kurtosis(control_values)
        treatment_kurt = stats.kurtosis(treatment_values)

        return DiagnosticResult(
            check_name="Normality Test",
            passed=passed,
            severity='info',  # Not critical due to CLT
            message=f"{'✅ PASS' if passed else 'ℹ️ INFO'}: Normality check",
            details={
                'platform': platform_name,
                'control_p_value': p_control,
                'treatment_p_value': p_treatment,
                'control_skewness': control_skew,
                'treatment_skewness': treatment_skew,
                'control_kurtosis': control_kurt,
                'treatment_kurtosis': treatment_kurt
            },
            recommendation=(
                "✓ Distributions are approximately normal." if passed else
                f"ℹ️ Distributions may not be normal (skew: C={control_skew:.2f}, T={treatment_skew:.2f}). "
                "With large samples, t-test is still valid due to Central Limit Theorem. "
                "For small samples or extreme skew, consider non-parametric tests (Mann-Whitney U) "
                "or transformation (log, sqrt)."
            )
        )

    def check_outliers(self, platform_name: str, iqr_multiplier: float = 3.0) -> DiagnosticResult:
        """
        Detect outliers that could skew results.

        Uses IQR method to identify extreme values.

        Args:
            platform_name: Platform to check
            iqr_multiplier: Multiplier for IQR to define outliers (3.0 for extreme outliers)

        Returns:
            DiagnosticResult with outlier analysis
        """
        data = self.platforms[platform_name]
        control_values = data['control'][data['metric_column']].dropna()
        treatment_values = data['treatment'][data['metric_column']].dropna()

        def find_outliers(values):
            q1 = values.quantile(0.25)
            q3 = values.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - iqr_multiplier * iqr
            upper_bound = q3 + iqr_multiplier * iqr
            outliers = values[(values < lower_bound) | (values > upper_bound)]
            return outliers, lower_bound, upper_bound

        control_outliers, c_lower, c_upper = find_outliers(control_values)
        treatment_outliers, t_lower, t_upper = find_outliers(treatment_values)

        control_outlier_pct = len(control_outliers) / len(control_values) * 100
        treatment_outlier_pct = len(treatment_outliers) / len(treatment_values) * 100

        # Consider it a warning if >5% are outliers
        passed = control_outlier_pct < 5 and treatment_outlier_pct < 5

        return DiagnosticResult(
            check_name="Outlier Detection",
            passed=passed,
            severity='warning' if not passed else 'info',
            message=f"{'✅ PASS' if passed else '⚠️ WARNING'}: Outlier check",
            details={
                'platform': platform_name,
                'control_outlier_count': len(control_outliers),
                'control_outlier_percentage': control_outlier_pct,
                'treatment_outlier_count': len(treatment_outliers),
                'treatment_outlier_percentage': treatment_outlier_pct,
                'control_bounds': (c_lower, c_upper),
                'treatment_bounds': (t_lower, t_upper)
            },
            recommendation=(
                f"✓ Outlier levels acceptable (C: {control_outlier_pct:.1f}%, T: {treatment_outlier_pct:.1f}%)." if passed else
                f"⚠️ High outlier rate detected (C: {control_outlier_pct:.1f}%, T: {treatment_outlier_pct:.1f}%). "
                "Investigate: 1) Data quality issues, 2) Bot traffic, 3) Legitimate extreme users. "
                "Consider winsorization, trimming, or robust statistics."
            )
        )

    def check_duplicate_users(self, platform_name: str) -> DiagnosticResult:
        """
        Check for duplicate user IDs which indicate tracking problems.

        Args:
            platform_name: Platform to check

        Returns:
            DiagnosticResult with duplicate user analysis
        """
        data = self.platforms[platform_name]
        user_col = data['user_id_column']

        control_users = data['control'][user_col]
        treatment_users = data['treatment'][user_col]

        # Check for duplicates within groups
        control_dups = control_users.duplicated().sum()
        treatment_dups = treatment_users.duplicated().sum()

        # Check for cross-contamination (users in both groups)
        control_set = set(control_users)
        treatment_set = set(treatment_users)
        cross_contamination = len(control_set & treatment_set)

        total_issues = control_dups + treatment_dups + cross_contamination
        passed = total_issues == 0

        return DiagnosticResult(
            check_name="Duplicate Users",
            passed=passed,
            severity='critical' if cross_contamination > 0 else 'warning' if not passed else 'info',
            message=f"{'✅ PASS' if passed else '❌ FAIL' if cross_contamination > 0 else '⚠️ WARNING'}: User uniqueness check",
            details={
                'platform': platform_name,
                'control_duplicates': control_dups,
                'treatment_duplicates': treatment_dups,
                'cross_contamination': cross_contamination,
                'total_unique_users': len(control_set | treatment_set)
            },
            recommendation=(
                "✓ All users are unique and properly assigned." if passed else
                f"❌ Critical: {cross_contamination} users appear in both groups! " if cross_contamination > 0 else "" +
                f"⚠️ Found duplicate users (C: {control_dups}, T: {treatment_dups}). "
                "Check: 1) User ID generation, 2) Data deduplication logic, "
                "3) Multiple sessions being counted as separate users."
            )
        )

    def check_bot_patterns(self, platform_name: str, high_frequency_threshold: int = 100) -> DiagnosticResult:
        """
        Detect potential bot traffic based on usage patterns.

        Looks for users with suspiciously high event counts.

        Args:
            platform_name: Platform to check
            high_frequency_threshold: Events per user that trigger bot flag

        Returns:
            DiagnosticResult with bot detection analysis
        """
        data = self.platforms[platform_name]
        user_col = data['user_id_column']

        # Count events per user
        control_user_counts = data['control'][user_col].value_counts()
        treatment_user_counts = data['treatment'][user_col].value_counts()

        # Identify high-frequency users
        control_bots = (control_user_counts > high_frequency_threshold).sum()
        treatment_bots = (treatment_user_counts > high_frequency_threshold).sum()

        control_bot_pct = control_bots / len(control_user_counts) * 100 if len(control_user_counts) > 0 else 0
        treatment_bot_pct = treatment_bots / len(treatment_user_counts) * 100 if len(treatment_user_counts) > 0 else 0

        # Consider it a warning if >2% are potential bots
        passed = control_bot_pct < 2 and treatment_bot_pct < 2

        return DiagnosticResult(
            check_name="Bot Pattern Detection",
            passed=passed,
            severity='warning' if not passed else 'info',
            message=f"{'✅ PASS' if passed else '⚠️ WARNING'}: Bot detection check",
            details={
                'platform': platform_name,
                'control_potential_bots': control_bots,
                'control_bot_percentage': control_bot_pct,
                'treatment_potential_bots': treatment_bots,
                'treatment_bot_percentage': treatment_bot_pct,
                'high_frequency_threshold': high_frequency_threshold
            },
            recommendation=(
                f"✓ Bot traffic appears minimal (C: {control_bot_pct:.1f}%, T: {treatment_bot_pct:.1f}%)." if passed else
                f"⚠️ High-frequency users detected (C: {control_bot_pct:.1f}%, T: {treatment_bot_pct:.1f}%). "
                "Investigate: 1) User agent strings, 2) IP patterns, 3) Behavioral signatures. "
                "Consider implementing bot filtering or using a bot detection service."
            )
        )

    def check_temporal_consistency(self, platform_name: str) -> DiagnosticResult:
        """
        Check if metric values are consistent over time (no data pipeline issues).

        Requires timestamp_column to be set.

        Args:
            platform_name: Platform to check

        Returns:
            DiagnosticResult with temporal consistency analysis
        """
        data = self.platforms[platform_name]
        ts_col = data['timestamp_column']

        if ts_col is None:
            return DiagnosticResult(
                check_name="Temporal Consistency",
                passed=True,
                severity='info',
                message="ℹ️ SKIPPED: No timestamp column provided",
                details={'platform': platform_name},
                recommendation="Provide timestamp_column to enable temporal consistency checks."
            )

        metric_col = data['metric_column']

        # Ensure timestamps are datetime
        control_data = data['control'].copy()
        treatment_data = data['treatment'].copy()

        if not pd.api.types.is_datetime64_any_dtype(control_data[ts_col]):
            control_data[ts_col] = pd.to_datetime(control_data[ts_col])
            treatment_data[ts_col] = pd.to_datetime(treatment_data[ts_col])

        # Group by day and check for anomalies
        control_daily = control_data.groupby(control_data[ts_col].dt.date)[metric_col].agg(['mean', 'count'])
        treatment_daily = treatment_data.groupby(treatment_data[ts_col].dt.date)[metric_col].agg(['mean', 'count'])

        # Check for days with zero data
        control_zero_days = (control_daily['count'] == 0).sum()
        treatment_zero_days = (treatment_daily['count'] == 0).sum()

        # Check coefficient of variation in daily means (high CV suggests instability)
        control_cv = control_daily['mean'].std() / control_daily['mean'].mean() if control_daily['mean'].mean() > 0 else 0
        treatment_cv = treatment_daily['mean'].std() / treatment_daily['mean'].mean() if treatment_daily['mean'].mean() > 0 else 0

        passed = control_zero_days == 0 and treatment_zero_days == 0 and control_cv < 0.5 and treatment_cv < 0.5

        return DiagnosticResult(
            check_name="Temporal Consistency",
            passed=passed,
            severity='warning' if not passed else 'info',
            message=f"{'✅ PASS' if passed else '⚠️ WARNING'}: Temporal consistency check",
            details={
                'platform': platform_name,
                'control_zero_days': control_zero_days,
                'treatment_zero_days': treatment_zero_days,
                'control_cv': control_cv,
                'treatment_cv': treatment_cv,
                'days_analyzed': len(control_daily)
            },
            recommendation=(
                "✓ Metrics are temporally consistent." if passed else
                f"⚠️ Temporal inconsistencies detected (CV: C={control_cv:.2f}, T={treatment_cv:.2f}). "
                "Check: 1) Data pipeline outages, 2) Weekend/weekday effects, 3) Marketing campaigns, "
                "4) Release timing issues."
            )
        )

    def run_all_diagnostics(
        self,
        platform_name: str,
        expected_ratio: Tuple[float, float] = (0.5, 0.5),
        mde: float = 0.01
    ) -> List[DiagnosticResult]:
        """
        Run all diagnostic checks for a platform.

        Args:
            platform_name: Platform to analyze
            expected_ratio: Expected control/treatment ratio
            mde: Minimum detectable effect (relative change)

        Returns:
            List of DiagnosticResult objects
        """
        if platform_name not in self.platforms:
            raise ValueError(f"Platform '{platform_name}' not loaded. Use load_platform_data() first.")

        results = []

        # Critical checks
        results.append(self.check_sample_ratio_mismatch(platform_name, expected_ratio))
        results.append(self.check_duplicate_users(platform_name))

        # Statistical validity checks
        results.append(self.check_minimum_sample_size(platform_name, mde))
        results.append(self.check_variance_homogeneity(platform_name))
        results.append(self.check_normality(platform_name))

        # Data quality checks
        results.append(self.check_outliers(platform_name))
        results.append(self.check_bot_patterns(platform_name))
        results.append(self.check_temporal_consistency(platform_name))

        self.results.extend(results)
        return results

    def get_summary(self, platforms: Optional[List[str]] = None) -> str:
        """
        Get a formatted summary of all diagnostic results.

        Args:
            platforms: List of platforms to include (None = all)

        Returns:
            Formatted summary string
        """
        if platforms is None:
            platforms = list(self.platforms.keys())

        summary_lines = [
            "=" * 80,
            "A/B TEST DIAGNOSTIC SUMMARY",
            "=" * 80,
            ""
        ]

        for platform in platforms:
            platform_results = [r for r in self.results if r.details.get('platform') == platform]

            if not platform_results:
                continue

            summary_lines.append(f"\n📱 Platform: {platform.upper()}")
            summary_lines.append("-" * 80)

            critical_fails = [r for r in platform_results if r.severity == 'critical' and not r.passed]
            warnings = [r for r in platform_results if r.severity == 'warning' and not r.passed]
            passes = [r for r in platform_results if r.passed]

            summary_lines.append(f"Status: {len(passes)}/{len(platform_results)} checks passed")
            if critical_fails:
                summary_lines.append(f"❌ {len(critical_fails)} CRITICAL ISSUES")
            if warnings:
                summary_lines.append(f"⚠️  {len(warnings)} warnings")

            summary_lines.append("")

            for result in platform_results:
                summary_lines.append(f"{result.message}")
                if not result.passed or result.severity == 'critical':
                    summary_lines.append(f"   {result.recommendation}")
                    summary_lines.append("")

        return "\n".join(summary_lines)
