from typing import Callable, TypeVar, Generic, Union, Generator, Any

from app.framework.data_access_layer.db_result_generator import DBResultGenerator

T = TypeVar('T')


class LazyWrapper(Generic[T]):
    """
    Обертка для ленивого извлечения полей бизнес сущности из хранилища,
    на вход принимает метод и параметры для этого метода

    Example:
        >>> from app.framework.data_access_layer.query_object.base import ABSQueryObject
        >>> from dataclasses import dataclass
        >>>
        >>>
        >>> @dataclass
        >>> class DomainEntityQO(ABSQueryObject):
        >>>     id: int
        >>>
        >>>
        >>> class Builder:
        >>>     def _build_domain_entity(self, domain_entity_qo: DomainEntityQO) -> Any:
        >>>         ...
        >>>
        >>>     def build_domain_entity(self, domain_entity_qo: DomainEntityQO) -> Any:
        >>>         return LazyWrapper(
        >>>             method=self._build_domain_entity,
        >>>             params={'domain_entity_qo': domain_entity_qo}
        >>>         )
        >>>
    """
    
    def __init__(self, method: Callable, params: dict) -> None:
        self._method = method
        self._params = params
    
    def fetch(self) -> Any:
        """
        Выполнить метод и извлечь данные из хранилища или выполнить сборку с помощью билдера
        :return: Доменную сущность/агрегат/объект-значение
        """
        return self._method(**self._params)


class LazyLoaderInEntity(Generic[T]):
    """
    Дескриптор для поля сущности, которое может лениво вычисляться.
    Помимо вычисления результата, умеет так же его кешировать,
    чтобы повторно не обращаться к базе

    Example:
        >>> from typing import Union
        >>>
        >>>
        >>> class SomeDomainEntity:
        >>>     pass
        >>>
        >>> class DomainAggregate:
        >>>     field: LazyLoaderInEntity[SomeDomainEntity] = LazyLoaderInEntity
        >>>
        >>>     def __init__(self, field: Union[SomeDomainEntity, LazyWrapper[SomeDomainEntity]]):
        >>>         self.field = field
        >>>
    """
    
    def __set_name__(self, owner, name: str):
        self.public_name = name
        self.private_name = '_lazy_wrapper_' + name
        self.cached_name = '_lazy_wrapper_cache_' + name

    def _process_lasy_wrapper(self, obj, value: LazyWrapper[T]) -> T:
        """
        Метод обработки, если поле в сущности передано как LazyWrapper.
        Так же кеширует результат из LazyWrapper.
        Так же генератор не может быть валидным результатом из LazyWrapper,
        потому что при повторном обращении к нему, генератор будет уже пустым,
        по этому, для последовательностей нужно использовать DBResultGenerator

        :param obj: доменный объект, у которого прописано поле как LazyLoaderInEntity
        :param value: LazyWrapper внутри поля
        :return: Либо вычисление LazyWrapper, либо результат кеширования от предыдущего вычисления LazyWrapper
        """
        if not hasattr(obj, self.cached_name):
            new_value = value.fetch()
            if isinstance(new_value, Generator):
                raise Exception('Generators are not allowed, use DBResultGenerator')
            setattr(obj, self.cached_name, new_value)
        else:
            new_value = getattr(obj, self.cached_name)
            if isinstance(new_value, DBResultGenerator):
                new_value.drop_position()
        return new_value

    def __get__(self, obj, type=None) -> T:
        """
        При попытке получить значение поля, если это LazyWrapper, произойдет его вычисление
        """
        if not hasattr(obj, self.private_name):
            raise Exception(
                f"Field '{self.public_name}' not exists in {obj}, also check '{self.private_name}' in object in runtime"
            )
        value = getattr(obj, self.private_name)
        if isinstance(value, LazyWrapper):
            return self._process_lasy_wrapper(obj, value)
        return value

    def __set__(self, obj: Union[LazyWrapper[T]|T|None], value) -> None:
        setattr(obj, self.private_name, value)

