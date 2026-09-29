import unittest

from keyword_extractor.engine import extract_keywords


class ExtractKeywordsTests(unittest.TestCase):
    def test_ranks_repeated_relevant_terms(self) -> None:
        result = extract_keywords(["insulated travel mug", "reusable travel mug", "desk light"], top=5)
        self.assertIn("travel mug", [item.keyword for item in result])
        self.assertEqual(result, extract_keywords(["insulated travel mug", "reusable travel mug", "desk light"], top=5))

    def test_stop_words_and_empty_documents(self) -> None:
        result = extract_keywords(["the custom token", "", "custom token"], stop_words=["custom"])
        self.assertEqual([item.keyword for item in result], ["token"])

    def test_rejects_invalid_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 1"):
            extract_keywords(["sample"], top=0)


if __name__ == "__main__":
    unittest.main()
