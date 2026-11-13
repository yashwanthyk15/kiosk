import unicodedata
from difflib import SequenceMatcher

from backend.menu import ITEM_ALIASES

QUANTITIES = {
    "zero": 0,
    "none": 0,
    "both": 2,
    "ಸೊನ್ನೆ": 0,
    "ಶೂನ್ಯ": 0,
    "ಒಂದು": 1,
    "ಒಂದೇ": 1,
    "ಇನ್ನೊಂದು": 1,
    "ಒಂದ್": 1,
    "ಒಂದ": 1,
    "ಒಂದನ್ನು": 1,
    "ಒಂದನ್ನ": 1,
    "ಒಂದಕ್ಕೆ": 1,
    "ಒಂದರಿಂದ": 1,
    "ಎರಡು": 2,
    "ಎರಡೇ": 2,
    "ಎರಡೂ": 2,
    "ಎರಡನ್ನು": 2,
    "ಎರಡನ್ನ": 2,
    "ಎರಡಕ್ಕೆ": 2,
    "ಎರಡರಿಂದ": 2,
    "ಮೂರು": 3,
    "ಮೂರನ್ನು": 3,
    "ಮೂರನ್ನ": 3,
    "ಮೂರಕ್ಕೆ": 3,
    "ಮೂರರಿಂದ": 3,
    "ನಾಲ್ಕು": 4,
    "ನಾಲ್ಕನ್ನು": 4,
    "ನಾಲ್ಕನ್ನ": 4,
    "ನಾಲ್ಕಕ್ಕೆ": 4,
    "ನಾಲ್ಕರಿಂದ": 4,
    "ಐದು": 5,
    "ಐದನ್ನು": 5,
    "ಐದನ್ನ": 5,
    "ಐದಕ್ಕೆ": 5,
    "ಐದರಿಂದ": 5,
    "ಆರು": 6,
    "ಆರನ್ನು": 6,
    "ಆರನ್ನ": 6,
    "ಆರಕ್ಕೆ": 6,
    "ಆರಿಂದ": 6,
    "ಏಳು": 7,
    "ಏಳನ್ನು": 7,
    "ಏಳನ್ನ": 7,
    "ಏಳಕ್ಕೆ": 7,
    "ಏಳರಿಂದ": 7,
    "ಎಂಟು": 8,
    "ಎಂಟನ್ನು": 8,
    "ಎಂಟನ್ನ": 8,
    "ಎಂಟಕ್ಕೆ": 8,
    "ಎಂಟರಿಂದ": 8,
    "ಒಂಬತ್ತು": 9,
    "ಒಂಬತ್ತನ್ನು": 9,
    "ಒಂಬತ್ತನ್ನ": 9,
    "ಒಂಬತ್ತಕ್ಕೆ": 9,
    "ಒಂಬತ್ತರಿಂದ": 9,
    "ಹತ್ತು": 10,
    "ಹತ್ತನ್ನು": 10,
    "ಹತ್ತನ್ನ": 10,
    "ಹತ್ತಕ್ಕೆ": 10,
    "ಹತ್ತರಿಂದ": 10,
    "பூஜ்ஜியம்": 0,
    "பூஜ்ஜியமாக": 0,
    "சுழியம்": 0,
    "ஒன்று": 1,
    "ஒரு": 1,
    "ஒன்றை": 1,
    "ஒன்றுக்கு": 1,
    "ஒன்றாக": 1,
    "இரண்டு": 2,
    "ரெண்டு": 2,
    "இரண்டை": 2,
    "இரண்டுக்கு": 2,
    "இரண்டாக": 2,
    "மூன்று": 3,
    "மூணு": 3,
    "மூன்றை": 3,
    "மூன்றுக்கு": 3,
    "மூன்றாக": 3,
    "நான்கு": 4,
    "நாலு": 4,
    "நான்கை": 4,
    "நான்குக்கு": 4,
    "நான்காக": 4,
    "ஐந்தாக": 5,
    "ஐந்து": 5,
    "அஞ்சு": 5,
    "ஆறு": 6,
    "ஆறாக": 6,
    "ஏழு": 7,
    "ஏழாக": 7,
    "எட்டு": 8,
    "எட்டாக": 8,
    "ஒன்பது": 9,
    "ஒன்பதாக": 9,
    "பத்து": 10,
    "பத்தாக": 10,
    "సున్నా": 0,
    "సున్నాగా": 0,
    "శూన్యం": 0,
    "ఒకటి": 1,
    "ఒక": 1,
    "ఒక్క": 1,
    "ఒకటిని": 1,
    "ఒకటికి": 1,
    "ఒకటిగా": 1,
    "రెండు": 2,
    "రెండూ": 2,
    "రెండింటిని": 2,
    "రెండుకు": 2,
    "రెండుగా": 2,
    "మూడు": 3,
    "మూడింటిని": 3,
    "మూడుకు": 3,
    "మూడుగా": 3,
    "నాలుగు": 4,
    "నాలుగుగా": 4,
    "నాలుగింటిని": 4,
    "ఐదు": 5,
    "ఐదుగా": 5,
    "ఆరు": 6,
    "ఆరుగా": 6,
    "ఏడు": 7,
    "ఏడుగా": 7,
    "ఎనిమిది": 8,
    "ఎనిమిదిగా": 8,
    "తొమ్మిది": 9,
    "తొమ్మిదిగా": 9,
    "పది": 10,
    "పదిగా": 10,
    "one": 1,
    "a": 1,
    "an": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}
SET_QUANTITY_FORMS = {
    "ಒಂದಕ್ಕೆ", "ಎರಡಕ್ಕೆ", "ಮೂರಕ್ಕೆ", "ನಾಲ್ಕಕ್ಕೆ", "ಐದಕ್ಕೆ", "ಆರಕ್ಕೆ",
    "ಏಳಕ್ಕೆ", "ಎಂಟಕ್ಕೆ", "ಒಂಬತ್ತಕ್ಕೆ", "ಹತ್ತಕ್ಕೆ",
    "பூஜ்ஜியமாக", "ஒன்றாக", "இரண்டாக", "மூன்றாக", "நான்காக", "ஐந்தாக",
    "ஆறாக", "ஏழாக", "எட்டாக", "ஒன்பதாக", "பத்தாக",
    "సున్నాగా", "ఒకటికి", "ఒకటిగా", "రెండుకు", "రెండుగా", "మూడుకు", "మూడుగా",
    "నాలుగుగా", "ఐదుగా", "ఆరుగా", "ఏడుగా", "ఎనిమిదిగా",
    "తొమ్మిదిగా", "పదిగా",
}
INDIC_DIGITS = str.maketrans("೦೧೨೩೪೫೬೭೮೯௦௧௨௩௪௫௬௭௮௯౦౧౨౩౪౫౬౭౮౯", "012345678901234567890123456789")
CONJUNCTIONS = {
    "ಮತ್ತು", "ಹಾಗೂ", "and", "plus", "ತದನಂತರ",
    "மற்றும்", "மேலும்", "మరియు", "ఇంకా",
}
ITEM_SUFFIXES = (
    "ಯನ್ನು", "ಗಳನ್ನು", "ವನ್ನು", "ಅನ್ನು", "ನ್ನು", "ನಲ್ಲಿ", "ಗೆ", "ಕ್ಕೆ",
    "களை", "களைத்", "யை", "ஐ", "க்கு", "க்காக", "இல்",
    "ని", "ను", "లు", "కి", "కు", "గా", "లో",
)


def _quantity_at(tokens: list[str], index: int) -> int | None:
    if index < 0 or index >= len(tokens):
        return None
    value = tokens[index]
    if value.isdigit():
        return int(value)
    return QUANTITIES.get(value)


def _matches_alias_token(token: str, alias_token: str) -> bool:
    if token == alias_token:
        return True
    return any(
        token == f"{alias_token}{suffix}"
        for suffix in ITEM_SUFFIXES
    )


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(INDIC_DIGITS).lower()
    return "".join(
        character
        if character.isspace() or unicodedata.category(character)[0] in ("L", "M", "N")
        else " "
        for character in text
    )


def fuzzy_item(token: str) -> str | None:
    """Return a canonical item for a close spelling, without deciding quantities."""
    candidate = normalize(token).strip()
    exact_matches = [
        item
        for item, aliases in ITEM_ALIASES.items()
        if any(candidate == normalize(alias) for alias in aliases)
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        return None

    scores = []
    for item, aliases in ITEM_ALIASES.items():
        if item == "bill":
            continue
        scores.extend(
            (SequenceMatcher(None, candidate, normalized).ratio(), item)
            for alias in aliases
            if len(candidate) >= 4
            and len(normalized := normalize(alias)) >= 4
            and all(ord(character) < 128 for character in candidate)
            and all(ord(character) < 128 for character in normalized)
        )
    if not scores:
        return None
    scores.sort(reverse=True)
    if scores[0][0] < 0.78:
        return None
    if len(scores) > 1 and scores[0][0] == scores[1][0] and scores[0][1] != scores[1][1]:
        return None
    return scores[0][1]


def match_order(transcript: str, expected: dict[str, int]) -> dict:
    tokens = normalize(transcript).split()
    found = {item: 0 for item in expected}
    matched_terms: list[str] = []
    matches: list[dict] = []
    aliases = {
        item: sorted(
            (normalize(alias).split() for alias in ITEM_ALIASES.get(item, ())),
            key=len,
            reverse=True,
        )
        for item in expected
    }

    index = 0
    while index < len(tokens):
        match = None
        for item, item_aliases in aliases.items():
            for alias_tokens in item_aliases:
                end = index + len(alias_tokens)
                if end <= len(tokens) and all(
                    _matches_alias_token(token, alias_token)
                    for token, alias_token in zip(tokens[index:end], alias_tokens)
                ):
                    match = (item, end, " ".join(alias_tokens))
                    break
            if match:
                break

        if match is None:
            item = fuzzy_item(tokens[index])
            if item in expected:
                match = (item, index + 1, tokens[index])

        if match is None:
            index += 1
            continue

        item, end, matched_term = match
        matched_terms.append(matched_term)
        matches.append({
            "key": item,
            "quantity": 1,
            "explicit_quantity": False,
            "start": index,
            "end": end,
            "matched_term": matched_term,
        })
        index = end

    quantity_positions = [
        position
        for position, token in enumerate(tokens)
        if _quantity_at(tokens, position) is not None
        and not any(match["start"] <= position < match["end"] for match in matches)
    ]
    if matches and quantity_positions:
        first_quantity = quantity_positions[0]
        quantity_follows_first_item = first_quantity >= matches[0]["end"]
        available_quantities = set(quantity_positions)

        for match_index, match in enumerate(matches):
            previous_end = matches[match_index - 1]["end"] if match_index else 0
            next_start = (
                matches[match_index + 1]["start"]
                if match_index + 1 < len(matches)
                else len(tokens)
            )
            prefix_quantities = [
                position
                for position in available_quantities
                if previous_end <= position < match["start"]
            ]
            suffix_quantities = [
                position
                for position in available_quantities
                if match["end"] <= position < next_start
                and not any(
                    token in CONJUNCTIONS
                    for token in tokens[match["end"]:position]
                )
            ]
            if quantity_follows_first_item:
                candidates = suffix_quantities or prefix_quantities
                select_earliest = bool(suffix_quantities)
            else:
                candidates = prefix_quantities or suffix_quantities
                select_earliest = not bool(prefix_quantities)
            if not candidates:
                continue

            quantity_position = min(candidates) if select_earliest else max(candidates)
            match["quantity"] = _quantity_at(tokens, quantity_position) or 0
            match["explicit_quantity"] = True
            available_quantities.remove(quantity_position)

    for match in matches:
        found[match["key"]] += match["quantity"]

    return {
        "matched": found == expected,
        "found": found,
        "expected": expected,
        "matched_terms": matched_terms,
        "matches": matches,
    }
