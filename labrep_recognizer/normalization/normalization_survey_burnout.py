import pandas as pd

from labrep_recognizer.normalization.normalization_standard import (
    select_single_normalized,
    normalize_results_to_standard,
)


def normalize_survey_burnout(df_header, df_details):
    df_normalized_standard = normalize_results_to_standard(df_header, df_details)

    important_bkt_columns = [
        "NE%",
        "WBC",
        "MO%",
        "LY%",
        "RBC",
        "EO%",
    ]

    df_normalized_survey_burnout = df_normalized_standard[df_normalized_standard["code"].isin(important_bkt_columns)]

    df_normalized_survey_burnout = select_single_normalized(df_normalized_survey_burnout, "code")

    df_matched = pd.DataFrame({"code": important_bkt_columns})
    df_matched["values"] = ""
    df_matched = df_matched.merge(df_normalized_survey_burnout, on="code", how="left")[["code", "value"]].sort_values(
        "code"
    )

    return df_matched
