from shorttest.core.markup import Segment, parse_markup, strip_markup
from shorttest.core.normalize import normalize


def seg(text, *styles):
    return Segment(text, frozenset(styles))


def test_plain():
    assert parse_markup("그냥 글") == [seg("그냥 글")]


def test_italic_and_bold():
    assert parse_markup("다음 중 *Escherichia coli*의 **모두**") == [
        seg("다음 중 "), seg("Escherichia coli", "i"), seg("의 "), seg("모두", "b"),
    ]


def test_sub_sup():
    assert parse_markup("H_{2}O와 Ca^{2+}") == [
        seg("H"), seg("2", "sub"), seg("O와 Ca"), seg("2+", "sup"),
    ]


def test_nested_and_escape():
    assert parse_markup("***E. coli***") == [seg("E. coli", "b", "i")]
    assert parse_markup(r"p < 0.05\* 참고") == [seg("p < 0.05* 참고")]


def test_unbalanced_left_alone():
    assert parse_markup("2 * 3 = 6") == [seg("2 * 3 = 6")]
    assert parse_markup("a_b 와 x^2") == [seg("a_b 와 x^2")]


def test_strip_and_normalize():
    assert strip_markup("*E. coli*의 H_{2}O") == "E. coli의 H2O"
    assert normalize("*Escherichia coli*") == normalize("Escherichia coli")
    assert normalize("H₂O") == normalize("H_{2}O") == "h2o"
    assert normalize("NF-κB") == "nf-κb"
