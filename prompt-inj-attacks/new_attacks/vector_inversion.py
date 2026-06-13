
"""
Module for Vector Inversion Attacks.
"""

class VectorInversionAttack:
    def __init__(self):
        self.name = "Vector Inversion Attacks"
        self.description = (
            "AI search indices and RAG systems rely on vector databases, which turn text into long "
            "lists of mathematical numbers called vector embeddings. While these numbers look "
            "completely meaningless to a highly specialized human or a traditional PII scanner, "
            "attackers can run these stolen vectors through specialized 'inversion models' "
            "paired with 'corrector models' to accurately reconstruct the original private "
            "text, names, dates, and financial figures."
        )
        self.example = (
            "An attacker used an open-source tool called 'vec2text' against an embedding of a "
            "private medical appointment message. The original sentence contained a "
            "patient's name, an orthopedic diagnosis, a specific date, and a $300 copayment. "
            "The initial inversion model returned a fuzzy, slightly incorrect guess. However, "
            "after running the text through 10 automated mathematical correction steps, "
            "the tool reconstructed the name, the specific date, the surgery type, and "
            "the exact dollar amount perfectly."
        )

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "example": self.example
        }
