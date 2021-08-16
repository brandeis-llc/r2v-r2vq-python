import itertools
from typing import Sequence, List, Tuple

import conllu
from conllu import parse_incr

from r2vq.annotation.models import (
    Token,
    Recipe,
    Sentence,
    Ingredient,
    Span,
    Relation,
    Argument,
    Predicate,
    FullEvent,
)
from r2vq.annotation.helper import (
    _decode_hidden,
    _decode_crl_bio,
    _decode_srl_bio,
    _get_relations,
    _get_predicates,
    _get_full_events,
    _parse_hidden_value,
)

INGREDIENT = "ingredients"
STEP = "step"


def ingest_r2vq_connlu(conllu_file: str) -> Tuple[List[Recipe], List[conllu.TokenList]]:
    # column names
    custom_cols_and_parsers = {
        "entity": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
        "participant_of": lambda line, i: conllu.parser.parse_int_value(line[i]),
        "result_of": lambda line, i: conllu.parser.parse_int_value(line[i]),
        "hidden": lambda line, i: _parse_hidden_value(line[i]),
        "coreference": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
        "predicate": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
        "arg_pred1": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
        "arg_pred2": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
        "arg_pred3": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
        "arg_pred4": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
        "arg_pred5": lambda line, i: conllu.parser.parse_nullable_value(line[i]),
    }
    r2vq_conllu_fields = list(conllu.parser.DEFAULT_FIELDS[:4]) + list(custom_cols_and_parsers.keys())

    conllu_f = open(conllu_file, "r", encoding="utf-8")
    sentences = parse_incr(
        conllu_f, fields=r2vq_conllu_fields, field_parsers=custom_cols_and_parsers
    )

    recipe_id = ""
    recipe_sents: List[Sentence] = []
    recipe_ingres: List[Ingredient] = []
    recipe_spans: List[Span] = []
    recipe_relations: List[Relation] = []
    recipe_arguments: List[Argument] = []
    recipe_predicates: List[Predicate] = []
    recipe_full_events: List[FullEvent] = []

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
                        recipe_full_events,
                    )
                )
                recipe_sents = []
                recipe_ingres = []
                recipe_spans = []
                recipe_relations = []
                recipe_arguments = []
                recipe_predicates = []
                recipe_full_events = []
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
            full_events = _get_full_events(sentence, rels, preds)
            recipe_full_events.extend(full_events)

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
                recipe_full_events,
            )
        )
    conllu_f.close()
    with open(conllu_file, "r", encoding="utf-8") as f:
        sentences = list(
            parse_incr(f, fields=r2vq_conllu_fields, field_parsers=custom_cols_and_parsers)
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
    events = recipe.full_events
    for e in events:
        print(e.predicate)
        print(e.relation)
        print("==" * 20)


if __name__ == "__main__":
    recipes, sentences = ingest_r2vq_connlu(
        "trial_all_formatted_corrected.csv"
    )
    test_recipe(recipes[0])
