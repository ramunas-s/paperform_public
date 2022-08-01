laboratory_types = [
    ("labrep_anteja_2021", "LabrepAnteja2021", "is_anteja_2021", "Anteja"),
    ("labrep_medicina_practica_2021", "LabrepMedicinaPractica2021", "is_medicina_practica_2021", "MedicinaPractica"),
    ("labrep_synlab_2021", "LabrepSynlab2021", "is_synlab_2021", "Synlab"),
]


class LabrepInterface:
    def __init__(
        self,
        df_abbyy_extracted,
        abbyy_tools,
        google_ocred_document,
        google_tools,
        tika_extracted_text,
    ):
        self.df_abbyy_extracted = df_abbyy_extracted
        self.abbyy_tools = abbyy_tools
        self.google_ocred_document = google_ocred_document
        self.google_tools = google_tools
        self.tika_extracted_text = tika_extracted_text

    def parse(self):
        header = dict()

        detail_fields_functions = [
            ("Laboratorija", self.header_laboratory_name),
            ("Užsakovas", self.header_requestor),
            ("Gydytojas", self.header_doctor),
            ("Pacientas", self.header_patient),
            ("Gimimo data", self.header_birth_date),
            ("Lytis", self.header_gender),
            ("Mėginys paimtas", self.header_sample_collected_time_raw),
            ("Nr", self.header_laboratory_report_id),
        ]

        for field, function in detail_fields_functions:
            try:
                header[field] = function()
            except (
                    IndexError,
                    AssertionError,
            ):
                header[field] = ""

        df_details_normalized_corrected = self.details()
        return header, df_details_normalized_corrected

    # Header methods

    def header_laboratory_name(self):
        pass

    def header_requestor(self):
        pass

    def header_doctor(self):
        pass

    def header_patient(self):
        pass

    def header_birth_date(self):
        pass

    def header_gender(self):
        pass

    def header_sample_collected_time_raw(self):
        pass

    def header_laboratory_report_id(self):
        pass

    # Details

    def details(self):
        pass
