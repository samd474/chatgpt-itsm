# Impact / urgency (1 = critical, 2 = high, 3 = medium) -> priority P1..P4.
PRIORITY_MATRIX = {
    (1, 1): 1, (1, 2): 1, (1, 3): 2,
    (2, 1): 1, (2, 2): 2, (2, 3): 3,
    (3, 1): 2, (3, 2): 3, (3, 3): 4,
}


def calculate_priority(impact, urgency):
    return PRIORITY_MATRIX[(int(impact), int(urgency))]
