import unittest

from jsonforge.core.casting import parse_typed_value, smart_cast


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


if __name__ == "__main__":
    unittest.main()
