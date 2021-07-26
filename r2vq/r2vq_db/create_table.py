from r2vq_db import db
from r2vq_db.models import Span, Relation
from r2vq_conllu.ingest import ingest_r2vq_connlu
from itertools import product


def create_tables(csv_file: str):
    db.connect()
    db.create_tables([Span, Relation])
    recipe = ingest_r2vq_connlu(csv_file)[0]
    spans = [
        {
            "uid": span.id,
            "lemma": span.lemma,
            "label": span.label,
            "coreference": span.coref_id,
        }
        for span in recipe.spans
    ]
    relations = []
    for rel in recipe.relations:
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
        keys = ["event", "ingre_par", "tool_par", "habitat_par", "ingre_res"]
        for combination in combinations:
            relations.append({k: v for k, v in zip(keys, combination)})
    with db.atomic():
        Span.insert_many(spans).execute()
        Relation.insert_many(relations).execute()
    db.close()


if __name__ == "__main__":
    create_tables("../r2vq_conllu_data/trial_recipes.conllu.annotation.csv")
