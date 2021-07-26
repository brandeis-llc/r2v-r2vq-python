from typing import Sequence, List, Tuple, Optional, Dict

import conllu
from conllu import parse_incr

from r2vq_conllu.data import Token, Recipe, Sentence, Ingredient, Span, Relation
from r2vq_conllu.helper import (
    _decode_hidden,
    _decode_bio,
    _get_relations,
    _parse_hidden_value,
)

INGREDIENT = "ingredients"
STEP = "step"


def ingest_r2vq_connlu(conllu_file: str) -> Tuple[List[Recipe], List[conllu.TokenList]]:
    r2vq_conllu_fields = list(conllu.parser.DEFAULT_FIELDS)
    r2vq_fields = ["entity", "participant_of", "result_of", "hidden", "coreference"]
    r2vq_conllu_fields.extend(r2vq_fields)

    custom_parsers = {
        "entity": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
        "participant_of": lambda line, i: conllu.parser.parse_int_value(line[i]),
        "result_of": lambda line, i: conllu.parser.parse_int_value(line[i]),
        "hidden": lambda line, i: _parse_hidden_value(line[i]),
        "coreference": lambda line, i: conllu.parser.parse_int_value(line[i]),
    }
    conllu_f = open(conllu_file, "r", encoding="utf-8")
    sentences = parse_incr(
        conllu_f, fields=r2vq_conllu_fields, field_parsers=custom_parsers
    )

    recipe_id = ""
    recipe_sents: List[Sentence] = []
    recipe_ingres: List[Ingredient] = []
    recipe_spans: List[Span] = []
    recipe_relations: List[Relation] = []
    recipes: List[Recipe] = []

    for sent in sentences:
        if sent.metadata.get("newdoc id"):
            if recipe_id and recipe_sents and recipe_ingres:
                recipes.append(
                    Recipe(
                        recipe_id,
                        recipe_ingres,
                        recipe_sents,
                        recipe_spans,
                        recipe_relations,
                    )
                )
                recipe_sents = []
                recipe_ingres = []
                recipe_spans = []
                recipe_relations = []
            recipe_id = sent.metadata["newdoc id"]
        sent_id = sent.metadata["sent_id"]
        text = sent.metadata["text"]
        tokens = [Token(**tok) for tok in sent]
        if INGREDIENT in sent_id:
            ingredient = Ingredient(sent_id, text, tokens)
            recipe_ingres.append(ingredient)
        elif STEP in sent_id:
            sentence = Sentence(sent_id, text, tokens)
            spans = _decode_bio(sentence) + _decode_hidden(sentence)
            recipe_spans.extend(spans)
            recipe_relations.extend(_get_relations(spans))
            recipe_sents.append(sentence)
        else:
            print(f"cannot identify sent_id: {sent_id}")
    if recipe_id and recipe_sents and recipe_ingres:
        recipes.append(
            Recipe(
                recipe_id, recipe_ingres, recipe_sents, recipe_spans, recipe_relations
            )
        )
    conllu_f.close()
    with open(conllu_file, "r", encoding="utf-8") as f:
        sentences = list(parse_incr(
            f, fields=r2vq_conllu_fields, field_parsers=custom_parsers
        ))
    return recipes, sentences


def write_r2vq_conllu(
    sentences: Sequence[conllu.models.TokenList], out_file: str
) -> None:
    with open(out_file, "w") as f:
        for snt_i, snt in enumerate(sentences):
            if snt.metadata.get("newdoc id") and snt_i:
                f.write("\n" + snt.serialize())
            else:
                f.write(snt.serialize())


def test_recipe(recipe: Recipe) -> None:
    relations = recipe.relations
    for rel in relations:
        print(rel)

    # spans = recipe.spans
    # for span in spans:
    #     print(span.text, span.id)


if __name__ == "__main__":
    recipes, sentences = ingest_r2vq_connlu(
        "../r2vq_conllu_data/trial_recipes.conllu.annotation.csv"
    )
    test_recipe(recipes[0])
