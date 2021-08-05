from typing import Optional, Dict, List

import conllu

from r2vq_conllu.data import (
    Sentence,
    Span,
    Relation,
    Argument,
    Predicate,
    CookingEvent,
    EventVerb,
)


def _decode_crl_bio(sentence: Sentence) -> List[Span]:
    full_labels = [tok.entity for tok in sentence.tokens]

    labels = [
        label.split("-") if label and label is not "O" else ["O", "O"]
        for label in full_labels
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
                    "::".join([sentence.id, str(start_idx).zfill(3), "CRL"]),
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
                    span_id = "::".join(
                        [
                            sentence.id,
                            "hidden",
                            str(i).zfill(2),
                            k,
                            str(hi).zfill(2),
                            "CRL",
                        ]
                    )
                    spans.append(Span.from_hidden(span_id, sentence, i, k, v))
    return spans


def _decode_srl_bio(sentence: Sentence) -> List[List[Argument]]:
    args1 = [tok.arg_pred1 for tok in sentence.tokens]
    args2 = [tok.arg_pred2 for tok in sentence.tokens]
    args3 = [tok.arg_pred3 for tok in sentence.tokens]
    args4 = [tok.arg_pred4 for tok in sentence.tokens]
    args5 = [tok.arg_pred5 for tok in sentence.tokens]
    arguments = []

    for i, full_labels in enumerate([args1, args2, args3, args4, args5]):
        pred_args = []

        labels = [
            label.split("-", 1) if label and label is not "O" else ["O", "O"]
            for label in full_labels
        ]
        labels_len = len(labels)

        start_idx = 0
        for idx, (tag, e_type) in enumerate(labels):
            if tag == "O":
                start_idx = idx + 1
            elif tag in "BI" and (idx + 1 == labels_len or labels[idx + 1][0] in "BO"):
                curr_idx = idx + 1
                pred_args.append(
                    Argument.from_arguments(
                        "::".join(
                            [sentence.id, str(start_idx).zfill(3), "SRL", str(i)]
                        ),
                        sentence,
                        start_idx,
                        idx + 1,
                        e_type,
                    )
                )
                start_idx = curr_idx
        if pred_args:
            arguments.append(pred_args)
    return arguments


def _get_predicates(spans: List[List[Argument]]) -> List[Predicate]:
    preds = []
    for args in spans:
        head = None
        others = []
        for arg in args:
            if arg.label == "V":
                head = arg
            else:
                others.append(arg)
        pred = Predicate(head, head.sent[head.start_pos].predicate)
        for arg in others:
            if arg.label == "Patient":
                pred.patient = arg
            elif arg.label == "Location":
                pred.location = arg
            elif arg.label == "Result":
                pred.result = arg
            elif arg.label == "Time":
                pred.time = arg
            elif arg.label == "Instrument":
                pred.instrument = arg
            elif arg.label == "Theme":
                pred.theme = arg
            elif arg.label == "Destination":
                pred.destination = arg
            elif arg.label == "Attribute":
                pred.attribute = arg
            elif arg.label == "Extent":
                pred.extent = arg
            elif arg.label == "Purpose":
                pred.purpose = arg
            elif arg.label == "Co-Patient":
                pred.co_patient = arg
        preds.append(pred)
    return preds


def _get_relations(spans: List[Span]) -> List[Relation]:
    events_mapping: Dict[int, Relation] = {
        span.start_pos: Relation(span) for span in spans if span.label == "EVENT"
    }
    for span in spans:
        if span.participant_of is not None:
            if span.label.startswith("RESULT"):
                events_mapping[span.result_of].ingre_results = span
            if span.label.endswith("INGREDIENT"):
                events_mapping[span.participant_of].ingre_participants = span
            elif span.label.endswith("TOOL"):
                events_mapping[span.participant_of].tool_participants = span
            elif span.label.endswith("HABITAT"):
                events_mapping[span.participant_of].habitat_participants = span
        elif span.result_of is not None:
            events_mapping[span.result_of].ingre_results = span
    return list(events_mapping.values())


def _get_cooking_events(
    sent: Sentence, rels: List[Relation], preds: List[Predicate]
) -> List[CookingEvent]:
    c_events = []
    rels_dict = {rel.event.id.rsplit("::", 1)[0]: rel for rel in rels}
    pred_dict = {pred.head.id.rsplit("::", 2)[0]: pred for pred in preds}
    for i, tok in enumerate(sent.tokens):
        tok_id = "::".join([sent.id, str(i).zfill(3)])
        if tok.entity == "B-EVENT" and tok.predicate:
            verb = rels_dict[tok_id].event
            verb_obj = EventVerb(
                tok_id, verb.sent, verb.start_pos, verb.end_pos, verb.text, verb.lemma
            )
            c_events.append(
                CookingEvent(verb_obj, pred_dict[tok_id], rels_dict[tok_id])
            )
        elif tok.entity == "B-EVENT":
            verb = rels_dict[tok_id].event
            verb_obj = EventVerb(
                tok_id, verb.sent, verb.start_pos, verb.end_pos, verb.text, verb.lemma
            )
            c_events.append(CookingEvent(verb_obj, None, rels_dict[tok_id]))
        elif tok.predicate:
            verb = pred_dict[tok_id].head
            verb_obj = EventVerb(
                tok_id, verb.sent, verb.start_pos, verb.end_pos, verb.text, verb.lemma
            )
            c_events.append(CookingEvent(verb_obj, pred_dict[tok_id], None))
    return c_events


def _parse_hidden_value(value: str) -> Optional[Dict[str, List[str]]]:
    hidden_dict = conllu.parser.parse_dict_value(value)
    if hidden_dict:
        return {
            k: [e.strip() for e in v.split(":")] for k, v in hidden_dict.items() if v
        }
    return None


def _parse_coref_value(value: str) -> Optional[int]:
    if value == "_":
        return None
    term, coref_id = value.split(".", 1)
    return int(coref_id.replace(".", ""))


def clean_conllu_empty_line(in_file, out_file) -> None:
    out_f = open(out_file, "w")
    with open(in_file, "r") as in_f:
        for line in in_f:
            out_f.write(line.strip() + "\n")
