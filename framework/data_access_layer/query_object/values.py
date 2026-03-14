from abc import ABC
from typing import TypeVar, Generic

T = TypeVar('T')




class QueryParamComparison(ABC, Generic[T]):
    """
    Базовый класс для управления параметрами фильтрации, используется только с ABSOrderObject
    """
    def __init__(self, value: T):
        self.value = value


class GTE(QueryParamComparison[T]):
    """
    Эквивалент <=
    """


class IN(QueryParamComparison[T]):
    """
    Для проверки элементов в списке
    """
