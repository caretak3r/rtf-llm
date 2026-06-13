
"""
Module for Indirect Prompt Injection.
"""

class IndirectPromptInjectionAttack:
    def __init__(self):
        self.name = "Indirect Prompt Injection"
        self.description = (
            "This attack targets users who utilize AI assistants (like Copilot or Gemini) to "
            "summarize or interact with their own private data, such as emails. Attackers hide "
            "malicious instructions inside an incoming email or document. When the victim's AI "

            "assistant scans that document to answer a question or summarize it, the hidden "
            "instructions hijack the AI, forcing it to execute commands on the attacker's behalf without "
            "the user realizing it."
        )
        self.example = (
            "An attacker sends an email containing hidden text. When the user asks Microsoft "
            "Copilot to summarize their inbox, Copilot reads the hidden text, which instructs it "
            "to grab sensitive data from the user's environment, format it into a Markdown link "
            "(to bypass Microsoft's external link blocks), and present it to the user. If the "
            "user clicks the seemingly innocuous link, their private data is secretly exfiltrated "
            "via the URL parameters. In another instance involving Google Gemini, hidden email "
            "instructions forced the summarizer to display a phishing phone number for the "
            "user to call immediately."
        )

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "example": self.example
        }
