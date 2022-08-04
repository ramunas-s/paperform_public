import pandas as pd


def select_single_normalized(df_normalized_revolab, id_column):
    df_normalized_revolab = df_normalized_revolab.dropna(subset=[id_column])
    df_normalized_revolab = df_normalized_revolab.dropna(subset=["value"])
    df_normalized_revolab["multiplier"] = pd.to_numeric(df_normalized_revolab["multiplier"], errors="coerce")
    df_normalized_revolab["priority"] = pd.to_numeric(df_normalized_revolab["priority"], errors="coerce")
    df_normalized_revolab["value"] = df_normalized_revolab.apply(
        lambda row: row["value"] * row["multiplier"]
        if str(row["units_conversion"]).lower() == "true"
        else row["value"],
        axis=1,
        result_type="reduce",
    )
    df_normalized_revolab["rank"] = (
        df_normalized_revolab.sort_values(
            [
                id_column,
                "priority",
                # below should not matter, but just in case there are similar mappings, should keep the stable output
                "test_type",
                "test_name",
                "units",
                "value",
            ]
        )
        .groupby([id_column])["priority"]
        .rank(method="first", ascending=True)
    )
    df_normalized_revolab = df_normalized_revolab[df_normalized_revolab["rank"] == 1]
    return df_normalized_revolab


def normalize_number(s):
    s = s.replace(",", ".")
    s = s.replace("(Teigiamas)", "")
    s = s.replace("(Neigiamas)", "")
    s = s.replace("*", "")
    s = s.strip()
    if (len(s) > 0) and (s[0] == "<"):
        normalized_number = 0
    else:
        normalized_number = pd.to_numeric(s, errors="coerce")
    return normalized_number


def normalize_results_to_standard(df_header, df_details):
    # TODO move to parameters, load once
    df_mapping_standard = pd.read_csv(
        "./data/mapping/pdf_to_standard_mapping.csv",
        dtype="str",
        keep_default_na=False,
    ).drop_duplicates(subset=["test_type", "test_name", "units"])
    df_normalized_standard = df_details.merge(df_mapping_standard, on=["test_type", "test_name", "units"], how="left")
    df_normalized_standard["value"] = df_normalized_standard["value"].apply(normalize_number)
    return df_normalized_standard
