import itertools
import random
from collections import defaultdict
from typing import Sequence, Set, Union, List

from r2vq_conllu.ingest import ingest_r2vq_connlu
from r2vq_db.functions import BasicFunctions, FilterFunctions, QueryFunctions
from r2vq_db.question_family import (
    CardinalityQuestions,
    EllipsisQuestions,
    ImplicitObjectQuestions,
    ObjLifeSpanQuestions,
)
from r2vq_db.models import Span

basic_f = BasicFunctions()
query_f = QueryFunctions()
filter_f = FilterFunctions()
cq = CardinalityQuestions()
eq = EllipsisQuestions()
iq = ImplicitObjectQuestions()
oq = ObjLifeSpanQuestions()


def get_answer_id(answers: Sequence[Sequence[Span]]) -> Sequence[Sequence[str]]:
    return [[e.uid for e in answer if e] for answer in answers if answer]


def format_qa_pair(question, answer: Union[int, bool, List]):
    if not isinstance(answer, (int, bool)):
        answer = "|".join([",".join(a) for a in answer])
    return f"{question}\t{answer}"


def generate_cq(
    tool_names: Set[str], habitat_names: Set[str], ingre_names: Set[str], rid: str
):
    questions = []
    for tool in random.sample(tool_names, min(2, len(tool_names))):
        questions.append(list(cq.question_answer1(tool, "TOOL", rid)))
        questions.append(list(cq.question_answer2(tool, "TOOL", rid)))
        questions.append(list(cq.question_answer3(tool, "TOOL", rid)))

    for hab in random.sample(habitat_names, min(2, len(habitat_names))):
        questions.append(list(cq.question_answer1(hab, "HABITAT", rid)))
        questions.append(list(cq.question_answer2(hab, "HABITAT", rid)))
        questions.append(list(cq.question_answer3(hab, "HABITAT", rid)))

    for ingre in random.sample(ingre_names, min(2, len(ingre_names))):
        questions.append(list(cq.question_answer4(ingre, rid)))

    return questions


def generate_eq(
    event_names: Set[str], tool_names: Set[str], habitat_names: Set[str], rid: str
):
    questions = []
    for verb in event_names:
        ques, ans = eq.question_answer1(verb, rid)
        if list(itertools.chain.from_iterable(ans)):
            questions.append([ques, get_answer_id(ans)])

    for v in event_names:
        for p in tool_names:
            ques, ans = eq.question_answer2(v, p, rid)
            if list(itertools.chain.from_iterable(ans)):
                questions.append([ques, get_answer_id(ans)])

    for v in event_names:
        for p in habitat_names:
            ques, ans = eq.question_answer3(v, p, rid)
            if list(itertools.chain.from_iterable(ans)):
                questions.append([ques, get_answer_id(ans)])
    return questions


def generate_iq(event_names: Set[str], rid: str):
    questions = []
    for eve in event_names:
        rels = []
        events = list(query_f.query_event(eve, rid))
        for e in events:
            rels.extend(list(query_f.query_relation_by_span(event=e, rid=rid)))
        ingredients = [rel.ingre_par.lemma for rel in rels if rel.ingre_par]
        if ingredients:
            for ingre in ingredients:
                ques, ans = iq.question_answer1(
                    eve,
                    ingre,
                )
                if list(itertools.chain.from_iterable(ans)):
                    questions.append([ques, get_answer_id(ans)])
                ques, ans = iq.question_answer2(
                    eve,
                    ingre,
                )
                if list(itertools.chain.from_iterable(ans)):
                    questions.append([ques, get_answer_id(ans)])
    return questions


def generate_oq(ingre_names: Set[str], rid: str):
    questions = []
    for ingre in ingre_names:
        ques, ans = oq.question_answer1(ingre, rid)
        if list(itertools.chain.from_iterable(ans)):
            questions.append([ques, get_answer_id(ans)])
        ques, ans = oq.question_answer2(ingre, rid)
        if ans is not None:
            questions.append([ques, ans])
    return questions


def write_qa_conllu(in_file, out_file):
    f_out = open(out_file, "w")
    with open(in_file, "r") as f:
        for line in f:
            f_out.write(line)
            if line.startswith("# newdoc id = "):
                rid = line.strip().split(" = ")[1]
                ques_families = questions[rid]
                for k in ques_families:
                    for i, qa in enumerate(ques_families[k], 1):
                        f_out.write(f"{k}{i} = {format_qa_pair(*qa)}\n")


if __name__ == "__main__":
    recipes, sentences = ingest_r2vq_connlu(
        "../r2vq_conllu_data/trial_recipes.conllu_ALL_formatted.csv"
    )

    questions = defaultdict(dict)
    for recipe in recipes:
        rid = recipe.r_id

        tool_names = set(p.lemma for p in basic_f.query_span("TOOL", rid))
        habitat_names = set(p.lemma for p in basic_f.query_span("HABITAT", rid))
        ingre_names = set(p.lemma for p in basic_f.query_span("INGREDIENT", rid))
        event_names = set(p.lemma for p in basic_f.query_span("EVENT", rid))

        questions[rid]["cq"] = generate_cq(tool_names, habitat_names, ingre_names, rid)
        questions[rid]["eq"] = generate_eq(event_names, tool_names, habitat_names, rid)
        questions[rid]["iq"] = generate_iq(event_names, rid)
        questions[rid]["oq"] = generate_oq(ingre_names, rid)

    write_qa_conllu(
        "../r2vq_conllu_data/trial_recipes.conllu.annotation.csv",
        "../r2vq_conllu_data/trial_recipes.conllu.annotation.qa22.csv",
    )
