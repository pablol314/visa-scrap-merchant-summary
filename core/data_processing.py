# data_processing.py

import pandas as pd
from utils.utils import search_string, complete_columns, to_float
from typing import List, Union, Tuple, Optional

df_establishments = pd.read_excel("./Establecimientos.xlsx")


def extract_accred_and_debits(df: pd.DataFrame, establishment: str) -> pd.DataFrame:
    """
    Extract accreditation and debit data and perform transformations.
    :param df: The DataFrame containing the data to extract from.
    :param establishment: The name of the establishment.
    :return: DataFrame with extracted and transformed data.
    """
    df = search_string(df, ["Total del día", "FECHA DE PAGO"])

    df.loc[:, 1] = df[0]
    df.loc[:, 3] = df[3].shift(-1)

    df = df.loc[df[1].str.contains("FECHA DE PAGO\d\d", na=False)]

    df = df[(df[3] != 0) & (df[3] != "") & df[3].notna()]
    df.loc[:, 3] = df[3].apply(to_float)

    mask = df[3] > 0
    df.loc[mask, 2] = ""
    df.loc[mask, 1] = "Accredi - " + establishment + df.loc[mask, 1].str.slice(-5)

    mask_inv = ~mask
    df.loc[mask_inv, 2] = -df.loc[mask_inv, 3]
    df.loc[mask_inv, 3] = ""
    df.loc[mask_inv, 1] = "Debit - " + establishment + df.loc[mask_inv, 1].str.slice(-5)

    return df


def extract_devolutions(df: pd.DataFrame, establishment: str) -> pd.DataFrame:
    """
    Extract devolution data and perform transformations.
    :param df: The DataFrame containing the data to extract from.
    :param establishment: The name of the establishment.
    :return: DataFrame with extracted and transformed data.
    """
    df = search_string(df, ["Fecha de prese", "Devoluci"])

    df.loc[:, 1] = df[1].shift(-1)

    df = df[(df[1] != 0) & (df[1] != "") & df[1].notna()]
    df.loc[:, 1] = df[1].apply(to_float)

    df.loc[:, 3] = -df[1]
    df.loc[:, 1] = "Devolution - " + establishment + df[0].str[-5:]
    df.loc[:, 2] = ""

    return df


def extract_sells(df: pd.DataFrame, establishment: str) -> pd.DataFrame:
    """
    Extract sales data and perform transformations.
    :param df: The DataFrame containing the data to extract from.
    :param establishment: The name of the establishment.
    :return: DataFrame with extracted and transformed data.
    """
    df = search_string(df, ["Ventas en", "Venta en", "Fecha de presenta"])
    df.reset_index(drop=True, inplace=True)

    df.loc[:, 1] = df[1].apply(to_float)

    fechas = []
    ventas = []

    for i, fila in df.iterrows():
        if "Fecha" in str(fila[0]):
            fechas.append(i)
            ventas.append(0)
        elif "Venta" in str(fila[0]):
            ventas[-1] += float(fila[1])

    df = complete_columns(pd.DataFrame(list(zip(df.loc[fechas][0], ventas)), columns=[0, 1]))
    df = df.drop(df[df[1] == 0].index)
    df.loc[:, 0] = "Sales - " + establishment + df[0]

    df.loc[:, 2] = df[1]
    df.loc[:, 1] = df[0]
    return df


def extract_chargeback(df: pd.DataFrame, month_settled: str, establishment: str) -> pd.DataFrame:
    """
    Extract chargeback data and perform transformations.
    :param df: The DataFrame containing the data to extract from.
    :param month_settled: The month for which the data is settled.
    :param establishment: The name of the establishment.
    :return: DataFrame with extracted and transformed data.
    """
    df = search_string(df, ["Contra"])

    chargeback_value = -df[1].apply(to_float).sum()

    if chargeback_value != 0:
        df = complete_columns(
            pd.DataFrame(data=[["Chargebacks - " + establishment + month_settled, chargeback_value]]))
        df.loc[:, 3] = df[1]
        df.loc[:, 1] = df[0]
        return df

    return complete_columns(pd.DataFrame())


def extract_reverse(df: pd.DataFrame, month_settled: str, establishment: str) -> pd.DataFrame:
    """
    Extract reverse data and perform transformations.
    :param df: The DataFrame containing the data to extract from.
    :param month_settled: The month for which the data is settled.
    :param establishment: The name of the establishment.
    :return: DataFrame with extracted and transformed data.
    """
    df = search_string(df, ["Reverso"])

    reverse_value = -df[1].apply(to_float).sum()

    if reverse_value != 0:
        df = complete_columns(
            pd.DataFrame(data=[["Reverse - " + establishment + month_settled, reverse_value]]))
        df.loc[:, 3] = df[1]
        df.loc[:, 1] = df[0]
        return df

    return complete_columns(pd.DataFrame())


def extract_full_discount(full_discount: float, month_settled: str, establishment: str) -> pd.DataFrame:
    """
    Extract total discount data and perform transformations.
    :param full_discount: The total discount value.
    :param month_settled: The month for which the data is settled.
    :param establishment: The name of the establishment.
    :return: DataFrame with extracted and transformed data.
    """
    df = complete_columns(pd.DataFrame(data=[["Total discounts - " + establishment + month_settled, full_discount]]))
    df.loc[:, 3] = df[1]
    df.loc[:, 1] = df[0]
    return df


def complete_establishment(df: pd.DataFrame, establishment: str) -> pd.DataFrame:
    """
    Complete the establishment name in a DataFrame based on previously loaded establishment data.
    :param df: The DataFrame to complete.
    :param establishment: The name of the establishment.
    :return: DataFrame with completed establishment name.
    """
    mask = df_establishments["Establecimiento"].astype(str) == establishment[2:]
    if mask.any():
        df.loc[:, 0] = df_establishments.loc[mask, "Nombre"].iloc[0]
        return df

    df.loc[:, 0] = "No registrado"
    return df
