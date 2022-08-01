import numpy as np
from copy import copy


class AbbyyTools:
    def __init__(self, df_extract):
        self.df_extract = df_extract
        self.extracted_all_fields = list(sorted(set(self.df_extract.to_numpy().flatten())))

    def find_at_offset(
        self,
        search_string,
        offset_x,
        offset_y,
    ):
        found_values = self.find_all_at_offset(search_string, offset_x, offset_y)

        # Assuming at least one appearance is found
        found_value = found_values[0]

        return found_value

    def find_all_at_offset(
        self,
        search_strings,
        offset_x,
        offset_y,
    ):
        if isinstance(search_strings, str):
            search_strings = (search_strings,)
        found_values = []
        for search_string in search_strings:
            found_at = np.where(self.df_extract.applymap(lambda cell: search_string in cell).to_numpy())
            for i in range(len(found_at[0])):
                x = found_at[1][i]
                y = found_at[0][i]
                found_values.append(self.df_extract.iloc[y + offset_y, x + offset_x])
        return sorted(list(set(found_values)))

    def find_anywhere(self, search_string):
        return any([search_string in field for field in self.extracted_all_fields])

    def find_till_the_end(self, search_string, remove=False):
        found_at = [i for i, field in enumerate(self.extracted_all_fields) if search_string in field][0]
        found_inside_at = self.extracted_all_fields[found_at].find(search_string)
        found_value = self.extracted_all_fields[found_at][found_inside_at + len(search_string) :].strip()
        if remove:
            self.extracted_all_fields[found_at] = self.extracted_all_fields[found_at][:found_inside_at]
        return found_value

    def find_whole_word(self, search_string, remove=False):
        found_at = [i for i, field in enumerate(self.extracted_all_fields) if search_string in field][0]
        found_inside_at = self.extracted_all_fields[found_at].find(search_string)
        found_value = self.extracted_all_fields[found_at][found_inside_at + len(search_string) :].strip().split(" ")[0]
        found_value_inside_at = self.extracted_all_fields[found_at].find(found_value)
        found_end_value = found_value_inside_at + len(found_value)
        if remove:
            self.extracted_all_fields[found_at] = (
                self.extracted_all_fields[found_at][:found_inside_at]
                + self.extracted_all_fields[found_at][found_end_value:]
            )

        return found_value

    # TODO refactor to avoid copying
    def find_till_the_end_in_copy(self, search_string, extracted_copy, remove=False):
        found_at = [i for i, field in enumerate(extracted_copy) if search_string in field][0]
        found_inside_at = extracted_copy[found_at].find(search_string)
        found_value = extracted_copy[found_at][found_inside_at + len(search_string) :].strip()
        if remove:
            extracted_copy[found_at] = extracted_copy[found_at][:found_inside_at]
        return found_value

    # TODO refactor to avoid copying
    def find_between_keywords(self, before, after):
        # TODO refactor to avoid copying
        extracted_copy = copy(self.extracted_all_fields)
        _ = self.find_till_the_end_in_copy(after, extracted_copy, remove=True)
        return self.find_till_the_end_in_copy(before, extracted_copy, remove=False)
