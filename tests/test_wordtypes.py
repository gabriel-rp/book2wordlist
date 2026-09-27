from book2wordlist.wordtypes import WordType


def test_labels_are_our_own_names():
    assert WordType.NAME.label == 'name'
    assert WordType.PREPOSITION.label == 'preposition'
    assert str(WordType.VERB) == 'verb'


def test_closed_class_is_carried_by_the_type_itself():
    assert WordType.DETERMINER.is_closed_class
    assert WordType.CONJUNCTION.is_closed_class
    assert not WordType.VERB.is_closed_class
    assert not WordType.NOUN.is_closed_class


def test_names_are_recognisable_without_a_tagset():
    assert WordType.NAME.is_name
    assert not WordType.NOUN.is_name


def test_every_type_has_a_distinct_label():
    labels = WordType.labels()

    assert len(labels) == len(set(labels)) == len(list(WordType))
