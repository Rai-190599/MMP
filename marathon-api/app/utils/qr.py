"""QR code generation utilities."""
import io

import qrcode
import qrcode.constants


def generate_qr_png(data: str) -> bytes:
    """
    Generate a QR code PNG for the given data string.

    Args:
        data: The string to encode — for BIB QRs this is str(registration_id).

    Returns:
        Raw PNG bytes ready to upload or serve.
    """
    qr = qrcode.QRCode(
        version=None,          # auto-size
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,              # 4-module white quiet zone (QR spec minimum)
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
