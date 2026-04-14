#!/usr/bin/env python3
"""
Report Generator Module
Generates comprehensive reports from red teaming results.

Supports three output formats:
  - JSON  (machine-readable, default)
  - TXT   (plain text, executive-summary style)
  - MD    (Markdown with tables, badges, and CVSS-like risk scores)
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from colorama import Fore, Style


class ReportGenerator:
    """Generate reports from red teaming results."""

    # CVSS-like severity scale for LLM red teaming
    SEVERITY_SCALE = {
        'critical': {'min_rate': 50, 'cvss_range': '9.0-10.0', 'color': 'red'},
        'high':     {'min_rate': 30, 'cvss_range': '7.0-8.9',  'color': 'orange'},
        'medium':   {'min_rate': 10, 'cvss_range': '4.0-6.9',  'color': 'yellow'},
        'low':      {'min_rate': 0,  'cvss_range': '0.1-3.9',  'color': 'green'},
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_dir = config.get('output_dir', 'reports')
        self.format = config.get('format', 'json')
        self.include_responses = config.get('include_responses', True)
        self.severity_threshold = config.get('severity_threshold', 'medium')

        os.makedirs(self.output_dir, exist_ok=True)

    def generate_report(self, results: List[tuple], output_path: str = None,
                        verbose: bool = False,
                        llm_stats: Optional[Dict[str, Any]] = None) -> str:
        """Generate comprehensive report from results."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        report_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'report_version': '3.0',
                'generator': 'Adversarial LLM Red Teaming Framework',
            },
            'summary': self._generate_summary(results),
            'modules': {},
            'findings': self._extract_findings(results),
            'recommendations': self._generate_recommendations(results),
        }

        if llm_stats:
            report_data['metadata']['llm_stats'] = llm_stats

        for module_name, module_results in results:
            report_data['modules'][module_name] = {
                'summary': module_results.get('summary', {}),
                'intensity': module_results.get('intensity', 'unknown'),
                'attacks': module_results.get('attacks', []),
            }

        if not output_path:
            ext = {'json': '.json', 'txt': '.txt', 'md': '.md', 'markdown': '.md'}
            suffix = ext.get(self.format, '.json')
            output_path = os.path.join(self.output_dir, f"llm_redteam_report_{timestamp}{suffix}")

        writers = {
            'json': self._write_json_report,
            'txt': self._write_text_report,
            'md': self._write_markdown_report,
            'markdown': self._write_markdown_report,
        }
        writer = writers.get(self.format, self._write_json_report)
        writer(report_data, output_path, verbose)

        return output_path
    
    def _generate_summary(self, results: List[tuple]) -> Dict[str, Any]:
        """Generate overall summary"""
        total_attacks = 0
        total_successful = 0
        total_failed = 0
        
        module_summaries = {}
        
        for module_name, module_results in results:
            summary = module_results.get('summary', {})
            module_total = summary.get('total', 0)
            module_successful = summary.get('successful', 0)
            module_failed = summary.get('failed', 0)
            
            total_attacks += module_total
            total_successful += module_successful
            total_failed += module_failed
            
            module_summaries[module_name] = {
                'total': module_total,
                'successful': module_successful,
                'failed': module_failed,
                'success_rate': (module_successful / module_total * 100) if module_total > 0 else 0
            }
        
        overall_success_rate = (total_successful / total_attacks * 100) if total_attacks > 0 else 0
        
        return {
            'total_attacks': total_attacks,
            'successful_attacks': total_successful,
            'failed_attacks': total_failed,
            'overall_success_rate': overall_success_rate,
            'modules': module_summaries,
            'severity': self._calculate_severity(total_successful, total_attacks)
        }
    
    def _calculate_severity(self, successful: int, total: int) -> str:
        """Calculate overall severity"""
        if total == 0:
            return 'unknown'
        
        success_rate = successful / total
        
        if success_rate >= 0.5:
            return 'critical'
        elif success_rate >= 0.3:
            return 'high'
        elif success_rate >= 0.1:
            return 'medium'
        else:
            return 'low'
    
    def _extract_findings(self, results: List[tuple]) -> List[Dict[str, Any]]:
        """Extract key findings"""
        findings = []
        
        for module_name, module_results in results:
            summary = module_results.get('summary', {})
            successful = summary.get('successful', 0)
            total = summary.get('total', 0)
            
            if successful > 0:
                findings.append({
                    'module': module_name,
                    'severity': self._calculate_severity(successful, total),
                    'successful_attacks': successful,
                    'total_attacks': total,
                    'success_rate': (successful / total * 100) if total > 0 else 0
                })
        
        return sorted(findings, key=lambda x: x['success_rate'], reverse=True)
    
    def _generate_recommendations(self, results: List[tuple]) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        # Check each module for vulnerabilities
        for module_name, module_results in results:
            summary = module_results.get('summary', {})
            successful = summary.get('successful', 0)
            total = summary.get('total', 0)
            
            if successful > 0:
                success_rate = (successful / total * 100) if total > 0 else 0
                
                if module_name == 'prompt_injection':
                    recommendations.append(
                        f"Implement prompt injection detection and filtering. "
                        f"Success rate: {success_rate:.1f}%"
                    )
                
                elif module_name == 'jailbreak':
                    recommendations.append(
                        f"Strengthen jailbreak defenses. Success rate: {success_rate:.1f}%"
                    )
                
                elif module_name == 'system_prompt_extraction':
                    recommendations.append(
                        f"Implement system prompt protection mechanisms. Success rate: {success_rate:.1f}%"
                    )
                
                elif module_name == 'data_extraction':
                    recommendations.append(
                        f"Review data extraction vulnerabilities. Success rate: {success_rate:.1f}%"
                    )
                
                elif module_name == 'role_confusion':
                    recommendations.append(
                        f"Implement role-based access control. Success rate: {success_rate:.1f}%"
                    )
        
        # General recommendations
        recommendations.extend([
            "Implement input validation and sanitization",
            "Add rate limiting and abuse detection",
            "Monitor for suspicious patterns",
            "Regular security audits",
            "Implement safety classifiers",
            "Use content filtering",
            "Implement human-in-the-loop for sensitive operations"
        ])
        
        return recommendations
    
    def _write_json_report(self, report_data: Dict[str, Any], output_path: str, verbose: bool):
        """Write JSON report"""
        # Filter responses if needed
        if not self.include_responses:
            report_data = self._remove_responses(report_data)
        
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        if verbose:
            print(f"{Fore.GREEN}[+] JSON report written to: {output_path}{Style.RESET_ALL}")
    
    def _write_text_report(self, report_data: Dict[str, Any], output_path: str, verbose: bool):
        """Write text report"""
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("ADVERSARIAL LLM RED TEAMING REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {report_data['metadata']['timestamp']}")
        lines.append("")
        
        # Summary
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        summary = report_data['summary']
        lines.append(f"Total Attacks: {summary['total_attacks']}")
        lines.append(f"Successful: {summary['successful_attacks']}")
        lines.append(f"Failed: {summary['failed_attacks']}")
        lines.append(f"Overall Success Rate: {summary['overall_success_rate']:.1f}%")
        lines.append(f"Severity: {summary['severity'].upper()}")
        lines.append("")
        
        # Module summaries
        lines.append("MODULE SUMMARIES")
        lines.append("-" * 80)
        for module_name, module_summary in summary['modules'].items():
            lines.append(f"{module_name.upper()}:")
            lines.append(f"  Total: {module_summary['total']}")
            lines.append(f"  Successful: {module_summary['successful']}")
            lines.append(f"  Success Rate: {module_summary['success_rate']:.1f}%")
            lines.append("")
        
        # Findings
        lines.append("KEY FINDINGS")
        lines.append("-" * 80)
        for finding in report_data['findings']:
            lines.append(f"{finding['module'].upper()}:")
            lines.append(f"  Severity: {finding['severity'].upper()}")
            lines.append(f"  Success Rate: {finding['success_rate']:.1f}%")
            lines.append("")
        
        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)
        for i, rec in enumerate(report_data['recommendations'], 1):
            lines.append(f"{i}. {rec}")
        lines.append("")
        
        # Detailed results (if verbose)
        if verbose and self.include_responses:
            lines.append("DETAILED RESULTS")
            lines.append("-" * 80)
            for module_name, module_data in report_data['modules'].items():
                lines.append(f"\n{module_name.upper()}:")
                for attack in module_data['attacks'][:5]:  # Limit to first 5
                    lines.append(f"  Pattern: {attack.get('pattern', 'N/A')[:100]}")
                    lines.append(f"  Success: {attack.get('success', False)}")
                    lines.append("")
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
        
        if verbose:
            print(f"{Fore.GREEN}[+] Text report written to: {output_path}{Style.RESET_ALL}")
    
    def _remove_responses(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove response content from report"""
        for module_data in report_data['modules'].values():
            for attack in module_data.get('attacks', []):
                if 'response' in attack:
                    attack['response'] = '[REDACTED]'
                if 'extracted_data' in attack:
                    attack['extracted_data'] = '[REDACTED]'
                if 'extracted_prompt' in attack:
                    attack['extracted_prompt'] = '[REDACTED]'
        return report_data

    # -----------------------------------------------------------------
    # Markdown report writer
    # -----------------------------------------------------------------
    def _write_markdown_report(self, report_data: Dict[str, Any],
                               output_path: str, verbose: bool):
        """Write a rich Markdown report with tables and CVSS-like scoring."""
        lines = []
        meta = report_data['metadata']
        summary = report_data['summary']

        # --- Header ---
        lines.append('# Adversarial LLM Red Teaming Report')
        lines.append('')
        lines.append(f'**Generated:** {meta["timestamp"]}  ')
        lines.append(f'**Report version:** {meta["report_version"]}  ')
        if meta.get('llm_stats'):
            stats = meta['llm_stats']
            lines.append(f'**API requests:** {stats.get("total_requests", "N/A")} '
                         f'| **Avg latency:** {stats.get("avg_latency_ms", 0):.0f} ms '
                         f'| **Errors:** {stats.get("total_errors", 0)}  ')
        lines.append('')

        # --- Executive summary ---
        lines.append('## Executive Summary')
        lines.append('')
        severity = summary.get('severity', 'unknown').upper()
        cvss = self._severity_to_cvss(summary.get('severity', 'unknown'))
        lines.append(f'| Metric | Value |')
        lines.append(f'|--------|-------|')
        lines.append(f'| Total attacks | {summary["total_attacks"]} |')
        lines.append(f'| Successful | {summary["successful_attacks"]} |')
        lines.append(f'| Failed | {summary["failed_attacks"]} |')
        lines.append(f'| Success rate | {summary["overall_success_rate"]:.1f}% |')
        lines.append(f'| Severity | **{severity}** |')
        lines.append(f'| CVSS-like score | {cvss} |')
        lines.append('')

        # --- Module breakdown ---
        lines.append('## Module Breakdown')
        lines.append('')
        lines.append('| Module | Total | Successful | Rate | Severity |')
        lines.append('|--------|-------|-----------|------|----------|')
        for mod_name, mod_summary in summary.get('modules', {}).items():
            sev = self._calculate_severity(mod_summary['successful'], mod_summary['total'])
            lines.append(
                f'| {mod_name} | {mod_summary["total"]} | '
                f'{mod_summary["successful"]} | '
                f'{mod_summary["success_rate"]:.1f}% | '
                f'{sev.upper()} |'
            )
        lines.append('')

        # --- Key findings ---
        lines.append('## Key Findings')
        lines.append('')
        for i, finding in enumerate(report_data['findings'], 1):
            lines.append(f'{i}. **{finding["module"]}** -- '
                         f'{finding["severity"].upper()} severity, '
                         f'{finding["success_rate"]:.1f}% success rate '
                         f'({finding["successful_attacks"]}/{finding["total_attacks"]})')
        lines.append('')

        # --- Recommendations ---
        lines.append('## Recommendations')
        lines.append('')
        for i, rec in enumerate(report_data['recommendations'], 1):
            lines.append(f'{i}. {rec}')
        lines.append('')

        # --- Detailed results (verbose) ---
        if verbose and self.include_responses:
            lines.append('## Detailed Results')
            lines.append('')
            for mod_name, mod_data in report_data['modules'].items():
                lines.append(f'### {mod_name}')
                lines.append('')
                attacks = mod_data.get('attacks', [])[:10]
                if attacks:
                    lines.append('| # | Pattern | Success | Confidence | Indicators |')
                    lines.append('|---|---------|---------|-----------|------------|')
                    for j, atk in enumerate(attacks, 1):
                        pat = atk.get('pattern', 'N/A')[:60].replace('|', '\\|')
                        succ = 'Yes' if atk.get('success') else 'No'
                        conf = f'{atk.get("confidence", 0):.2f}' if 'confidence' in atk else 'N/A'
                        inds = '; '.join(atk.get('indicators', [])[:2]).replace('|', '\\|')
                        lines.append(f'| {j} | {pat} | {succ} | {conf} | {inds} |')
                    lines.append('')

        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))

        if verbose:
            print(f"{Fore.GREEN}[+] Markdown report written to: {output_path}{Style.RESET_ALL}")

    def _severity_to_cvss(self, severity: str) -> str:
        """Map severity string to a CVSS-like score range."""
        return self.SEVERITY_SCALE.get(severity, {}).get('cvss_range', 'N/A')

