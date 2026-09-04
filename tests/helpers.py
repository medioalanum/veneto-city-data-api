from __future__ import annotations

import io
import zipfile


def zip_bytes(filename: str, content: str) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(filename, content)
    return output.getvalue()


def istat_zip() -> bytes:
    return zip_bytes(
        "POSAS_2026_en_028_Padova.csv",
        '"Resident population by age and sex on 1st January 2026"\n'
        '"Municipality code","Municipality","Age","Total males","Total females","Total"\n'
        '"028060","Exactville",17,25000,25000,50000\n'
        '"028001","Padova",0,10000,9000,19000\n'
        '"028001","Padova",18,15000,16000,31000\n'
        '"028001","Padova",65,8000,12000,20000\n'
        '"028001","Padova",999,33000,37000,70000\n'
        ",,,,,\n",
    )


def mef_zip() -> bytes:
    return zip_bytes(
        "income.csv",
        "Anno di imposta;Codice Istat Comune;Denominazione Comune;Regione;"
        "Numero contribuenti;Reddito complessivo - Ammontare in euro;"
        "Imposta netta - Ammontare in euro\n"
        "2024;028001;PADOVA;Veneto;50000;1500000000;250000000\n"
        "2024;001001;AGLIE;Piemonte;1000;20000000;3000000\n",
    )
