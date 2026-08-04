import os
import sys
from io import StringIO

import matplotlib
matplotlib.use("Agg")  # sin entorno gráfico (necesario en GitHub Actions)
import matplotlib.pyplot as plt
import pandas as pd
import requests

SHEET_URL = os.environ["SHEET_URL"]
WHATSAPP_TOKEN = os.environ["WHATSAPP_TOKEN"]
PHONE_NUMBER_ID = os.environ["PHONE_NUMBER_ID"]
RECIPIENT_NUMBER = os.environ["RECIPIENT_NUMBER"]
TEMPLATE_NAME = os.environ.get("TEMPLATE_NAME", "reporte_semanal")
TEMPLATE_LANG = os.environ.get("TEMPLATE_LANG", "es")

GRAPH_API_VERSION = "v21.0"
IMAGE_PATH = "reporte.png"
MAX_ROWS = 30  # límite para que la imagen no salga gigante si el sheet crece mucho


def fetch_sheet_data() -> pd.DataFrame:
    response = requests.get(SHEET_URL, timeout=30)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))


def render_table_image(df: pd.DataFrame, path: str) -> None:
    shown = df.head(MAX_ROWS)

    fig_height = 0.45 * (len(shown) + 1) + 1
    fig_width = max(6, 1.3 * len(shown.columns))
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")

    table = ax.table(
        cellText=shown.values,
        colLabels=shown.columns,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)

    for (row, _col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#4472C4")
            cell.set_text_props(color="white", weight="bold")
        else:
            cell.set_facecolor("#F2F2F2" if row % 2 == 0 else "white")

    ax.set_title("Reporte semanal", fontsize=14, weight="bold", pad=20)
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    if len(df) > MAX_ROWS:
        print(f"Aviso: se muestran solo las primeras {MAX_ROWS} filas de {len(df)}.")


def upload_media(path: str) -> str:
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    with open(path, "rb") as f:
        files = {"file": (path, f, "image/png")}
        data = {"messaging_product": "whatsapp", "type": "image/png"}
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    if not resp.ok:
        print("Error subiendo la imagen a WhatsApp:", resp.text, file=sys.stderr)
    resp.raise_for_status()
    return resp.json()["id"]


def send_template_with_image(media_id: str) -> None:
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": RECIPIENT_NUMBER,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": TEMPLATE_LANG},
            "components": [
                {
                    "type": "header",
                    "parameters": [
                        {"type": "image", "image": {"id": media_id}}
                    ],
                }
            ],
        },
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if not resp.ok:
        print("Error enviando el mensaje de WhatsApp:", resp.text, file=sys.stderr)
    resp.raise_for_status()


def main() -> None:
    df = fetch_sheet_data()
    print(f"Filas: {len(df)} | Columnas: {len(df.columns)}")

    render_table_image(df, IMAGE_PATH)
    media_id = upload_media(IMAGE_PATH)
    send_template_with_image(media_id)
    print("Mensaje enviado correctamente.")


if __name__ == "__main__":
    main()
