from r2vq_db import db
from r2vq_db.models import Span, Relation
from r2vq_conllu.ingest import ingest_r2vq_connlu
from itertools import product


def create_tables(csv_file: str):
    db.connect()
    db.create_tables([Span, Relation])
    recipes, _ = ingest_r2vq_connlu(csv_file)
    recipe = recipes[0]
    spans = [
        {
            "uid": span.id,
            "lemma": span.lemma,
            "label": span.label,
            "coreference": span.coref_id,
        }
        for span in recipe.spans
    ]
    spans.extend(
        {
            "uid": span.id,
            "lemma": span.lemma,
            "label": span.label,
            "coreference": None,
        }
        for span in recipe.arguments
    )
    spans.extend(
        {
            "uid": span.verb.id,
            "lemma": span.verb.lemma,
            "label": "EventVerb",
            "coreference": None,
        }
        for span in recipe.cooking_events
    )
    relations = []
    crl_keys = ["event", "ingre_par", "tool_par", "habitat_par", "ingre_res"]
    srl_keys = ["head", "patient", "location", "result", "time", "instrument", "theme", "destination", "attribute",
                "extent", "purpose", "co_patient"]
    for ce in recipe.cooking_events:
        rel = ce.relation
        pred = ce.predicate
        if rel:
            event = [rel.event.id]
            ingre_par = (
                [r.id for r in rel.ingre_participants] if rel.ingre_participants else [None]
            )
            tool_par = (
                [r.id for r in rel.tool_participants] if rel.tool_participants else [None]
            )
            habitat_par = (
                [r.id for r in rel.habitat_participants]
                if rel.habitat_participants
                else [None]
            )
            ingre_res = [r.id for r in rel.ingre_results] if rel.ingre_results else [None]
            combinations = product(event, ingre_par, tool_par, habitat_par, ingre_res)
        else:
            combinations = [[None] * len(crl_keys)]

        for combination in combinations:
            relation = {k: v for k, v in zip(crl_keys, combination)}
            relation["event_verb"] = ce.verb.id
            if pred:
                relation["head"] = pred.head.id
                relation.update(
                    {k: pred.__dict__[f"_{k}"].id if pred.__dict__[f"_{k}"] else None for k in srl_keys[1:]})
            else:
                relation["head"] = None
                relation.update({k: None for k in srl_keys[1:]})
            relations.append(relation)

    with db.atomic():
        Span.insert_many(spans).execute()
        Relation.insert_many(relations).execute()
    db.close()


if __name__ == "__main__":
    create_tables("../r2vq_conllu_data/trial_recipes.conllu_ALL_formatted.csv")
