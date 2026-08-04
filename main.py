import os
import requests
import pandas as pd
from io import StringIO
SHEET_URL = os.environ["SHEET_URL"]
response = requests.get(SHEET_URL)
response.raise_for_status()
csv_data = StringIO(response.text)
df = pd.read_csv(csv_data)
print(df)
print()
print("Filas:", len(df))
print("Columnas:", len(df.columns))
