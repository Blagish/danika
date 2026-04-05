def _bold(n: int) -> str:
    return f"[**{n}**]"


def _parens(trace: str) -> str:
    """Оборачивает в скобки, если trace содержит сложение/вычитание или начинается как отрицательное число."""
    if " + " in trace or " - " in trace or trace.startswith("-"):
        return f"({trace})"
    return trace


def _pick_trace(rolls: list[int], take: int, highest: bool) -> str:
    """Форматирует броски pick: взятые кубы жирным, отброшенные зачёркнутым."""
    selected = sorted(rolls, reverse=highest)[:take]
    remaining = list(selected)
    parts = []
    for r in rolls:
        if r in remaining:
            remaining.remove(r)
            parts.append(_bold(r))
        else:
            parts.append(f"~~{r}~~")
    return " + ".join(parts)


def _adv_trace(rolls: list[int], highest: bool) -> str:
    """Форматирует броски преимущества/помехи: выигравший бросок жирным, проигравший зачеркнутым."""
    winner, loser = (max(rolls), min(rolls)) if highest else (min(rolls), max(rolls))
    prefix = "a" if highest else "d"
    return f"{prefix}[**{winner}**|~~{loser}~~]"
