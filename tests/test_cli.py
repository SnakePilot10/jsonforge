import subprocess
import sys
import unittest


class CliTests(unittest.TestCase):
    def test_module_exit_code_for_search_miss(self):
        result = subprocess.run(
            [sys.executable, "-m", "jsonforge", "search", "tests/fixtures/sample.json", "missing-value"],
            check=False,
        )

        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
