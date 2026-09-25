import unittest

from query_build import Query, parse, build


class TestBuild(unittest.TestCase):

    def test_simple_pair(self):
        self.assertEqual(build(Query([("a", "1")]), ) if False else build(Query([("a", "1")])), "a=1")

    def test_repeated_keys_preserved(self):
        q = Query([("tag", "py"), ("tag", "web")])
        self.assertEqual(build(q), "tag=py&tag=web")

    def test_none_value_bare_key(self):
        self.assertEqual(build(Query([("flag", None)])), "flag")

    def test_empty_string_value_keeps_equals(self):
        self.assertEqual(build(Query([("k", "")]), ), "k=")

    def test_order_preserved(self):
        q = Query([("z", "1"), ("a", "2"), ("m", "3")])
        self.assertEqual(build(q), "z=1&a=2&m=3")

    def test_empty_query_is_empty_string(self):
        self.assertEqual(build(Query()), "")

    def test_encoding_of_special_chars(self):
        self.assertEqual(build(Query([("q", "a b")]), ) if False else build(Query([("q", "a b")])), "q=a%20b")
        self.assertEqual(build(Query([("k", "a&b")]), ) if False else build(Query([("k", "a&b")])), "k=a%26b")
        self.assertEqual(build(Query([("k", "a=b")]), ) if False else build(Query([("k", "a=b")])), "k=a%3Db")

    def test_mixed_none_and_values(self):
        q = Query([("flag", None), ("x", "1")])
        self.assertEqual(build(q), "flag&x=1")

    def test_dict_input_with_list_value(self):
        self.assertEqual(build({"tag": ["a", "b"]}), "tag=a&tag=b")

    def test_dict_input_with_scalar(self):
        self.assertEqual(build({"a": "1"}), "a=1")


class TestParse(unittest.TestCase):

    def test_simple(self):
        q = parse("a=1")
        self.assertEqual(q.get("a"), "1")

    def test_repeated_keys_collected(self):
        q = parse("tag=py&tag=web")
        self.assertEqual(q.get_all("tag"), ["py", "web"])

    def test_bare_key_is_none(self):
        q = parse("flag")
        self.assertIsNone(q.get("flag"))

    def test_empty_value_is_empty_string(self):
        q = parse("k=")
        self.assertEqual(q.get("k"), "")

    def test_decoding(self):
        q = parse("q=a%20b")
        self.assertEqual(q.get("q"), "a b")

    def test_empty_string(self):
        self.assertEqual(list(parse("").items()), [])

    def test_leading_question_mark_stripped(self):
        q = parse("?a=1")
        self.assertEqual(q.get("a"), "1")

    def test_skips_empty_pieces(self):
        q = parse("a=1&&b=2")
        self.assertEqual(q.get("a"), "1")
        self.assertEqual(q.get("b"), "2")

    def test_full_url_query_extracted(self):
        q = parse("http://example.org/path?a=1&b=2")
        self.assertEqual(q.get("a"), "1")
        self.assertEqual(q.get("b"), "2")


class TestRoundTrip(unittest.TestCase):

    def test_roundtrip_repeated(self):
        s = "tag=py&tag=web"
        self.assertEqual(build(parse(s)), s)

    def test_roundtrip_bare_key(self):
        s = "flag&x=1"
        self.assertEqual(build(parse(s)), s)

    def test_roundtrip_empty_value(self):
        s = "k="
        self.assertEqual(build(parse(s)), s)


class TestQueryContainer(unittest.TestCase):

    def test_set_replaces(self):
        q = Query([("a", "1"), ("a", "2")])
        q.set("a", "3")
        self.assertEqual(q.get_all("a"), ["3"])

    def test_remove(self):
        q = Query([("a", "1"), ("b", "2")])
        q.remove("a")
        self.assertNotIn("a", q)
        self.assertIn("b", q)

    def test_len_counts_values(self):
        q = Query([("a", "1"), ("a", "2"), ("b", "3")])
        self.assertEqual(len(q), 3)

    def test_get_default(self):
        q = Query()
        self.assertEqual(q.get("missing", "fallback"), "fallback")

    def test_items_yields_per_value(self):
        q = Query([("a", "1"), ("a", "2")])
        self.assertEqual(list(q.items()), [("a", "1"), ("a", "2")])

    def test_eq(self):
        a = Query([("k", "v")])
        b = Query([("k", "v")])
        self.assertEqual(a, b)

    def test_type_error_on_non_str_key(self):
        with self.assertRaises(TypeError):
            Query().add(123, "x")


if __name__ == "__main__":
    unittest.main()
