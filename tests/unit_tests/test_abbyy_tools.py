import unittest
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

        self.assertEqual([], abbyy_tools.find_all_at_offset("not_found_string", 0, 1))

        pass
