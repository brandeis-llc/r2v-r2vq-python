from typing import Optional, Dict, List

import conllu

from r2vq_conllu.data import Sentence, Span, Relation


def _decode_bio(sentence: Sentence) -> List[Span]:
    full_labels = [tok.entity for tok in sentence.tokens]
    if not all(full_labels):
        return []

    labels = [
        label.split("-") if label is not "O" else ["O", "O"] for label in full_labels
    ]
    labels_len = len(labels)

    spans = []
    start_idx = 0
    for idx, (tag, e_type) in enumerate(labels):
        if tag == "O":
            start_idx = idx + 1
        elif tag in "BI" and (idx + 1 == labels_len or labels[idx + 1][0] in "BO"):
            curr_idx = idx + 1
            spans.append(
                Span.from_entity(
                    "::".join([sentence.id, str(start_idx).zfill(3)]),
                    sentence,
                    start_idx,
                    idx + 1,
                    e_type,
                )
            )
            start_idx = curr_idx
    return spans


def _decode_hidden(sentence: Sentence) -> List[Span]:
    spans = []
    for i, token in enumerate(sentence.tokens):
        hidden = token.hidden
        if hidden:
            for k in hidden:
                for hi, v in enumerate(hidden[k]):
                    span_id = "::".join([sentence.id, "hidden", str(i).zfill(2), k, str(hi).zfill(2)])
                    spans.append(Span.from_hidden(span_id, sentence, i, k, v))
    return spans


def _get_relations(spans: List[Span]) -> List[Relation]:
    events_mapping: Dict[int, Relation] = {
        span.start_pos: Relation(span) for span in spans if span.label == "EVENT"
    }
    for span in spans:
        if span.participant_of is not None:
            if span.label.endswith("INGREDIENT"):
                events_mapping[span.participant_of].ingre_participants = span
            elif span.label.endswith("TOOL"):
                events_mapping[span.participant_of].tool_participants = span
            elif span.label.endswith("HABITAT"):
                events_mapping[span.participant_of].habitat_participants = span
        elif span.result_of is not None:
            events_mapping[span.result_of].ingre_results = span
    return list(events_mapping.values())


def _parse_hidden_value(value: str) -> Optional[Dict[str, List[str]]]:
    hidden_dict = conllu.parser.parse_dict_value(value)
    if hidden_dict:
        return {k: v.split(":") for k, v in hidden_dict.items() if v}
    return None


def clean_conllu_empty_line(in_file, out_file) -> None:
    out_f = open(out_file, "w")
    with open(in_file, "r") as in_f:
        for line in in_f:
            out_f.write(line.strip() + "\n")
