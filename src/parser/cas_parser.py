import io
import re
import pypdf
import logging

logger = logging.getLogger("investmind.parser")

def validate_isin(isin: str) -> bool:
    """
    Validates an Indian ISIN checksum using the standard ISO 6166 algorithm.
    Returns True if the check digit is valid, False otherwise.
    """
    if len(isin) != 12 or not isin.startswith("IN"):
        return False
        
    try:
        # Convert characters to digits
        digits_str = ""
        for char in isin[:-1]:
            if char.isdigit():
                digits_str += char
            elif char.isalpha():
                digits_str += str(ord(char.upper()) - ord('A') + 10)
            else:
                return False
                
        int_digits = [int(x) for x in digits_str]
        
        # Multiply alternate digits by 2, starting from the right-most digit of this converted string
        total_sum = 0
        multiply = True
        for d in reversed(int_digits):
            if multiply:
                prod = d * 2
                total_sum += sum(int(x) for x in str(prod))
            else:
                total_sum += d
            multiply = not multiply
            
        check_digit = (10 - (total_sum % 10)) % 10
        return check_digit == int(isin[-1])
    except Exception:
        return False

def parse_cas_pdf(pdf_bytes: bytes, password: str) -> list[dict]:
    """
    Parses a password-protected CAS PDF from a byte stream.
    Supports CAMS/Karvy mutual funds CAS via casparser library,
    and CDSL/NSDL equity CAS statements via a structured column row fallback.
    """
    holdings = []
    pdf_stream = None
    reader = None
    
    # 1. Attempt to parse using the official casparser library first (Mutual Funds)
    try:
        import casparser
        pdf_stream = io.BytesIO(pdf_bytes)
        data = casparser.read_cas_pdf(pdf_stream, password)
        
        for folio in data.get("folios", []):
            for scheme in folio.get("schemes", []):
                isin = scheme.get("isin")
                if isin and validate_isin(isin):
                    holdings.append({
                        "isin": isin,
                        "name": scheme.get("scheme"),
                        "quantity": float(scheme.get("close", 0.0))
                    })
        if holdings:
            logger.info(f"Successfully parsed mutual funds CAS via casparser library: {len(holdings)} holdings found.")
            return holdings
    except Exception as e:
        logger.info(f"casparser library bypassed or failed (likely equity CAS): {e}. Falling back to structured custom parser.")
    finally:
        if pdf_stream is not None:
            pdf_stream.close()

    # 2. Structured Custom Parser Fallback (Equity CAS - CDSL/NSDL)
    try:
        pdf_stream = io.BytesIO(pdf_bytes)
        reader = pypdf.PdfReader(pdf_stream)
        
        if reader.is_encrypted:
            logger.info("PDF is encrypted. Decrypting for custom parser...")
            decrypted = reader.decrypt(password)
            if decrypted == 0:
                raise ValueError("Incorrect password for CAS PDF.")
                
        # Match standard rows: ISIN (Group 1), Company Name (Group 2), Quantity (Group 3)
        # Allows for spaces and ignores subsequent rate/value columns on the row
        row_pattern = re.compile(
            r"\b(IN[A-Z0-9]{9}\d)\b\s+(.+?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\b"
        )
        
        for page in reader.pages:
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split("\n")
            for line in lines:
                match = row_pattern.search(line)
                if match:
                    isin = match.group(1)
                    if validate_isin(isin):
                        name = match.group(2).strip()
                        qty_str = match.group(3).replace(",", "")
                        quantity = float(qty_str)
                        
                        holdings.append({
                            "isin": isin,
                            "name": name,
                            "quantity": quantity
                        })
                        
        logger.info(f"Successfully extracted {len(holdings)} holdings via structured custom parser.")
    except Exception as e:
        logger.error(f"Error in structured custom parser: {e}")
        raise e
    finally:
        if pdf_stream is not None:
            pdf_stream.close()
            del pdf_stream
        if reader is not None:
            del reader
            
    return holdings
