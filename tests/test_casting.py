import unittest

from jsonforge.core.casting import parse_preserving_type, parse_typed_value, smart_cast


class SmartCastTests(unittest.TestCase):
    def test_smart_cast_literals(self):
        self.assertIs(smart_cast("true"), True)
        self.assertIs(smart_cast("false"), False)
        self.assertIsNone(smart_cast("null"))

    def test_smart_cast_numbers(self):
        self.assertEqual(smart_cast("42"), 42)
        self.assertEqual(smart_cast("3.5"), 3.5)

    def test_smart_cast_json_and_string(self):
        self.assertEqual(smart_cast('{"a": 1}'), {"a": 1})
        self.assertEqual(smart_cast("hello"), "hello")

    def test_parse_typed_value_can_force_string(self):
        self.assertEqual(parse_typed_value("00123", "string"), "00123")

    def test_parse_typed_value_json(self):
        self.assertEqual(parse_typed_value('[1, 2]', "json"), [1, 2])

    def test_reject_infinity_from_auto_cast(self):
        with self.assertRaises(ValueError):
            smart_cast("1e999")

    def test_reject_nan_from_json_type(self):
        with self.assertRaises(ValueError):
            parse_typed_value('{"value": NaN}', "json")

    def test_parse_preserving_type_keeps_strings_as_strings(self):
        self.assertEqual(parse_preserving_type("false", "true"), "false")

    def test_parse_preserving_type_keeps_bool_as_bool(self):
        self.assertIs(parse_preserving_type("false", True), False)

    def test_parse_preserving_type_rejects_object_to_scalar(self):
        with self.assertRaisesRegex(ValueError, "Expected a JSON object"):
            parse_preserving_type("123", {"a": 1})

    def test_parse_preserving_type_rejects_array_to_object(self):
        with self.assertRaisesRegex(ValueError, "Expected a JSON array"):
            parse_preserving_type('{"a": 1}', [1, 2])

    def test_parse_preserving_type_preserves_null_only_for_null_text(self):
        self.assertIsNone(parse_preserving_type("null", None))
        with self.assertRaisesRegex(ValueError, "Preserving null"):
            parse_preserving_type("hello", None)

    def test_parse_preserving_type_allows_object_to_object(self):
        self.assertEqual(parse_preserving_type('{"b": 2}', {"a": 1}), {"b": 2})

    def test_parse_preserving_type_allows_array_to_array(self):
        self.assertEqual(parse_preserving_type("[3, 4]", [1, 2]), [3, 4])


if __name__ == "__main__":
    unittest.main()
