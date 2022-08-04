import unittest
from mock import patch
import pandas as pd

from labrep_recognizer.recognition_tools.abbyy_tools import AbbyyTools


class AbbyyToolsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.df_spreadsheet = pd.DataFrame(
            {
                0: [
                    "a0",
                    "b0",
                    "c0",
                ],
                1: [
                    "string_a1",
                    "string_b1",
                    "string_c1",
                ],
                2: [
                    "a2",
                    "b2",
                    "c2",
                ],
            }
        )

    def test_init(self):
        abbyy_tools = AbbyyTools(AbbyyToolsTestCase.df_spreadsheet)
        extracted_all_fields_expected = ["a0", "a2", "b0", "b2", "c0", "c2", "string_a1", "string_b1", "string_c1"]
        self.assertEqual(extracted_all_fields_expected, abbyy_tools.extracted_all_fields)

    def test_find_anywhere(self):
        abbyy_tools = AbbyyTools(AbbyyToolsTestCase.df_spreadsheet)
        self.assertTrue(abbyy_tools.find_anywhere("b1"))
        self.assertFalse(abbyy_tools.find_anywhere("not_found_string"))

    def test_find_all_at_offset(self):
        abbyy_tools = AbbyyTools(AbbyyToolsTestCase.df_spreadsheet)

        self.assertEqual(
            ["b0", "b2", "c0", "c2", "string_b1", "string_c1"], abbyy_tools.find_all_at_offset(["a", "b"], 0, 1)
        )

        self.assertEqual(["c0", "c2", "string_c1"], abbyy_tools.find_all_at_offset(["b"], 0, 1))

        # TODO Fix IndexError: single positional indexer is out-of-bounds

        # self.assertEqual([], abbyy_tools.find_all_at_offset("c", 0, 1))
        self.assertEqual([], abbyy_tools.find_all_at_offset("not_found_string", 0, 1))

    @patch(
        "labrep_recognizer.recognition_tools.abbyy_tools.AbbyyTools.find_all_at_offset",
        return_value=["b_value", "c_value", "a_value"],
    )
    def test_find_at_offset(self, find_all_at_offset_mock):
        abbyy_tools = AbbyyTools(AbbyyToolsTestCase.df_spreadsheet)
        self.assertEqual("b_value", abbyy_tools.find_at_offset(["a", "b"], 0, 1))

    @patch("labrep_recognizer.recognition_tools.abbyy_tools.AbbyyTools.find_all_at_offset", return_value=[])
    def test_find_at_offset_failure(self, find_all_at_offset_mock):
        abbyy_tools = AbbyyTools(AbbyyToolsTestCase.df_spreadsheet)
        with self.assertRaises(IndexError):
            abbyy_tools.find_at_offset(["a", "b"], 0, 1)

    def test_find_till_the_end(self):
        df_spreadsheet_augmented = AbbyyToolsTestCase.df_spreadsheet.copy()
        df_spreadsheet_augmented.iloc[1][1] = "string_to_find word1 word2"
        abbyy_tools = AbbyyTools(df_spreadsheet_augmented)
        self.assertEqual("word1 word2", abbyy_tools.find_till_the_end("string_to_find", remove=False))
        self.assertEqual("word1 word2", abbyy_tools.find_till_the_end("string_to_find", remove=True))
        with self.assertRaises(IndexError):
            self.assertEqual("word1 word2", abbyy_tools.find_till_the_end("string_to_find", remove=False))

    def test_find_whole_word(self):
        df_spreadsheet_augmented = AbbyyToolsTestCase.df_spreadsheet.copy()
        df_spreadsheet_augmented.iloc[1][1] = "string_to_find word1 word2"
        abbyy_tools = AbbyyTools(df_spreadsheet_augmented)
        self.assertEqual("word1", abbyy_tools.find_whole_word("string_to_find", remove=False))
        self.assertEqual("word1", abbyy_tools.find_whole_word("string_to_find", remove=True))
        with self.assertRaises(IndexError):
            self.assertEqual("word1", abbyy_tools.find_whole_word("string_to_find", remove=False))

    def test_find_till_the_end_in_copy(self):
        abbyy_tools = AbbyyTools(AbbyyToolsTestCase.df_spreadsheet)
        all_fields_expected_copy = [
            "d_a0",
            "d_a2",
            "d_b0",
            "d_b2",
            "d_c0",
            "d_c2",
            "d_string_a1",
            "different_string_to_find d_word1 d_word2",
            "d_string_c1",
        ]
        self.assertEqual(
            "d_word1 d_word2",
            abbyy_tools.find_till_the_end_in_copy("different_string_to_find", all_fields_expected_copy, remove=False),
        )
        self.assertEqual(
            "d_word1 d_word2",
            abbyy_tools.find_till_the_end_in_copy("different_string_to_find", all_fields_expected_copy, remove=True),
        )
        with self.assertRaises(IndexError):
            self.assertEqual(
                "d_word1 d_word2",
                abbyy_tools.find_till_the_end_in_copy(
                    "different_string_to_find", all_fields_expected_copy, remove=False
                ),
            )

    @patch(
        "labrep_recognizer.recognition_tools.abbyy_tools.AbbyyTools.find_till_the_end_in_copy",
        return_value="expected_value",
    )
    def test_find_between_keywords(self, find_between_keywords_mock):
        abbyy_tools = AbbyyTools(AbbyyToolsTestCase.df_spreadsheet)
        self.assertEqual("expected_value", abbyy_tools.find_between_keywords("before", "after"))
