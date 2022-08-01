import pandas as pd

from labrep_recognizer.normalization.normalization_standard import (
    select_single_normalized,
    normalize_results_to_standard,
)


def normalize_result_to_revolab(df_header, df_details):
    df_normalized_standard = normalize_results_to_standard(df_header, df_details)

    # TODO move to parameters, load once
    df_mapping_revolab = pd.read_csv(
        "./data/mapping/standard_to_revolab_mapping.csv",
        dtype="str",
        keep_default_na=False,
    ).drop_duplicates(subset=["code"])

    df_normalized_revolab = df_normalized_standard.merge(df_mapping_revolab, on=["code"], how="left")
    df_normalized_revolab = select_single_normalized(df_normalized_revolab, "revolab_id")
    matched = (
        df_normalized_revolab.rename(columns={"revolab_id": "test_code"}).set_index("test_code").to_dict()["value"]
    )
    return matched
