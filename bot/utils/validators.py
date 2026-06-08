import re


def validate_name(name: str) -> bool:
    name = name.strip()
    if len(name) < 2 or len(name) > 50:
        return False
    return bool(re.match(r'^[a-zA-Zа-яА-ЯёЁ0-9\s\-]+$', name))


def validate_age(age: str) -> bool:
    try:
        age_num = int(age)
        return 14 <= age_num <= 99
    except ValueError:
        return False
