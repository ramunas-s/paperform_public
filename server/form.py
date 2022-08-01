import pandas as pd

from labrep_recognizer.shared.pdf_parser_logging import get_logger

import datetime
import json
import os

import pikepdf

from flask import Flask, render_template, request, send_from_directory

from labrep_recognizer.normalization.normalization_revolab import normalize_result_to_revolab
from labrep_recognizer.pipeline import process_single_pdf_in_gs, initialize_infrastructure
from labrep_recognizer.shared.utils import make_dirs, file_to_sha256

log = get_logger(__name__)
app = Flask(__name__)


@app.route("/")
def hello():
    return "<h1 style='color:blue'>Hello There!</h1>"


@app.route("/form")
def form():
    return render_template("form.html")


@app.route("/images/<path:path>")
def send_js(path):
    return send_from_directory("./images", path)


# @app.route("/upload", methods=["POST", "GET"])
# def upload():
#     if request.method == "POST":
#         print(f"Post from {request.remote_addr}")
#         f = request.files["File"]
#         f.save("./server/images/" + f.filename)
#
#         test_interpretation = pdf_to_interpretation("./server/images/" + f.filename)
#
#         print(test_interpretation)
#
#         return f'Interpretacija: {test_interpretation} <img src="{"/images/" + f.filename}" alt="My Image">'


@app.route("/recognize", methods=["POST"])
def recognize():
    import uuid

    date_time_utc = datetime.datetime.utcnow().isoformat(timespec="microseconds")
    uuid_srt = str(uuid.uuid4().hex)

    request_json = request.json

    print(f"Recognize API post from: {request.remote_addr}, json: {json.dumps(request_json, indent=4)}")

    files = request_json["files"]

    assert len(files) == 1

    file = files[0]

    bucket_name = os.environ.get("recognizer_bucket_name")
    uploaded_file_uri = f"gs://{bucket_name}/{file['hashedName']}"
    recognizer_infrastructure = initialize_infrastructure()

    # Password removal
    password_removal = False
    uploaded_file_password_removed_uri = ""
    if "passwordSecret" in file and file["passwordSecret"] is not None and file["passwordSecret"] != "":
        password_removal = True
        password_secret = file["passwordSecret"]
        log.info(f"Got request with password_secret: {password_secret}")
        uploaded_file_password_removed_uri = remove_pdf_password(
            recognizer_infrastructure=recognizer_infrastructure,
            uploaded_file_uri=uploaded_file_uri,
            password_secret=password_secret,
        )
        uploaded_file_uri = uploaded_file_password_removed_uri
        log.info(f"Password removal successful, new uri: {uploaded_file_uri}")

    recognition_ok, recognition_error, df_header, df_details = process_single_pdf_in_gs(
        uploaded_file_uri, recognizer_infrastructure
    )

    if password_removal:
        log.info(f"Cleaning up password removed temp file: {uploaded_file_password_removed_uri}")
        recognizer_infrastructure.delete_file_from_google_bucket(uploaded_file_password_removed_uri)

    if recognition_ok:
        print(df_header.T)
        print(df_details)

        df_header.T.to_excel("./data/parsed/" + file["hashSha256"] + "_header.xlsx")
        df_details.to_excel("./data/parsed/" + file["hashSha256"] + "_details.xlsx", index=None)

        # Test lookup

        matched = normalize_result_to_revolab(df_header, df_details)

        test_date = (
            datetime.datetime.fromisoformat(df_header.iloc[0]["Mėginys paimtas"]).isoformat(timespec="milliseconds")
            + "Z"
        )

        parsing_status = {
            "recognitionStatus": "OK",
            "errorText": "",
            "testDate": test_date,
            "laboratoryId": df_header.iloc[0]["laboratory_id"],
            "recognizedTestResults": matched,
        }

    else:
        parsing_status = {
            "recognitionStatus": "ERROR",
            "errorText": "Recognition failed: " + recognition_error,
            "recognizedTestResults": dict(),
        }

    execution_log = {
        "date_time_utc": date_time_utc,
        "uuid": uuid_srt,
        "remote_addr": request.remote_addr,
        "request": request_json,
        "response": parsing_status,
    }
    log_file_name = f"./data/execution_logs/{date_time_utc}_{uuid_srt}.json"
    make_dirs(log_file_name)
    with open(log_file_name, "w") as f:
        json.dump(execution_log, f)

    return parsing_status


# TODO remove, deprecated
@app.route("/recognize-diagnostic", methods=["POST"])
def recognize_diagnostic():

    request_json = request.json

    print(f"Recognize-diagnostic API post from: {request.remote_addr}, json: {json.dumps(request_json, indent=4)}")

    files = request_json["files"]

    assert len(files) == 1

    file = files[0]
    uploaded_file_uri = f"gs://revolab-test.appspot.com/{file['hashedName']}"

    recognizer_infrastructure = initialize_infrastructure()
    recognition_ok, recognition_error, df_header, df_details = process_single_pdf_in_gs(
        uploaded_file_uri, recognizer_infrastructure
    )

    if recognition_ok:

        pd.options.display.max_rows = 300
        pd.options.display.width = 1000
        pd.options.display.max_columns = None
        pd.options.display.max_colwidth = 200

        print(df_header.T)
        print(df_details)

        df_header.T.to_excel("./data/parsed/" + file["hashSha256"] + "_header.xlsx")
        df_details.to_excel("./data/parsed/" + file["hashSha256"] + "_details.xlsx", index=None)

        parsing_status = {
            "recognitionStatus": "OK",
            "errorText": "",
            "header": df_header.T.to_dict(),
            "details": df_details.to_dict(),
        }

    else:
        parsing_status = {
            "recognitionStatus": "ERROR",
            "errorText": "Recognition failed: " + recognition_error,
        }

    return parsing_status


def remove_pdf_password(recognizer_infrastructure, uploaded_file_uri, password_secret):
    pdf_password = get_google_secret(recognizer_infrastructure.secret_manager_client, password_secret)
    downloaded_pdf = recognizer_infrastructure.download_file_from_google_bucket(
        uploaded_file_uri, "data/local_input_copy"
    )
    downloaded_pdf_password_removed = downloaded_pdf + "_password_removed"
    remove_password(downloaded_pdf, downloaded_pdf_password_removed, pdf_password)
    hash_password_removed = file_to_sha256(downloaded_pdf_password_removed)
    target_file_name = "temp_passwd_removed/" + hash_password_removed + ".pdf"
    uploaded_file_password_removed_uri = recognizer_infrastructure.upload_pdf_to_google_bucket(
        downloaded_pdf_password_removed, target_file_name
    )
    uploaded_file_password_removed_uri
    return uploaded_file_password_removed_uri


# TODO move to utils
def remove_password(pdf_in, pdf_out, passwd):
    with pikepdf.open(
        pdf_in,
        password=passwd,
    ) as pdf:
        num_pages = len(pdf.pages)
        pdf.save(pdf_out)
        print(f"{'-' * 100}")
        print(f"removing passwrord from: {pdf_in}")
        print(f"saving as:               {pdf_out}")
        print(f"pages: {num_pages}")
        print(f"{'-' * 100}")
    return None


# TODO move to google tools or infrastructure
def get_google_secret(secret_manager_client, password_secret):
    full_password_secret = password_secret + "/versions/latest"
    password = secret_manager_client.access_secret_version(request={"name": full_password_secret}).payload.data.decode(
        "UTF-8"
    )
    return password


if __name__ == "__main__":
    app.run(
        debug=False,
        host="0.0.0.0",
        ssl_context=(
            "./data/labrep_config/paperform.dev-ssl-bundle/domain.cert.pem",  # Cert file
            "./data/labrep_config/paperform.dev-ssl-bundle/private.key.pem",  # Key file
        ),
        port=36282,
    )
