#!/usr/bin/env python3
"""
Multi-Model Comparison Runner
Benchmarks multiple LLM targets side-by-side using the same attack modules.

Reads comparison.targets from config, creates an LLMClient per target,
runs selected attack modules, and merges results into a single report.
"""

import os
import time
from typing import Dict, List, Any, Optional
from colorama import Fore, Style
from .llm_client import LLMClient
from .evaluator import AttackEvaluator
from .judge_evaluator import JudgeEvaluator
from .config_manager import ConfigManager
from .prompt_injection import PromptInjectionModule
from .jailbreak import JailbreakModule
from .data_extraction import DataExtractionModule
from .system_prompt_extraction import SystemPromptExtractionModule
from .adversarial_inputs import AdversarialInputsModule
from .role_confusion import RoleConfusionModule
from .context_injection import ContextInjectionModule
from .weight_manipulation import ModelWeightManipulationModule


class ComparisonRunner:
    """Multi-model comparison benchmark runner"""

    MODULE_MAP = {
        'prompt_injection': PromptInjectionModule,
        'jailbreak': JailbreakModule,
        'data_extraction': DataExtractionModule,
        'system_prompt_extraction': SystemPromptExtractionModule,
        'adversarial_inputs': AdversarialInputsModule,
        'role_confusion': RoleConfusionModule,
        'context_injection': ContextInjectionModule,
        'weight_manipulation': ModelWeightManipulationModule,
    }

    def __init__(self, base_config: Dict[str, Any], intensity: str = 'high'):
        self.base_config = base_config
        self.intensity = intensity

    def run_comparison(self, modules: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run comparison across all configured targets."""
        if modules is None:
            modules = list(self.MODULE_MAP.keys())

        targets = self.base_config.get('comparison', {}).get('targets', [])
        if not targets:
            print(f"{Fore.YELLOW}[!] No comparison targets configured. Set comparison.targets in config.{Style.RESET_ALL}")
            return {
                'module': 'comparison',
                'targets': {},
                'combined_summary': {'total_targets': 0, 'total_attacks': 0, 'total_successful': 0, 'total_failed': 0},
            }

        print(f"{Fore.YELLOW}[*] Running multi-model comparison across {len(targets)} targets...{Style.RESET_ALL}")
        print(f"  Modules: {', '.join(modules)}")
        print(f"  Intensity: {self.intensity}")

        all_results = {
            'module': 'comparison',
            'targets': {},
            'combined_summary': {
                'total_targets': len(targets),
                'total_attacks': 0,
                'total_successful': 0,
                'total_failed': 0,
            },
        }

        rate_delay = self.base_config.get('rate_limiting', {}).get('delay_between_requests', 0.5)

        for target_cfg in targets:
            label = target_cfg.get('label', 'unnamed')
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  Target: {label}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

            try:
                target_results = self._run_target(target_cfg, modules, rate_delay)
                all_results['targets'][label] = target_results
            except Exception as e:
                print(f"{Fore.RED}[!] Error running target '{label}': {e}{Style.RESET_ALL}")
                all_results['targets'][label] = {
                    'error': str(e),
                    'module_results': {},
                    'summary': {'total': 0, 'successful': 0, 'failed': 0},
                }

            time.sleep(rate_delay)

        # Compute combined summary
        for label, target_data in all_results['targets'].items():
            summary = target_data.get('summary', {})
            all_results['combined_summary']['total_attacks'] += summary.get('total', 0)
            all_results['combined_summary']['total_successful'] += summary.get('successful', 0)
            all_results['combined_summary']['total_failed'] += summary.get('failed', 0)

        self._print_comparison_summary(all_results)
        return all_results

    def _run_target(self, target_cfg: Dict[str, Any], modules: List[str],
                    rate_delay: float) -> Dict[str, Any]:
        """Run all requested modules against a single target."""
        provider = target_cfg.get('provider', 'openai')
        model = target_cfg.get('model', 'gpt-4')
        api_key_env = target_cfg.get('api_key_env', '')
        base_url = target_cfg.get('base_url')
        label = target_cfg.get('label', 'unnamed')

        api_key = os.environ.get(api_key_env, '') if api_key_env else ''
        if api_key_env and not api_key:
            print(f"{Fore.YELLOW}[!] API key env var '{api_key_env}' not set for target '{label}'{Style.RESET_ALL}")

        llm_config = {
            'provider': provider,
            'model': model,
            'api_key': api_key or 'not-needed',
            'base_url': base_url,
            'temperature': self.base_config.get('llm', {}).get('temperature', 0.7),
            'max_tokens': self.base_config.get('llm', {}).get('max_tokens', 2000),
            'timeout': self.base_config.get('llm', {}).get('timeout', 60),
        }

        llm_client = LLMClient(llm_config)

        evaluator_config = dict(self.base_config)
        evaluator = AttackEvaluator.create_evaluator(llm_client, evaluator_config)

        target_result = {
            'provider': provider,
            'model': model,
            'module_results': {},
            'summary': {'total': 0, 'successful': 0, 'failed': 0},
        }

        for module_name in modules:
            if module_name not in self.MODULE_MAP:
                print(f"{Fore.YELLOW}[!] Unknown module '{module_name}', skipping{Style.RESET_ALL}")
                continue

            print(f"{Fore.CYAN}  [*] Running {module_name} on {label}...{Style.RESET_ALL}")
            module_cls = self.MODULE_MAP[module_name]

            try:
                module_instance = module_cls(llm_client, evaluator_config, intensity=self.intensity)
                result = module_instance.run_all_attacks()
                target_result['module_results'][module_name] = result

                summary = result.get('summary', {})
                target_result['summary']['total'] += summary.get('total', 0)
                target_result['summary']['successful'] += summary.get('successful', 0)
                target_result['summary']['failed'] += summary.get('failed', 0)
            except Exception as e:
                print(f"{Fore.RED}[!] Error running {module_name} on {label}: {e}{Style.RESET_ALL}")
                target_result['module_results'][module_name] = {
                    'error': str(e),
                    'summary': {'total': 0, 'successful': 0, 'failed': 0},
                }

            time.sleep(rate_delay)

        return target_result

    def _print_comparison_summary(self, results: Dict[str, Any]):
        """Print side-by-side comparison summary."""
        combined = results['combined_summary']

        print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  COMPARISON SUMMARY{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print(f"  Targets tested: {combined['total_targets']}")
        print(f"  Total attacks  : {combined['total_attacks']}")
        print(f"  Successful     : {Fore.RED}{combined['total_successful']}{Style.RESET_ALL}")
        print(f"  Failed         : {Fore.GREEN}{combined['total_failed']}{Style.RESET_ALL}")

        if combined['total_attacks'] > 0:
            overall_rate = combined['total_successful'] / combined['total_attacks'] * 100
            print(f"  Success rate   : {overall_rate:.1f}%")

        print(f"\n  {Fore.YELLOW}Per-target breakdown:{Style.RESET_ALL}")
        for label, target_data in results['targets'].items():
            summary = target_data.get('summary', {})
            model = target_data.get('model', 'unknown')
            total = summary.get('total', 0)
            successful = summary.get('successful', 0)
            failed = summary.get('failed', 0)
            rate = (successful / total * 100) if total > 0 else 0.0
            print(f"    {label} ({model}): {successful}/{total} attacks succeeded ({rate:.1f}%)")

        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")

    # -----------------------------------------------------------------
    # run_all_attacks interface (compatibility with main.py)
    # -----------------------------------------------------------------
    def run_all_attacks(self) -> Dict[str, Any]:
        """Run comparison with defaults for main.py compatibility."""
        result = self.run_comparison()

        return {
            'module': 'comparison',
            'intensity': self.intensity,
            'attacks': [],
            'summary': {
                'total': result['combined_summary']['total_attacks'],
                'successful': result['combined_summary']['total_successful'],
                'failed': result['combined_summary']['total_failed'],
            },
            'targets': result['targets'],
            'combined_summary': result['combined_summary'],
        }
