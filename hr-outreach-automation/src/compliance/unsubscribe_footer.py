from dataclasses import dataclass


@dataclass
class UnsubscribeFooter:
    text: str

    def render(self) -> str:
        return f"\n\n---\n{self.text}"
