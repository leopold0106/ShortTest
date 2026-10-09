from shorttest.core.normalize import normalize


def test_fullwidth_and_case():
    assert normalize("Ｈ２Ｏ") == "h2o"
    assert normalize("  H2O ") == "h2o"


def test_inner_spaces():
    assert normalize("엽록  체") == "엽록 체"
    assert normalize("엽록  체", ignore_inner_spaces=True) == "엽록체"
