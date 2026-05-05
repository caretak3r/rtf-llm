#!/usr/bin/env python3
"""
Adversarial LLM Red Teaming Framework
Production-Ready Exploit Kit for LLM Security Testing

⚠️ AUTHORIZED USE ONLY ⚠️
This framework is for authorized security testing only.
Unauthorized use is illegal and unethical.
"""

import argparse
import json
import sys
import os
import threading
import webbrowser
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from colorama import init, Fore, Style
from modules.prompt_injection import PromptInjectionModule
from modules.jailbreak import JailbreakModule
from modules.data_extraction import DataExtractionModule
from modules.system_prompt_extraction import SystemPromptExtractionModule
from modules.adversarial_inputs import AdversarialInputsModule
from modules.role_confusion import RoleConfusionModule
from modules.context_injection import ContextInjectionModule
from modules.weight_manipulation import ModelWeightManipulationModule
from modules.multi_turn import MultiTurnModule
from modules.comparison import ComparisonRunner
from modules.payload_loader import PayloadLoader
from modules.persistence import PersistenceModule
from modules.c2_communication import C2Communication
from modules.data_exfiltration import DataExfiltrationModule
from modules.polymorphic_encoding import PolymorphicEncoder
from modules.defense_tester import DefenseTester
from modules.purple_team import PurpleTeamOrchestrator
from modules.multimodal_injection import MultimodalInjectionModule
from modules.report_generator import ReportGenerator
from modules.llm_client import LLMClient
from modules.config_manager import ConfigManager

init(autoreset=True)

def print_banner():
    """Display framework banner"""
    banner = f"""
{Fore.RED}╔══════════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║    ADVERSAЯIAL LLM RED TEAMING EXPLOIT KIT v4.0 - PRODUCTION       ║
║                                                                      ║
║     ⚠️  AUTHORIZED LLM SECURITY TESTING ONLY  ⚠️                   ║
║                                                                      ║
║    Red Team  | Blue Team  | Purple Team  | Modern Techniques        ║
║    Crescendo | Many-Shot  | Skeleton Key | Defense Hardening        ║
╚══════════════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}
"""
    print(banner)

def load_config():
    """Load configuration using ConfigManager"""
    config_manager = ConfigManager()
    return config_manager.config

def serve_dashboard(report_path, host='0.0.0.0', port=8090):
    """Serve the HTML dashboard on an HTTP server."""
    report_dir = os.path.dirname(os.path.abspath(report_path))
    report_file = os.path.basename(report_path)

    class DashboardHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=report_dir, **kwargs)

        def log_message(self, format, *args):
            pass  # Suppress per-request logging

    try:
        server = HTTPServer((host, port), DashboardHandler)
        url = f"http://{host}:{port}/{report_file}"
        if host == '0.0.0.0':
            url = f"http://localhost:{port}/{report_file}"

        print(f"\n{Fore.CYAN}[*] Serving dashboard at: {Fore.WHITE}{url}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[*] Press Ctrl+C to stop the server{Style.RESET_ALL}")

        webbrowser.open(url)
        server.serve_forever()
    except OSError as e:
        if 'Address already in use' in str(e) or e.errno == 98:
            print(f"{Fore.YELLOW}[!] Port {port} already in use, trying {port + 1}...{Style.RESET_ALL}")
            serve_dashboard(report_path, host, port + 1)
        else:
            print(f"{Fore.RED}[!] Failed to start dashboard server: {e}{Style.RESET_ALL}")
    except KeyboardInterrupt:
        print(f"\n{Fore.GREEN}[+] Dashboard server stopped{Style.RESET_ALL}")
        server.shutdown()


def require_authorization():
    """Require user to acknowledge authorization"""
    print(f"\n{Fore.RED}⚠️  AUTHORIZATION REQUIRED ⚠️{Style.RESET_ALL}")
    print("This framework is for AUTHORIZED LLM security testing only.")
    print("Unauthorized use violates computer fraud laws and AI safety regulations.")
    response = input("Do you have written authorization? (yes/no): ")
    if response.lower() != 'yes':
        print(f"{Fore.RED}[!] Authorization required. Exiting.{Style.RESET_ALL}")
        sys.exit(1)
    print(f"{Fore.GREEN}[+] Authorization acknowledged{Style.RESET_ALL}\n")

def main():
    parser = argparse.ArgumentParser(
        description='Adversarial LLM Red Teaming Framework - Authorized Testing Only',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--module', '-m', required=True,
                       choices=['prompt-injection', 'jailbreak', 'data-extraction', 
                               'system-prompt-extraction', 'adversarial-inputs',
                               'role-confusion', 'context-injection', 'weight-manipulation',
                               'multi-turn', 'payload-loader', 'persistence', 'c2-communication',
                               'data-exfiltration', 'polymorphic-encoding',
                               'defense-tester', 'purple-team', 'multimodal-injection',
                               'comparison', 'all'],
                       help='Module to execute')
    
    parser.add_argument('--target', '-t', help='Target LLM API endpoint or model identifier')
    parser.add_argument('--api-key', '-k', help='LLM API key')
    parser.add_argument('--provider', '-p',
                       choices=['openai', 'anthropic', 'google', 'cohere', 'custom',
                               'groq', 'together', 'perplexity', 'mistral', 'fireworks',
                               'openrouter', 'anyscale', 'novita', 'deepinfra', 'sambanova',
                               'ollama', 'lmstudio', 'any'],
                       help='LLM provider (use "any" for auto-detect from URL)')
    parser.add_argument('--model', help='Model identifier (e.g., gpt-4, claude-3-opus)')
    parser.add_argument('--output', '-o', help='Output report file path')
    parser.add_argument('--intensity', '-i', 
                       choices=['low', 'medium', 'high', 'extreme'],
                       default='high',
                       help='Attack intensity level')
    parser.add_argument('--no-auth', action='store_true',
                       help='Skip authorization check (NOT RECOMMENDED)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--report-format', choices=['json', 'txt', 'md', 'html'],
                        default=None,
                        help='Report output format (overrides config)')
    parser.add_argument('--system-prompt', '-s', default=None,
                       help='System prompt to test defenses against (defense-tester / purple-team)')
    parser.add_argument('--defense-profile',
                       choices=['minimal', 'standard', 'hardened', 'maximum'],
                       default='standard',
                       help='Defense profile for blue team testing')
    parser.add_argument('--judge', action='store_true',
                       help='Enable LLM-as-Judge evaluation')
    parser.add_argument('--judge-mode', choices=['self', 'structured', 'both'],
                       default='both',
                       help='Judge evaluation mode')
    parser.add_argument('--comparison', action='store_true',
                       help='Run attacks against all comparison targets')
    parser.add_argument('--no-judge', action='store_true',
                       help='Disable LLM-as-Judge even if enabled in config')
    parser.add_argument('--no-serve', action='store_true',
                       help='Do not serve the HTML dashboard after the run')
    parser.add_argument('--serve-host', default='0.0.0.0',
                       help='Host to serve the dashboard on (default: 0.0.0.0)')
    parser.add_argument('--serve-port', type=int, default=8090,
                       help='Port to serve the dashboard on (default: 8090)')
    
    args = parser.parse_args()
    
    print_banner()
    
    if not args.no_auth:
        require_authorization()
    
    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.config
    
    # Override config with CLI args
    if args.api_key:
        config_manager.set('llm.api_key', args.api_key)
    if args.provider:
        config_manager.set('llm.provider', args.provider)
    if args.model:
        config_manager.set('llm.model', args.model)
    if args.target:
        config_manager.set('llm.base_url', args.target)
    
    # Judge evaluation CLI overrides
    if args.judge:
        config_manager.set('judge.enabled', True)
    if args.no_judge:
        config_manager.set('judge.enabled', False)
    if args.judge_mode:
        config_manager.set('judge.mode', args.judge_mode)
    
    # Get LLM config
    llm_config = config_manager.get_llm_config()
    
    # Prompt for API key if not set
    if not llm_config.get('api_key'):
        provider = llm_config.get('provider', 'openai')
        llm_config['api_key'] = config_manager.prompt_for_api_key(provider)
    
    # Initialize LLM client
    try:
        llm_client = LLMClient(llm_config)
        print(f"{Fore.GREEN}[+] LLM client initialized: {llm_config['provider']}/{llm_config['model']}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[!] Failed to initialize LLM client: {e}{Style.RESET_ALL}")
        sys.exit(1)
    
    # Identify the model's true identity (first action before any attacks)
    print(f"\n{Fore.CYAN}[*] Probing target model for true identity...{Style.RESET_ALL}")
    model_identity = llm_client.identify_model()
    identified_name = model_identity['identified_name']
    identified_provider = model_identity['identified_provider']
    print(f"{Fore.GREEN}[+] Model identified: {Fore.WHITE}{identified_name}{Style.RESET_ALL}"
          f"  (provider: {identified_provider})")
    if identified_name != llm_config.get('model', ''):
        print(f"{Fore.YELLOW}[!] Config says '{llm_config.get('model')}' but model self-reports as '{identified_name}'{Style.RESET_ALL}")
    
    # Initialize report generator
    reporting_config = config.get('reporting', {})
    if args.report_format:
        reporting_config['format'] = args.report_format
    report_gen = ReportGenerator(reporting_config)
    results = []
    
    try:
        if args.module == 'prompt-injection' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Running Prompt Injection Attacks...{Style.RESET_ALL}")
            module = PromptInjectionModule(llm_client, config, intensity=args.intensity)
            result = module.run_all_attacks()
            results.append(('prompt_injection', result))
            
        if args.module == 'jailbreak' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Running Jailbreak Attacks...{Style.RESET_ALL}")
            module = JailbreakModule(llm_client, config, intensity=args.intensity)
            result = module.run_all_attacks()
            results.append(('jailbreak', result))
            
        if args.module == 'data-extraction' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Running Data Extraction Attacks...{Style.RESET_ALL}")
            module = DataExtractionModule(llm_client, config, intensity=args.intensity)
            result = module.run_all_attacks()
            results.append(('data_extraction', result))
            
        if args.module == 'system-prompt-extraction' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Running System Prompt Extraction Attacks...{Style.RESET_ALL}")
            module = SystemPromptExtractionModule(llm_client, config, intensity=args.intensity)
            result = module.run_all_attacks()
            results.append(('system_prompt_extraction', result))
            
        if args.module == 'adversarial-inputs' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Running Adversarial Input Attacks...{Style.RESET_ALL}")
            module = AdversarialInputsModule(llm_client, config, intensity=args.intensity)
            result = module.run_all_attacks()
            results.append(('adversarial_inputs', result))
            
        if args.module == 'role-confusion' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Running Role Confusion Attacks...{Style.RESET_ALL}")
            module = RoleConfusionModule(llm_client, config, intensity=args.intensity)
            result = module.run_all_attacks()
            results.append(('role_confusion', result))
            
        if args.module == 'context-injection' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Running Context Injection Attacks...{Style.RESET_ALL}")
            module = ContextInjectionModule(llm_client, config, intensity=args.intensity)
            result = module.run_all_attacks()
            results.append(('context_injection', result))
            
        if args.module == 'weight-manipulation' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Running Weight Manipulation Attacks...{Style.RESET_ALL}")
            module = ModelWeightManipulationModule(llm_client, config, intensity=args.intensity)
            result = module.run_all_attacks()
            results.append(('weight_manipulation', result))
        
        if args.module == 'multi-turn' or (args.module == 'all' and config.get('attacks', {}).get('enable_multi_turn', True)):
            print(f"\n{Fore.CYAN}[*] Running Multi-Turn Attacks...{Style.RESET_ALL}")
            module = MultiTurnModule(llm_client, config, intensity=args.intensity)
            result = module.run_all_attacks()
            results.append(('multi_turn', result))
        
        if args.module == 'defense-tester' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Running Defense Tester (Blue Team)...{Style.RESET_ALL}")
            module = DefenseTester(llm_client, config, intensity=args.intensity)
            sys_prompt = args.system_prompt or "You are a helpful assistant."
            eval_result = module.evaluate_defenses(
                sys_prompt, profile=args.defense_profile
            )
            result = {
                'module': 'defense_tester',
                'intensity': args.intensity,
                'attacks': eval_result['defended']['attacks'],
                'summary': {
                    'total': eval_result['defended']['summary']['total'],
                    'successful': eval_result['defended']['summary']['bypassed'],
                    'failed': eval_result['defended']['summary']['blocked'],
                },
            }
            results.append(('defense_tester', result))
        
        if args.module == 'purple-team' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Running Purple Team Exercise...{Style.RESET_ALL}")
            module = PurpleTeamOrchestrator(llm_client, config, intensity=args.intensity)
            sys_prompt = args.system_prompt or "You are a helpful assistant."
            result = module.run_all_attacks()
            results.append(('purple_team', result))
        
        if args.module == 'multimodal-injection' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Running Multimodal Injection Attacks...{Style.RESET_ALL}")
            module = MultimodalInjectionModule(llm_client, config, intensity=args.intensity)
            result = module.run_all_attacks()
            results.append(('multimodal_injection', result))
        
        # Red team capabilities modules (LAB SANDBOX USE ONLY)
        if args.module == 'payload-loader' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Testing Payload Loader Module...{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY{Style.RESET_ALL}")
            loader = PayloadLoader(config)
            if loader.enabled:
                # Example: Create encrypted payload
                test_payload = b"print('Test payload - LAB USE ONLY')"
                encrypted = loader.encrypt_payload(test_payload)
                print(f"{Fore.GREEN}[+] Payload encryption test successful{Style.RESET_ALL}")
                results.append(('payload_loader', {'status': 'tested', 'encryption': 'success'}))
            else:
                print(f"{Fore.YELLOW}[!] Payload loader disabled in config{Style.RESET_ALL}")
        
        if args.module == 'persistence' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Testing Persistence Module...{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY{Style.RESET_ALL}")
            persistence = PersistenceModule(config)
            if persistence.enabled:
                # Simulate persistence methods
                import platform
                if platform.system().lower() == 'windows':
                    persistence.simulate_registry_persistence(
                        "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                        "TestApp",
                        "C:\\test\\payload.exe"
                    )
                else:
                    persistence.simulate_startup_script("~/.test_script.sh", "/tmp/payload.sh")
                persistence.save_persistence_report()
                results.append(('persistence', {'status': 'simulated', 'methods': len(persistence.get_all_persistence_methods())}))
            else:
                print(f"{Fore.YELLOW}[!] Persistence disabled in config{Style.RESET_ALL}")
        
        if args.module == 'c2-communication' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Testing C2 Communication Module...{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY{Style.RESET_ALL}")
            c2 = C2Communication(config)
            if c2.enabled:
                # Send test beacon
                beacon_result = c2.send_beacon()
                results.append(('c2_communication', {'status': 'tested', 'beacon': beacon_result}))
            else:
                print(f"{Fore.YELLOW}[!] C2 communication disabled in config{Style.RESET_ALL}")
        
        if args.module == 'data-exfiltration' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Testing Data Exfiltration Module...{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY{Style.RESET_ALL}")
            exfil = DataExfiltrationModule(config)
            if exfil.enabled:
                # Simulate data collection
                collection_result = exfil.simulate_data_collection(duration=5)
                results.append(('data_exfiltration', {'status': 'simulated', 'data': collection_result}))
            else:
                print(f"{Fore.YELLOW}[!] Data exfiltration disabled in config{Style.RESET_ALL}")
        
        if args.module == 'polymorphic-encoding' or args.module == 'all':
            print(f"\n{Fore.CYAN}[*] Testing Polymorphic Encoding Module...{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY{Style.RESET_ALL}")
            encoder = PolymorphicEncoder(config)
            if encoder.enabled:
                # Test encoding
                test_data = b"Test payload for polymorphic encoding"
                encoded = encoder.polymorphic_encode_payload(test_data, method='combined')
                decoded = encoder.polymorphic_decode_payload(
                    encoded['encoded'],
                    encoded['method'],
                    encoded['key']
                )
                if decoded == test_data:
                    print(f"{Fore.GREEN}[+] Polymorphic encoding test successful{Style.RESET_ALL}")
                    results.append(('polymorphic_encoding', {'status': 'tested', 'encoding': 'success'}))
            else:
                print(f"{Fore.YELLOW}[!] Polymorphic encoding disabled in config{Style.RESET_ALL}")
        
        # Comparison mode -- run against multiple targets
        if args.module == 'comparison' or args.comparison:
            print(f"\n{Fore.CYAN}[*] Running Multi-Model Comparison...{Style.RESET_ALL}")
            comparison_config = config.get('comparison', {})
            if not comparison_config.get('targets'):
                print(f"{Fore.YELLOW}[!] No comparison targets defined in config{Style.RESET_ALL}")
            else:
                runner = ComparisonRunner(config, intensity=args.intensity)
                comp_result = runner.run_comparison()
                results.append(('comparison', comp_result))
        
        # Generate report
        print(f"\n{Fore.CYAN}[*] Generating report...{Style.RESET_ALL}")
        llm_stats = llm_client.get_stats() if hasattr(llm_client, 'get_stats') else None
        report_path = report_gen.generate_report(results, 
                                                output_path=args.output,
                                                verbose=args.verbose,
                                                llm_stats=llm_stats,
                                                model_identity=model_identity)
        
        print(f"\n{Fore.GREEN}[+] Red teaming complete!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[+] Report saved to: {report_path}{Style.RESET_ALL}")
        
        # Print summary
        total_attacks = sum(len(r['attacks']) for _, r in results)
        successful = sum(sum(1 for a in r['attacks'] if a.get('success', False)) 
                        for _, r in results)
        print(f"\n{Fore.YELLOW}[*] Summary:{Style.RESET_ALL}")
        print(f"  Total attacks: {total_attacks}")
        print(f"  Successful: {Fore.RED}{successful}{Style.RESET_ALL}")
        print(f"  Failed: {Fore.GREEN}{total_attacks - successful}{Style.RESET_ALL}")
        
        # Determine the HTML report path and serve it
        if not args.no_serve:
            html_report = report_path
            if not html_report.endswith('.html'):
                html_report = os.path.splitext(html_report)[0] + '.html'
            if not os.path.exists(html_report):
                # Search for any HTML report in the output directory
                report_dir = os.path.dirname(html_report) or reporting_config.get('output_dir', 'reports')
                html_files = sorted(
                    [f for f in os.listdir(report_dir) if f.endswith('.html')],
                    key=lambda f: os.path.getmtime(os.path.join(report_dir, f)),
                    reverse=True,
                ) if os.path.isdir(report_dir) else []
                if html_files:
                    html_report = os.path.join(report_dir, html_files[0])
            
            if os.path.exists(html_report):
                serve_dashboard(html_report, host=args.serve_host, port=args.serve_port)
            else:
                print(f"{Fore.YELLOW}[!] No HTML report found to serve{Style.RESET_ALL}")
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Interrupted by user{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        print(f"{Fore.RED}[!] Error: {e}{Style.RESET_ALL}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

