import PIL
from shapely.geometry import Point, Polygon

from labrep_recognizer.recognition_tools.image_debug import ImageDebug
from labrep_recognizer.shared.utils import find_all_strings


class GoogleTools(ImageDebug):
    def __init__(self, google_ocred_document):
        super().__init__()
        self.google_ocred_document = google_ocred_document

    def extract_text_from_rectangle_to_left_between_keys(
        self,
        page_no,
        labels_key_current_line,
        labels_key_below_line,
        right_boundary,
        line_separator,
    ):

        for label_group in labels_key_current_line:
            tokens_key_current_line = self.gd_find_by_keywords(page_no, label_group)
            if tokens_key_current_line:
                break

        for label_group in labels_key_below_line:
            tokens_key_below_line = self.gd_find_by_keywords(page_no, label_group)
            if tokens_key_below_line:
                break

        x_0 = tokens_key_current_line[0].layout.bounding_poly.normalized_vertices[1].x - 0.001
        x_1 = right_boundary
        y_0 = tokens_key_current_line[0].layout.bounding_poly.normalized_vertices[1].y - 0.01
        y_1 = tokens_key_below_line[0].layout.bounding_poly.normalized_vertices[1].y
        found_tokens = self.gd_find_tokens_in_box(
            0,
            [
                (x_0, y_0),
                (x_1, y_0),
                (x_1, y_1),
                (x_0, y_1),
            ],
        )
        concatenated_text = self.concatenate_tokens_box(found_tokens, line_separator=line_separator)
        return concatenated_text

    def gd_find_by_keywords(
        self,
        page_index,
        search_keywords,
    ):
        tokens_current = self.gd_find_token_by_text_from_token_list(
            self.google_ocred_document.pages[page_index].tokens,
            search_keywords[0],
        )

        # TODO draw debug info here for tokens_current
        # self.image_save()

        for i in range(1, len(search_keywords)):
            tokens_to_the_right = []
            for token_current in tokens_current:
                tokens_to_the_right += self.gd_find_token_to_right(
                    page_index, token_current, boundary_x=0.03, boundary_relative=True
                )
            tokens_to_the_right_matching = self.gd_find_token_by_text_from_token_list(
                tokens_to_the_right, search_keywords[i]
            )
            tokens_current = tokens_to_the_right_matching
        return tokens_current

    def concatenate_tokens_box(self, tokens, line_separator=" "):
        lines = self.organize_tokens_box(tokens)

        return line_separator.join([" ".join([self.get_token_text(token).strip() for token in line]) for line in lines])

    def organize_tokens_box(self, tokens):
        lines = []
        tokens = sorted(
            tokens, key=(lambda token_internal: token_internal.layout.bounding_poly.normalized_vertices[0].x)
        )
        token_is_available = [True] * len(tokens)
        while any(token_is_available):
            available_range = [i for i, x in enumerate(token_is_available) if x]
            token_from = tokens[available_range[0]]
            line_tokens = []
            lines.append(line_tokens)
            for i in available_range:
                token = tokens[i]
                if self.is_same_row(token_from, token):
                    lines[-1].append(token)
                    token_is_available[i] = False
        lines = sorted(lines, key=(lambda line: line[0].layout.bounding_poly.normalized_vertices[0].y))
        return lines

    def is_same_row(self, token_1, token_2):
        tolerance = 0.25

        tokens = sorted([token_1, token_2], key=self.get_token_height)

        y_small_0 = tokens[0].layout.bounding_poly.normalized_vertices[0].y
        y_small_1 = tokens[0].layout.bounding_poly.normalized_vertices[3].y

        y_large_0 = tokens[1].layout.bounding_poly.normalized_vertices[0].y
        y_large_1 = tokens[1].layout.bounding_poly.normalized_vertices[3].y
        y_large_sorted = sorted([y_large_0, y_large_1])

        y_small_fit_0 = y_small_0 + ((y_small_1 - y_small_0) * tolerance)
        y_small_fit_1 = y_small_1 - ((y_small_1 - y_small_0) * tolerance)

        return (y_large_sorted[0] < y_small_fit_0 < y_large_sorted[1]) and (
            y_large_sorted[0] < y_small_fit_1 < y_large_sorted[1]
        )

    def get_token_height(self, token):
        token_height = (
            Point(self.get_point_from_token(token, 0)).distance(Point(self.get_point_from_token(token, 3)))
            + Point(self.get_point_from_token(token, 1)).distance(Point(self.get_point_from_token(token, 2)))
        ) / 2.0
        return token_height

    def get_token_length(self, token):
        token_length = (
            Point(self.get_point_from_token(token, 0)).distance(Point(self.get_point_from_token(token, 1)))
            + Point(self.get_point_from_token(token, 2)).distance(Point(self.get_point_from_token(token, 3)))
        ) / 2.0
        return token_length

    def get_point_from_token(self, token, index):
        point = (
            token.layout.bounding_poly.normalized_vertices[index].x,
            token.layout.bounding_poly.normalized_vertices[index].y,
        )
        return point

    def get_token_text(self, token):
        return self.google_ocred_document.text[
            token.layout.text_anchor.text_segments[0].start_index : token.layout.text_anchor.text_segments[0].end_index
        ]

    def gd_find_token_by_text_from_token_list(self, tokens, search_string):
        found_tokens = [token for token in tokens if search_string in self.get_token_text(token)]

        if self.debug_draw_image:
            # TODO get an access to real page index
            page_index = 0
            for token in found_tokens:
                self.draw_token_rectangle_img_token(page_index, token, PIL.ImageColor.getrgb("red"))

        return found_tokens

    def gd_find_token_to_right(
        self,
        page_index,
        search_from_token,
        boundary_x=1.0,
        boundary_relative=False,
        offset_y=0.0,
    ):
        found_tokens = []
        page = self.google_ocred_document.pages[page_index]

        scan_start_x = search_from_token.layout.bounding_poly.normalized_vertices[1].x - 0.001
        scan_start_y = (
            search_from_token.layout.bounding_poly.normalized_vertices[1].y
            + search_from_token.layout.bounding_poly.normalized_vertices[2].y
        ) / 2 + offset_y
        if boundary_relative:
            boundary_x += search_from_token.layout.bounding_poly.normalized_vertices[1].x

        # Debug
        self.draw_token_strikethrough_img(
            page_index,
            scan_start_x,
            scan_start_y,
            boundary_x,
            PIL.ImageColor.getrgb("blue"),
        )

        for token_to_the_right in page.tokens:
            if (
                (token_to_the_right.layout.bounding_poly.normalized_vertices[0].x > scan_start_x)
                and (token_to_the_right.layout.bounding_poly.normalized_vertices[0].x < boundary_x)
                and (token_to_the_right.layout.bounding_poly.normalized_vertices[0].y < scan_start_y)
                and (token_to_the_right.layout.bounding_poly.normalized_vertices[3].y > scan_start_y)
            ):
                found_tokens.append(token_to_the_right)
        return found_tokens

    def gd_find_tokens_in_box(
        self,
        page_index,
        box,
    ):
        found_tokens = []
        page = self.google_ocred_document.pages[page_index]

        # Debug
        self.draw_token_rectangle_img_box(page_index, box, PIL.ImageColor.getrgb("blue"))

        polygon = Polygon(box)
        for token in page.tokens:
            if all(
                [
                    polygon.contains(Point(normalized_vertice.x, normalized_vertice.y))
                    for normalized_vertice in token.layout.bounding_poly.normalized_vertices
                ]
            ):
                found_tokens.append(token)
                # Debug
                self.draw_token_boundary_img(page_index, token, PIL.ImageColor.getrgb("brown"))

        return found_tokens

    def gd_get_text_to_right_from_keywords(
        self,
        page_index,
        search_keywords,
        boundary_x=1.0,
        boundary_relative=False,
        offset_y=0,
        line_separator=" ",
    ):
        token_from = self.gd_find_by_keywords(page_index, search_keywords)
        assert len(token_from) > 0
        found_tokens = self.gd_find_token_to_right(page_index, token_from[0], boundary_x, boundary_relative, offset_y)
        return self.concatenate_tokens_box(found_tokens, line_separator)

    def gd_get_text_to_right_from_keywords_all_pages(
        self,
        search_keywords,
        boundary_x=1.0,
        boundary_relative=False,
        offset_y=0,
        line_separator=" ",
    ):
        for page_index in range(len(self.google_ocred_document.pages)):
            token_from = self.gd_find_by_keywords(page_index, search_keywords)
            if len(token_from) > 0:
                break
        assert len(token_from) > 0
        found_tokens = self.gd_find_token_to_right(page_index, token_from[0], boundary_x, boundary_relative, offset_y)
        return self.concatenate_tokens_box(found_tokens, line_separator)

    def gd_get_text_to_right_from_keywords_options(
        self,
        page_index,
        search_keywords,
        boundary_x=1.0,
        boundary_relative=False,
        offset_y=0,
        line_separator=" ",
    ):
        for label_group in search_keywords:
            try:

                found_tokens = self.gd_get_text_to_right_from_keywords(
                    page_index,
                    label_group,
                    boundary_x,
                    boundary_relative,
                    offset_y,
                    line_separator,
                )
                return found_tokens
            except AssertionError:
                pass
        # Did not exit on any sucessfull combination, so crashing
        assert False

    def gd_find_by_text(self, page_index, search_string):
        found_at_start = list(find_all_strings(search_string, self.google_ocred_document.text))
        found_at_end = list(map(lambda x: x + len(search_string), found_at_start))
        found_at = list(zip(found_at_start, found_at_end))
        found_tokens = []
        page = self.google_ocred_document.pages[page_index]
        for token in page.tokens:
            for serch_range in found_at:
                assert len(token.layout.text_anchor.text_segments) == 1
                if (token.layout.text_anchor.text_segments[0].start_index <= serch_range[0]) and (
                    token.layout.text_anchor.text_segments[0].end_index >= serch_range[1]
                ):
                    found_tokens.append(token)
        return found_tokens
