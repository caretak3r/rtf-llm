
"""
Module for System Prompt and RAG Context Theft.
"""

class RAGContextTheftAttack:
    def __init__(self):
        self.name = "System Prompt and RAG Context Theft"
        self.description = (
            "Retrieval-Augmented Generation (RAG) systems automatically search for contextually relevant "
            "private files or logs and inject them into the LLM's prompt behind the scenes to generate "
            "better answers. Attackers can use manipulative phrasing to force the model to ignore its "
            "initial instructions and reveal the hidden system prompt or the sensitive context injected via RAG."
        )
        self.example = (
            "During a demonstration against an AI chat application connected to a database of "
            "synthetic emails, the attacker bypassed the explicit 'Do not share personal information "
            "or secrets' instruction by telling the model to write its output backwards. The model then "
            "leaked the hidden system prompt. In another instance, after clearing the chat history, "
            "the attacker repeatedly demanded the new admin credentials, and the model successfully "
            "extracted and printed the passwords straight out of the hidden RAG context. Additionally, "
            "the automated 'Rag Thief' attack utilizes an LLM to systematically ask for fragments of data, "
            "allowing it to extract up to 70% of a target's entire RAG knowledge base piece by piece."
        )

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "example": self.example
        }
