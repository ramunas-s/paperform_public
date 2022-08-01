from labrep_recognizer.shared.pdf_parser_logging import get_logger
import threading
from enum import Enum

import pandas as pd
from tika import parser

from labrep_recognizer.labrep_types.labrep_interface import laboratory_types
from labrep_recognizer.recognition_tools.abbyy_tools import AbbyyTools
from labrep_recognizer.recognition_tools.google_tools import GoogleTools
from openpyxl import load_workbook

log = get_logger(__name__)


class IOFileType(Enum):
    INPUT_GS_PDF_RAW_LAB_REPORT = 101
    INPUT_LOC_PDF_RAW_LAB_REPORT = 111
    OUTPUT_GS_XLSX_OCRED_LAB_REPORT = 201


class LabrepRecognizeRequest:
    def __init__(self, recognizer_infrastructure, input_files, parallel_execution):
        self.recognizer_infrastructure = recognizer_infrastructure
        self.parallel_execution = parallel_execution

        self.abbyy_tools = None
        self.google_tools = None

        # Input
        self.input_files = input_files

        # Extracted common intermediate data
        self.input_pdf_file_uri = None
        self.ocred_file = None
        self.google_ocred_document = None
        self.df_abbyy_extracted = None
        self.tika_extracted_text = None

        # Extracted results
        self.df_header = None
        self.df_details = None

    def _get_uploaded_pdf_uri(self):
        # Assume there is only one input file; type is PDF and location on Google Cloud Storage
        assert len(self.input_files) == 1
        assert self.input_files[0]["FILE_TYPE"] == IOFileType.INPUT_GS_PDF_RAW_LAB_REPORT
        return self.input_files[0]["FILE_PATH"]

    def run_google(self):
        log.info("Starring Google OCR...")
        self.google_ocred_document = self.recognizer_infrastructure.ocr_google(self.input_pdf_file_uri)
        self.google_tools = GoogleTools(self.google_ocred_document)
        log.info("Finished Google OCR.")
        return None

    def run_abbyy(self):
        log.info("Starring ABBYY OCR...")
        (
            self.abbyy_conversion_ok,
            self.abbyy_error_message,
            self.ocred_file,
        ) = self.recognizer_infrastructure.ocr_abbyy_fr_engine(self.input_pdf_file_uri)
        if self.abbyy_conversion_ok:
            log.info("Finished ABBYY OCR.")
            log.info("Starting DF extraction...")
            self.df_abbyy_extracted = self.read_fix_excel(self.ocred_file, "Sheet1")
            self.df_abbyy_extracted = self.df_abbyy_extracted.fillna("").astype(str)
            self.abbyy_tools = AbbyyTools(self.df_abbyy_extracted)
            log.info("Finished DF extraction.")
        return None

    def run_local_processing(self):
        log.info("Starting local processing...")
        log.info("Downloading local PDF copy...")
        local_pdf_copy = self.recognizer_infrastructure.download_file_from_google_bucket(
            self.input_pdf_file_uri, "data/local_input_copy"
        )
        log.info("Starting Tika parser...")
        self.tika_extracted_text = str(parser.from_file(local_pdf_copy)["content"])
        log.info("Finished Tika parser...")
        log.info("Finished local processing.")

    def recognize(self):

        recognition_status_ok = False
        recognition_error = ""

        ###########################################################################
        # Extract common data from PDF                                            #
        ###########################################################################

        self.input_pdf_file_uri = self._get_uploaded_pdf_uri()
        log.info(f"input_pdf_file_uri: {self.input_pdf_file_uri}")

        if self.parallel_execution:
            # Run in parallel
            thread_abbyy = threading.Thread(target=self.run_abbyy)
            thread_google = threading.Thread(target=self.run_google)
            thread_local = threading.Thread(target=self.run_local_processing)
            thread_abbyy.start()
            thread_google.start()
            thread_local.start()
            thread_google.join()
            thread_abbyy.join()
            thread_local.join()
        else:
            # Run 1 by 1
            self.run_abbyy()
            self.run_google()
            self.run_local_processing()

        # TODO add status check from Google as well
        if self.abbyy_conversion_ok:

            ###########################################################################
            # Identify LabRep type                                                    #
            ###########################################################################

            log.info("Starting report type identification...")
            laboratory = self.identify()
            log.info(laboratory)
            log.info("Finished report type identification.")

            df_header = None
            df_details = None

            ###########################################################################
            # Parse common data with selected LabRep parser                           #
            ###########################################################################

            log.info("Starting recognition...")
            if sum(laboratory.values()) == 1:

                for laboratory_type in laboratory_types:
                    if laboratory[laboratory_type[2]]:
                        mod = __import__(
                            "labrep_recognizer.labrep_types." + laboratory_type[0], fromlist=[laboratory_type[1]]
                        )
                        labrep = getattr(mod, laboratory_type[1])

                        # Disable debug
                        self.google_tools.debug_draw_image = False

                        parsing_function = labrep(
                            self.df_abbyy_extracted,
                            self.abbyy_tools,
                            self.google_ocred_document,
                            self.google_tools,
                            self.tika_extracted_text,
                        ).parse

                        try:
                            header, df_details = parsing_function()
                            header["labrep_type"] = laboratory_type[0]
                            header["laboratory_id"] = laboratory_type[3]
                            df_header = pd.DataFrame({k: [v] for k, v in header.items()})
                            recognition_status_ok = True

                        except AssertionError:
                            recognition_status_ok = False
            else:
                recognition_status_ok = False
                recognition_error += f"Can't identify LabRep type: {laboratory} "

            log.info("Finished recognition.")

            self.df_header = df_header
            self.df_details = df_details

        else:
            if not self.abbyy_conversion_ok:
                recognition_status_ok = False
                recognition_error += f"{self.abbyy_error_message} "

        return recognition_status_ok, recognition_error

    def identify(self):
        laboratory = dict()
        for laboratory_type in laboratory_types:
            mod = __import__("labrep_recognizer.labrep_types." + laboratory_type[0], fromlist=[laboratory_type[1]])
            LabrepClass = getattr(mod, laboratory_type[1])

            # Disable debug
            self.google_tools.debug_draw_image = False

            labrep = LabrepClass(
                self.df_abbyy_extracted,
                self.abbyy_tools,
                self.google_ocred_document,
                self.google_tools,
                self.tika_extracted_text,
            )
            laboratory[laboratory_type[2]] = labrep.identify()
        return laboratory

    def read_fix_excel(self, file_name, sheet_name):
        wb = load_workbook(file_name, data_only=True)
        sh = wb[sheet_name]
        for row in sh:
            for cell in row:
                # print(f"{cell.number_format}: {cell.value}")
                if cell.number_format == "#,##0":
                    # print(f"Updating cell {cell}...")
                    value = cell.value
                    cell.number_format = "General"
                    cell.value = f"{value:,}"
        df = pd.DataFrame(sh.values)
        return df
