from skills import EXTENDED_120_SKILLS

XP_PRECISION = 10

# Optional exact cumulative XP table for Invention.
# Index by level (e.g. index 0 => level 1 cumulative XP, index 119 => level 120).
INVENTION_XP_TABLE = [
    0,
    830,
    1861,
    2902,
    3980,
    5126,
    6390,
    7787,
    9400,
    11275,
    13605,
    16372,
    19656,
    23546,
    28138,
    33520,
    39809,
    47109,
    55535,
    64802,
    77190,
    90811,
    106221,
    123573,
    143025,
    164742,
    188893,
    215651,
    245196,
    277713,
    316311,
    358547,
    404634,
    454796,
    509259,
    568254,
    632019,
    700797,
    774834,
    854383,
    946227,
    1044569,
    1149696,
    1261903,
    1381488,
    1508756,
    1644015,
    1787581,
    1939773,
    2100917,
    2283490,
    2476369,
    2679907,
    2894505,
    3120508,
    3358307,
    3608290,
    3870846,
    4146374,
    4435275,
    4758122,
    5096111,
    5449685,
    5819299,
    6205407,
    6608473,
    7028964,
    7467354,
    7924122,
    8399751,
    8925664,
    9472665,
    10041285,
    10632061,
    11245538,
    11882262,
    12542789,
    13227679,
    13937496,
    14672812,
    15478994,
    16313404,
    17176661,
    18069395,
    18992239,
    19945833,
    20930821,
    21947856,
    22997593,
    24080695,
    25259906,
    26475754,
    27728955,
    29020233,
    30350318,
    31719944,
    33129852,
    34580790,
    36073511,
    37608773,
    39270442,
    40978509,
    42733789,
    44537107,
    46389643,
    48291180,
    50243611,
    52247435,
    54303504,
    56412678,
    58575823,
    60793812,
    63067521,
    65397835,
    67785643,
    70231841,
    72737330,
    75303019,
    77929820,
    80618654,
]


def _is_max_level(skill: str, level: int) -> bool:
    return level >= 120 or (level >= 99 and skill not in EXTENDED_120_SKILLS)


def _standard_xp(level: int) -> int:
    total = 0
    for i in range(1, level):
        total += int(i + 300 * (2 ** (i / 7.0)))
    return total // 4


def _invention_xp(level: int) -> int:
    idx = level - 1
    if 0 <= idx < len(INVENTION_XP_TABLE):
        return int(INVENTION_XP_TABLE[idx])
    # Fallback approximation until table is provided
    return int(36000000 * ((level / 99.0) ** 3.5))


def xp_to_next_level(skill: str, level: int, xp: int) -> int:
    if _is_max_level(skill, level):
        return 0

    normalized_xp = xp / XP_PRECISION
    if skill == "Invention":
        next_level_xp = _invention_xp(level + 1)
    else:
        next_level_xp = _standard_xp(level + 1)

    remaining = max(0.0, next_level_xp - normalized_xp)
    return int(round(remaining * XP_PRECISION))


def calculate_progress(skill: str, level: int, xp: int) -> float:
    normalized_xp = xp / XP_PRECISION

    # Handle max levels (120 caps vs 99 caps)
    if _is_max_level(skill, level):
        return 1.0

    if skill == "Invention":
        current_level_xp = _invention_xp(level)
        next_level_xp = _invention_xp(level + 1)
    else:
        current_level_xp = _standard_xp(level)
        next_level_xp = _standard_xp(level + 1)

    if normalized_xp >= next_level_xp or next_level_xp == current_level_xp:
        return 1.0

    progress = (normalized_xp - current_level_xp) / (next_level_xp - current_level_xp)
    return max(0.0, min(1.0, progress))
