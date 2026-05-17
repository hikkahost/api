import base64
from io import BytesIO

import qrcode
from qrcode.constants import ERROR_CORRECT_H

QR_BOX_SIZE = 10
QR_BORDER = 2
QR_LOGO_MODULES = 13

QR_MODULE_COLOR = "#ffffff"
QR_BACKGROUND_COLOR = "#0a0a0a"


def qr_logo_ratio(qr: qrcode.QRCode, logo_modules: int = QR_LOGO_MODULES) -> float:
    total = qr.modules_count + 2 * qr.border
    return logo_modules / total


async def render_qr_data_uri(url: str) -> dict:
    """White-on-dark PNG QR (scannable, matches setup_web theme)."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=QR_BOX_SIZE,
        border=QR_BORDER,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color=QR_MODULE_COLOR, back_color=QR_BACKGROUND_COLOR)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "qr_image": f"data:image/png;base64,{encoded}",
        "qr_logo_ratio": qr_logo_ratio(qr),
    }
