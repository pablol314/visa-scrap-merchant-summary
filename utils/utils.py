# utils.py

import re
import pandas as pd
from datetime import datetime
from typing import List, Union


def export_to_excel(list_dfs: List[pd.DataFrame], directory_in: str) -> None:
    """
    Export data to an Excel file.
    :param list_dfs: List of DataFrames to export.
    :param directory_in: The directory path for saving the Excel file.
    """
    match = re.search(r"\\([^\\]+)\\[^\\]*\.pdf", directory_in)
    name_excel = match.group(1).replace(" ", "_") if match else "default_name"

    df = pd.concat(list_dfs)
    df.reset_index(drop=True, inplace=True)
    df.to_excel(directory_in[:-6] +
                datetime.today().strftime("%d-%m-%Y") + "_" + name_excel + ".xlsx", sheet_name="Sheet 1")


def search_string(df: pd.DataFrame, match_words: List[str]) -> pd.DataFrame:
    """
    Search for a series of words in the DataFrame and return the matching rows.
    :param df: The DataFrame to search in.
    :param match_words: List of words to search for.
    :return: DataFrame containing matching rows.
    """
    pattern = re.compile("|".join(match_words))
    return df.loc[df[0].str.contains(pattern, na=False)]


def to_float(data: Union[float, str]) -> float:
    """
    Convert a string to a floating-point number.
    :param data: The input data to convert.
    :return: The converted floating-point number.
    """
    data = str(data)
    if data:
        return float(("-" + data.replace("-", "") if "-" in data else data)
                     .replace(".", "")
                     .replace(",", ".")
                     .replace("$", ""))
    return 0


def even_odd_lists(n: int) -> List[List[int]]:
    """
    Generate lists of even and odd numbers up to a given number (n).
    :param n: The maximum number in the lists.
    :return: A list containing two sublists - one for even numbers and one for odd numbers.
    """
    even = [num for num in range(2, n + 1, 2)]
    odd = [num for num in range(1, n + 1, 2)]
    return [even, odd]


def complete_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Complete a DataFrame with empty columns until it has a total of 4 columns.
    :param df: The DataFrame to complete.
    :return: The DataFrame with empty columns added.
    """
    while len(df.columns) != 4:
        df[len(df.columns)] = ""
    return df
