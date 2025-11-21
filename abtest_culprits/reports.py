"""
Report generation for A/B test diagnostics.
"""

from typing import List, Dict, Optional
from .diagnostics import DiagnosticResult
from .analyzer import PlatformResult, CrossPlatformAnalyzer
import json


class DiagnosticReport:
    """
    Generates formatted reports from diagnostic results.
    """

    @staticmethod
    def generate_html_report(
        platform_results: Dict[str, List[DiagnosticResult]],
        analyzer: Optional[CrossPlatformAnalyzer] = None
    ) -> str:
        """
        Generate an HTML report for easy viewing.

        Args:
            platform_results: Dictionary mapping platform names to diagnostic results
            analyzer: Optional cross-platform analyzer for comparison data

        Returns:
            HTML string
        """
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>A/B Test Diagnostic Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .platform { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .check { margin: 15px 0; padding: 15px; border-left: 4px solid #ccc; background: #f9f9f9; }
        .check.passed { border-left-color: #27ae60; }
        .check.warning { border-left-color: #f39c12; background: #fef5e7; }
        .check.critical { border-left-color: #e74c3c; background: #fadbd8; }
        .check-name { font-weight: bold; font-size: 1.1em; margin-bottom: 5px; }
        .check-message { margin: 5px 0; }
        .recommendation { margin-top: 10px; padding: 10px; background: white; border-radius: 4px; font-size: 0.95em; }
        .details { font-size: 0.85em; color: #666; margin-top: 8px; }
        .summary { background: #ecf0f1; padding: 15px; border-radius: 8px; margin: 20px 0; }
        .comparison-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .comparison-table th, .comparison-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        .comparison-table th { background: #3498db; color: white; }
        .comparison-table tr:hover { background: #f5f5f5; }
    </style>
</head>
<body>
    <h1>🔬 A/B Test Diagnostic Report</h1>
"""

        # Overall summary
        total_checks = sum(len(results) for results in platform_results.values())
        total_passed = sum(sum(1 for r in results if r.passed) for results in platform_results.values())
        total_critical = sum(sum(1 for r in results if r.severity == 'critical' and not r.passed) for results in platform_results.values())
        total_warnings = sum(sum(1 for r in results if r.severity == 'warning' and not r.passed) for results in platform_results.values())

        html += f"""
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Checks:</strong> {total_checks}</p>
        <p><strong>Passed:</strong> {total_passed} ✅</p>
        <p><strong>Critical Issues:</strong> {total_critical} ❌</p>
        <p><strong>Warnings:</strong> {total_warnings} ⚠️</p>
    </div>
"""

        # Cross-platform comparison
        if analyzer and len(analyzer.platform_results) > 1:
            html += "<h2>📊 Cross-Platform Comparison</h2>"
            df = analyzer.compare_lift_across_platforms()
            html += '<table class="comparison-table">'
            html += '<tr><th>Platform</th><th>Lift %</th><th>P-Value</th><th>Significant</th><th>Sample Size (C/T)</th></tr>'
            for _, row in df.iterrows():
                html += f"""
                <tr>
                    <td>{row['platform']}</td>
                    <td>{row['lift_pct']:.2f}%</td>
                    <td>{row['p_value']:.4f}</td>
                    <td>{row['significant']}</td>
                    <td>{row['control_n']:,} / {row['treatment_n']:,}</td>
                </tr>
                """
            html += '</table>'

            # Homogeneity test
            is_homogeneous, p_value, interpretation = analyzer.test_homogeneity_of_effects()
            html += f'<div class="check {"passed" if is_homogeneous else "warning"}">'
            html += f'<div class="check-name">Homogeneity Test</div>'
            html += f'<div class="check-message">{interpretation}</div>'
            html += '</div>'

        # Platform-specific results
        for platform_name, results in platform_results.items():
            html += f'<div class="platform">'
            html += f'<h2>📱 {platform_name.upper()}</h2>'

            passed = sum(1 for r in results if r.passed)
            html += f'<p><strong>Status:</strong> {passed}/{len(results)} checks passed</p>'

            for result in results:
                severity_class = 'passed' if result.passed else result.severity
                html += f'<div class="check {severity_class}">'
                html += f'<div class="check-name">{result.check_name}</div>'
                html += f'<div class="check-message">{result.message}</div>'

                if result.recommendation:
                    html += f'<div class="recommendation">{result.recommendation}</div>'

                # Add key details
                if result.details:
                    details_str = " | ".join([
                        f"{k}: {v:.4f}" if isinstance(v, float) and k != 'platform' else f"{k}: {v}"
                        for k, v in result.details.items()
                        if k != 'platform' and k not in ['control_bounds', 'treatment_bounds']
                    ])
                    html += f'<div class="details">{details_str}</div>'

                html += '</div>'

            html += '</div>'

        html += """
</body>
</html>
"""
        return html

    @staticmethod
    def generate_json_report(
        platform_results: Dict[str, List[DiagnosticResult]],
        analyzer: Optional[CrossPlatformAnalyzer] = None
    ) -> str:
        """
        Generate a JSON report for programmatic consumption.

        Args:
            platform_results: Dictionary mapping platform names to diagnostic results
            analyzer: Optional cross-platform analyzer

        Returns:
            JSON string
        """
        report = {
            'summary': {},
            'platforms': {},
            'cross_platform_analysis': {}
        }

        # Summary
        total_checks = sum(len(results) for results in platform_results.values())
        total_passed = sum(sum(1 for r in results if r.passed) for results in platform_results.values())
        total_critical = sum(sum(1 for r in results if r.severity == 'critical' and not r.passed) for results in platform_results.values())

        report['summary'] = {
            'total_checks': total_checks,
            'total_passed': total_passed,
            'total_critical': total_critical,
            'pass_rate': total_passed / total_checks if total_checks > 0 else 0
        }

        # Platform results
        for platform_name, results in platform_results.items():
            report['platforms'][platform_name] = {
                'checks': [
                    {
                        'check_name': r.check_name,
                        'passed': r.passed,
                        'severity': r.severity,
                        'message': r.message,
                        'details': r.details,
                        'recommendation': r.recommendation
                    }
                    for r in results
                ],
                'summary': {
                    'total': len(results),
                    'passed': sum(1 for r in results if r.passed),
                    'critical_failures': sum(1 for r in results if r.severity == 'critical' and not r.passed)
                }
            }

        # Cross-platform analysis
        if analyzer and len(analyzer.platform_results) > 1:
            is_homogeneous, p_value, _ = analyzer.test_homogeneity_of_effects()
            culprits = analyzer.identify_likely_culprits()

            report['cross_platform_analysis'] = {
                'homogeneity_test': {
                    'is_homogeneous': is_homogeneous,
                    'p_value': p_value
                },
                'platform_comparisons': {
                    name: {
                        'lift_pct': result.lift,
                        'p_value': result.p_value,
                        'significant': result.statistically_significant,
                        'sample_size': {'control': result.control_n, 'treatment': result.treatment_n}
                    }
                    for name, result in analyzer.platform_results.items()
                },
                'identified_culprits': culprits
            }

        return json.dumps(report, indent=2)

    @staticmethod
    def generate_markdown_report(
        platform_results: Dict[str, List[DiagnosticResult]],
        analyzer: Optional[CrossPlatformAnalyzer] = None
    ) -> str:
        """
        Generate a Markdown report.

        Args:
            platform_results: Dictionary mapping platform names to diagnostic results
            analyzer: Optional cross-platform analyzer

        Returns:
            Markdown string
        """
        lines = [
            "# A/B Test Diagnostic Report",
            "",
            "## Summary",
            ""
        ]

        total_checks = sum(len(results) for results in platform_results.values())
        total_passed = sum(sum(1 for r in results if r.passed) for results in platform_results.values())
        total_critical = sum(sum(1 for r in results if r.severity == 'critical' and not r.passed) for results in platform_results.values())
        total_warnings = sum(sum(1 for r in results if r.severity == 'warning' and not r.passed) for results in platform_results.values())

        lines.extend([
            f"- **Total Checks:** {total_checks}",
            f"- **Passed:** {total_passed} ✅",
            f"- **Critical Issues:** {total_critical} ❌",
            f"- **Warnings:** {total_warnings} ⚠️",
            ""
        ])

        # Cross-platform comparison
        if analyzer and len(analyzer.platform_results) > 1:
            lines.extend([
                "## Cross-Platform Comparison",
                ""
            ])

            df = analyzer.compare_lift_across_platforms()
            lines.append("| Platform | Lift % | P-Value | Significant | Sample Size (C/T) |")
            lines.append("|----------|--------|---------|-------------|-------------------|")
            for _, row in df.iterrows():
                lines.append(
                    f"| {row['platform']} | {row['lift_pct']:.2f}% | {row['p_value']:.4f} | "
                    f"{row['significant']} | {row['control_n']:,} / {row['treatment_n']:,} |"
                )
            lines.append("")

            # Homogeneity test
            is_homogeneous, p_value, interpretation = analyzer.test_homogeneity_of_effects()
            lines.extend([
                "### Homogeneity Test",
                "",
                interpretation,
                ""
            ])

            # Culprits
            culprits = analyzer.identify_likely_culprits()
            has_culprits = any(len(issues) > 0 for issues in culprits.values())

            if has_culprits:
                lines.extend([
                    "### Identified Issues",
                    ""
                ])

                for category, issues in culprits.items():
                    if issues:
                        lines.append(f"#### {category.replace('_', ' ').title()}")
                        for issue in issues:
                            lines.append(f"- {issue}")
                        lines.append("")

        # Platform-specific results
        for platform_name, results in platform_results.items():
            lines.extend([
                f"## Platform: {platform_name.upper()}",
                ""
            ])

            passed = sum(1 for r in results if r.passed)
            lines.append(f"**Status:** {passed}/{len(results)} checks passed")
            lines.append("")

            for result in results:
                icon = '✅' if result.passed else ('❌' if result.severity == 'critical' else '⚠️')
                lines.extend([
                    f"### {icon} {result.check_name}",
                    "",
                    result.message,
                    ""
                ])

                if result.recommendation:
                    lines.extend([
                        f"**Recommendation:** {result.recommendation}",
                        ""
                    ])

        return "\n".join(lines)
