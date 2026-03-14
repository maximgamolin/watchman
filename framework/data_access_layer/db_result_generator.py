from itertools import chain
from typing import Generator, Generic, TypeVar

T = TypeVar('T')


class DBResultGenerator(Generic[T]):
    """
    Генератор с возможностью кеширования каждого элемента.
    Можно сбросить его позицию, тогда значения будут передаваться снова с начала,
    но уже из кеша самого генератора. Если сброс позиции произошел раньше,
    чем закончился генератор переданный в DBResultGenerator, то по исчерпанию значений в кеше,
    значения снова будут браться из переданного генератора, до тех пор, пока он не исчерпает себя.

    Example:
        >>>
        >>> def some_generator_method():
        >>>     return DBResultGenerator((i for i in range(0, 100)))
        >>>
        >>> def more_complex_generator():
        >>>     ...
        >>>     for i in range(0, 100):
        >>>         yield i
        >>>
        >>> generator = DBResultGenerator(more_complex_generator())
    """

    def __init__(self, db_generator: Generator):
        self._db_generator = db_generator
        self._cache: list[T] = []
        self._position = 1
        self._is_finished = False

    def drop_position(self) -> None:
        """
        Сбрасывает позицию в DBResultGenerator, если исходный генератор не исчерпан,
        сперва кеш, а потом исходный генератор
        """
        self._position = 1
        if self._is_finished:
            self._db_generator = iter(self._cache)
        else:
            self._db_generator = chain(self._cache, self._db_generator)

    def _add_value_to_cache(self, value):
        """
        Добавляет значение в кеш, по этому элементу исходного генератора еще не проходились
        :param value:
        :return:
        """
        if self._position > len(self._cache) and not self._is_finished:
            self._cache.append(value)
        self._position += 1

    def __iter__(self):
        return self

    def __next__(self) -> T:
        try:
            result = next(self._db_generator)
        except StopIteration as e:
            self._is_finished = True
            raise e
        self._add_value_to_cache(result)
        return result