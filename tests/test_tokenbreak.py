from modules.adversarial_inputs import AdversarialInputsModule


def test_tokenbreak_patterns_present():
    module = AdversarialInputsModule.__new__(AdversarialInputsModule)
    patterns = module._get_tokenbreak_patterns()
    assert isinstance(patterns, list)
    assert len(patterns) >= 3
    # Spot-check at least one payload looks like a tokenizer trick
    combined = " ".join(patterns).lower()
    assert any(word in combined for word in ["token", "over-ride", "bypass", "decode"])


def test_tokenbreak_registered_in_adversarial_patterns():
    module = AdversarialInputsModule.__new__(AdversarialInputsModule)
    patterns = module._load_adversarial_patterns()
    assert "tokenbreak" in patterns
    assert len(patterns["tokenbreak"]) > 0


def test_tokenbreak_in_technique_kb():
    from modules.technique_kb import TECHNIQUE_INFO
    assert "tokenbreak" in TECHNIQUE_INFO
    assert "description" in TECHNIQUE_INFO["tokenbreak"]
    assert "defense" in TECHNIQUE_INFO["tokenbreak"]
