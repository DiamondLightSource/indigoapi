from collections.abc import Sequence

import numpy as np

from indigoapi.analyses.decorator import analysis


@analysis("double")
def double(number: float | int) -> float:

    return number * 2


@analysis("sum")
def sum_numbers(numbers: Sequence[float | int]) -> float:

    return np.sum(numbers)
