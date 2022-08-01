from copy import copy
import string

from labrep_recognizer.labrep_types.labrep_interface import LabrepInterface
from functools import partial
import pandas as pd
from labrep_recognizer.recognition_tools.ocr_tolerance import (
    correct_ocr_error_by_one_corpus,
    correct_ocr_error_by_flex_corpuses,
)
from labrep_recognizer.shared.utils import is_valid_iso_date_time_str


class LabrepAnteja2021(LabrepInterface):
    def anteja_2021_corrector_rezult(self, s):
        if isinstance(s, str):
            s = s.replace("∕", "/")
        return s

    def identify(self):
        return self.abbyy_tools.find_anywhere("300598351")

    # Header methods

    def header_laboratory_name(self):
        return "Antėja"

    def header_requestor(self):
        return self.abbyy_tools.find_till_the_end("Užsakovas:", remove=False)

    def header_doctor(self):
        return self.abbyy_tools.find_till_the_end("Gydytojas:", remove=False)

    def header_patient(self):
        return self.abbyy_tools.find_till_the_end("Pacientas:", remove=False)

    def header_birth_date(self):
        return self.abbyy_tools.find_between_keywords("Gimimo data:", "Lytis:")

    def header_gender(self):
        return self.abbyy_tools.find_till_the_end("Lytis:", remove=False)

    def header_sample_collected_time_raw(self):
        sample_collected_time_candidate = self.abbyy_tools.find_at_offset("Mėginys paimtas", 0, 1)
        if not is_valid_iso_date_time_str(sample_collected_time_candidate):
            sample_collected_time_candidate = self.abbyy_tools.find_between_keywords("Užsakymo data:", "Nr.:")
        return sample_collected_time_candidate

    def header_laboratory_report_id(self):
        return self.abbyy_tools.find_till_the_end("Nr.:", remove=False)

    # Details

    def details(self):
        # Look 2 above and 1 below for possible header/footer info
        df_extract_detail_candidates = self.df_abbyy_extracted.copy()

        df_extract_detail_candidates["is_detail_candiadte"] = (df_extract_detail_candidates[7] != "") & (
            df_extract_detail_candidates[7] != "M"
        )
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
            if (not row["is_detail_candiadte"]) and (row[0] != ""):
                categry_1 = row[0]
            categories_1.append(categry_1)

        df_extract_detail_candidates["category_1"] = categories_1

        df_details = df_extract_detail_candidates[
            (df_extract_detail_candidates[7] != "") & (df_extract_detail_candidates[7] != "M")
        ].copy()

        # pd.to_numeric(df_details[1].str.replace(",", "."), "coerce")

        # df_details["Rezultatas"] = pd.to_numeric(df_details[1].str.replace(",", "."), "coerce")
        df_details["Rezultatas"] = df_details[1]

        df_details["Atlikimo laikas"] = pd.to_datetime(df_details[4], "coerce")
        df_details = df_details.rename(columns={2: "Norma"})

        ds_test_and_measurement = (
            df_details[0]
            .str.replace("(Programa)", "", regex=False)
            .str.replace("[104]", "", regex=False)
            .str.replace("[105]", "", regex=False)
            .str.replace("[109]", "", regex=False)
            .str.replace("(ŠG norma)", "", regex=False)
            .str.replace("Programa", "", regex=False)
            .str.replace(")", "", regex=False)
        ).str.split("(")

        df_details["Tyrimas"] = ds_test_and_measurement.apply(lambda x: x[0].strip())
        df_details["Matavimo vienetai"] = ds_test_and_measurement.apply(lambda x: x[-1].strip())

        df_details_normalized = (
            df_details[
                [
                    "category_1",
                    "Tyrimas",
                    "Rezultatas",
                    "Matavimo vienetai",
                    "Norma",
                    "Atlikimo laikas",
                ]
            ]
            .rename(
                columns={
                    "category_1": "category",
                    "Tyrimas": "test_name",
                    "Rezultatas": "value",
                    "Matavimo vienetai": "units",
                    "Norma": "ranges",
                    "Atlikimo laikas": "date_time",
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

        # TODO risky replacement, should do additional check
        df_details_normalized["units"] = df_details_normalized["units"].str.replace("pg/l", "μg/l")

        df_details_normalized["units"] = df_details_normalized.apply(
            lambda row: row["units"].replace(
                "pmol/l",
                "μmol/l"
                if row["test_name"]
                not in [
                    "FT4 Laisvas tiroksinas",
                ]
                else row["units"],
            ),
            axis=1,
        )

        df_details_normalized["units"] = df_details_normalized["units"].replace(
            {
                "*10^9Zl": "*10^9/l",
                "*10^9ZI": "*10^9/l",
                "*10^12Zl": "*10^12/l",
                "μmolZl": "μmol/l",
                "g∕∣": "g/l",
                "2019-nCoV RNR tyrimas tikralaikės PGR metodu": "",
            }
        )

        google_ocred_text = str(self.google_ocred_document.text).replace("\n", " ").replace("–", "-")

        # df_details_normalized.applymap(corrector_rezult_anteja).applymap(
        #     lambda x: (str(x).replace(".", ",")) if isinstance(x, float) else (str(x))
        # )

        # search_string = "hemoglobinas"
        # found_values = find_with_1_2_character_tolerance(google_ocred_text, search_string)
        #
        # print(f"\nfound:\nf{found_values}")

        df_details_normalized_corrected = df_details_normalized.applymap(self.anteja_2021_corrector_rezult)

        # df_details_normalized_corrected["ranges"].apply(partial(correct_ocr_error_by_one_corpus, google_ocred_text))

        change_test_names, df_corpus_exact_test_names, df_corpus_exclude_test_names = get_corpus_dfs()

        corpus_exact_test_names = df_corpus_exact_test_names["test_name"]

        df_details_normalized_corrected["test_name"] = df_details_normalized_corrected["test_name"].apply(
            lambda x: correct_ocr_error_by_flex_corpuses(
                [google_ocred_text],
                [
                    [x],
                    # in order to ensure that the value is overridden if the data is found in more than one supporting corpus
                    corpus_exact_test_names,
                    corpus_exact_test_names,  # Duplicate to increase an inportan ce
                ],
                x,
            )
        )

        test_names_to_exclude = df_corpus_exclude_test_names["test_name"]
        df_details_normalized_corrected = df_details_normalized_corrected[
            ~df_details_normalized_corrected["test_name"].isin(test_names_to_exclude)
        ]

        df_details_normalized_corrected["test_name"] = df_details_normalized_corrected["test_name"].replace(
            change_test_names
        )

        return df_details_normalized_corrected


# TODO move to utils module


def get_corpus_dfs():
    df_corpus_exact_test_names = pd.read_csv(
        "./data/corpus/test_names_exact.csv",
        dtype=str,
        keep_default_na=False,
    )
    df_corpus_exclude_test_names = pd.read_csv(
        "./data/corpus/test_names_exclude.csv",
        dtype=str,
        keep_default_na=False,
    )
    df_corpus_change_test_names = pd.read_csv(
        "./data/corpus/test_names_change.csv",
        dtype=str,
        keep_default_na=False,
    )
    change_test_names = df_corpus_change_test_names.set_index("test_name_before")["test_name_after"].to_dict()
    return change_test_names, df_corpus_exact_test_names, df_corpus_exclude_test_names


urine_codes_set = [
    {"gliukozė", "glu", "glucose"},
    {"bil", "bilirubin", "bilirubinas"},
    {"ket", "ketonai", "ketone"},
    {"gravity", "sg", "svoris", "tankis"},
    {"eritrocitai", "ery", "hemoglobinas", "mioglobinas", "rbc", "red"},
    {"ph"},
    {"albuminas", "baltymas", "pro", "protein"},
    {"ubg", "urb", "uro", "urobilinogen", "urobilinogenas"},
    {"bacteria", "bakterijos", "bakteriurija", "nit", "nitritai", "nitrites"},
    {"leu", "leucocytes", "leukocitai", "leukocytes", "wbc", "white"},
    {"bld", "blood", "kraujas"},
    {"vtc"},
]


def split_words(s):
    for punctuator in string.punctuation:
        s = s.replace(punctuator, " ")
    return s.split()


def find_urine_code(s, urine_codes):
    found_code = None
    s_split = set([word.lower() for word in split_words(s)])

    for i, line in enumerate(urine_codes):
        if line & s_split:
            found_code = i
            break
    return found_code


def find_urine_block(df_urine, column_test_name):
    df_urine["urine_index"] = df_urine[column_test_name].apply(find_urine_code, urine_codes=urine_codes_set)
    df_urine["could_be_urine"] = df_urine["urine_index"] >= 0
    df_urine["urine_block_index"] = (df_urine["could_be_urine"] != df_urine["could_be_urine"].shift()).cumsum()
    df_urine["urine_consec_count"] = df_urine.groupby(["urine_block_index"]).cumcount()
    df_urine["urine_max_count"] = df_urine.groupby(["urine_block_index"])["urine_consec_count"].transform(max) + 1
    df_urine["is_urine_block"] = (df_urine["urine_max_count"] >= 7) & (df_urine["could_be_urine"])
    df_urine = df_urine.drop(
        columns=[
            "urine_index",
            "could_be_urine",
            "urine_block_index",
            "urine_consec_count",
            "urine_max_count",
        ]
    )
    return df_urine
