import unittest

from jsonforge.core.search import search


class SearchTests(unittest.TestCase):
    def test_search_finds_embedded_json_value(self):
        data = {"settings": '{"theme":"dark"}'}
        matches = list(search(data, "dark"))
        self.assertTrue(any(path == "settings.theme" for path, _ in matches))


if __name__ == "__main__":
    unittest.main()
