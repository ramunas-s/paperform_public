from functools import partial
import pandas as pd

from labrep_recognizer.labrep_types.labrep_anteja_2021 import get_corpus_dfs, find_urine_block
from labrep_recognizer.labrep_types.labrep_interface import LabrepInterface
from labrep_recognizer.recognition_tools.image_debug import debug_img
from labrep_recognizer.recognition_tools.ocr_tolerance import correct_ocr_error_by_two_corpus
from labrep_recognizer.shared.utils import split_cell


class LabrepSynlab2021(LabrepInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Debug
        # page_no = 0
        # self.google_tools.debug_draw_image = True
        # self.google_tools.draw_page_img(page_no)
        # self.google_tools.zoom_factor = 2000.0

    def identify(self):
        try:
            is_synlab_2021 = "SYNLAB" in self.google_tools.gd_get_text_to_right_from_keywords(
                0,
                ["Laboratorija"],
                boundary_x=1.0,
                boundary_relative=False,
                offset_y=0,
                line_separator=" ",
            )
        except AssertionError:
            is_synlab_2021 = False

        return is_synlab_2021

    # Specific functions

    # Header methods

    # @debug_img
    def header_patient(self):
        page_no = 0

        # Debug
        # self.google_tools.draw_page_img(page_no)

        labels_key_current_line = [
            ["Paciento", "pavardė", "vardas", ":"],
            ["Paciento", "pavardė", ","],
            ["Paciento", "pavardė"],
            ["Paciento"],
        ]
        labels_key_below_line = [["Gimimo", "data"], ["Gimimo"]]
        right_boundary = 0.50
        line_separator = " "

        concatenated_text = self.google_tools.extract_text_from_rectangle_to_left_between_keys(
            page_no, labels_key_current_line, labels_key_below_line, right_boundary, line_separator
        )

        # Debug:
        # self.google_tools.image_save()

        return concatenated_text

    def header_laboratory_name(self):
        return self.google_tools.gd_get_text_to_right_from_keywords_options(
            0,
            [["Laboratorija", ":"], ["Laboratorija"]],
            boundary_x=1.0,
            boundary_relative=False,
            offset_y=0,
            line_separator=" ",
        )

    def header_requestor(self):
        return self.google_tools.gd_get_text_to_right_from_keywords(
            0, ["Siuntėjas"], boundary_x=1.0, boundary_relative=False, offset_y=0, line_separator=" "
        )

    # @debug_img
    def header_doctor(self):
        page_no = 0

        # Debug
        # self.google_tools.draw_page_img(page_no)

        labels_key_current_line = [["Gydytojo", "vardas"], ["Gydytojo"]]
        labels_key_below_line = [["Klinikinė", "diagnozė"], ["Klinikinė"]]
        right_boundary = 1.0
        line_separator = ""

        concatenated_text = self.google_tools.extract_text_from_rectangle_to_left_between_keys(
            page_no, labels_key_current_line, labels_key_below_line, right_boundary, line_separator
        )

        # Debug:
        # self.google_tools.image_save()

        return concatenated_text

    def header_birth_date(self):

        # Debug
        # self.google_tools.draw_page_img(0)

        concatenated_text = self.google_tools.gd_get_text_to_right_from_keywords_options(
            0,
            [["Gimimo", "data", ":"], ["Gimimo", "data"]],
            boundary_x=0.44,
            boundary_relative=False,
            offset_y=0,
            line_separator=" ",
        )

        # Debug:
        # self.google_tools.image_save()

        return concatenated_text

    def header_gender(self):
        return self.google_tools.gd_get_text_to_right_from_keywords_options(
            0, [["Lytis", ":"], ["Lytis"]], boundary_x=0.44, boundary_relative=False, offset_y=0, line_separator=" "
        )

    def header_sample_collected_time_raw(self):
        sample_date_time_candidate = self.google_tools.gd_get_text_to_right_from_keywords_options(
            0,
            [["Eminių", "data", ":"], ["Ėminių", "data"]],
            boundary_x=0.44,
            boundary_relative=False,
            offset_y=0,
            line_separator=" ",
        )
        sample_date_time_candidate = sample_date_time_candidate.split(",")[0].strip()
        return sample_date_time_candidate

    def header_laboratory_report_id(self):
        return self.google_tools.gd_get_text_to_right_from_keywords(
            0, ["Tyrimų", "atsakymas", "Nr"], boundary_x=1.0, boundary_relative=False, offset_y=0, line_separator=" "
        )

    def synlab_2021_corrector_rezult(self, s):
        if isinstance(s, str):
            s = s.replace("∕", "/")
            s = s.replace("_", "")
        return s

    # Diagnostics

    def synlab_2021_diagnostics(self, google_ocred_document):
        page_no = 0
        zoom_factor = 1000.0
        canvas = self.google_tools.initiate_canvas(
            google_ocred_document,
            page_no=page_no,
            zoom_factor=zoom_factor,
        )
        # Test conservative approach by scanning two lines
        tokens_paciento_pavarde = self.google_tools.gd_find_by_keywords(google_ocred_document, 0)
        # tokens_paciento_pavarde = gd_find_by_keywords(
        #     google_ocred_document, 0, ["RDW", "eritrocitų", "pasiskirstymas", "pagal"], debug_draw_image
        # )
        assert len(tokens_paciento_pavarde) == 1
        token_paciento_pavarde = tokens_paciento_pavarde[0]
        tokens_paciento_pavarde_value = []
        tokens_paciento_pavarde_value += self.google_tools.gd_find_token_to_right(
            google_ocred_document, 0, token_paciento_pavarde, offset_y=-0.002
        )
        tokens_paciento_pavarde_value += self.google_tools.gd_find_token_to_right(
            google_ocred_document, 0, token_paciento_pavarde, offset_y=0.015
        )
        # Test is same row
        token_from = self.google_tools.gd_find_by_text(google_ocred_document, 0, "RBC")[0]
        self.google_tools.draw_token_polygon(canvas, token_from, "blue", zoom_factor)
        for token in google_ocred_document.pages[0].tokens:
            if self.google_tools.is_same_row(token_from, token):
                self.google_tools.draw_token_polygon(canvas, token, "aqua", zoom_factor)
        # Test find and organize tokens in a box
        found_tokens = self.google_tools.gd_find_tokens_in_box(google_ocred_document, 0)
        print(self.google_tools.concatenate_tokens_box(found_tokens, google_ocred_document))
        # Test get patient name from GD
        print(self.header_patient())

        return None

    # Details

    def details(self):
        df_extract = self.df_abbyy_extracted.copy()

        # TODO identify columns for:
        #    test name
        #    value
        #    unit

        original_columns = df_extract.shape[1]
        units_split_decision = None

        if original_columns == 4:
            # verify if column 1 is not used, or is a value
            col_1_is_number = sum(~pd.to_numeric(df_extract[1], errors="coerce").isna()) >= 2
            if col_1_is_number:
                df_extract = df_extract.rename(
                    columns={
                        0: "column_test_name",
                        1: "column_value",
                        2: "column_unit_1",
                        3: "column_range_1",
                    }
                )
                df_extract["column_range_2"] = ""
                df_extract["column_range_3"] = ""
                df_extract["column_unit_2"] = ""
            else:
                df_extract = df_extract.rename(
                    columns={
                        0: "column_test_name",
                        1: "column_not_used_1",
                        2: "column_value",
                        3: "column_unit_1",
                    }
                )
                df_extract["column_range_1"] = (
                    df_extract["column_unit_1"].apply(split_cell, separator="    ").apply(lambda x: x[1])
                )
                df_extract["column_unit_1"] = (
                    df_extract["column_unit_1"].apply(split_cell, separator="    ").apply(lambda x: x[0])
                )
                df_extract["column_range_2"] = ""
                df_extract["column_range_3"] = ""
                df_extract["column_unit_2"] = ""
        elif original_columns == 5:
            # resolve the case where either units are split or ranges are split
            # does not work well when different split is applied on different pages
            # e.g. edc1dae59b07450c925e856661af88cbd9846384937f3f09d4a2349a8affb0b7.pdf

            units_split_decision = (
                sum(df_extract[2].apply(lambda s: "10^" in s) & df_extract[3].apply(lambda s: "9/l" in s)) >= 2
            )

            if units_split_decision:
                df_extract = df_extract.rename(
                    columns={
                        0: "column_test_name",
                        1: "column_value",
                        2: "column_unit_1",
                        3: "column_unit_2",
                        4: "column_range_1",
                    }
                )
                df_extract["column_range_2"] = ""
                df_extract["column_range_3"] = ""
            else:
                df_extract = df_extract.rename(
                    columns={
                        0: "column_test_name",
                        1: "column_value",
                        2: "column_unit_1",
                        3: "column_range_1",
                        4: "column_range_2",
                    }
                )
                df_extract["column_range_3"] = ""
                df_extract["column_unit_2"] = ""
        elif original_columns == 6:
            df_extract = df_extract.rename(
                columns={
                    0: "column_test_name",
                    1: "column_value",
                    2: "column_unit_1",
                    3: "column_range_1",
                    4: "column_range_2",
                    5: "column_range_3",
                }
            )
            df_extract["column_unit_2"] = ""

        elif original_columns == 7:
            df_extract = df_extract.rename(
                columns={
                    0: "column_test_name",
                    1: "column_value",
                    2: "column_unit_1",
                    3: "column_range_1",
                    4: "column_range_2",
                    5: "column_range_3",
                }
            )
            df_extract["column_unit_2"] = ""

        df_extract["column_unit"] = df_extract["column_unit_1"].str.strip() + df_extract["column_unit_2"].str.strip()
        if original_columns == 5 and units_split_decision:
            df_extract["column_unit"] = df_extract["column_unit"].replace(
                {
                    "10^'9/i": "10^9/l",
                    "10^'12/i": "10^12/l",
                    "10^' 12/l": "10^12/l",
                }
            )

        # Remove empty rows
        df_extract = df_extract[df_extract.any(axis=1)]

        df_extract["test_name_above"] = df_extract["column_test_name"].shift(1, fill_value="")
        df_extract["result_above"] = df_extract["column_value"].shift(1, fill_value="")
        df_extract["test_name_is_above"] = (
            # ((df_extract["column_range_2"] != "") | (df_extract["column_range_1"] != ""))
            (df_extract["column_test_name"] == "")
            & (df_extract["column_value"] != "")
            & (df_extract["test_name_above"] != "")
            & (df_extract["result_above"] == "")
        )
        df_extract["misplaced_test_name"] = df_extract["test_name_is_above"].shift(-1, fill_value=False)
        df_extract = df_extract[~df_extract["misplaced_test_name"]].copy()
        df_extract["test_name"] = df_extract.apply(
            lambda row_internal: row_internal["test_name_above"]
            if row_internal["test_name_is_above"]
            else row_internal["column_test_name"],
            axis=1,
        )

        # Look 2 above and 1 below for possible header/footer info
        df_extract["is_detail_candiadte"] = (df_extract["column_range_2"] != "") | (df_extract["column_range_1"] != "")
        df_extract["is_detail_h_f_candiadte"] = (
            (df_extract["is_detail_candiadte"])
            | (df_extract["is_detail_candiadte"].shift(-1, fill_value=False))
            #     | (df_abbyy_extracted["is_detail_candiadte"].shift(-2, fill_value=False))
            #     | (df_abbyy_extracted["is_detail_candiadte"].shift(1, fill_value=False))
        )

        df_extract["is_detail_h_f_candiadte"] = (
            df_extract["is_detail_h_f_candiadte"] | ~pd.to_numeric(df_extract["column_value"], errors="coerce").isna()
        )

        df_extract_detail_candidates = df_extract[df_extract["is_detail_h_f_candiadte"]].copy()

        categry_1 = ""
        categories_1 = []
        for i, row in df_extract_detail_candidates.iterrows():
            if not row["is_detail_candiadte"]:
                categry_1 = row["test_name"]
            categories_1.append(categry_1)

        df_extract_detail_candidates["category_1"] = categories_1

        df_extract_detail_candidates = df_extract_detail_candidates[
            df_extract_detail_candidates["is_detail_h_f_candiadte"]
        ]

        df_extract_detail_candidates = df_extract_detail_candidates[
            (
                (df_extract_detail_candidates["column_value"] != "")
                & (df_extract_detail_candidates["column_value"] != "Rezultatas")
            )
        ]

        df_details = df_extract_detail_candidates.copy()

        # df_details["Rezultatas"] = pd.to_numeric(df_details["column_value"], "coerce")
        df_details["Rezultatas"] = df_details["column_value"]

        df_details = df_details.rename(columns={"column_unit": "Vienetai"})

        df_details["Vienetai"] = df_details["Vienetai"].str.replace("λ", "^").str.replace("∕", "/")

        df_details["ribos"] = (df_details["column_range_1"] + " " + df_details["column_range_2"]).str.strip()

        df_details_normalized = (
            df_details[
                [
                    "category_1",
                    "test_name",
                    "Rezultatas",
                    "Vienetai",
                    "ribos",
                ]
            ]
            .rename(
                columns={
                    "category_1": "category",
                    "test_name": "test_name",
                    "Rezultatas": "value",
                    "Vienetai": "units",
                    "ribos": "ranges",
                }
            )
            .reset_index(drop=True)
        )

        # Identify urine samples
        df_details_normalized = find_urine_block(df_details_normalized, "test_name")
        df_details_normalized["is_urine_category"] = df_details_normalized["category"].apply(
            lambda x: any([fragment in x.lower() for fragment in ["šlap", "bšt"]])
        )
        df_details_normalized["test_type"] = (
            df_details_normalized["is_urine_block"] & df_details_normalized["is_urine_category"]
        ).map({True: "urine", False: "blood"})
        df_details_normalized = df_details_normalized.drop(columns=["is_urine_block", "is_urine_category"])

        df_details_normalized["date_time"] = pd.NaT

        google_ocred_text = str(self.google_ocred_document.text).replace("\n", " ").replace("–", "-")

        # search_string = "hemoglobinas"
        # found_values = find_with_1_2_character_tolerance(google_ocred_text, search_string)
        # print(f"\nfound:\nf{found_values}")

        df_details_normalized_corrected = df_details_normalized.applymap(self.synlab_2021_corrector_rezult)

        df_details_normalized_corrected["test_name"] = df_details_normalized_corrected["test_name"].apply(
            partial(correct_ocr_error_by_two_corpus, google_ocred_text, self.tika_extracted_text)
        )
        df_details_normalized_corrected["units"] = (
            df_details_normalized_corrected["units"]
            .apply(partial(correct_ocr_error_by_two_corpus, google_ocred_text, self.tika_extracted_text))
            .str.strip()
        )
        df_details_normalized_corrected["ranges"] = (
            df_details_normalized_corrected["ranges"]
            .str.replace(" -", "-")
            .str.replace("- ", "-")
            .str.replace(" - ", "-")
            .str.replace("-", " - ")
        )

        change_test_names, df_corpus_exact_test_names, df_corpus_exclude_test_names = get_corpus_dfs()

        test_names_to_exclude = df_corpus_exclude_test_names["test_name"]
        df_details_normalized_corrected = df_details_normalized_corrected[
            ~df_details_normalized_corrected["test_name"].isin(test_names_to_exclude)
        ]

        df_details_normalized_corrected["units"] = df_details_normalized_corrected["units"].replace(
            {
                "10^9/1": "10^9/l",
                "10^12/1": "10^12/l",
                "U/l (x0.0167=ukat/l)": "U/l (x0.0167=μkat/l)",
                "U/l (x0.0167=ųkat/l)": "U/l (x0.0167=μkat/l)",
                "o/ /0": "%",
            }
        )

        return df_details_normalized_corrected
