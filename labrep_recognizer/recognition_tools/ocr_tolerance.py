import pandas as pd
import math

from labrep_recognizer.shared.utils import find_all_strings
import Levenshtein


def find_partial(corpus, part_1, wildcards, part_2):
    #     print(f"searching for: <{part_1}{'*' * wildcards}{part_2}>")
    found_1_all = find_all_strings(part_1, corpus)
    found_whole_phrases = []
    for found_1 in found_1_all:
        part_2_candidate = corpus[found_1 + len(part_1) + wildcards : found_1 + len(part_1) + wildcards + len(part_2)]
        if part_2_candidate == part_2:
            found_whole_phrase = corpus[found_1 : found_1 + len(part_1) + wildcards + len(part_2)]
            found_whole_phrases.append(found_whole_phrase)
    found_whole_phrases = list(sorted(set(found_whole_phrases)))
    #     print(f"found: {found_whole_phrases}")
    return found_whole_phrases


def find_partial_scan(corpus, search_string, range_from, range_to, part_2_drop, wildcards):
    found_partial_values = []
    for i in range(range_from, len(search_string) + range_to):
        part_1 = search_string[:i]
        part_2 = search_string[i + part_2_drop :]
        found_partial_values += find_partial(corpus, part_1, wildcards, part_2)
    return found_partial_values


def find_with_1_2_character_tolerance(corpus, search_string):
    if search_string in corpus:
        return [search_string]
    else:
        found_values = []
        # missing character
        # for i in range(1, len(search_string) - 0):
        #     part_1 = search_string[: i]
        #     part_2 = search_string[i:]
        #     found_values += find_partial(corpus, part_1, 1, part_2)
        found_values += find_partial_scan(corpus, search_string, 1, 0, 0, 1)

        # extra character
        # for i in range(0, len(search_string) - 0):
        #     part_1 = search_string[: i]
        #     part_2 = search_string[i + 1:]
        #     found_values += find_partial(corpus, part_1, 0, part_2)
        found_values += find_partial_scan(corpus, search_string, 0, 0, 1, 0)

        # wrong character 1 to 1
        # for i in range(0, len(search_string) - 0):
        #     part_1 = search_string[: i]
        #     part_2 = search_string[i + 1:]
        #     found_values += find_partial(corpus, part_1, 1, part_2)
        found_values += find_partial_scan(corpus, search_string, 0, 0, 1, 1)

        # wrong character 1 to 2
        # for i in range(0, len(search_string) - 0):
        #     part_1 = search_string[: i]
        #     part_2 = search_string[i + 1:]
        #     found_values += find_partial(corpus, part_1, 2, part_2)
        found_values += find_partial_scan(corpus, search_string, 0, 0, 1, 2)

        # wrong character 2 to 1
        # for i in range(0, len(search_string) - 1):
        #     part_1 = search_string[: i]
        #     part_2 = search_string[i + 2:]
        #     found_values += find_partial(corpus, part_1, 1, part_2)
        found_values += find_partial_scan(corpus, search_string, 0, -1, 2, 1)

        found_values = list(
            sorted(
                set(found_values),
                key=(
                    lambda x: (
                        -len(x),
                        x,
                    )
                ),
            )
        )
        return found_values


# TODO Generalize to correction with multiple corpus


# TODO Return not only the first appearance but all possible values


def correct_ocr_error_by_one_corpus(corpus_1, value_to_correct):
    if value_to_correct not in corpus_1:
        # print(f"  --<{value_to_correct}> not found in corpus, will perform search with tolerance:")
        found_in_corpus_1 = find_with_1_2_character_tolerance(corpus_1, value_to_correct)
        # print(f"  --Found in corpus_1 : {found_in_corpus_1}")
        if len(found_in_corpus_1) > 0:
            return found_in_corpus_1[0]
    return value_to_correct


# TODO Return not only the first appearance but all possible values with probabilities


def correct_ocr_error_by_two_corpus(corpus_1, corpus_2, value_to_correct):
    if value_to_correct not in corpus_1:
        #         print("  --Not found in corpus, will perform search with tolerance:")
        found_in_corpus_1 = find_with_1_2_character_tolerance(corpus_1, value_to_correct)
        found_in_corpus_2 = find_with_1_2_character_tolerance(corpus_2, value_to_correct)
        #         print(f"  --Found in  corpus_1: {found_in_corpus_1}")
        #         print(f"  --Found in corpus_2 : {found_in_corpus_2}")
        if (
            (len(found_in_corpus_1) > 0)
            and (len(found_in_corpus_2) > 0)
            and (found_in_corpus_1[0] == found_in_corpus_2[0])
        ):
            return found_in_corpus_1[0]
    return value_to_correct


def find_in_exact(corpus_exact, value_to_correct, tolerance):
    found_exact = []
    for match_exact in corpus_exact:
        if Levenshtein.distance(value_to_correct, match_exact) <= tolerance:
            found_exact.append(match_exact)
    return found_exact


def correct_ocr_error_by_flex_corpuses(corpuses_flat, corpuses_exact, value_to_correct):
    if len(value_to_correct) == 0:
        return value_to_correct
    dfs_found = []
    for i, corpus_flat in enumerate(corpuses_flat):
        found_flat = find_with_1_2_character_tolerance(corpus_flat, value_to_correct)
        df_found = pd.DataFrame({"match": found_flat})
        df_found["category"] = f"corpus_flat_{i}"
        dfs_found.append(df_found)
    for i, corpus_exact in enumerate(corpuses_exact):
        found_exact = find_in_exact(corpus_exact, value_to_correct, tolerance=len(value_to_correct) // 3)
        df_found = pd.DataFrame({"match": found_exact})
        df_found["category"] = f"corpus_exact_{i}"
        dfs_found.append(df_found)
    dfs_found = pd.concat(dfs_found)
    if len(dfs_found):
        df_found_grouped = dfs_found.groupby("match").size().to_frame("count").reset_index(drop=False)
        df_found_grouped["levenshtein_distance"] = df_found_grouped.match.apply(
            lambda x: Levenshtein.distance(x, value_to_correct)
        )
        # print(f"value_to_correct {value_to_correct}")
        # fmt: off
        df_found_grouped["relevance"] = df_found_grouped.apply(lambda row: (
            (1 - row.levenshtein_distance / (len(value_to_correct))) *
            (1 / (1 + math.exp(-row["count"]))) *
            (1 / (1 + math.exp(-len(row.match))))
        ), axis=1)
        # fmt: on
        df_found_grouped = df_found_grouped.sort_values("relevance", ascending=False).reset_index(drop=True)

        # df_found_grouped["match_mark"] = "_" + df_found_grouped["match"] + "_"
        # print(df_found_grouped)

        if len(df_found_grouped):
            value_corrected = df_found_grouped.iloc[0]["match"]
        else:
            value_corrected = value_to_correct
    else:
        value_corrected = value_to_correct
    return value_corrected


def main_test():
    corpus_flat = [
        "mano batai buvo du, vienas dingo, nerandu",
        "dvi rankytės ieško bato, dvi akytės juos pamato",
        "aš su vienu batuku niekur eiti negaliu",
    ]
    corpus_exact = [
        [
            "batas",
            "bato",
            "batui",
            "batai",
        ],
        [
            "Batas",
            "Bato",
            "Batui",
            "Batai",
        ],
    ]

    corrected_value = correct_ocr_error_by_flex_corpuses(corpus_flat, corpus_exact, "batas")
    print(corrected_value)

    pass


if __name__ == "__main__":
    main_test()
