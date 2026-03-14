from abc import ABC

class OrderParamComparison(ABC):
    """
    Базовый класс для управления параметрами сортировки, используется только с ABSOrderObject
    """


class ASC(OrderParamComparison):
    """
    Прямой порядок сортировки (по возрастанию), от меньшего к большему
    """


class DESC(OrderParamComparison):
    """
    Обратный порядок сортировки (по убыванию), от большего к меньшему
    """
