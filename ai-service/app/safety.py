import re
def mask(text):
    text = re.sub(r'(?<!\d)(?:\d[ -]?){13,19}(?!\d)', '[REDACTED_CARD]', str(text))
    text = re.sub(r'(?<!\d)(?:\+91[ -]?)?([6-9]\d{9})(?!\d)', lambda m: '******'+m[1][-4:], text)
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[REDACTED_EMAIL]', text)
    text = re.sub(r'(?i)\b(cvv|pin|otp|password|bank account|government id|aadhaar|health details)\s*(?:is|:|=)?\s*[^,;.\n]+', r'\1 [REDACTED]', text)
    return text
def safe_tree(value):
    if isinstance(value, str): return mask(value)
    if isinstance(value, list): return [safe_tree(v) for v in value]
    if isinstance(value, dict):
        machine_fields={'id','source_id','source_hash','sha256','checksum','reference','filename','version','file','sku','store_id','vendor_id','receipt_id','return_id','case_id','employee_id'}
        return {k:(v if k in machine_fields else safe_tree(v)) for k,v in value.items()}
    return value
def restricted(text):
    return bool(re.search(r'(?i)(ignore (?:all |previous |prior )?instructions|reveal.*(?:prompt|test case)|hidden judge|bypass.*(?:rules|safety|auth)|invent a policy|do not cite|(?:show|give|print|reveal|access|list|export|tell|share|send|retrieve|dump|display|provide).{0,80}(?:card numbers|cvv|payment tokens|passwords?|credentials|customer database|private.*records|employee records|supplier.*pric|contract))', text))
def export_cell(value):
    text = str(value)
    return "'"+text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else text
