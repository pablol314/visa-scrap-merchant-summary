# main.py

import glob
import pandas as pd
import itertools
from core.pdf_extraction import read_pdf_
from core.constants import *
from core.data_processing import (
    extract_accred_and_debits,
    extract_devolutions,
    extract_sells,
    extract_chargeback,
    extract_reverse,
    extract_full_discount,
    complete_establishment,
)
from utils.utils import (
    even_odd_lists,
    to_float,
    complete_columns,
    export_to_excel,
)
from routes import directory_in
import logging

logging.basicConfig(level=logging.INFO)


def extract_visa_data(file: str) -> pd.DataFrame:
    """
    Extract Visa data from a PDF file, perform transformations, and export the data.
    :param file: The path to the PDF file containing Visa data.
    :return: DataFrame with extracted and transformed Visa data.
    """
    logging.info(f"Starting data extraction from {file}.")

    # READ PDF
    month_settled = MONTH_SETTLED

    establishment_number = read_pdf_(file, 1, INFO_AREA, COLUMNS_INFO)[0].loc[0, 1]

    establishment = complete_establishment(
        complete_columns(pd.DataFrame(data=[[establishment_number]])), establishment_number
    ).loc[0, 0] + " "

    full_discount = to_float(read_pdf_(file, 1, INFO_AREA, COLUMNS_INFO)[0].loc[4, 0])

    even_odd = even_odd_lists(len(read_pdf_(file, "all", ODD_DATA_AREA, COLUMNS_DATA)))

    list_df_odd = read_pdf_(file, even_odd[1], ODD_DATA_AREA, COLUMNS_DATA)

    list_df_even = (
        read_pdf_(file, even_odd[0], EVEN_DATA_AREA, COLUMNS_DATA)
        if even_odd[0]
        else [complete_columns(pd.DataFrame())]
    )

    list_all_df = list(itertools.chain(*zip(list_df_odd, list_df_even)))

    df = pd.concat(list(map(complete_columns, list_all_df)))

    # EXTRACT
    df_full_discount = extract_full_discount(full_discount, month_settled, establishment)
    df_accred_and_debits = extract_accred_and_debits(df, establishment)
    df_devolutions = extract_devolutions(df, establishment)
    df_sells = extract_sells(df, establishment)
    df_chargeback = extract_chargeback(df, month_settled, establishment)
    df_reverse = extract_reverse(df, month_settled, establishment)

    # EXPORT
    df = pd.concat(
        [
            df_chargeback,
            df_reverse,
            df_accred_and_debits,
            df_devolutions,
            df_sells,
            df_full_discount,
        ]
    )

    df[0] = establishment_number
    df.columns = COLUMN_NAMES
    df = df.replace("", "No data")

    return df


def main():
    logging.info("Starting Visa data extraction.")

    list_files = glob.glob(directory_in)

    visa_data = []

    for file in list_files:
        df = extract_visa_data(file)
        visa_data.append(df)

    export_to_excel(visa_data, directory_in)
    logging.info("Visa data exported.")


if __name__ == "__main__":
    main()
