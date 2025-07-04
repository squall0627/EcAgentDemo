import re
from typing import LiteralString


def clean_think_output(text: str) -> tuple[str, LiteralString | None]:
    thoughts = re.findall(r"<think>(.*?)</think>", text, flags=re.DOTALL)
    cleaned_text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    return cleaned_text, '\n'.join(thoughts) if thoughts else None
