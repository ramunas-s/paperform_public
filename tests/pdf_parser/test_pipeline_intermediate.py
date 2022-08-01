import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from labrep_recognizer.pipeline import initialize_infrastructure, upload_pdf_to_gs, process_single_pdf_in_gs


class PipelineIntermediateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @staticmethod
    def single_run(test_name, recognizer_infrastructure):
        print(f"Testing {test_name}:")
        raw_pdf = "./test_data_files/labrep_recognizer/pdf_examples/" + test_name + ".pdf"
        status = []
        uploaded_file_uri = upload_pdf_to_gs(raw_pdf, recognizer_infrastructure)
        recognition_status_ok, recognition_error, df_header, df_details = process_single_pdf_in_gs(
            uploaded_file_uri, recognizer_infrastructure
        )
        status.append((test_name, "parsing_status", recognition_status_ok, recognition_error))
        if recognition_status_ok:

            # Backwards compatibility with tests with numeric values
            # df_details["value"] = pd.to_numeric(df_details["value"].str.replace(",", "."), errors="coerce")

            df_header.to_parquet("./test_data_files/labrep_recognizer/test_results/" + test_name + "_header.parquet")
            df_details.to_parquet("./test_data_files/labrep_recognizer/test_results/" + test_name + "_details.parquet")

            df_header_e = pd.read_parquet(
                "./test_data_files/labrep_recognizer/expected/" + test_name + "_header.parquet"
            )
            df_details_e = pd.read_parquet(
                "./test_data_files/labrep_recognizer/expected/" + test_name + "_details.parquet"
            )

            try:
                assert_frame_equal(df_header, df_header_e, check_like=True)
                status.append((test_name, "df_header", True, ""))
            except AssertionError as e:
                status.append((test_name, "df_header", False, ""))
                print(e)

            try:
                columns_to_ignore = [
                    # "test_type",
                    # "category",
                ]
                assert_frame_equal(
                    df_details.drop(columns=columns_to_ignore, errors="ignore"),
                    df_details_e.drop(columns=columns_to_ignore, errors="ignore"),
                )
                status.append((test_name, "df_abbyy_extracted", True, ""))
            except AssertionError as e:
                status.append((test_name, "df_abbyy_extracted", False, ""))
                print(e)

        return status

    def test_single_instance(self):
        recognizer_infrastructure = initialize_infrastructure()

        test_names = [
            "anteja",
            "medicina_practica",
            "synlab",
        ]

        status = []

        for test_name in test_names:
            status += PipelineIntermediateTest.single_run(test_name, recognizer_infrastructure)

        df_status = pd.DataFrame(status)
        print(df_status.loc[:, 0:2])

        print("\n".join([str(element) for element in status if not element[2]]))
        assert all(df_status[2])

        if recognizer_infrastructure._cache:
            recognizer_infrastructure._cache.persist_cache()
