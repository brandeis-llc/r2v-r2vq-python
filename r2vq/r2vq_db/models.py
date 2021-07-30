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
    uid = CharField(primary_key=True)
    lemma = CharField()
    label = CharField()
    coreference = IntegerField(null=True)


class Relation(BaseModel):
    event = ForeignKeyField(Span, backref="event", null=True)
    ingre_par = ForeignKeyField(Span, backref="ingre_par", null=True)
    tool_par = ForeignKeyField(Span, backref="tool_par", null=True)
    habitat_par = ForeignKeyField(Span, backref="habitat_par", null=True)
    ingre_res = ForeignKeyField(Span, backref="ingre_res", null=True)
    event_verb = ForeignKeyField(Span, backref="event")
    head = ForeignKeyField(Span, backref="head", null=True)
    patient = ForeignKeyField(Span, null=True)
    location = ForeignKeyField(Span, null=True)
    result = ForeignKeyField(Span, null=True)
    time = ForeignKeyField(Span, null=True)
    instrument = ForeignKeyField(Span, null=True)
    theme = ForeignKeyField(Span, null=True)
    destination = ForeignKeyField(Span, null=True)
    attribute = ForeignKeyField(Span, null=True)
    extent = ForeignKeyField(Span, null=True)
    purpose = ForeignKeyField(Span, null=True)
    co_patient = ForeignKeyField(Span, null=True)

