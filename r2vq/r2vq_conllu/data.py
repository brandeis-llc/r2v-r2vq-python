from typing import Optional, Dict, List, Union

import attr


@attr.s(frozen=True, repr=False)
class Token:
    id: str = attr.ib()
    form: str = attr.ib()
    lemma: str = attr.ib()
    upos: str = attr.ib()
    xpos: str = attr.ib()
    feats: Optional[Dict[str, str]] = attr.ib()
    head: int = attr.ib()
    deprel: str = attr.ib()
    deps: Optional[str] = attr.ib()
    misc: Optional[str] = attr.ib()
    entity: Optional[str] = attr.ib()
    participant_of: Optional[int] = attr.ib()
    result_of: Optional[int] = attr.ib()
    hidden: Optional[Dict[str, List[str]]] = attr.ib()
    coreference: Optional[int] = attr.ib()

    def __repr__(self):
        return self.form


@attr.s(frozen=True, repr=False)
class Sentence:
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
    id: str = attr.ib()
    sent: Sentence = attr.ib()
    start_pos: int = attr.ib()
    end_pos: int = attr.ib()
    label: str = attr.ib()
    text: str = attr.ib()
    coref_id: Optional[int] = attr.ib()
    participant_of: Optional[int] = attr.ib()
    result_of: Optional[int] = attr.ib()

    @classmethod
    def from_entity(
        cls, span_id: str, sent: Sentence, start: int, end: int, label: str
    ) -> "Span":
        text = " ".join([tok.form for tok in sent[start:end]])
        coref_id = sent[start].coreference
        participant_of: Optional[int] = sent[start].participant_of
        result_of: Optional[int] = sent[start].result_of
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
        key_mapping = {
            "Hidden": "HIDDENINGREDIENT",
            "Drop": "DROPINGREDIENT",
            "Tool": "HIDDENTOOL",
            "Habitat": "HIDDENHABITAT",
        }
        label = key_mapping[key]
        try:
            text, coref_str = value.split(".")
            coref_id: Optional[int] = int(coref_str)
        except ValueError:
            text, coref_id = value, None

        return cls(span_id, sent, -1, -1, label, text, coref_id, tok_idx, None)

    @property
    def lemma(self):
        if self.start_pos == self.end_pos == -1:  # TODO: add a lemmatizer
            return self.text.lower()
        else:
            return " ".join(
                [tok.lemma for tok in self.sent[self.start_pos : self.end_pos]]
            )

    def __repr__(self):
        return self.text


@attr.s(frozen=False, repr=False)
class Relation:
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
class Ingredient:
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

    def __getitem__(self, item: int):
        return self.sentences[item]
