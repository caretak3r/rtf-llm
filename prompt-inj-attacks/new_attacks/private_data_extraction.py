
"""
Module for Extraction of Private Data from Fine-Tuned Models.
"""

class PrivateDataExtractionAttack:
    def __init__(self):
        self.name = "Extraction of Private Data from Fine-Tuned Models"
        self.description = (
            "Fine-tuning involves adding specialized, often private, training data to a model. "
            "Even if the resulting model is explicitly trained with safety guardrails to withhold "
            "personal identifiable information (PII) or secrets, attackers can exploit the probabilistic "
            "nature of neural networks. By persistently asking questions or demanding more information, "
            "the model's safety alignments can be broken down until it outputs the restricted data as a statistical outlier."
        )
        self.example = (
            "An attacker targeted a Llama 3.2 model fine-tuned on synthetic private data. "
            "After asking for the details of a specific individual, the model initially refused, "

            "stating it could not provide private information on citizens. The attacker simply repeated "
            "the prompts and persistently commanded the model to provide 'more.' Eventually, the model "
            "bypassed its own restrictions and leaked the individual's phone number and passport number."
        )

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "example": self.example
        }
