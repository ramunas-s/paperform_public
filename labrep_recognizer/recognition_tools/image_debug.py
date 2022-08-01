import PIL
from PIL import ImageDraw
from PIL import ImageFont
import traceback

from labrep_recognizer.shared.utils import make_dirs


class ImageDebug:
    def __init__(self):
        self.debug_draw_image = None
        self.zoom_factor = 2000.0
        self.draw = None
        self.im = None

    def draw_page_img(self, page_index):
        if self.debug_draw_image:
            xy_zoom_ratio = (
                self.google_ocred_document.pages[page_index].dimension.width
                / self.google_ocred_document.pages[page_index].dimension.height
            )
            image_size = (int(self.zoom_factor * xy_zoom_ratio), int(self.zoom_factor))
            print(f"Initiating image size: {image_size}")
            self.im = PIL.Image.new(
                mode="RGB", size=image_size, color=(238, 232, 213)
            )
            self.draw = PIL.ImageDraw.Draw(self.im)
            for token in self.google_ocred_document.pages[page_index].tokens:
                self.draw_token_polygon_img(page_index, token, (0, 128, 128))
                fnt = PIL.ImageFont.truetype("./fonts/font_1.ttf", int(0.009 * self.zoom_factor))
                text_coordinate_x = token.layout.bounding_poly.normalized_vertices[0].x
                text_coordinate_y = (
                    token.layout.bounding_poly.normalized_vertices[0].y
                    + token.layout.bounding_poly.normalized_vertices[3].y
                ) / 2
                self.draw.text(
                    (
                        (text_coordinate_x * xy_zoom_ratio + 0.001) * self.zoom_factor,
                        (text_coordinate_y - 0.0038) * self.zoom_factor,
                    ),
                    self.google_ocred_document.text[
                        token.layout.text_anchor.text_segments[0]
                        .start_index : token.layout.text_anchor.text_segments[0]
                        .end_index
                    ],
                    font=fnt,
                    fill=(0, 0, 0),
                )
        return None

    def draw_token_boundary_img(self, page, token, colour):
        self.draw_token_polygon_img(page, token, colour, fill=None)
        return None

    def draw_token_polygon_img(self, page, token, colour, fill=(255, 255, 255)):
        if self.debug_draw_image:
            xy_zoom_ratio = (
                self.google_ocred_document.pages[page].dimension.width
                / self.google_ocred_document.pages[page].dimension.height
            )
            poly_points = [
                (
                    vertice.x * self.zoom_factor * xy_zoom_ratio,
                    vertice.y * self.zoom_factor,
                )
                for vertice in token.layout.bounding_poly.normalized_vertices
            ]
            self.draw.polygon(poly_points, outline=colour, fill=fill)
        return None

    def draw_token_rectangle_img_token(self, page, token, colour):
        if self.debug_draw_image:
            box = [
                (
                    vertice.x,
                    vertice.y,
                )
                for vertice in token.layout.bounding_poly.normalized_vertices
            ]
            self.draw_token_rectangle_img_box(page, box, colour)
        return None

    def draw_token_rectangle_img_box(self, page, box, colour):
        if self.debug_draw_image:
            xy_zoom_ratio = (
                self.google_ocred_document.pages[page].dimension.width
                / self.google_ocred_document.pages[page].dimension.height
            )
            box_scaled = list(
                map(lambda point: (point[0] * self.zoom_factor * xy_zoom_ratio, point[1] * self.zoom_factor), box)
            )
            self.draw.polygon(box_scaled, outline=colour, fill=None)
        return None

    def draw_token_strikethrough_img(self, page, scan_start_x, scan_start_y, boundary_x, colour):
        if self.debug_draw_image:
            xy_zoom_ratio = (
                self.google_ocred_document.pages[page].dimension.width
                / self.google_ocred_document.pages[page].dimension.height
            )

            self.draw.polygon(
                [
                    (scan_start_x * self.zoom_factor * xy_zoom_ratio, scan_start_y * self.zoom_factor),
                    (boundary_x * self.zoom_factor * xy_zoom_ratio, scan_start_y * self.zoom_factor),
                ],
                outline=colour,
            )
        return None

    def image_save(self, image_name=None):

        if self.debug_draw_image:
            if image_name is None:
                try:
                    traceback_list = list(traceback.extract_stack())
                    calling_interface_index = [
                        i
                        for i, traceback_element in enumerate(traceback_list)
                        if (traceback_element.filename.split("/")[-1] == "labrep_interface.py")
                        and (traceback_element.name.split("/")[-1] == "parse")
                    ]

                    calling_function_element = traceback_list[calling_interface_index[0] + 1]
                    image_name = calling_function_element.filename.split("/")[-1].split(".")[0] + "-" + calling_function_element.name

                except:
                    image_name = "image"
            file_name = f"./logs/images/{image_name}.png"
            make_dirs(file_name)
            self.im.save(file_name)
        return None


def debug_img(func):
    def wrap(self, *args, **kwargs):

        # Before
        page_no = 0
        self.google_tools.draw_page_img(page_no)

        result = func(self, *args, **kwargs)

        # After
        self.google_tools.image_save(func.__module__.split(".")[-1] + "-" + func.__name__)

        return result

    return wrap
