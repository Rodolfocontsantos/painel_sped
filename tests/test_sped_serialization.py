import unittest

from qt_backend import build_full_content


class SpedSerializationTests(unittest.TestCase):
    def test_uses_crlf_and_terminates_the_last_line(self):
        content = build_full_content(
            ["|0000|TESTE|", "|0990|2|"],
            ["|9999|3|"],
        )

        self.assertEqual(
            content,
            "|0000|TESTE|\r\n|0990|2|\r\n|9999|3|\r\n",
        )
        self.assertTrue(content.endswith("\r\n"))
        self.assertNotIn("\n", content.replace("\r\n", ""))

    def test_empty_sped_remains_empty(self):
        self.assertEqual(build_full_content([], []), "")


if __name__ == "__main__":
    unittest.main()
