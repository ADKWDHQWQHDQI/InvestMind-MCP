import io
import re
import pypdf
import logging

logger = logging.getLogger("investmind.parser")

def parse_cas_pdf(pdf_bytes: bytes, password: str) -> list[dict]:
    """
    Parses a password-protected CAS PDF from a byte stream.
    Decrypts the PDF in memory and extracts holdings using regular expressions.
    Returns a list of raw holding dictionaries.
    """
    holdings = []
    pdf_stream = None
    reader = None
    
    try:
        # Wrap bytes in BytesIO to keep it entirely in memory (RAM-only)
        pdf_stream = io.BytesIO(pdf_bytes)
        reader = pypdf.PdfReader(pdf_stream)
        
        if reader.is_encrypted:
            logger.info("PDF is encrypted. Attempting to decrypt...")
            decrypted = reader.decrypt(password)
            if decrypted == 0:
                logger.error("Failed to decrypt PDF. Incorrect password.")
                raise ValueError("Incorrect password for CAS PDF.")
            logger.info("PDF decrypted successfully.")

        # Regex for Indian ISIN: starts with 'IN', followed by 9 alphanumeric chars, and a check digit (12 chars total)
        isin_pattern = re.compile(r"\b(IN[A-Z0-9]{9}\d)\b")
        
        # Parse text page by page
        for page in reader.pages:
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split("\n")
            for line in lines:
                isin_match = isin_pattern.search(line)
                if isin_match:
                    isin = isin_match.group(1)
                    parts = line.strip().split()
                    
                    try:
                        isin_idx = parts.index(isin)
                    except ValueError:
                        continue
                    
                    # Find all numbers in the line to identify units/quantities
                    numbers = []
                    for p in parts:
                        clean_p = p.replace(",", "")
                        # Matches integers and decimals
                        if re.match(r"^\d+(\.\d+)?$", clean_p):
                            numbers.append(float(clean_p))
                    
                    quantity = 0.0
                    if numbers:
                        # Usually, units/quantity appear after the ISIN in a row
                        post_isin_parts = parts[isin_idx+1:]
                        post_isin_numbers = []
                        for p in post_isin_parts:
                            clean_p = p.replace(",", "")
                            if re.match(r"^\d+(\.\d+)?$", clean_p):
                                post_isin_numbers.append(float(clean_p))
                        
                        if post_isin_numbers:
                            quantity = post_isin_numbers[0]  # First number after ISIN is typically the quantity
                        else:
                            quantity = numbers[-1]  # Fallback to the last number in the line
                            
                    # Company/Security Name is what remains after stripping the ISIN and numbers
                    company_parts = []
                    for p in parts:
                        if p == isin:
                            continue
                        clean_p = p.replace(",", "")
                        if re.match(r"^\d+(\.\d+)?$", clean_p):
                            continue
                        company_parts.append(p)
                        
                    company_name = " ".join(company_parts).strip()
                    
                    holdings.append({
                        "isin": isin,
                        "name": company_name,
                        "quantity": quantity,
                    })
                    
        logger.info(f"Successfully extracted {len(holdings)} raw holdings from CAS.")
    except Exception as e:
        logger.error(f"Error parsing CAS PDF: {e}")
        raise e
    finally:
        # Explicitly clean up to avoid holding decrypted PDF data in memory
        if pdf_stream is not None:
            pdf_stream.close()
            del pdf_stream
        if reader is not None:
            del reader
            
    return holdings
