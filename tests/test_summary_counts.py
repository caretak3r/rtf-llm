# Mirrors the fixed aggregation in main.py so a regression re-introduces a failure here.
def module_counts(r):
    attacks = r.get('attacks') or []
    if attacks:
        total = len(attacks)
        succ = sum(1 for a in attacks if a.get('success', False))
        canary = sum(1 for a in attacks if a.get('canary_leaked', False))
        return total, succ, canary
    summary = r.get('summary', {})
    return summary.get('total', 0), summary.get('successful', 0), 0


def test_attack_shaped_result():
    r = {'attacks': [{'success': True, 'canary_leaked': True},
                     {'success': False}]}
    assert module_counts(r) == (2, 1, 1)


def test_comparison_shaped_result_no_attacks_key():
    r = {'module': 'comparison',
         'combined_summary': {'total_attacks': 5},
         'summary': {'total': 5, 'successful': 2}}
    # No 'attacks' key -> must not raise; falls back to summary.
    assert module_counts(r) == (5, 2, 0)


def test_lab_module_shaped_result():
    r = {'status': 'tested', 'encryption': 'success'}  # payload_loader shape
    assert module_counts(r) == (0, 0, 0)
