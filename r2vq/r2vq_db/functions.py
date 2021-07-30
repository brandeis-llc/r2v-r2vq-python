from typing import Union

import attr
import peewee

from r2vq_conllu.ingest import ingest_r2vq_connlu
from r2vq_db import db
from r2vq_db.models import Span, Relation
from r2vq_conllu.data import Relation as RecipeRel
from r2vq_conllu.data import Span as RecipeSpan


@attr.s()
class BasicFunctions:
    @db.connection_context()
    def query_span_by_id(self, span_id: str) -> Span:
        return Span.get_by_id(span_id)

    @db.connection_context()
    def query_relation_by_id(self, rel_id: Union[int, str]) -> Relation:
        return Relation.get_by_id(rel_id)

    @db.connection_context()
    def query_span(self, label_suffix: str = "", rid: str = "") -> peewee.ModelSelect:
        query = Span.select().where(
            (Span.label.endswith(label_suffix)) & (Span.uid.startswith(rid))
        )
        return query

    @db.connection_context()
    def count_span(
        self, name: str, label_suffix: str, unique: bool, rid: str = ""
    ) -> int:
        query = Span.select().where(
            (Span.lemma == name)
            & (Span.label.endswith(label_suffix))
            & (Span.uid.startswith(rid))
        )
        if unique:
            return query.group_by(Span.coreference).count()
        return query.count()

    @db.connection_context()
    def exist_span(self, name: str, label_suffix: str = "", rid: str = "") -> bool:
        return self.count_span(name, label_suffix, False, rid) > 0

    @staticmethod
    def compare_order(rel1: Relation, rel2: Relation) -> bool:
        assert (
            rel2.event_verb.uid != rel1.event_verb.uid
        ), f"relations have the same event! ({rel1.event_verb.lemma}, {rel1.event_verb.uid})"
        return rel2.event_verb.uid > rel1.event_verb.uid


@attr.s()
class QueryFunctions:
    bf: BasicFunctions = attr.ib(default=BasicFunctions())

    @db.connection_context()
    def query_ingredient(self, name: str, rid: str = "") -> peewee.ModelSelect:
        return self.bf.query_span("INGREDIENT", rid).where((Span.lemma == name))

    @db.connection_context()
    def query_event(self, name: str, rid: str = "") -> peewee.ModelSelect:
        return self.bf.query_span("EVENT", rid).where((Span.lemma == name))

    @db.connection_context()
    def query_tool(self, name: str, rid: str = "") -> peewee.ModelSelect:
        return self.bf.query_span("TOOL", rid).where((Span.lemma == name))

    @db.connection_context()
    def query_habitat(self, name: str, rid: str = "") -> peewee.ModelSelect:
        return self.bf.query_span("HABITAT", rid).where((Span.lemma == name))

    @db.connection_context()
    def query_relation_by_span(
        self,
        event: Union[str, Span] = None,
        ingre: Union[str, Span] = None,
        tool: Union[str, Span] = None,
        habitat: Union[str, Span] = None,
        result: Union[str, Span] = None,
        rid: str = "",
    ) -> peewee.ModelSelect:
        query = Relation.select().where((Relation.event.startswith(rid)))
        if event:
            query = query.where((Relation.event == event))
        if ingre:
            query = query.where((Relation.ingre_par == ingre))
        if tool:
            query = query.where((Relation.tool_par == tool))
        if habitat:
            query = query.where((Relation.habitat_par == habitat))
        if result:
            query = query.where((Relation.ingre_res == result))

        return query


@attr.s()
class FilterFunctions:
    bf: BasicFunctions = attr.ib(default=BasicFunctions())

    @db.connection_context()
    def filter_ingredient(self, label_prefix: str, rid: str = "") -> peewee.ModelSelect:
        """
        :param label_prefix: 'explicit', 'implicit', 'hidden', 'drop'
        :param rid
        """
        query = self.bf.query_span(label_prefix.upper() + "INGREDIENT", rid)
        return query

    @db.connection_context()
    def filter_tool(self, label_prefix: str, rid: str = "") -> peewee.ModelSelect:
        """
        :param label_prefix: 'explicit', 'hidden'
        :param rid
        """
        query = self.bf.query_span(label_prefix.upper() + "TOOL", rid)
        return query

    @db.connection_context()
    def filter_habitat(self, label_prefix: str, rid: str = "") -> peewee.ModelSelect:
        """
        :param label_prefix: 'explicit', 'hidden'
        :param rid
        """
        query = self.bf.query_span(label_prefix.upper() + "HABITAT", rid)
        return query


if __name__ == "__main__":
    recipes, _ = ingest_r2vq_connlu(
        "../r2vq_conllu_data/trial_recipes.conllu_ALL_formatted.csv"
    )
    basic_f = BasicFunctions()
    query_f = QueryFunctions()
    filter_f = FilterFunctions()

    c = basic_f.count_span("white wine", "INGREDIENT", True)
    print(c)
    d = basic_f.exist_span("white wine", "INGREDIENT")
    print(d)
    pancettas = query_f.query_habitat("large pot")
    print([p.coreference for p in pancettas])
    rels = query_f.query_relation_by_span(event="f-QTSTCCSV::step05::sent01::000::CRL")
    print(list(rels)[0].ingre_par)
    print("======================")
    print(
        basic_f.compare_order(
            basic_f.query_relation_by_id("6"), basic_f.query_relation_by_id("3")
        )
    )
    fils = filter_f.filter_ingredient("explicit")
    print(list(fils))
    print(basic_f.query_span_by_id("f-QTSTCCSV::step02::sent01::000::CRL").lemma)
    print(basic_f.query_relation_by_id("1").event)
