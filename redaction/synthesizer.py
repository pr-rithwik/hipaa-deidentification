from faker import Faker
import random
import string
from datetime import timedelta
from dateutil import parser as dateparser

fake = Faker("en_IN")  # indian locale for more realistic names/addresses


def get_replacement(entity_type: str, original_text: str) -> str:
    """
    Generate a synthetic replacement for a given PHI span.
    Tried to keep replacements roughly the same length as original
    so the PDF layout doesn't break too badly.
    """
    generators = {
        "PERSON": _fake_person,
        "PHONE_NUMBER": _fake_phone,
        "EMAIL_ADDRESS": _fake_email,
        "LOCATION": _fake_location,
        "DATE_TIME": _fake_date,
        "URL": _fake_url,
        "ID": _fake_id,
        "AGE": _fake_age,
    }

    generator = generators.get(entity_type, _fake_generic)
    return generator(original_text)


def _fake_person(original: str) -> str:
    # preserve "Dr." prefix if present
    if original.strip().lower().startswith("dr.") or original.strip().lower().startswith("dr "):
        return "Dr. " + fake.last_name()
    return fake.name()


def _fake_phone(original: str) -> str:
    # try to preserve the format (with/without country code, separators)
    if original.startswith("+91"):
        return "+91" + str(random.randint(6000000000, 9999999999))
    if original.startswith("0") and len(original) > 10:
        # landline with STD
        std = original[:4]
        return std + str(random.randint(1000000, 9999999))
    # default 10 digit mobile
    return str(random.randint(6000000000, 9999999999))


def _fake_email(original: str) -> str:
    return fake.email()


def _fake_location(original: str) -> str:
    length = len(original)
    # random uppercase string same length as original
    k = max(5, length//2)
    return "".join(random.choices(string.ascii_uppercase, k=k))


def _fake_date(original: str) -> str:
    try:
        parsed = dateparser.parse(original, fuzzy=True)
        shift = timedelta(days=random.randint(1, 30))
        new_date = parsed + shift
        if "/" in original:
            result = new_date.strftime("%d/%m/%Y")
        else:
            result = new_date.strftime("%d %b %Y")
        # cap to original length to prevent overflow
        return result[:len(original)]
    except Exception:
        return "01 Jan 2000"[:len(original)]


def _fake_url(original: str) -> str:
    return "[REDACTED_URL]"


def _fake_id(original: str) -> str:
    # keep same length as original id
    length = len(original)
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def _fake_generic(original: str) -> str:
    return "[REDACTED]"

def _fake_age(original: str) -> str:
    # preserve the format - if original is "21 Years" keep "Years"
    suffix = "Years" if "year" in original.lower() else "Yrs"
    return f"{random.randint(25, 75)} {suffix}"