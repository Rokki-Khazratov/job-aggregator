from jobagg.hashing import clean_text, description_hash, build_dedup_key


def test_clean_text_strips_tags():
    assert clean_text("<p>Hello <b>world</b></p>") == "Hello world"


def test_clean_text_unescapes_entities():
    assert clean_text("Salary &amp; Benefits") == "Salary & Benefits"


def test_clean_text_collapses_whitespace():
    assert clean_text("  foo  \n\n  bar  ") == "foo bar"


def test_clean_text_none():
    assert clean_text(None) == ""


def test_description_hash_stable():
    html1 = "<p>We are looking for a <b>Python</b> developer.</p>"
    html2 = "  We  are  looking  for  a  Python  developer.  "
    assert description_hash(html1) == description_hash(html2)


def test_description_hash_case_insensitive():
    assert description_hash("HELLO") == description_hash("hello")


def test_description_hash_different_content():
    assert description_hash("job A") != description_hash("job B")


def test_build_dedup_key_structure():
    key = build_dedup_key("Python Dev", "Acme GmbH", "Berlin", "Great job description here")
    parts = key.split("|")
    assert len(parts) == 4
    assert parts[0] == "python-dev"
    assert parts[1] == "acme-gmbh"
    assert parts[2] == "berlin"
    assert len(parts[3]) == 40  # sha1 hex


def test_build_dedup_key_none_inputs():
    key = build_dedup_key(None, None, None, None)
    assert key.count("|") == 3
