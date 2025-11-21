"""
Cross-platform A/B test analyzer.

Compares test results across multiple platforms to identify discrepancies
and potential root causes.
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import warnings


@dataclass
class PlatformResult:
    """A/B test results for a single platform."""
    platform_name: str
    control_mean: float
    treatment_mean: float
    control_std: float
    treatment_std: float
    control_n: int
    treatment_n: int
    lift: float  # Relative lift (%)
    absolute_diff: float
    p_value: float
    confidence_interval: Tuple[float, float]
    statistically_significant: bool


class CrossPlatformAnalyzer:
    """
    Analyzes A/B test results across multiple platforms to identify discrepancies.

    This class helps answer: "Why are my results different across platforms?"
    """

    def __init__(self, alpha: float = 0.05):
        """
        Initialize cross-platform analyzer.

        Args:
            alpha: Significance level (default: 0.05)
        """
        self.alpha = alpha
        self.platform_results: Dict[str, PlatformResult] = {}

    def calculate_platform_result(
        self,
        platform_name: str,
        control_data: pd.Series,
        treatment_data: pd.Series,
        use_welch: bool = True
    ) -> PlatformResult:
        """
        Calculate A/B test results for a single platform.

        Args:
            platform_name: Name of the platform
            control_data: Control group metric values
            treatment_data: Treatment group metric values
            use_welch: Use Welch's t-test (doesn't assume equal variance)

        Returns:
            PlatformResult with test statistics
        """
        # Clean data
        control_data = control_data.dropna()
        treatment_data = treatment_data.dropna()

        # Basic statistics
        control_mean = control_data.mean()
        treatment_mean = treatment_data.mean()
        control_std = control_data.std(ddof=1)
        treatment_std = treatment_data.std(ddof=1)
        control_n = len(control_data)
        treatment_n = len(treatment_data)

        # Calculate lift
        absolute_diff = treatment_mean - control_mean
        lift = (absolute_diff / control_mean * 100) if control_mean != 0 else np.inf

        # Statistical test
        if use_welch:
            t_stat, p_value = stats.ttest_ind(treatment_data, control_data, equal_var=False)
        else:
            t_stat, p_value = stats.ttest_ind(treatment_data, control_data, equal_var=True)

        # Confidence interval for the difference
        if use_welch:
            # Welch-Satterthwaite degrees of freedom
            dof = (
                (control_std**2 / control_n + treatment_std**2 / treatment_n)**2 /
                (
                    (control_std**2 / control_n)**2 / (control_n - 1) +
                    (treatment_std**2 / treatment_n)**2 / (treatment_n - 1)
                )
            )
        else:
            dof = control_n + treatment_n - 2

        se_diff = np.sqrt(control_std**2 / control_n + treatment_std**2 / treatment_n)
        t_critical = stats.t.ppf(1 - self.alpha / 2, dof)
        ci_lower = absolute_diff - t_critical * se_diff
        ci_upper = absolute_diff + t_critical * se_diff

        result = PlatformResult(
            platform_name=platform_name,
            control_mean=control_mean,
            treatment_mean=treatment_mean,
            control_std=control_std,
            treatment_std=treatment_std,
            control_n=control_n,
            treatment_n=treatment_n,
            lift=lift,
            absolute_diff=absolute_diff,
            p_value=p_value,
            confidence_interval=(ci_lower, ci_upper),
            statistically_significant=p_value < self.alpha
        )

        self.platform_results[platform_name] = result
        return result

    def compare_lift_across_platforms(self) -> pd.DataFrame:
        """
        Compare relative lift across all platforms.

        Returns:
            DataFrame with lift comparison and rankings
        """
        data = []
        for name, result in self.platform_results.items():
            data.append({
                'platform': name,
                'lift_pct': result.lift,
                'p_value': result.p_value,
                'significant': '✅' if result.statistically_significant else '❌',
                'control_mean': result.control_mean,
                'treatment_mean': result.treatment_mean,
                'control_n': result.control_n,
                'treatment_n': result.treatment_n
            })

        df = pd.DataFrame(data)
        df = df.sort_values('lift_pct', ascending=False)
        return df

    def detect_inconsistent_platforms(self, lift_threshold: float = 5.0) -> List[str]:
        """
        Identify platforms with suspiciously different results.

        Args:
            lift_threshold: Minimum absolute difference in lift % to flag (default: 5%)

        Returns:
            List of platform names with inconsistent results
        """
        if len(self.platform_results) < 2:
            return []

        lifts = [r.lift for r in self.platform_results.values()]
        median_lift = np.median(lifts)

        inconsistent = []
        for name, result in self.platform_results.items():
            if abs(result.lift - median_lift) > lift_threshold:
                inconsistent.append(name)

        return inconsistent

    def test_homogeneity_of_effects(self) -> Tuple[bool, float, str]:
        """
        Test if treatment effects are homogeneous across platforms.

        Uses Cochran's Q test for binary outcomes or chi-square test for
        heterogeneity of effects.

        Returns:
            Tuple of (is_homogeneous, p_value, interpretation)
        """
        if len(self.platform_results) < 2:
            return True, 1.0, "Not enough platforms to test homogeneity"

        # Extract effect sizes and variances
        effects = []
        variances = []
        sample_sizes = []

        for result in self.platform_results.values():
            effects.append(result.absolute_diff)

            # Variance of the difference
            var_diff = (
                result.control_std**2 / result.control_n +
                result.treatment_std**2 / result.treatment_n
            )
            variances.append(var_diff)
            sample_sizes.append(min(result.control_n, result.treatment_n))

        effects = np.array(effects)
        variances = np.array(variances)
        weights = 1 / variances

        # Weighted mean effect
        weighted_mean = np.sum(weights * effects) / np.sum(weights)

        # Q statistic (heterogeneity test)
        Q = np.sum(weights * (effects - weighted_mean)**2)
        df = len(effects) - 1
        p_value = 1 - stats.chi2.cdf(Q, df)

        is_homogeneous = p_value > self.alpha

        interpretation = (
            f"✅ Effects are homogeneous across platforms (Q={Q:.2f}, p={p_value:.4f})"
            if is_homogeneous else
            f"⚠️ Significant heterogeneity detected (Q={Q:.2f}, p={p_value:.4f}). "
            f"Different platforms show different treatment effects. Investigate platform-specific issues."
        )

        return is_homogeneous, p_value, interpretation

    def identify_likely_culprits(self) -> Dict[str, List[str]]:
        """
        Identify likely causes of cross-platform discrepancies.

        Returns:
            Dictionary mapping culprit categories to specific issues found
        """
        culprits = {
            'sample_size': [],
            'variance': [],
            'effect_direction': [],
            'significance_mismatch': []
        }

        if len(self.platform_results) < 2:
            return culprits

        # Get reference values (median or most reliable platform)
        lifts = [r.lift for r in self.platform_results.values()]
        median_lift = np.median(lifts)
        sample_sizes = [min(r.control_n, r.treatment_n) for r in self.platform_results.values()]
        median_sample_size = np.median(sample_sizes)

        for name, result in self.platform_results.items():
            min_n = min(result.control_n, result.treatment_n)

            # Sample size issues
            if min_n < median_sample_size * 0.5:
                culprits['sample_size'].append(
                    f"{name}: Small sample size ({min_n:,} vs median {int(median_sample_size):,})"
                )

            # Variance issues
            variance_ratio = max(result.control_std, result.treatment_std) / min(result.control_std, result.treatment_std) if min(result.control_std, result.treatment_std) > 0 else np.inf
            if variance_ratio > 3:
                culprits['variance'].append(
                    f"{name}: High variance ratio ({variance_ratio:.2f}x)"
                )

            # Effect direction issues
            if np.sign(result.lift) != np.sign(median_lift) and abs(result.lift) > 1:
                culprits['effect_direction'].append(
                    f"{name}: Opposite effect direction (lift: {result.lift:.2f}% vs median {median_lift:.2f}%)"
                )

            # Significance mismatch
            # Count how many platforms are significant
            sig_count = sum(r.statistically_significant for r in self.platform_results.values())
            is_majority_sig = sig_count > len(self.platform_results) / 2

            if result.statistically_significant != is_majority_sig:
                culprits['significance_mismatch'].append(
                    f"{name}: {'Significant' if result.statistically_significant else 'Not significant'} "
                    f"while majority is {'significant' if is_majority_sig else 'not significant'} "
                    f"(p={result.p_value:.4f})"
                )

        return culprits

    def generate_comparison_report(self) -> str:
        """
        Generate a comprehensive cross-platform comparison report.

        Returns:
            Formatted report string
        """
        lines = [
            "=" * 80,
            "CROSS-PLATFORM A/B TEST COMPARISON",
            "=" * 80,
            ""
        ]

        # Summary table
        df = self.compare_lift_across_platforms()
        lines.append("📊 RESULTS SUMMARY")
        lines.append("-" * 80)
        lines.append(df.to_string(index=False))
        lines.append("")

        # Homogeneity test
        is_homogeneous, p_value, interpretation = self.test_homogeneity_of_effects()
        lines.append("🔬 HOMOGENEITY TEST")
        lines.append("-" * 80)
        lines.append(interpretation)
        lines.append("")

        # Inconsistent platforms
        inconsistent = self.detect_inconsistent_platforms()
        if inconsistent:
            lines.append("⚠️ INCONSISTENT PLATFORMS")
            lines.append("-" * 80)
            for platform in inconsistent:
                result = self.platform_results[platform]
                lines.append(f"  • {platform}: {result.lift:.2f}% lift (p={result.p_value:.4f})")
            lines.append("")

        # Likely culprits
        culprits = self.identify_likely_culprits()
        has_culprits = any(len(issues) > 0 for issues in culprits.values())

        if has_culprits:
            lines.append("🔍 LIKELY CULPRITS")
            lines.append("-" * 80)

            if culprits['sample_size']:
                lines.append("\n📏 Sample Size Issues:")
                for issue in culprits['sample_size']:
                    lines.append(f"  • {issue}")

            if culprits['variance']:
                lines.append("\n📊 Variance Issues:")
                for issue in culprits['variance']:
                    lines.append(f"  • {issue}")

            if culprits['effect_direction']:
                lines.append("\n🔄 Effect Direction Issues:")
                for issue in culprits['effect_direction']:
                    lines.append(f"  • {issue}")

            if culprits['significance_mismatch']:
                lines.append("\n⚡ Statistical Significance Mismatches:")
                for issue in culprits['significance_mismatch']:
                    lines.append(f"  • {issue}")

            lines.append("")

        # Recommendations
        lines.append("💡 RECOMMENDATIONS")
        lines.append("-" * 80)

        if not is_homogeneous:
            lines.append("1. Run platform-specific diagnostics to identify root causes")
            lines.append("2. Check for differences in:")
            lines.append("   - Randomization implementation")
            lines.append("   - Metric instrumentation")
            lines.append("   - User populations")
            lines.append("   - Feature implementation")

        if culprits['sample_size']:
            lines.append("3. Increase sample size for platforms with insufficient data")

        if culprits['variance']:
            lines.append("4. Investigate high-variance platforms for:")
            lines.append("   - Bot traffic")
            lines.append("   - Outliers")
            lines.append("   - Heterogeneous user segments")

        if culprits['effect_direction']:
            lines.append("5. CRITICAL: Opposite effects detected - investigate immediately:")
            lines.append("   - Feature implementation bugs")
            lines.append("   - Metric calculation errors")
            lines.append("   - Incorrect variant assignment")

        lines.append("")
        return "\n".join(lines)

    def recommend_statistical_test(self) -> str:
        """
        Recommend appropriate statistical test based on data characteristics.

        Returns:
            Recommendation string
        """
        recommendations = []

        for name, result in self.platform_results.items():
            variance_ratio = max(result.control_std, result.treatment_std) / min(result.control_std, result.treatment_std) if min(result.control_std, result.treatment_std) > 0 else np.inf

            if variance_ratio > 2:
                recommendations.append(
                    f"• {name}: Use Welch's t-test (unequal variances, ratio: {variance_ratio:.2f}x)"
                )
            elif min(result.control_n, result.treatment_n) < 30:
                recommendations.append(
                    f"• {name}: Consider Mann-Whitney U test (small sample size: {min(result.control_n, result.treatment_n)})"
                )
            else:
                recommendations.append(
                    f"• {name}: Standard t-test is appropriate"
                )

        return "\n".join(recommendations)
