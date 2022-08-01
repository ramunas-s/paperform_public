import json
import os
import sys

import cachetools
import requests
from google.cloud import documentai_v1beta2 as documentai, storage
from google.cloud.documentai_v1beta2 import Document
from google.cloud import secretmanager
from tika.tika import checkTikaServer

from labrep_recognizer.shared.pdf_parser_logging import get_logger
from labrep_recognizer.shared.recognizer_cache import RecognizerCache


log = get_logger(__name__)


class RecognizerInfrastructure:
    def __init__(
        self,
        project_id,
        google_application_credentials,
        ocr_abbyy_fr_engine_url,
        recognizer_cache,
    ):
        self._cache = recognizer_cache
        self.project_id = project_id
        self.ocr_abbyy_fr_engine_url = ocr_abbyy_fr_engine_url
        self.google_application_credentials = google_application_credentials
        self.storage_client = storage.Client.from_service_account_json(self.google_application_credentials)
        self.ocr_client = documentai.DocumentUnderstandingServiceClient.from_service_account_json(
            self.google_application_credentials
        )
        self.secret_manager_client = secretmanager.SecretManagerServiceClient.from_service_account_json(
            self.google_application_credentials
        )

    def ocr_google(self, input_uri):
        google_document_ai_json = self._ocr_google_to_json(input_uri, "_ocr_google_to_json")
        google_document_ai = Document.from_json(google_document_ai_json)
        return google_document_ai

    @cachetools.cachedmethod(lambda self: self._cache, key=RecognizerCache.pickled_hashkey)
    def _ocr_google_to_json(self, input_uri, function_name):
        # ## OCR uploaded document with google document AI
        gcs_source = documentai.types.GcsSource(uri=input_uri)
        # mime_type can be application/pdf, image/tiff,
        # and image/gif, or application/json
        input_config = documentai.types.InputConfig(gcs_source=gcs_source, mime_type="application/pdf")
        # Improve table parsing results by providing bounding boxes
        # specifying where the box appears in the document (optional)
        table_bound_hints = [
            documentai.types.TableBoundHint(
                page_number=1,
                bounding_box=documentai.types.BoundingPoly(
                    # Define a polygon around tables to detect
                    # Each vertice coordinate must be a number between 0 and 1
                    normalized_vertices=[
                        # Top left
                        documentai.types.geometry.NormalizedVertex(x=0, y=0),
                        # Top right
                        documentai.types.geometry.NormalizedVertex(x=1, y=0),
                        # Bottom right
                        documentai.types.geometry.NormalizedVertex(x=1, y=1),
                        # Bottom left
                        documentai.types.geometry.NormalizedVertex(x=0, y=1),
                    ]
                ),
            )
        ]
        # Setting enabled=True enables form extraction
        table_extraction_params = documentai.types.TableExtractionParams(
            enabled=True, table_bound_hints=table_bound_hints
        )
        # Location can be 'us' or 'eu'
        parent = "projects/{}/locations/eu".format(self.project_id)
        request = documentai.types.ProcessDocumentRequest(
            parent=parent,
            input_config=input_config,
            table_extraction_params=table_extraction_params,
        )
        google_document_ai = self.ocr_client.process_document(request=request)
        google_document_ai_json = Document.to_json(google_document_ai)

        return google_document_ai_json

    @cachetools.cachedmethod(lambda self: self._cache, key=RecognizerCache.pickled_hashkey)
    def ocr_abbyy_fr_engine(self, uploaded_uri):
        return self._ocr_abbyy_fr_engine(uploaded_uri, "_ocr_abbyy_fr_engine")

    def _ocr_abbyy_fr_engine(self, uploaded_uri, function_name):

        conversion_ok = False
        error_message = "#_undefined_error_#"

        input_files = [
            {
                "FILE_TYPE": "INPUT_GS_PDF_RAW_LAB_REPORT",
                "FILE_PATH": uploaded_uri,
            },
        ]

        languages = "English, Lithuanian, Mathematical"

        output_types = [
            "OUTPUT_GS_XLSX_OCRED_LAB_REPORT",
        ]

        url = self.ocr_abbyy_fr_engine_url
        data = {
            "input_files": json.dumps(input_files),
            "languages": languages,
            "output_types": json.dumps(output_types),
        }
        try:
            response = requests.post(
                url=url,
                data=data,
            )
            conversion_ok = True
            error_message = ""
        except (requests.exceptions.ConnectionError, requests.exceptions.MissingSchema) as e:
            conversion_ok = False
            error_message = f"Error from ocr_abbyy_fr_engine: {str(e)}, url: {self.ocr_abbyy_fr_engine_url}"
            log.error(error_message)
        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise

        if conversion_ok:
            # print(response.status_code, response.reason)
            response_json = response.json()
            # print(response_json)

            if response.status_code == 200:
                if "conversionStatus" in response_json:
                    if response_json["conversionStatus"] == "OK":
                        conversion_ok = True
                        error_message = ""
                    elif response_json["conversionStatus"] == "ERROR":
                        conversion_ok = False
                        error_message = (
                            f"Error from ocr_abbyy_fr_engine, url: {url}, data: {data}, {response_json['errorMessage']}"
                        )
                        log.error(error_message)
            else:
                conversion_ok = False
                error_message = f"Error from ocr_abbyy_fr_engine, url: {url}, data: {data}, status_code: {response.status_code}, {response.reason}, {response.text}"
                log.error(error_message)

        if conversion_ok:
            xlsx_files = [
                output_file["FILE_PATH"]
                for output_file in response_json["outputFiles"]
                if output_file["FILE_TYPE"] == "OUTPUT_GS_XLSX_OCRED_LAB_REPORT"
            ]
            assert len(xlsx_files) == 1
            xlsx_file_uri = xlsx_files[0]

            ocred_file = self.download_file_from_google_bucket(xlsx_file_uri, "data/ocred")

            return (
                True,
                error_message,
                ocred_file,
            )

        else:
            return (
                False,
                error_message,
                None,
            )

    def upload_pdf_to_google_bucket(self, raw_pdf, blob_name):
        original_input_uri = self._upload_pdf_to_google_bucket(raw_pdf, blob_name, "_upload_pdf_to_google_bucket")
        return original_input_uri

    @cachetools.cachedmethod(lambda self: self._cache, key=RecognizerCache.pickled_hashkey)
    def _upload_pdf_to_google_bucket(self, raw_pdf, blob_name, function_name):
        # ### Upload PDF to google cloud bucket
        bucket_name = os.environ.get("recognizer_bucket_name")
        print(list(self.storage_client.list_buckets()))
        bucket = self.storage_client.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(raw_pdf)
        print(blob.public_url)
        input_uri = "gs://" + bucket_name + "/" + blob_name
        print(input_uri)
        return input_uri

    def delete_file_from_google_bucket(self, uri):
        bucket_name = os.environ.get("recognizer_bucket_name")
        blob_name = self.get_blob_name_from_uri(uri, bucket_name)
        bucket = self.storage_client.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.delete()
        return None

    def download_file_from_google_bucket(self, uri, destination_dir):
        return self._download_file_from_google_bucket(uri, destination_dir, "_download_file_from_google_bucket")

    @cachetools.cachedmethod(lambda self: self._cache, key=RecognizerCache.pickled_hashkey)
    def _download_file_from_google_bucket(self, uri, destination_dir, function_name):
        bucket_name = os.environ.get("recognizer_bucket_name")
        blob_name = self.get_blob_name_from_uri(uri, bucket_name)
        print(list(self.storage_client.list_buckets()))
        bucket = self.storage_client.get_bucket(bucket_name)
        blob = bucket.get_blob(blob_name)

        downloaded_file_path = os.path.join(destination_dir, os.path.split(blob_name)[1])

        blob.download_to_filename(downloaded_file_path)

        return downloaded_file_path

    def get_blob_name_from_uri(self, uri, bucket_name):
        full_input_file_path = ""
        found_bucket_name = False
        for element in uri.split("/"):
            if found_bucket_name:
                if full_input_file_path == "":
                    full_input_file_path = element
                else:
                    full_input_file_path = full_input_file_path + "/" + element
            if element == bucket_name:
                found_bucket_name = True
        blob_name = full_input_file_path
        return blob_name

    def warm_up(self):
        tika_server = checkTikaServer()
        log.info(f"Tika server is runnign at: {tika_server}")
        return None
