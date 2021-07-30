import itertools
from typing import Sequence, List, Tuple, Optional, Dict

import attr
import conllu
from conllu import parse_incr

from r2vq_conllu.data import (
    Token,
    Recipe,
    Sentence,
    Ingredient,
    Span,
    Relation,
    Argument,
    Predicate,
    CookingEvent,
)
from r2vq_conllu.helper import (
    _decode_hidden,
    _decode_crl_bio,
    _decode_srl_bio,
    _get_relations,
    _get_predicates,
    _get_cooking_events,
    _parse_hidden_value,
    _parse_coref_value,
)

INGREDIENT = "ingredients"
STEP = "step"


def ingest_r2vq_connlu(conllu_file: str) -> Tuple[List[Recipe], List[conllu.TokenList]]:
    # column names
    r2vq_conllu_fields = [
        "id",
        "form",
        "lemma",
        "upos",
        "entity",
        "participant_of",
        "result_of",
        "hidden",
        "coreference",
        "predicate",
        "arg_pred1",
        "arg_pred2",
        "arg_pred3",
        "arg_pred4",
        "arg_pred5",
    ]

    custom_parsers = {
        "entity": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
        "participant_of": lambda line, i: conllu.parser.parse_int_value(line[i]),
        "result_of": lambda line, i: conllu.parser.parse_int_value(line[i]),
        "hidden": lambda line, i: _parse_hidden_value(line[i]),
        "coreference": lambda line, i: _parse_coref_value(line[i]),
        "predicate": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
        "arg_pred1": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
        "arg_pred2": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
        "arg_pred3": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
        "arg_pred4": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
        "arg_pred5": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
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
    recipe_arguments: List[Argument] = []
    recipe_predicates: List[Predicate] = []
    recipe_cooking_events: List[CookingEvent] = []

    recipes: List[Recipe] = []

    for sent in sentences:
        if sent.metadata.get("newdoc id"):
            # start of a new recipe
            if recipe_id and recipe_sents and recipe_ingres:
                recipes.append(
                    Recipe(
                        recipe_id,
                        recipe_ingres,
                        recipe_sents,
                        recipe_spans,
                        recipe_relations,
                        recipe_arguments,
                        recipe_predicates,
                        recipe_cooking_events,
                    )
                )
                recipe_sents = []
                recipe_ingres = []
                recipe_spans = []
                recipe_relations = []
                recipe_arguments = []
                recipe_predicates = []
                recipe_cooking_events = []
            recipe_id = sent.metadata["newdoc id"]
        # get sentence meta and tokens
        sent_id = sent.metadata["sent_id"]
        text = sent.metadata["text"]
        tokens = [Token(**tok) for tok in sent]
        if INGREDIENT in sent_id:
            # sentence as an ingredient
            ingredient = Ingredient(sent_id, text, tokens)
            recipe_ingres.append(ingredient)
        elif STEP in sent_id:
            # sentence as a step
            sentence = Sentence(sent_id, text, tokens)
            spans = _decode_crl_bio(sentence) + _decode_hidden(
                sentence
            )  # get entity spans from the sentence
            recipe_spans.extend(spans)
            rels = _get_relations(spans)
            recipe_relations.extend(rels)  # get relations from the sentence
            recipe_sents.append(sentence)
            args = _decode_srl_bio(sentence)
            recipe_arguments.extend(list(itertools.chain.from_iterable(args)))
            preds = _get_predicates(_decode_srl_bio(sentence))
            recipe_predicates.extend(preds)
            cooking_events = _get_cooking_events(sentence, rels, preds)
            recipe_cooking_events.extend(cooking_events)

        else:
            print(f"cannot identify sent_id: {sent_id}")

    # consume the last recipe
    if recipe_id and recipe_sents and recipe_ingres:
        recipes.append(
            Recipe(
                recipe_id,
                recipe_ingres,
                recipe_sents,
                recipe_spans,
                recipe_relations,
                recipe_arguments,
                recipe_predicates,
                recipe_cooking_events,
            )
        )
    conllu_f.close()
    with open(conllu_file, "r", encoding="utf-8") as f:
        sentences = list(
            parse_incr(f, fields=r2vq_conllu_fields, field_parsers=custom_parsers)
        )
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
    # relations = recipe.relations
    # for rel in relations:
    #     print(rel.event.id)
    # print(len(relations))
    # spans = recipe.spans
    # for span in spans:
    #     print(span.text, span.lemma, span.id)
    # predicates = recipe.predicates
    # for pred in predicates:
    #     print(pred.head.id)
    # print(len(predicates))
    events = recipe.cooking_events
    for e in events:
        print(e.predicate.__dict__["head"].id)


if __name__ == "__main__":
    recipes, sentences = ingest_r2vq_connlu(
        "../r2vq_conllu_data/trial_recipes.conllu_ALL_formatted.csv"
    )
    test_recipe(recipes[0])
