from tabula import read_pdf
from routes import *
from datetime import datetime
import itertools
import glob
import re
import pandas as pd
import logging
logging.basicConfig(level=logging.INFO)

pd.options.mode.chained_assignment = None

list_files = glob.glob(directory_in)

match = re.search(r"\\([^\\]+)\\[^\\]*\.pdf", directory_in)
name_excel = match.group(1).replace(" ", "_") if match else "default_name"

df_establishments = pd.read_excel("Establecimientos.xlsx")

def _extract_visa():
    logging.info("Beginning extract Visa.")
    visa_df = []

    for file in list_files:
        logging.info("Beginning extract {}.".format(file))

        #PDF READER
        month_settled = _read_pdf(file, 1, (318, 98, 347, 406), (120, 180))[0].loc[0, 1]

        establishment_number = _read_pdf(file, 1, (144, 348, 268, 507), (455, 506))[0].loc[0, 1]

        establishment = _complete_establishment(_complete_columns(pd.DataFrame(data=[[establishment_number]])),
                                                establishment_number).loc[0, 0] + " "

        full_discount = _to_float(_read_pdf(file, 1, (144, 348, 268, 507), (455, 506))[0].loc[4, 0])

        even_odd_list = _even_odd_list(len(read_pdf(input_path=file,
                                                    pages="all", encoding="windows-1252", guess=False)))

        list_df_odd = _read_pdf(file, even_odd_list[1], (373, 0, 945, 535), (190, 263, 460))

        list_df_even = _read_pdf(file, even_odd_list[0], (84, 0, 945, 535), (190, 263, 460))\
            if even_odd_list[0] else [_complete_columns(pd.DataFrame())]

        list_all_df = list(itertools.chain(*zip(list_df_odd, list_df_even)))

        df = pd.concat(list(map(_complete_columns, list_all_df)))

        #DATA EXTRACT
        df_full_discount = _extract_full_dis(full_discount, month_settled, establishment)
        df_accred_and_debits = _extract_accred_and_debits(df, establishment)
        df_devolutions = _extract_devol(df, establishment)
        df_sells = _extract_sells(df, establishment)
        df_chargeback = _extract_charg(df, month_settled, establishment)
        df_reverse = _extract_reverse(df, month_settled, establishment)

        #EXPORT
        df = pd.concat([df_chargeback, df_reverse, df_accred_and_debits, df_devolutions, df_sells, df_full_discount])
        df[0] = establishment_number
        df.columns = ["Establecimiento", "Detalle", "Debe", "Haber"]
        df = df.replace("", "No data")
        visa_df.append(df)

    _export_to_excel(visa_df)
    logging.info("Visa exported.")


def _read_pdf(file, pages, area, columns):
    return read_pdf(input_path=file, guess=False, pages=pages,
                    encoding="windows-1252", area=area, columns=columns,
                    pandas_options={"header": None})


def _search_string(df, match_words):
    pattern = re.compile("|".join(match_words))
    return df.loc[df[0].str.contains(pattern, na=False)]


def _to_float(data):
    data = str(data)
    if data:
        return float(("-" + data.replace("-", "") if "-" in data else data)
                     .replace(".", "")
                     .replace(",", ".")
                     .replace("$", ""))
    else:
        return 0


def _even_odd_list(len):
    odd = []
    even = []
    for n in range(len + 1):
        if n % 2 == 0:
            if n != 0:
                even.append(n)
        else:
            odd.append(n)
    return [even, odd]


def _complete_columns(df):
    while len(df.columns) != 4:
        df[len(df.columns)] = ""
    return df


def _extract_accred_and_debits(df, establishment):
    df = _search_string(df, ["Total del día", "FECHA DE PAGO"])

    df[1] = df[0]
    df[3] = df[3].shift(-1)

    df = df.loc[df[1].str.contains("FECHA DE PAGO\d\d", na=False)]

    df = df[(df[3] != 0) & (df[3] != "") & df[3].notna()]
    df[3] = df[3].apply(_to_float)

    mask = df[3] > 0
    df.loc[mask, 2] = ""
    df.loc[mask, 1] = "Acredi - " + establishment + df.loc[mask, 1].str.slice(-5)

    mask_inv = ~mask
    df.loc[mask_inv, 2] = -df.loc[mask_inv, 3]
    df.loc[mask_inv, 3] = ""
    df.loc[mask_inv, 1] = "Debito - " + establishment + df.loc[mask_inv, 1].str.slice(-5)

    return df


def _extract_devol(df, establishment):
    df = _search_string(df, ["Fecha de prese", "Devoluci"])

    df[1] = df[1].shift(-1)

    df = df[(df[1] != 0) & (df[1] != "") & df[1].notna()]
    df[1] = df[1].apply(_to_float)

    df[3] = -df[1]
    df[1] = "Devolucion - " + establishment + df[0].str[-5:]
    df[2] = ""

    return df


def _extract_sells(df, establishment):
    df = _search_string(df, ["Ventas en", "Venta en", "Fecha de presenta"])
    df.reset_index(drop=True, inplace=True)

    df[1] = df[1].apply(_to_float)

    fechas = []
    ventas = []

    for i, fila in df.iterrows():
        if "Fecha" in str(fila[0]):
            fechas.append(i)
            ventas.append(0)
        elif "Venta" in str(fila[0]):
            ventas[-1] += float(fila[1])

    df = _complete_columns(pd.DataFrame(list(zip(df.loc[fechas][0], ventas)), columns=[0, 1]))
    df = df.drop(df[df[1] == 0].index)
    df[0] = "Ventas - " + establishment + df[0]

    df[2] = df[1]
    df[1] = df[0]
    return df


def _extract_charg(df, month_settled, establishment):
    df = _search_string(df, ["Contra"])

    chargeback_value = -df[1].apply(_to_float).sum()

    if not (chargeback_value == 0):
        df = _complete_columns(
            pd.DataFrame(data=[["Contracargos - " + establishment + month_settled, chargeback_value]]))
        df[3] = df[1]
        df[1] = df[0]
        return df

    return _complete_columns(pd.DataFrame())


def _extract_reverse(df, month_settled, establishment):
    df = _search_string(df, ["Reverso"])

    reverse_value = -df[1].apply(_to_float).sum()

    if not (reverse_value == 0):
        df = _complete_columns(
            pd.DataFrame(data=[["Reverso - " + establishment + month_settled, reverse_value]]))
        df[3] = df[1]
        df[1] = df[0]
        return df

    return _complete_columns(pd.DataFrame())


def _extract_full_dis(full_discount, month_settled, establishment):
    df = _complete_columns(pd.DataFrame(data=[["Total descuentos - " + establishment + month_settled, full_discount]]))
    df[3] = df[1]
    df[1] = df[0]
    return df


def _complete_establishment(df, establishment):
    mask = df_establishments["Establecimiento"].astype(str) == establishment[2:]
    if mask.any():
        df[0] = df_establishments.loc[mask, "Nombre"].iloc[0]
    else:
        df[0] = "No registrado"
    return df


def _export_to_excel(list_dfs):
    df = pd.concat(list_dfs)
    df.reset_index(drop=True, inplace=True)
    df.to_excel(directory_out +
                datetime.today().strftime("%d-%m-%Y") + "_" + name_excel +".xlsx", sheet_name="Sheet 1")

if __name__ == "__main__":
    _extract_visa()
