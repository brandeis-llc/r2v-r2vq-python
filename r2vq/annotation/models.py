import re
from typing import Optional, Dict, List, Union
from importlib import resources

import attr
from attr import validators, converters

CRL_ENTITY_LABELS = resources.read_text('r2vq.res', 'crl_entity_labels.txt').strip().split('\n')
CRL_HIDDEN_KEYS = resources.read_text('r2vq.res', 'crl_hidden_keys.txt').strip().split('\n')
SRL_PRED_SENSES = resources.read_text('r2vq.res', 'srl_pred_senses.txt').strip().split('\n')
SRL_ARG_LABELS = resources.read_text('r2vq.res', 'srl_arg_labels.txt').strip().split('\n')

# validate input has BIO tagging and correct labels (e.g. B-TOOL, I-Time, O)
crl_entity_validator = validators.matches_re(
    rf"^O|^[BI]-({'|'.join(CRL_ENTITY_LABELS)})$"
)
srl_argument_validator = validators.matches_re(
    rf"^O|^[BI]-({'|'.join(SRL_ARG_LABELS)})$"
)

# validate co-reference id (e.g. asparagus.2.1.3)
crl_coref_validator = validators.optional(
    validators.matches_re(r"^[a-zA-Z0-9_]+?(\.\d+?\.\d+?\.\d+?)?$")
)


# validate hidden arguments (e.g. [asparagus.2.1.3, pancetta.3.5.2])
def crl_hidden_value_validator(instance, attribute, value):
    if value:
        for v in value:
            if not re.match(r"^[/a-zA-Z0-9_-]+?(\.\d+\.\d+\.\d+)?$", v):
                raise ValueError(f"{repr(v)} doesn't match the hidden value format.")


crl_hidden_validator = validators.optional(
    validators.deep_mapping(
        key_validator=validators.in_(CRL_HIDDEN_KEYS),
        value_validator=validators.and_(
            validators.optional(validators.instance_of(list)),
            crl_hidden_value_validator,
        ),
    )
)


@attr.s(frozen=True, repr=False)
class Token:
    # token line dataclass, it contains the original values for the CoNLL-U file

    # meta fields
    id: str = attr.ib()
    form: str = attr.ib()
    lemma: str = attr.ib()
    upos: str = attr.ib()

    # CRL fields
    entity: Optional[str] = attr.ib(
        validator=crl_entity_validator, converter=converters.default_if_none("O")
    )
    participant_of: Optional[int] = attr.ib(
        validator=validators.optional(validators.instance_of(int))
    )
    result_of: Optional[int] = attr.ib(
        validator=validators.optional(validators.instance_of(int))
    )
    hidden: Optional[Dict[str, List[str]]] = attr.ib(validator=crl_hidden_validator)
    coreference: Optional[str] = attr.ib(validator=crl_coref_validator)

    # SRL fields
    predicate: Optional[str] = attr.ib(
        validator=validators.optional(validators.in_(SRL_PRED_SENSES))
    )
    arg_pred1: Optional[str] = attr.ib(
        validator=srl_argument_validator, converter=converters.default_if_none("O")
    )
    arg_pred2: Optional[str] = attr.ib(
        validator=srl_argument_validator, converter=converters.default_if_none("O")
    )
    arg_pred3: Optional[str] = attr.ib(
        validator=srl_argument_validator, converter=converters.default_if_none("O")
    )
    arg_pred4: Optional[str] = attr.ib(
        validator=srl_argument_validator, converter=converters.default_if_none("O")
    )
    arg_pred5: Optional[str] = attr.ib(
        validator=srl_argument_validator, converter=converters.default_if_none("O")
    )

    def __repr__(self):
        return self.form


@attr.s(frozen=True, repr=False)
class Sentence:
    # sentence dataclass
    id: str = attr.ib()
    text: str = attr.ib()
    tokens: List[Token] = attr.ib()

    def __getitem__(self, item: Union[int, slice]):
        if isinstance(item, int):
            return self.tokens[item]
        elif isinstance(item, slice):
            return self.tokens[item.start : item.stop : item.step]
        else:
            raise ValueError()

    def __repr__(self):
        return self.text


@attr.s(frozen=True, repr=False)
class Span:
    # CRL entity dataclass
    id: str = attr.ib()
    sent: Sentence = attr.ib()
    start_pos: int = attr.ib()
    end_pos: int = attr.ib()
    label: str = attr.ib()
    text: str = attr.ib()
    coref_id: Optional[int] = attr.ib(
        validator=validators.optional(validators.instance_of(int))
    )
    participant_of: Optional[int] = attr.ib()
    result_of: Optional[int] = attr.ib()

    @classmethod
    def from_entity(
        cls, span_id: str, sent: Sentence, start: int, end: int, label: str
    ) -> "Span":
        """
        instantiate from the Entity column

        """
        text = " ".join([tok.form for tok in sent[start:end]])

        if sent[start].coreference:
            # split on the first dot only to separate co-referred entity, e.g. "pancetta_grease.1.1.5"
            _, coref_str = sent[start].coreference.split(".", 1)
            coref_id: Optional[int] = int(coref_str.replace(".", ""))
        else:
            coref_id = None

        participant_of: Optional[int] = sent[start].participant_of
        result_of: Optional[int] = sent[start].result_of
        # in CoNLL-U token id starts with 1 instead of 0
        if participant_of:
            participant_of -= 1
        if result_of:
            result_of -= 1
        return cls(
            span_id, sent, start, end, label, text, coref_id, participant_of, result_of
        )

    @classmethod
    def from_hidden(
        cls, span_id: str, sent: Sentence, tok_idx: int, key: str, value: str
    ) -> "Span":
        """
        instantiate from the Hidden column

        """
        key_mapping = {
            "Shadow": "SHADOWINGREDIENT",
            "Drop": "DROPINGREDIENT",
            "Result": "RESULTINGREDIENT",
            "Tool": "HIDDENTOOL",
            "Habitat": "HIDDENHABITAT",
        }
        label = key_mapping[key]
        try:
            # split on the first dot only to separate coreferred entity, e.g. "pancetta_grease.1.1.5"
            text, coref_str = value.split(".", 1)
            coref_id: Optional[int] = int(coref_str.replace(".", ""))
        except ValueError:
            text, coref_id = value, None
        # replace "_" with a space, e.g. "pancetta_grease"
        text = text.replace("_", " ")

        if label == "RESULTINGREDIENT":
            return cls(span_id, sent, -1, -1, label, text, coref_id, None, tok_idx)
        else:
            return cls(span_id, sent, -1, -1, label, text, coref_id, tok_idx, None)

    @property
    def lemma(self):
        if (
            self.start_pos == self.end_pos == -1
        ):  # TODO: add a lemmatizer for spans from Hidden column
            return self.text.lower()
        else:
            # heuristics: only get the lemma of the last token of the span
            return " ".join(
                [tok.form for tok in self.sent[self.start_pos : self.end_pos - 1]]
                + [self.sent[self.end_pos - 1].lemma]
            ).lower()

    def __repr__(self):
        return self.text


@attr.s(frozen=True, repr=False)
class Argument:
    # SRL argument dataclass
    id: str = attr.ib()
    sent: Sentence = attr.ib()
    start_pos: int = attr.ib()
    end_pos: int = attr.ib()
    label: str = attr.ib()
    text: str = attr.ib()

    @classmethod
    def from_arguments(
        cls, span_id: str, sent: Sentence, start: int, end: int, label: str
    ) -> "Argument":
        """
        instantiated from the arg-pred column

        """
        text = " ".join([tok.form for tok in sent[start:end]])

        return cls(span_id, sent, start, end, label, text)

    @property
    def lemma(self):
        return self.text.lower()

    def __repr__(self):
        return self.text


@attr.s(frozen=False, repr=False)
class Predicate:
    # SRL predicate dataclass (from columns J to O)
    head: Argument = attr.ib()
    sense: str = attr.ib()
    _patient: Argument = attr.ib(default=None)
    _location: Argument = attr.ib(default=None)
    _result: Argument = attr.ib(default=None)
    _time: Argument = attr.ib(default=None)
    _instrument: Argument = attr.ib(default=None)
    _theme: Argument = attr.ib(default=None)
    _destination: Argument = attr.ib(default=None)
    _attribute: Argument = attr.ib(default=None)
    _extent: Argument = attr.ib(default=None)
    _purpose: Argument = attr.ib(default=None)
    _co_patient: Argument = attr.ib(default=None)

    def __repr__(self):
        head = f"{self.head}[{self.sense}]"
        args = []
        for k in self.__dict__:
            if k.startswith("_") and self.__dict__[k]:
                args.append(f"{self.__dict__[k]}[{k[1:]}]")
        return f"{head} -> {'-'.join(args)}"

    @head.validator
    def _check_pred_head(self, attribute, value) -> None:
        if value.label != "V":
            raise ValueError("span a predicate head!")

    @property
    def patient(self):
        return self._patient

    @patient.setter
    def patient(self, value: Argument):
        self._patient = value

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value: Argument):
        self._location = value

    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, value: Argument):
        self._result = value

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, value: Argument):
        self._time = value

    @property
    def instrument(self):
        return self._instrument

    @instrument.setter
    def instrument(self, value: Argument):
        self._instrument = value

    @property
    def theme(self):
        return self._theme

    @theme.setter
    def theme(self, value: Argument):
        self._theme = value

    @property
    def destination(self):
        return self._destination

    @destination.setter
    def destination(self, value: Argument):
        self._destination = value

    @property
    def attribute(self):
        return self._attribute

    @attribute.setter
    def attribute(self, value: Argument):
        self._attribute = value

    @property
    def extent(self):
        return self._extent

    @extent.setter
    def extent(self, value: Argument):
        self._extent = value

    @property
    def purpose(self):
        return self._purpose

    @purpose.setter
    def purpose(self, value: Argument):
        self._purpose = value

    @property
    def co_patient(self):
        return self._co_patient

    @co_patient.setter
    def co_patient(self, value: Argument):
        self._co_patient = value


@attr.s(frozen=False, repr=False)
class Relation:
    # CRL relation dataclass (from columns E-I)
    event: Span = attr.ib()
    _ingre_participants: List[Span] = attr.ib(factory=list)
    _tool_participants: List[Span] = attr.ib(factory=list)
    _habitat_participants: List[Span] = attr.ib(factory=list)
    _ingre_results: List[Span] = attr.ib(factory=list)

    @event.validator
    def _check_event(self, attribute, value) -> None:
        if value.label != "EVENT":
            raise ValueError("span label is not EVENT!")

    @property
    def ingre_participants(self):
        return self._ingre_participants

    @ingre_participants.setter
    def ingre_participants(self, value: Span):
        self._ingre_participants.append(value)

    @property
    def tool_participants(self):
        return self._tool_participants

    @tool_participants.setter
    def tool_participants(self, value: Span):
        self._tool_participants.append(value)

    @property
    def habitat_participants(self):
        return self._habitat_participants

    @habitat_participants.setter
    def habitat_participants(self, value: Span):
        self._habitat_participants.append(value)

    @property
    def ingre_results(self):
        return self._ingre_results

    @ingre_results.setter
    def ingre_results(self, value: Span):
        self._ingre_results.append(value)

    def __repr__(self):
        return f"{(self.ingre_participants, self.tool_participants, self.habitat_participants)}->{self.event.text}->{self.ingre_results}"


@attr.s(frozen=True, repr=False)
class EventVerb:
    # verb head of a cooking event
    id: str = attr.ib()
    sent: Sentence = attr.ib()
    start_pos: int = attr.ib()
    end_pos: int = attr.ib()
    text: str = attr.ib()
    lemma: str = attr.ib()

    def __repr__(self):
        return self.text


@attr.s(frozen=False, repr=True)
class CookingEvent:
    # cooking event dataclass, it consists of the verb head, CRL relation and SRL predicate
    verb: EventVerb = attr.ib()
    predicate: Optional[Predicate] = attr.ib()
    relation: Optional[Relation] = attr.ib()


@attr.s(frozen=True, repr=False)
class Ingredient:
    # ingredient dataclass
    id: str = attr.ib()
    text: str = attr.ib()
    tokens: List[Token] = attr.ib()

    def __repr__(self):
        return self.text


@attr.s(frozen=True)
class Recipe:
    r_id: str = attr.ib()
    ingredients: List[Ingredient] = attr.ib()
    sentences: List[Sentence] = attr.ib()
    spans: List[Span] = attr.ib()
    relations: List[Relation] = attr.ib()
    arguments: List[Argument] = attr.ib()
    predicates: List[Predicate] = attr.ib()
    cooking_events: List[CookingEvent] = attr.ib()

    def __getitem__(self, item: int):
        return self.sentences[item]


if __name__ == "__main__":
    print(CRL_ENTITY_LABELS)
    pass
