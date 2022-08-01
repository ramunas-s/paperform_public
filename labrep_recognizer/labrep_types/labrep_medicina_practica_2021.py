import pandas as pd

from labrep_recognizer.labrep_types.labrep_anteja_2021 import get_corpus_dfs
from labrep_recognizer.labrep_types.labrep_interface import LabrepInterface


class LabrepMedicinaPractica2021(LabrepInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.google_tools.debug_draw_image = False


    def medicina_practica_2021_corrector_rezult(self, s):
        if isinstance(s, str):
            s = s.replace("∕", "/")
        return s

    def identify(self):
        return self.abbyy_tools.find_anywhere("Medicina practica laboratorija, UAB")

    # Header methods

    def header_laboratory_name(self):
        return "Medicina practica"

    def header_requestor(self):
        return self.abbyy_tools.find_at_offset("Užsakovas:", 1, 0)

    def header_doctor(self):
        return self.abbyy_tools.find_till_the_end("Gydytojas:")

    def header_patient(self):
        return self.abbyy_tools.find_till_the_end("Pacientas").replace(",", "")

    def header_birth_date(self):
        return self.abbyy_tools.find_at_offset("Gimimo data:", 1, 0).replace(".", "-")

    def header_gender(self):
        return self.abbyy_tools.find_at_offset("Lytis:", 1, 0)

    def header_sample_collected_time_raw(self):
        found_value = self.google_tools.gd_get_text_to_right_from_keywords_all_pages(["Mėginio", "priėmimo", "data", "ir",
                                                                               "laikas"], boundary_x=0.73,
                                                                           boundary_relative=False, offset_y=0,
                                                                           line_separator=" ")
        return found_value[:16].replace(".", "-")

    def header_laboratory_report_id(self):
        order_no = self.abbyy_tools.find_at_offset(
            [
                "Užsakymo nr.:",
                "Užsakymo Nr.:",
            ],
            1,
            0,
        )
        return order_no

    # Details

    def details(self):
        # Look 2 above and 1 below for possible header/footer info
        df_extract_detail_candidates = self.df_abbyy_extracted.copy()
        df_extract_detail_candidates["is_detail_candiadte"] = df_extract_detail_candidates[7] != ""
        df_extract_detail_candidates["is_detail_h_f_candiadte"] = (
            (df_extract_detail_candidates["is_detail_candiadte"])
            | (df_extract_detail_candidates["is_detail_candiadte"].shift(-1, fill_value=False))
            #     | (df_abbyy_extracted["is_detail_candiadte"].shift(-2, fill_value=False))
            #     | (df_abbyy_extracted["is_detail_candiadte"].shift(1, fill_value=False))
        )

        df_extract_detail_candidates = df_extract_detail_candidates[
            df_extract_detail_candidates["is_detail_h_f_candiadte"]
        ].copy()

        categry_1 = ""
        categories_1 = []
        for i, row in df_extract_detail_candidates.iterrows():
            if (not row["is_detail_candiadte"]) and ("pastaba" not in (row[2].lower())):
                categry_1 = row[2]
            categories_1.append(categry_1)

        df_extract_detail_candidates["category_1"] = categories_1

        df_extract_detail_candidates = df_extract_detail_candidates[
            ((df_extract_detail_candidates[7] != "") & (df_extract_detail_candidates[7] != "Atlikimo data, laikas"))
        ]

        df_details = df_extract_detail_candidates.copy()

        # df_details["Rezultatas"] = pd.to_numeric(df_details[5].str.replace(",", "."), "coerce")
        df_details["Rezultatas"] = df_details[5]

        df_details = df_details.rename(columns={3: "Vienetai"})

        df_details = df_details.rename(columns={4: "ribos"})

        df_details = df_details.rename(columns={2: "test_name"})

        df_details["date_time"] = pd.to_datetime(df_details[7].str.replace(".", "-", regex=False), "coerce")

        df_details_normalized = (
            df_details[
                [
                    "category_1",
                    "test_name",
                    "Rezultatas",
                    "Vienetai",
                    "ribos",
                    "date_time",
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

        # TODO Identify urine samples
        df_details_normalized["test_type"] = "blood"

        # TODO Risky approach, refactor
        df_details_normalized["units"] = df_details_normalized["units"].str.replace("pg/L", "μg/L")
        df_details_normalized["units"] = df_details_normalized["units"].str.replace("pmol/L", "μmol/L")

        df_details_normalized_corrected = df_details_normalized.applymap(
            self.medicina_practica_2021_corrector_rezult
        ).copy()

        df_details_normalized_corrected["ranges"] = (
            df_details_normalized_corrected["ranges"]
            .str.replace(" -", "-")
            .str.replace("- ", "-")
            .str.replace(" - ", "-")
            .str.replace("-", " - ")
        )

        df_details_normalized_corrected["units"] = df_details_normalized_corrected["units"].replace(
            {
                "*10A9/L": "*10^9/L",
                "*10A12/L": "*10^12/L",
                "10A9/L": "10^9/L",
            }
        )

        change_test_names, df_corpus_exact_test_names, df_corpus_exclude_test_names = get_corpus_dfs()
        test_names_to_exclude = df_corpus_exclude_test_names["test_name"]
        df_details_normalized_corrected = df_details_normalized_corrected[
            ~df_details_normalized_corrected["test_name"].isin(test_names_to_exclude)
        ]


        return df_details_normalized_corrected
