import unittest

from jsonforge.core.embedded_json import decode_if_embedded_json, encode_if_needed


class EmbeddedJsonTests(unittest.TestCase):
    def test_decode_embedded_json_object(self):
        decoded = decode_if_embedded_json('{"a":1}')
        self.assertIs(decoded.was_embedded_json, True)
        self.assertEqual(decoded.value, {"a": 1})

    def test_non_json_string_is_unchanged(self):
        decoded = decode_if_embedded_json("plain")
        self.assertIs(decoded.was_embedded_json, False)
        self.assertEqual(decoded.value, "plain")

    def test_encode_embedded_json(self):
        self.assertEqual(encode_if_needed({"a": 1}, True), '{"a":1}')


if __name__ == "__main__":
    unittest.main()
