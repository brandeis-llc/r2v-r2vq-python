import random
from typing import Tuple, List, Any, Optional

import attr
import peewee

from r2vq_db.functions import BasicFunctions, FilterFunctions, QueryFunctions
from r2vq_db.models import Span, Relation

from lemminflect import getInflection  # type: ignore


def get_plural_prop(prop: str) -> str:
    *toks, last = prop.split()
    prop_plural = " ".join(toks + [getInflection(last, tag="NNS")[0]])
    return prop_plural


def get_plural_ingre(ingre: str) -> str:
    *toks, last = ingre.split()
    ingre_plural = " ".join(
        toks + [getInflection(last, tag="NNS")[-1]]
    )  # handle mass noun
    return ingre_plural


def get_past_participle(verb: str) -> str:
    first, *toks = verb.split()
    past_p = " ".join([getInflection(first, tag="VBN")[0]] + toks)
    return past_p


basic_f = BasicFunctions()
query_f = QueryFunctions()
filter_f = FilterFunctions()


@attr.s()
class CardinalityQuestions:
    q_template1: str = "How many [PROP] are used?"
    q_template2: str = "How many times the [PROP] is used?"
    q_template3: str = "Are there more [PROP]?"

    def question_answer1(
        self, prop: str, prop_label: str, rid: str = ""
    ) -> Tuple[str, int]:
        question = self.q_template1.replace("[PROP]", get_plural_prop(prop))
        answer = basic_f.count_span(prop, prop_label, unique=True, rid=rid)
        return question, answer

    def question_answer2(
        self, prop: str, prop_label: str, rid: str = ""
    ) -> Tuple[str, int]:
        question = self.q_template2.replace("[PROP]", prop)
        answer = basic_f.count_span(prop, prop_label, unique=False, rid=rid)
        return question, answer

    def question_answer3(
        self, prop: str, prop_label: str, rid: str = ""
    ) -> Tuple[str, int]:
        question = self.q_template3.replace("[PROP]", get_plural_prop(prop))
        answer = basic_f.count_span(prop, prop_label, unique=True, rid=rid) > 1
        return question, answer


@attr.s()
class EllipsisQuestions:
    q_template1: str = "What should be [VERB]?"
    q_template2: str = "What should be [VERB] by the [PROP]?"
    q_template3: str = "What should be [VERB] in/on/to the [PROP]?"
    q_template4: str = "What should be [VERB] to [PROP] and [VERB]?"

    def question_answer1(
        self, verb: str, rid: str = ""
    ) -> Tuple[str, List[Tuple[Span, ...]]]:
        question = self.q_template1.replace("[VERB]", get_past_participle(verb))
        events = list(query_f.query_event(verb, rid))
        answer = []
        for event in events:
            answer.append(
                tuple(i.ingre_par for i in query_f.query_relation_by_span(event=event))
            )
        return question, answer

    def question_answer2(
        self, verb: str, prop: str, rid: str = ""
    ) -> Tuple[str, List[Tuple[Span, ...]]]:
        question = self.q_template2.replace("[VERB]", get_past_participle(verb))
        question = question.replace("[PROP]", prop)
        events = list(query_f.query_event(verb, rid))
        answer = []

        for event in events:
            rels = query_f.query_relation_by_span(event=event)
            answer.append(
                tuple(rel.ingre_par for rel in rels if rel.tool_par.lemma == prop)
            )

        return question, answer

    def question_answer3(
        self, verb: str, prop: str, rid: str = ""
    ) -> Tuple[str, List[Tuple[Span, ...]]]:
        question = self.q_template3.replace("[VERB]", get_past_participle(verb))
        question = question.replace("[PROP]", prop)
        events = list(query_f.query_event(verb, rid))
        answer = []

        for event in events:
            rels = query_f.query_relation_by_span(event=event)
            answer.append(
                tuple(
                    rel.ingre_par.lemma for rel in rels if rel.habitat_par.lemma == prop
                )
            )

        return question, answer


@attr.s()
class ImplicitObjectQuestions:
    q_template1: str = "What is used to [VERB] the [INGRE]?"
    q_template2: str = "Where should you [VERB] the [INGRE]?"

    def question_answer1(
        self, verb: str, ingredient: str, rid: str = ""
    ) -> Tuple[str, List[Tuple[Span, ...]]]:
        question = self.q_template1.replace("[VERB]", verb)
        question = question.replace("[INGRE]", get_plural_ingre(ingredient))
        events = list(query_f.query_event(verb, rid))
        answer = []

        for event in events:
            rels = query_f.query_relation_by_span(event=event)
            answer.append(
                tuple(
                    rel.tool_par
                    for rel in rels
                    if rel.ingre_par.lemma == ingredient
                    and rel.tool_par.label == "HIDDENTOOL"
                )
            )
        return question, answer

    def question_answer2(
        self, verb: str, ingredient: str, rid: str = ""
    ) -> Tuple[str, List[Tuple[Span, ...]]]:
        question = self.q_template2.replace("[VERB]", verb)
        question = question.replace("[INGRE]", get_plural_ingre(ingredient))
        events = list(query_f.query_event(verb, rid))
        answer = []

        for event in events:
            rels = query_f.query_relation_by_span(event=event)
            answer.append(
                tuple(
                    rel.habitat_par.lemma
                    for rel in rels
                    if rel.ingre_par.lemma == ingredient
                    and rel.habitat_par.label == "HIDDENHABITAT"
                )
            )
        return question, answer


@attr.s()
class ObjLifeSpanQuestions:
    q_template1: str = "What is in the [INGRE]?"
    q_template2: str = "Are the [INGRE] in step [NUM] and step [NUM] identical?"

    def question_answer1(
        self, ingredient: str, rid: str = ""
    ) -> Tuple[str, List[Tuple[Span, ...]]]:
        question = self.q_template1.replace("[INGRE]", ingredient)
        ingres = list(query_f.query_ingredient(ingredient, rid))
        answer = []
        for ingre in ingres:
            rels = query_f.query_relation_by_span(result=ingre)
            answer.append(tuple(rel.ingre_par for rel in rels))
        return question, answer

    def question_answer2(
        self, ingredient: str, rid: str = ""
    ) -> Tuple[str, Optional[bool]]:
        ingre_step_ids = [
            (int(ingre.uid.split("::")[1][-2:]), ingre)
            for ingre in query_f.query_ingredient(ingredient, rid)
        ]

        if len(ingre_step_ids) > 1:
            ingre_pair = random.sample(ingre_step_ids, 2)
            question = self.q_template2.replace("[INGRE]", ingredient)
            question = question.replace("[NUM]", str(ingre_pair[0][0]), 1)
            question = question.replace("[NUM]", str(ingre_pair[1][0]), 1)
            answer = (
                ingre_pair[0][1].coreference is not None
                and ingre_pair[0][1].coreference == ingre_pair[1][1].coreference
            )
            return question, answer
        return self.q_template2, None


if __name__ == "__main__":
    cq = CardinalityQuestions()
    eq = EllipsisQuestions()
    iq = ImplicitObjectQuestions()
    oq = ObjLifeSpanQuestions()
    print(cq.question_answer1("spatula", "TOOL"))
    print(cq.question_answer2("spatula", "TOOL"))
    print(cq.question_answer3("spatula", "TOOL"))
    print(eq.question_answer1("toss"))
    print(eq.question_answer2("saute", "spatula"))
    print(eq.question_answer3("add", "pan"))
    print(iq.question_answer1("sprinkle", "pasta"))
    print(iq.question_answer2("stir", "pancetta"))
    print(oq.question_answer1("pasta"))
    print(oq.question_answer2("asparagus"))
