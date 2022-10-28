import itertools
import pandas as pd
from tabula import read_pdf
import glob
from routes import *
pd.options.mode.chained_assignment = None
from datetime import datetime
import logging
logging.basicConfig(level=logging.INFO)
import re

list_files = glob.glob(directory_in)
df_establishments = pd.read_excel("Establecimientos.xlsx")

def _extract_visa():
    logging.info("Beginning extract Visa.")
    count_files = 0
    visa_df = []

    for file in list_files:
        logging.info("Beginning extract {}.".format(file))
        count_files += 1

        month_settled = _read_pdf(file, 1, (318, 98, 347, 406), (120, 180))[0].loc[0, 1]
        establishment_number = _read_pdf(file, 1, (144, 348, 268, 507), (455, 506))[0].loc[0, 1]
        establishment = _complete_establishment(_complete_columns(pd.DataFrame(data=[[establishment_number]])),
                                                establishment_number).loc[0, 0] + " "
        full_discount = _to_float(_read_pdf(file, 1, (144, 348, 268, 507), (455, 506))[0].loc[4, 0])

        even_odd_list = _even_odd_list(len(read_pdf(input_path=file,
                                                    pages="all", encoding="windows-1252", guess=False)))
        list_df_odd = _read_pdf(file, even_odd_list[1], (373, 0, 945, 535), (190, 263, 460))
        list_df_even = _read_pdf(file, even_odd_list[0], (84, 0, 945, 535), (190, 263, 460))

        list_all_df = list(itertools.chain(*zip(list_df_odd, list_df_even)))

        for df in list_all_df:
            _complete_columns(df)

        df = pd.concat(list_all_df)
        df.reset_index(drop=True, inplace=True)

        df_full_discount = _extract_full_dis(full_discount, month_settled, establishment)
        df_accred_and_debits = _extract_accred_and_debits(df, establishment)
        df_devolutions = _extract_devol(df, establishment)
        df_sells = _extract_sells(df, establishment)
        df_chargeback = _extract_charg(df, month_settled, establishment)
        df = pd.concat([df_chargeback, df_accred_and_debits, df_devolutions, df_sells, df_full_discount])

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


def _to_float(data):
    data = str(data)
    # Si data no existe.
    if data:
        return float(("-" + data.replace("-", "") if "-" in data else data).replace(".", "").replace(",", "."))
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


def _move_vertical_column_up(df, column):
    for i in df.index:
        if i != (len(df.index) - 1):
            df[column][i] = (df[column][i + 1])
    return df


def _extract_accred_and_debits(df, establishment):
    match_words = ["Total del día", "FECHA DE PAGO"]
    df = df.loc[df[0].str.contains("|".join(match_words), na=False)]
    df[1] = df[0]
    df.reset_index(drop=True, inplace=True)
    df = _move_vertical_column_up(df, 3)

    for i in df.index:
        if not (re.search(r"FECHA DE PAGO\d\d", df[1][i])):
            df = df.drop(i)
        else:
            df[3][i] = _to_float(df[3][i])
            if df[3][i] < 0:
                df[2][i] = float(str(df[3][i]).replace("-", ""))
                df[3][i] = ""
                df[1][i] = "Debito - " + establishment + (df[1][i])[-5:]
            elif df[3][i] > 0:
                df[2][i] = ""
                df[1][i] = "Acredi - " + establishment + (df[1][i])[-5:]
            else:
                df = df.drop(i)

    df.reset_index(drop=True, inplace=True)
    return df


def _extract_devol(df, establishment):
    match_words = ["Fecha de prese", "Devoluci"]
    df = df.loc[df[0].str.contains("|".join(match_words), na=False)]
    df.reset_index(drop=True, inplace=True)
    df = _move_vertical_column_up(df, 1)

    for i in df.index:
        if not (re.search(r"Fecha", df[0][i])) or pd.isna(df[1][i]):
            df = df.drop(i)
        else:
            df[3][i] = float(str(_to_float(df[1][i])).replace("-", ""))
            df[1][i] = "Devolucion - " + establishment + (df[0][i])[-5:]
            df[2][i] = ""

    df.reset_index(drop=True, inplace=True)
    return df


def _extract_sells(df, establishment):
    match_words = ["Ventas en", "Venta en", "Fecha de presenta"]
    df = df.loc[df[0].str.contains("|".join(match_words), na=False)]
    df.reset_index(drop=True, inplace=True)

    _len = len(df.index) - 1
    for i in df.index:
        if not (i == _len):
            if (re.search(r"\d Venta", df[0][i])) and pd.isna(df[1][i]):
                df = df.drop(i)
            elif not (re.search(r"\d Venta", df[0][i])):
                if not ("Venta" in str(df[0][i + 1])):
                    df = df.drop(i)
        elif not (re.search(r"\d Venta", df[0][i])):
            df = df.drop(i)

    df.reset_index(drop=True, inplace=True)

    sell_amount = 0
    sells = []
    sells_detail = []
    _len = len(df.index) - 1
    for i in df.index:
        if re.search(r"Fecha", df[0][i]):
            df[0][i] = "Ventas - " + establishment + str(df[0][i])[-5:]
            sells_detail.append(df[0][i])
            if sell_amount != 0:
                sells.append(sell_amount)
            sell_amount = 0
        elif re.search(r"Venta", df[0][i]):
            sell_amount += _to_float(df[1][i])
            if i == _len:
                sells.append(sell_amount)

    df = _complete_columns(pd.DataFrame(list(zip(sells_detail, sells))))
    df[2] = df[1]
    df[1] = df[0]
    return df


def _extract_charg(df, month_settled, establishment):
    match_words = ["Contra"]
    df = df.loc[df[0].str.contains("|".join(match_words), na=False)]
    df.reset_index(drop=True, inplace=True)

    chargeback_value = 0
    for i in df.index:
        df[1][i] = _to_float(df[1][i]) * -1
        chargeback_value += df[1][i]

    if not (chargeback_value == 0):
        df = _complete_columns(
            pd.DataFrame(data=[["Contracargos - " + establishment + month_settled, chargeback_value]]))
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
    find = False
    for i in df_establishments.index:
        if str(establishment) == str("00" + str(df_establishments["Establecimiento"][i])).replace(".0", ""):
            df[0] = str(df_establishments["Nombre"][i])
            find = True
    if not (find):
        df[0] = "No registrado"
    return df


def _export_to_excel(list_dfs):
    df = pd.concat(list_dfs)
    df.reset_index(drop=True, inplace=True)
    df.to_excel(directory_out +
                datetime.today().strftime("%d-%m-%Y") + ' Visa.xlsx', sheet_name="Sheet 1")

if __name__ == "__main__":
    _extract_visa()
