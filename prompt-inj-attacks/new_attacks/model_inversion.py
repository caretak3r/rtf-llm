
"""
Module for Model Inversion Attacks.
"""

class ModelInversionAttack:
    def __init__(self):
        self.name = "Model Inversion Attacks (Data Extraction from Base Models)"
        self.description = (
            "This attack involves prompting Large Language Models (LLMs) to reproduce exact copies of "
            "their underlying training data. Because LLMs absorb vast amounts of text and imagery during training, "
            "specific prompts can effectively trick the model into directly regurgitating copyrighted or private "
0           information that it has memorized."
        )
        self.example = (
            "In the New York Times lawsuit against OpenAI, attackers bypassed paywalls by prompting ChatGPT "
            "with leading questions like, 'what's the first paragraph of article XYZ,' and sequentially asking "
            "for the next paragraphs. This resulted in the verbatim extraction of paywalled content. "
            "Similarly, image generators were prompted to create pictures of specific public figures, "
            "yielding near-identical copies of copyrighted photos sourced from specific media outlets."
        )

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "example": self.example
        }
