"""Lectura local de placas con Tesseract OCR."""

import re
import os
from dataclasses import dataclass

from PIL import Image, ImageOps


class OCRUnavailable(Exception):
    """El motor Tesseract no está instalado o no se puede ejecutar."""


@dataclass(frozen=True)
class PlateReading:
    placa: str
    confianza: float


def read_plate(image_file):
    """Lee una línea alfanumérica y su confianza desde una imagen subida."""
    try:
        import pytesseract
    except ImportError as error:
        raise OCRUnavailable(
            "Falta pytesseract. Instala las dependencias del proyecto."
        ) from error

    configured_engine = os.environ.get("TESSERACT_CMD")
    if configured_engine:
        pytesseract.pytesseract.tesseract_cmd = configured_engine

    try:
        image_file.seek(0)
        with Image.open(image_file) as source:
            prepared = ImageOps.exif_transpose(source).convert("L")
            prepared = ImageOps.autocontrast(prepared)
            if prepared.width > 2000 or prepared.height > 2000:
                prepared.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
            if prepared.width < 1200:
                ratio = 1200 / prepared.width
                prepared = prepared.resize(
                    (1200, round(prepared.height * ratio)),
                    Image.Resampling.LANCZOS,
                )
            data = pytesseract.image_to_data(
                prepared,
                lang="eng",
                config=(
                    "--oem 3 --psm 7 "
                    "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                ),
                output_type=pytesseract.Output.DICT,
                timeout=8,
            )
    except (pytesseract.TesseractNotFoundError, pytesseract.TesseractError) as error:
        raise OCRUnavailable(
            "No se encontró el motor Tesseract. Instálalo y reinicia el servidor."
        ) from error
    except RuntimeError as error:
        raise OCRUnavailable(
            "La lectura tardó demasiado. Usa una imagen más clara o captura la placa manualmente."
        ) from error
    except (OSError, ValueError) as error:
        raise OCRUnavailable("No se pudo procesar la imagen adjunta.") from error
    finally:
        image_file.seek(0)

    tokens = []
    confidences = []
    for text, raw_confidence in zip(data["text"], data["conf"]):
        token = re.sub(r"[^A-Z0-9]", "", text.upper())
        if not token:
            continue
        tokens.append(token)
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            continue
        if confidence >= 0:
            confidences.append(confidence)

    plate = "".join(tokens)
    if not 4 <= len(plate) <= 15 or not confidences:
        return None
    return PlateReading(
        placa=plate,
        confianza=sum(confidences) / len(confidences),
    )
