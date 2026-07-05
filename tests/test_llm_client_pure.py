from modules.llm_client import auto_detect_provider, LLMClient


def test_auto_detect_ollama_by_port():
    assert auto_detect_provider("http://localhost:11434") == "ollama"


def test_auto_detect_lmstudio_by_port():
    assert auto_detect_provider("http://127.0.0.1:1234/v1") == "lmstudio"


def test_auto_detect_openai_by_domain():
    assert auto_detect_provider("https://api.openai.com/v1") == "openai"


def test_auto_detect_unknown_is_custom():
    assert auto_detect_provider("https://example.internal/v1") == "custom"


def test_auto_detect_empty_is_custom():
    assert auto_detect_provider("") == "custom"


def test_extract_first_model_id_openai_shape():
    data = {"data": [{"id": "gpt-4o"}, {"id": "gpt-3.5"}]}
    assert LLMClient._extract_first_model_id(data) == "gpt-4o"


def test_extract_first_model_id_ollama_tags_shape():
    data = {"models": [{"name": "llama3.1"}]}
    assert LLMClient._extract_first_model_id(data) == "llama3.1"


def test_extract_first_model_id_bare_list():
    assert LLMClient._extract_first_model_id(["mistral", "qwen"]) == "mistral"


def test_extract_first_model_id_empty_returns_none():
    assert LLMClient._extract_first_model_id({"data": []}) is None
