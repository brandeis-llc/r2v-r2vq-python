from peewee import (
    Model,
    CharField,
    ForeignKeyField,
    IntegerField,
)  # type: ignore
from r2vq_db import db


class BaseModel(Model):
    class Meta:
        database = db


class Span(BaseModel):
    # TODO: maybe also add text field here. "slotted spoon" vs. "slot spoon"
    uid = CharField(primary_key=True)
    lemma = CharField()
    label = CharField()
    coreference = IntegerField(null=True)


class Relation(BaseModel):
    event = ForeignKeyField(Span, backref="event")
    ingre_par = ForeignKeyField(Span, backref="ingre_par", null=True)
    tool_par = ForeignKeyField(Span, backref="tool_par", null=True)
    habitat_par = ForeignKeyField(Span, backref="habitat_par", null=True)
    ingre_res = ForeignKeyField(Span, backref="ingre_res", null=True)
