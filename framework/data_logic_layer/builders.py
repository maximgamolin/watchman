from typing import TypeVar, Generic, Iterable

from app.framework.data_access_layer.lazy import LazyWrapper

T = TypeVar('T')

class ABSEntityFromRepoBuilder(Generic[T]):
    """
    Билдер собирать сущности и агрегаты извлекаемые из хранилища
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__()
    def build_lazy_one(self) -> LazyWrapper[T]:
        """
        Подготовить ленивое извлечение одной сущности
        :return: настроенный LazyWrapper
        """
        raise NotImplementedError
    
    def build_lazy_many(self) -> LazyWrapper[Iterable[T]]:
        """
        Подготовить ленивое извлечение последовательности сущностей
        :return: настроенный LazyWrapper
        """
        raise NotImplementedError
    
    def build_one(self) -> T:
        """
        Собрать и вернуть сущность
        :return:
        """
        raise NotImplementedError
    
    def build_many(self) -> Iterable[T]:
        """
        Собрать и вернуть
        :return:
        """
        raise NotImplementedError
