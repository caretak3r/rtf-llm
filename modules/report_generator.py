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
import logging
import os
import html as html_lib
from datetime import datetime
from typing import Dict, List, Any, Optional
from colorama import Fore, Style


class ReportGenerator:
    """Generate reports from red teaming results."""

    # CVSS-like severity scale for LLM red teaming
    SEVERITY_SCALE = {
        "critical": {"min_rate": 50, "cvss_range": "9.0-10.0", "color": "red"},
        "high": {"min_rate": 30, "cvss_range": "7.0-8.9", "color": "orange"},
        "medium": {"min_rate": 10, "cvss_range": "4.0-6.9", "color": "yellow"},
        "low": {"min_rate": 0, "cvss_range": "0.1-3.9", "color": "green"},
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_dir = config.get("output_dir", "docs/reports")
        self.format = config.get("format", "json")
        self.include_responses = config.get("include_responses", True)
        self.severity_threshold = config.get("severity_threshold", "medium")
        self.include_owasp = config.get("include_owasp_mapping", True)
        self.include_judge_reasoning = config.get("include_judge_reasoning", True)
        self.per_attack_severity = config.get("per_attack_severity", True)
        self.specific_recommendations = config.get("specific_recommendations", True)

        os.makedirs(self.output_dir, exist_ok=True)

        # Set up structured logging to file
        log_file = os.path.join(self.output_dir, "llm_redteam.log")
        self.logger = logging.getLogger("llm_redteam")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            fh = logging.FileHandler(log_file, mode="w")
            fh.setLevel(logging.INFO)
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
        self.log_file = log_file

    def _get_pattern(self, attack: Dict[str, Any]) -> str:
        """Resolve pattern text from an attack result, checking all possible field names."""
        for key in ("pattern", "pattern_name", "input", "user_prompt", "prompt", "goal", "name"):
            val = attack.get(key)
            if val:
                return str(val)
        return "N/A"

    def _write_attack_log(self, results: List[tuple]):
        """Write a structured log of every attack to the log file."""
        self.logger.info("=" * 80)
        self.logger.info("ADVERSARIAL LLM RED TEAMING - FULL ATTACK LOG")
        self.logger.info("=" * 80)
        self.logger.info("")

        total = 0
        successful = 0

        for module_name, module_results in results:
            summary = module_results.get("summary", {})
            attacks = module_results.get("attacks", [])

            self.logger.info(f"MODULE: {module_name}")
            self.logger.info(
                f"  Total: {summary.get('total', 0)} | "
                f"Successful: {summary.get('successful', 0)} | "
                f"Failed: {summary.get('failed', 0)}"
            )
            self.logger.info("-" * 80)

            for atk in attacks:
                total += 1
                succ = atk.get("success", False)
                if succ:
                    successful += 1

                status = "SUCCESS" if succ else "BLOCKED"
                severity = atk.get("severity", "N/A").upper()
                cvss = atk.get("cvss_score", 0.0)
                category = atk.get("category", "N/A")
                owasp = atk.get("owasp_category", "N/A")
                confidence = atk.get("confidence", None)
                pattern = self._get_pattern(atk)[:200]

                conf_str = f"{confidence:.2f}" if confidence is not None else "N/A"
                self.logger.info(
                    f"  [{status:7s}] cvss={cvss:.1f} category={category} "
                    f"owasp={owasp} severity={severity} confidence={conf_str}"
                )
                self.logger.info(f"    pattern: {pattern}")

                indicators = atk.get("indicators", [])
                if indicators:
                    for ind in indicators:
                        self.logger.info(f"    indicator: {ind}")

                if self.include_responses:
                    response = atk.get("response", None)
                    if response:
                        resp_snippet = str(response)[:300]
                        self.logger.info(f"    response: {resp_snippet}")

                judge_reasoning = atk.get("judge_reasoning", None)
                if judge_reasoning:
                    self.logger.info(f"    judge_reasoning: {judge_reasoning[:300]}")

                self.logger.info("")

            self.logger.info("")

        self.logger.info("=" * 80)
        self.logger.info(
            f"TOTAL ATTACKS: {total} | SUCCESSFUL: {successful} | BLOCKED: {total - successful}"
        )
        self.logger.info("=" * 80)

    def generate_report(
        self,
        results: List[tuple],
        output_path: str = None,
        verbose: bool = False,
        llm_stats: Optional[Dict[str, Any]] = None,
        model_identity: Optional[Dict[str, Any]] = None,
        target_system_prompt: Optional[str] = None,
        canary_token: Optional[str] = None,
    ) -> str:
        """Generate comprehensive report from results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        report_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "report_version": "4.0",
                "generator": "Adversarial LLM Red Teaming Framework",
            },
            "summary": self._generate_summary(results),
            "modules": {},
            "findings": self._extract_findings(results),
            "recommendations": self._generate_recommendations(results),
            "owasp_heatmap": self._build_owasp_heatmap(results) if self.include_owasp else {},
        }

        if llm_stats:
            report_data["metadata"]["llm_stats"] = llm_stats

        if model_identity:
            report_data["metadata"]["model_identity"] = model_identity

        if target_system_prompt:
            report_data["metadata"]["target_system_prompt"] = target_system_prompt
        if canary_token:
            report_data["metadata"]["canary_token"] = canary_token

        # Count canary leaks across all attacks for the summary card
        canary_leaks = 0
        for _, mod_res in results:
            for atk in mod_res.get("attacks", []):
                if atk.get("canary_leaked"):
                    canary_leaks += 1
        report_data["summary"]["canary_leaks"] = canary_leaks

        for module_name, module_results in results:
            module_total, module_successful, module_failed = self._module_counts(module_results)
            report_data["modules"][module_name] = {
                "summary": {
                    **module_results.get("summary", {}),
                    "total": module_total,
                    "successful": module_successful,
                    "failed": module_failed,
                    "success_rate": (
                        module_successful / module_total * 100 if module_total > 0 else 0
                    ),
                },
                "intensity": module_results.get("intensity", "unknown"),
                "attacks": module_results.get("attacks", []),
            }

        if not output_path:
            ext = {"json": ".json", "txt": ".txt", "md": ".md", "markdown": ".md", "html": ".html"}
            suffix = ext.get(self.format, ".json")
            output_path = os.path.join(self.output_dir, f"llm_redteam_report_{timestamp}{suffix}")

        # Write full attack log
        self._write_attack_log(results)

        writers = {
            "json": self._write_json_report,
            "txt": self._write_text_report,
            "md": self._write_markdown_report,
            "markdown": self._write_markdown_report,
            "html": self._write_html_dashboard,
        }
        writer = writers.get(self.format, self._write_json_report)
        writer(report_data, output_path, verbose)

        # Always generate HTML dashboard alongside primary report
        if self.format != "html":
            base = os.path.splitext(output_path)[0]
            html_path = base + ".html"
            self._write_html_dashboard(report_data, html_path, verbose)

        return output_path

    def _generate_summary(self, results: List[tuple]) -> Dict[str, Any]:
        """Generate overall summary"""
        total_attacks = 0
        total_successful = 0
        total_failed = 0

        module_summaries = {}

        for module_name, module_results in results:
            module_total, module_successful, module_failed = self._module_counts(module_results)

            total_attacks += module_total
            total_successful += module_successful
            total_failed += module_failed

            module_summaries[module_name] = {
                "total": module_total,
                "successful": module_successful,
                "failed": module_failed,
                "success_rate": (module_successful / module_total * 100) if module_total > 0 else 0,
            }

        overall_success_rate = (total_successful / total_attacks * 100) if total_attacks > 0 else 0

        return {
            "total_attacks": total_attacks,
            "successful_attacks": total_successful,
            "failed_attacks": total_failed,
            "overall_success_rate": overall_success_rate,
            "modules": module_summaries,
            "severity": self._calculate_severity(total_successful, total_attacks),
        }

    @staticmethod
    def _module_counts(module_results: Dict[str, Any]) -> tuple[int, int, int]:
        attacks = module_results.get("attacks", [])
        if attacks:
            total = len(attacks)
            successful = sum(1 for atk in attacks if atk.get("success"))
            return total, successful, total - successful

        summary = module_results.get("summary", {})
        total = summary.get("total", 0)
        successful = summary.get("successful", 0)
        failed = summary.get("failed", max(total - successful, 0))
        return total, successful, failed

    def _calculate_severity(self, successful: int, total: int) -> str:
        """Calculate overall severity"""
        if total == 0:
            return "unknown"

        success_rate = successful / total

        if success_rate >= 0.5:
            return "critical"
        elif success_rate >= 0.3:
            return "high"
        elif success_rate >= 0.1:
            return "medium"
        else:
            return "low"

    def _extract_findings(self, results: List[tuple]) -> List[Dict[str, Any]]:
        """Extract key findings"""
        findings = []

        for module_name, module_results in results:
            total, successful, _ = self._module_counts(module_results)

            if successful > 0:
                findings.append(
                    {
                        "module": module_name,
                        "severity": self._calculate_severity(successful, total),
                        "successful_attacks": successful,
                        "total_attacks": total,
                        "success_rate": (successful / total * 100) if total > 0 else 0,
                    }
                )

        return sorted(findings, key=lambda x: x["success_rate"], reverse=True)

    def _generate_recommendations(self, results: List[tuple]) -> List[Dict[str, Any]]:
        """Generate specific, actionable security recommendations from findings."""
        recommendations = []

        # Analyze per-module results for targeted recommendations
        for module_name, module_results in results:
            attacks = module_results.get("attacks", [])
            total, successful, _ = self._module_counts(module_results)
            if total == 0:
                continue

            success_rate = successful / total * 100

            # Find weakest categories within the module
            cat_stats: Dict[str, Dict[str, int]] = {}
            for atk in attacks:
                cat = atk.get("category", "unknown")
                if cat not in cat_stats:
                    cat_stats[cat] = {"total": 0, "successful": 0}
                cat_stats[cat]["total"] += 1
                if atk.get("success"):
                    cat_stats[cat]["successful"] += 1

            weakest_cats = sorted(
                [c for c in cat_stats.items() if c[1]["successful"] > 0],
                key=lambda x: x[1]["successful"] / max(x[1]["total"], 1),
                reverse=True,
            )

            # Module-specific targeted recommendations
            if module_name == "prompt_injection" and success_rate > 10:
                rec = {
                    "owasp": "LL01",
                    "severity": self._calculate_severity(successful, total),
                    "recommendation": f"Prompt injection defense needed (success rate: {success_rate:.1f}%).",
                    "actions": [],
                }
                if any(c[0] == "encoding_attacks" for c in weakest_cats):
                    rec["actions"].append(
                        "Add input normalization and encoding detection layer (base64, hex, ROT13, Unicode)"
                    )
                if any(c[0] == "crescendo" for c in weakest_cats):
                    rec["actions"].append(
                        "Implement multi-turn conversation monitoring for escalation patterns"
                    )
                if any(c[0] == "many_shot" for c in weakest_cats):
                    rec["actions"].append(
                        "Limit in-context example count and add few-shot detection"
                    )
                if any(c[0] == "indirect_injection" for c in weakest_cats):
                    rec["actions"].append(
                        "Sanitize all external content (documents, search results, emails) before model input"
                    )
                if not rec["actions"]:
                    rec["actions"].append(
                        "Add instruction hierarchy enforcement and input boundary filtering"
                    )
                recommendations.append(rec)

            elif module_name == "jailbreak" and success_rate > 10:
                rec = {
                    "owasp": "LL01",
                    "severity": self._calculate_severity(successful, total),
                    "recommendation": f"Jailbreak defense strengthening needed (success rate: {success_rate:.1f}%).",
                    "actions": [],
                }
                if any(c[0] == "skeleton_key" for c in weakest_cats):
                    rec["actions"].append("Add master-key / override phrase detection and blocking")
                if any(c[0] == "persona_modulation" for c in weakest_cats):
                    rec["actions"].append(
                        "Implement persona lock -- reject requests to adopt alternative identities"
                    )
                if any(c[0] == "prefix_injection" for c in weakest_cats):
                    rec["actions"].append(
                        "Add prefix monitoring to detect forced compliance tokens"
                    )
                if not rec["actions"]:
                    rec["actions"].append(
                        "Implement role-lock instructions and output filtering for system prompt content"
                    )
                recommendations.append(rec)

            elif module_name == "system_prompt_extraction" and success_rate > 5:
                rec = {
                    "owasp": "LL02",
                    "severity": self._calculate_severity(successful, total),
                    "recommendation": f"System prompt leakage protection needed (success rate: {success_rate:.1f}%).",
                    "actions": [
                        "Add role-lock instructions that prevent revealing system content",
                        "Implement output filtering for system prompt keywords and structure",
                    ],
                }
                recommendations.append(rec)

            elif module_name == "data_extraction" and success_rate > 10:
                rec = {
                    "owasp": "LL02",
                    "severity": self._calculate_severity(successful, total),
                    "recommendation": f"Data extraction vulnerabilities detected (success rate: {success_rate:.1f}%).",
                    "actions": [
                        "Implement output filtering for sensitive patterns",
                        "Add data boundary enforcement to prevent training data leakage",
                    ],
                }
                recommendations.append(rec)

            elif module_name == "role_confusion" and success_rate > 10:
                rec = {
                    "owasp": "LL04",
                    "severity": self._calculate_severity(successful, total),
                    "recommendation": f"Role confusion defense needed (success rate: {success_rate:.1f}%).",
                    "actions": [
                        "Implement role-lock in system prompt",
                        "Reject authority claims from user messages",
                    ],
                }
                recommendations.append(rec)

            elif module_name == "context_injection" and success_rate > 10:
                rec = {
                    "owasp": "LL03",
                    "severity": self._calculate_severity(successful, total),
                    "recommendation": f"Context injection defense needed (success rate: {success_rate:.1f}%).",
                    "actions": [
                        "Add context boundary enforcement",
                        "Sanitize multi-turn conversation history for injection patterns",
                    ],
                }
                recommendations.append(rec)

            elif module_name == "weight_manipulation" and success_rate > 10:
                rec = {
                    "owasp": "LL09",
                    "severity": self._calculate_severity(successful, total),
                    "recommendation": f"Weight/info disclosure risk (success rate: {success_rate:.1f}%).",
                    "actions": [
                        "Restrict model architecture and parameter disclosure",
                        "Implement access controls on model introspection endpoints",
                    ],
                }
                recommendations.append(rec)

        # General hardening recommendations
        recommendations.append(
            {
                "owasp": "General",
                "severity": "info",
                "recommendation": "General security hardening",
                "actions": [
                    "Implement input validation and sanitization",
                    "Add rate limiting and abuse detection",
                    "Monitor for suspicious patterns",
                    "Conduct regular security audits",
                    "Implement safety classifiers for output filtering",
                ],
            }
        )

        return recommendations

    def _build_owasp_heatmap(self, results: List[tuple]) -> Dict[str, Any]:
        """Build OWASP LLM Top 10 coverage heatmap from results."""
        from .evaluator import AttackEvaluator

        heatmap = {}
        for module_name, module_results in results:
            attacks = module_results.get("attacks", [])
            summary = module_results.get("summary", {})

            # Map module to OWASP category
            owasp_cat = AttackEvaluator.OWASP_MAPPING.get(module_name, "LL00 Unclassified")

            if owasp_cat not in heatmap:
                heatmap[owasp_cat] = {
                    "total_tested": 0,
                    "successful": 0,
                    "failed": 0,
                    "success_rate": 0.0,
                    "modules": [],
                    "max_severity": "info",
                    "avg_cvss": 0.0,
                    "_cvss_scores": [],
                }

            heatmap[owasp_cat]["total_tested"] += summary.get("total", 0)
            heatmap[owasp_cat]["successful"] += summary.get("successful", 0)
            heatmap[owasp_cat]["failed"] += summary.get("failed", 0)
            if module_name not in heatmap[owasp_cat]["modules"]:
                heatmap[owasp_cat]["modules"].append(module_name)

            # Track severity and CVSS from individual attacks
            sev_order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
            for atk in attacks:
                atk_sev = atk.get("severity", "info")
                if sev_order.get(atk_sev, 0) > sev_order.get(heatmap[owasp_cat]["max_severity"], 0):
                    heatmap[owasp_cat]["max_severity"] = atk_sev
                cvss = atk.get("cvss_score", 0.0)
                if cvss > 0:
                    heatmap[owasp_cat]["_cvss_scores"].append(cvss)

        # Compute derived fields
        for cat, data in heatmap.items():
            if data["total_tested"] > 0:
                data["success_rate"] = round(data["successful"] / data["total_tested"] * 100, 1)
            if data["_cvss_scores"]:
                data["avg_cvss"] = round(sum(data["_cvss_scores"]) / len(data["_cvss_scores"]), 1)
            del data["_cvss_scores"]

        return heatmap

    def _write_json_report(self, report_data: Dict[str, Any], output_path: str, verbose: bool):
        """Write JSON report"""
        # Filter responses if needed
        if not self.include_responses:
            report_data = self._remove_responses(report_data)

        with open(output_path, "w") as f:
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
        summary = report_data["summary"]
        lines.append(f"Total Attacks: {summary['total_attacks']}")
        lines.append(f"Successful: {summary['successful_attacks']}")
        lines.append(f"Failed: {summary['failed_attacks']}")
        lines.append(f"Overall Success Rate: {summary['overall_success_rate']:.1f}%")
        lines.append(f"Severity: {summary['severity'].upper()}")
        lines.append("")

        # Module summaries
        lines.append("MODULE SUMMARIES")
        lines.append("-" * 80)
        for module_name, module_summary in summary["modules"].items():
            lines.append(f"{module_name.upper()}:")
            lines.append(f"  Total: {module_summary['total']}")
            lines.append(f"  Successful: {module_summary['successful']}")
            lines.append(f"  Success Rate: {module_summary['success_rate']:.1f}%")
            lines.append("")

        # Findings
        lines.append("KEY FINDINGS")
        lines.append("-" * 80)
        for finding in report_data["findings"]:
            lines.append(f"{finding['module'].upper()}:")
            lines.append(f"  Severity: {finding['severity'].upper()}")
            lines.append(f"  Success Rate: {finding['success_rate']:.1f}%")
            lines.append("")

        # OWASP Heatmap
        if report_data.get("owasp_heatmap"):
            lines.append("OWASP LLM TOP 10 COVERAGE")
            lines.append("-" * 80)
            for cat, data in report_data["owasp_heatmap"].items():
                lines.append(
                    f"  {cat}: {data['successful']}/{data['total_tested']} "
                    f"({data['success_rate']:.1f}%) -- Max Severity: {data['max_severity'].upper()}"
                )
            lines.append("")

        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)
        for i, rec in enumerate(report_data["recommendations"], 1):
            if isinstance(rec, dict):
                lines.append(
                    f"{i}. [{rec.get('owasp', 'General')}] {rec['recommendation']} "
                    f"({rec.get('severity', 'info').upper()})"
                )
                for action in rec.get("actions", []):
                    lines.append(f"   - {action}")
            else:
                lines.append(f"{i}. {rec}")
        lines.append("")

        # Detailed results (if verbose)
        if verbose and self.include_responses:
            lines.append("DETAILED RESULTS")
            lines.append("-" * 80)
            for module_name, module_data in report_data["modules"].items():
                lines.append(f"\n{module_name.upper()}:")
                for attack in module_data["attacks"][:5]:  # Limit to first 5
                    lines.append(f"  Pattern: {self._get_pattern(attack)[:100]}")
                    lines.append(f"  Success: {attack.get('success', False)}")
                    lines.append("")

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        if verbose:
            print(f"{Fore.GREEN}[+] Text report written to: {output_path}{Style.RESET_ALL}")

    def _remove_responses(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove response content from report"""
        for module_data in report_data["modules"].values():
            for attack in module_data.get("attacks", []):
                if "response" in attack:
                    attack["response"] = "[REDACTED]"
                if "extracted_data" in attack:
                    attack["extracted_data"] = "[REDACTED]"
                if "extracted_prompt" in attack:
                    attack["extracted_prompt"] = "[REDACTED]"
        return report_data

    # -----------------------------------------------------------------
    # Markdown report writer
    # -----------------------------------------------------------------
    def _write_markdown_report(self, report_data: Dict[str, Any], output_path: str, verbose: bool):
        """Write a rich Markdown report with tables and CVSS-like scoring."""
        lines = []
        meta = report_data["metadata"]
        summary = report_data["summary"]

        # --- Header ---
        lines.append("# Adversarial LLM Red Teaming Report")
        lines.append("")
        lines.append(f"**Generated:** {meta['timestamp']}  ")
        lines.append(f"**Report version:** {meta['report_version']}  ")
        if meta.get("llm_stats"):
            stats = meta["llm_stats"]
            lines.append(
                f"**API requests:** {stats.get('total_requests', 'N/A')} "
                f"| **Avg latency:** {stats.get('avg_latency_ms', 0):.0f} ms "
                f"| **Errors:** {stats.get('total_errors', 0)}  "
            )
        lines.append("")

        # --- Executive summary ---
        lines.append("## Executive Summary")
        lines.append("")
        severity = summary.get("severity", "unknown").upper()
        cvss = self._severity_to_cvss(summary.get("severity", "unknown"))
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total attacks | {summary['total_attacks']} |")
        lines.append(f"| Successful | {summary['successful_attacks']} |")
        lines.append(f"| Failed | {summary['failed_attacks']} |")
        lines.append(f"| Success rate | {summary['overall_success_rate']:.1f}% |")
        lines.append(f"| Severity | **{severity}** |")
        lines.append(f"| CVSS-like score | {cvss} |")
        lines.append("")

        # --- OWASP LLM Top 10 Heatmap ---
        if report_data.get("owasp_heatmap"):
            lines.append("## OWASP LLM Top 10 Coverage")
            lines.append("")
            lines.append(
                "| Category | Tested | Successful | Rate | Max Severity | Avg CVSS | Modules |"
            )
            lines.append(
                "|----------|--------|-----------|------|-------------|---------|---------|"
            )
            for cat, data in report_data["owasp_heatmap"].items():
                mods = ", ".join(data.get("modules", []))
                lines.append(
                    f"| {cat} | {data['total_tested']} | {data['successful']} | "
                    f"{data['success_rate']:.1f}% | {data['max_severity'].upper()} | "
                    f"{data['avg_cvss']} | {mods} |"
                )
            lines.append("")

        # --- Module breakdown ---
        lines.append("## Module Breakdown")
        lines.append("")
        lines.append("| Module | Total | Successful | Rate | Severity |")
        lines.append("|--------|-------|-----------|------|----------|")
        for mod_name, mod_summary in summary.get("modules", {}).items():
            sev = self._calculate_severity(mod_summary["successful"], mod_summary["total"])
            lines.append(
                f"| {mod_name} | {mod_summary['total']} | "
                f"{mod_summary['successful']} | "
                f"{mod_summary['success_rate']:.1f}% | "
                f"{sev.upper()} |"
            )
        lines.append("")

        # --- Key findings ---
        lines.append("## Key Findings")
        lines.append("")
        for i, finding in enumerate(report_data["findings"], 1):
            lines.append(
                f"{i}. **{finding['module']}** -- "
                f"{finding['severity'].upper()} severity, "
                f"{finding['success_rate']:.1f}% success rate "
                f"({finding['successful_attacks']}/{finding['total_attacks']})"
            )
        lines.append("")

        # --- Recommendations ---
        lines.append("## Recommendations")
        lines.append("")
        for i, rec in enumerate(report_data["recommendations"], 1):
            if isinstance(rec, dict):
                lines.append(
                    f"{i}. **[{rec.get('owasp', 'General')}] {rec['recommendation']}** "
                    f"({rec.get('severity', 'info').upper()})"
                )
                for action in rec.get("actions", []):
                    lines.append(f"   - {action}")
            else:
                lines.append(f"{i}. {rec}")
        lines.append("")

        # --- Detailed results (verbose) ---
        if verbose and self.include_responses:
            lines.append("## Detailed Results")
            lines.append("")
            for mod_name, mod_data in report_data["modules"].items():
                lines.append(f"### {mod_name}")
                lines.append("")
                attacks = mod_data.get("attacks", [])[:10]
                if attacks:
                    lines.append("| # | Pattern | Success | Confidence | Severity | CVSS | OWASP |")
                    lines.append("|---|---------|---------|-----------|----------|------|-------|")
                    for j, atk in enumerate(attacks, 1):
                        pat = self._get_pattern(atk)[:60].replace("|", "\\|")
                        succ = "Yes" if atk.get("success") else "No"
                        conf = f"{atk.get('confidence', 0):.2f}" if "confidence" in atk else "N/A"
                        sev = atk.get("severity", "info").upper()
                        cvss_val = f"{atk.get('cvss_score', 0.0):.1f}"
                        owasp = atk.get("owasp_category", "N/A")
                        lines.append(
                            f"| {j} | {pat} | {succ} | {conf} | {sev} | {cvss_val} | {owasp} |"
                        )
                    lines.append("")

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        if verbose:
            print(f"{Fore.GREEN}[+] Markdown report written to: {output_path}{Style.RESET_ALL}")

    def _severity_to_cvss(self, severity: str) -> str:
        """Map severity string to a CVSS-like score range."""
        return self.SEVERITY_SCALE.get(severity, {}).get("cvss_range", "N/A")

    def _write_html_dashboard(self, report_data: Dict[str, Any], output_path: str, verbose: bool):
        """Write a self-contained HTML dashboard from template."""
        summary = report_data["summary"]
        modules = report_data["modules"]
        findings = report_data["findings"]
        owasp_heatmap = report_data.get("owasp_heatmap", {})
        recommendations = report_data["recommendations"]
        metadata = report_data["metadata"]

        # Gather all attacks
        all_attacks: List[Dict[str, Any]] = []
        for mod_name, mod_data in modules.items():
            for atk in mod_data.get("attacks", []):
                atk_copy = dict(atk)
                atk_copy["_module"] = mod_name
                all_attacks.append(atk_copy)

        # Severity counts
        sev_counts: Dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for atk in all_attacks:
            s = atk.get("severity", "info")
            sev_counts[s] = sev_counts.get(s, 0) + 1

        # Category stats
        cat_stats: Dict[str, Dict[str, int]] = {}
        for atk in all_attacks:
            cat = atk.get("category", "unknown")
            if cat not in cat_stats:
                cat_stats[cat] = {"total": 0, "success": 0, "blocked": 0}
            cat_stats[cat]["total"] += 1
            if atk.get("success"):
                cat_stats[cat]["success"] += 1
            else:
                cat_stats[cat]["blocked"] += 1

        # JSON blobs for JS - include full attack vector for defensive education
        from .technique_kb import TECHNIQUE_INFO

        def _esc_html(value):
            return html_lib.escape(str(value or ""), quote=True)

        def _safe_json(obj):
            # Inline-into-<script> safe: prevent premature </script> close,
            # HTML comment confusion, and U+2028/U+2029 JS line terminators.
            s = json.dumps(obj, ensure_ascii=False)
            return (
                s.replace("</", "<\\/")
                .replace("<!--", "<\\!--")
                .replace("\u2028", "\\u2028")
                .replace("\u2029", "\\u2029")
            )

        attacks_json = _safe_json(
            [
                {
                    "module": a["_module"],
                    "category": a.get("category", "N/A"),
                    "pattern": self._get_pattern(a),
                    "prompt": str(
                        a.get("prompt", "")
                        or a.get("combined_prompt", "")
                        or self._get_pattern(a)
                        or ""
                    ),
                    "goal": str(a.get("malicious_goal", "") or a.get("goal", "") or ""),
                    "success": bool(a.get("success", False)),
                    "severity": a.get("severity", "info"),
                    "cvss": a.get("cvss_score", 0.0),
                    "confidence": a.get("confidence", None),
                    "owasp": a.get("owasp_category", "N/A"),
                    "indicators": a.get("indicators", []),
                    "response": str(
                        a.get("response", "") or a.get("error", "") or "(no response captured)"
                    ),
                    "judge_reasoning": str(a.get("judge_reasoning", "") or ""),
                    "canary_leaked": bool(a.get("canary_leaked", False)),
                }
                for a in all_attacks
            ]
        )
        technique_info_json = _safe_json(TECHNIQUE_INFO)

        sev = summary.get("severity", "unknown")
        sev_info = self.SEVERITY_SCALE.get(sev, {})
        sev_color = sev_info.get("color", "var(--text)")
        cvss_range = sev_info.get("cvss_range", "N/A")

        # LLM stats section
        llm_stats_html = ""
        ls = metadata.get("llm_stats")
        if ls:
            llm_stats_html = (
                '<table style="margin-bottom:16px"><tr><td><strong>Metric</strong></td>'
                "<td><strong>Value</strong></td></tr>"
                f"<tr><td>API Requests</td><td>{ls.get('total_requests', 'N/A')}</td></tr>"
                f"<tr><td>Avg Latency</td><td>{ls.get('avg_latency_ms', 0):.0f} ms</td></tr>"
                f"<tr><td>Errors</td><td>{ls.get('total_errors', 0)}</td></tr></table>"
            )

        # Model identity section
        model_identity_html = ""
        mi = metadata.get("model_identity")
        if mi:
            raw_identified_name = (
                mi.get("identified_name") or mi.get("configured_name") or "Unknown"
            )
            raw_identified_provider = (
                mi.get("identified_provider") or mi.get("configured_provider") or "Unknown"
            )
            raw_configured_name = mi.get("configured_name") or ""
            identified_name = _esc_html(raw_identified_name)
            identified_provider = _esc_html(raw_identified_provider)
            configured_name = _esc_html(raw_configured_name)
            mismatch = raw_identified_name != raw_configured_name and raw_configured_name
            model_identity_html = (
                '<div style="margin-bottom:16px;padding:12px 16px;background:var(--surface);'
                'border:1px solid var(--border);border-radius:8px">'
                '<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">'
                '<div><span style="color:var(--muted);font-size:0.7rem;text-transform:uppercase;'
                'letter-spacing:0.5px">Target Model</span><br>'
                f'<span style="font-size:1.3rem;font-weight:700;color:var(--accent)">'
                f"{identified_name}</span></div>"
                f'<div><span style="color:var(--muted);font-size:0.7rem;text-transform:uppercase;'
                f'letter-spacing:0.5px">Provider</span><br>'
                f'<span style="font-size:1rem;font-weight:600">{identified_provider}</span></div>'
            )
            if mismatch:
                model_identity_html += (
                    f'<div><span style="color:var(--muted);font-size:0.7rem;text-transform:uppercase;'
                    f'letter-spacing:0.5px">Config Name</span><br>'
                    f'<span style="font-size:0.85rem;color:var(--orange)">{configured_name}'
                    f' <span style="font-size:0.7rem">(mismatch)</span></span></div>'
                )
            model_identity_html += "</div></div>"

        # Load template
        tpl_path = os.path.join(os.path.dirname(__file__), "html_dashboard_template.html")
        try:
            with open(tpl_path, "r") as f:
                html = f.read()
        except FileNotFoundError:
            print(f"{Fore.YELLOW}[!] HTML template not found at {tpl_path}{Style.RESET_ALL}")
            return

        # Replace placeholders
        html = html.replace("__TIMESTAMP__", _esc_html(metadata.get("timestamp", "")))
        html = html.replace("__VERSION__", _esc_html(metadata.get("report_version", "")))
        mi = metadata.get("model_identity", {})
        html = html.replace(
            "__MODEL_NAME__",
            _esc_html(mi.get("identified_name") or mi.get("configured_name") or "Unknown"),
        )
        html = html.replace(
            "__MODEL_PROVIDER__",
            _esc_html(mi.get("identified_provider") or mi.get("configured_provider") or "Unknown"),
        )
        html = html.replace("__MODEL_IDENTITY__", model_identity_html)
        html = html.replace("__TOTAL__", str(summary.get("total_attacks", 0)))
        html = html.replace("__SUCCESSFUL__", str(summary.get("successful_attacks", 0)))
        html = html.replace("__BLOCKED__", str(summary.get("failed_attacks", 0)))
        html = html.replace("__RATE__", f"{summary.get('overall_success_rate', 0):.1f}")
        html = html.replace("__SEVERITY__", sev.upper())
        html = html.replace("__SEV_COLOR__", sev_color)
        html = html.replace("__CVSS_RANGE__", cvss_range)
        html = html.replace("__LLM_STATS__", llm_stats_html)
        html = html.replace("__ATTACK_COUNT__", str(len(all_attacks)))
        html = html.replace("__ATTACKS_JSON__", attacks_json)
        html = html.replace("__CAT_STATS_JSON__", _safe_json(cat_stats))
        html = html.replace("__SEV_COUNTS_JSON__", _safe_json(sev_counts))
        html = html.replace("__MOD_SUMMARIES_JSON__", _safe_json(summary.get("modules", {})))
        html = html.replace("__OWASP_JSON__", _safe_json(owasp_heatmap))
        html = html.replace("__FINDINGS_JSON__", _safe_json(findings))
        html = html.replace("__RECS_JSON__", _safe_json(recommendations))
        html = html.replace("__TECHNIQUE_INFO_JSON__", technique_info_json)

        # Canary / target system prompt info
        canary_token = metadata.get("canary_token", "")
        target_sysprompt = metadata.get("target_system_prompt", "")
        canary_leaks = summary.get("canary_leaks", 0)
        if canary_token:
            canary_html = (
                '<div style="margin-bottom:16px;padding:12px 16px;background:var(--surface);'
                "border:1px solid " + ("var(--red)" if canary_leaks else "var(--green)") + ";"
                'border-radius:8px">'
                '<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">'
                '<div><span style="color:var(--muted);font-size:0.7rem;text-transform:uppercase;'
                'letter-spacing:0.5px">Ground-Truth Canary</span><br>'
                '<code style="font-size:1rem;color:var(--accent)">'
                + _esc_html(canary_token)
                + "</code></div>"
                '<div><span style="color:var(--muted);font-size:0.7rem;text-transform:uppercase;'
                'letter-spacing:0.5px">Verified Leaks</span><br>'
                '<span style="font-size:1.4rem;font-weight:700;color:'
                + ("var(--red)" if canary_leaks else "var(--green)")
                + '">'
                + str(canary_leaks)
                + "</span></div>"
                '<div style="flex:1;min-width:300px">'
                '<span style="color:var(--muted);font-size:0.7rem;text-transform:uppercase;'
                'letter-spacing:0.5px">Deployed Target System Prompt</span><br>'
                '<details><summary style="cursor:pointer;font-size:0.85rem">show prompt</summary>'
                '<pre style="font-size:0.78rem;white-space:pre-wrap;margin-top:6px;'
                'background:var(--bg);padding:8px;border-radius:4px">'
                + _esc_html(target_sysprompt)
                + "</pre></details></div></div>"
                '<div style="margin-top:8px;font-size:0.78rem;color:var(--muted)">'
                'Attacks marked <span class="badge critical">CANARY LEAKED</span> contain '
                "this token verbatim — a definitive system-prompt extraction (ground truth)."
                "</div></div>"
            )
        else:
            canary_html = (
                '<div style="margin-bottom:16px;padding:10px 14px;background:var(--surface);'
                'border:1px solid var(--orange);border-radius:8px;font-size:0.82rem">'
                "No target system prompt deployed. Attack success is inferred from "
                "keyword heuristics and judge scoring only — not ground truth."
                "</div>"
            )
        html = html.replace("__CANARY_INFO__", canary_html)

        with open(output_path, "w") as f:
            f.write(html)

        if verbose:
            print(f"{Fore.GREEN}[+] HTML dashboard written to: {output_path}{Style.RESET_ALL}")
