# pdf_extraction.py

from tabula import read_pdf


def read_pdf_(file, pages, area, columns):
    """
    Customized version of the tabula read_pdf function for specific purposes.
    """
    columns = list(columns)
    return read_pdf(input_path=file,
                    guess=False,
                    pages=pages,
                    encoding="windows-1252",
                    area=area,
                    columns=columns,
                    pandas_options={"header": None}
                    )
