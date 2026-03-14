import abc
from typing import Optional, TypeVar, Union, Iterable, Generic, Any

from app.framework.data_access_layer.basic import EntityTypeVar
from app.framework.data_access_layer.db_result_generator import DBResultGenerator
from app.framework.data_access_layer.order_object.base import ABSOrderObject
from app.framework.data_access_layer.query_object.base import ABSQueryObject
from app.framework.domain.abs import IDTO, IEntity

ORMModel = TypeVar('ORMModel')
ISessionTypeVar = TypeVar('ISessionTypeVar')


class NoQueryBuilderRepositoryMixin:
    """
    Миксин для репозиториев, с методами конвертации
    """
    @abc.abstractmethod
    def _dto_to_orm(self, dto: Union[IDTO, IEntity]) -> ORMModel:
        """
        Конвертирует Доменный объект в ORM модель
        :param dto: Доменная доменный объект
        :return: ORM модель
        """


    @abc.abstractmethod
    def _orm_to_dto(self, orm_model: ORMModel) -> Union[IDTO, IEntity]:
        """
        Конвертирует ORM модель в Доменную сущность или Объект из хранилища, отвязанный от ORM
        :param orm_model: ORM модель которая должна быть сконвертированна
        :return: Заполненную сущность
        """

    @abc.abstractmethod
    def _qo_to_filter_params(self, filter_params: Optional[ABSQueryObject]) -> Any:
        """
        Конвертация объекта фильтрации в параметры, валидные для ORM или сырого запроса в базу
        :param filter_params: Заполненый объект параметров фильтрации
        :return: Любой тип данных, валидный для ORM или работы с хранилищем
        """


    @abc.abstractmethod
    def _oo_to_order_params(self, order_params: Optional[ABSOrderObject]) -> Any:
        """
        Конвертация объекта сортировки в параметры, валидные для ORM или сырого запроса в базу
        :param order_params: Заполненый объект c параметрами сортировки
        :return: Любой тип данных, валидный для ORM или работы с хранилищем
        """


class ABSRepository(abc.ABC, Generic[EntityTypeVar]):
    """
    Базовый репозиторий, от которого они наследуются
    """

    __slots__ = ('session', )

    def __init__(self, session: ISessionTypeVar):
        """
        :param session: Актуально для некоторых типов хранилищ или ORM
        """
        self.session = session

    @abc.abstractmethod
    def exists(self, filter_params: Optional[ABSQueryObject]) -> bool:
        """
        Проверка на существование записей в хранилище
        :param filter_params: Настроенные параметры фильтрации
        :return: Булево значение true или false
        """
        pass

    @abc.abstractmethod
    def count(self, filter_params: Optional[ABSQueryObject] = None) -> int:
        """
        Подсчет количества объектов в хранилище
        :param filter_params: Настроенные параметры фильтрации
        :return: Количество объектов в хранилище
        """

    @abc.abstractmethod
    def fetch_one(
            self,
            filter_params: Optional[ABSQueryObject] = None,
            order_params: Optional[ABSOrderObject] = None,
            raise_if_empty: bool = True
    ) -> Optional[EntityTypeVar]:
        """
        Получить один элемент из хранилища
        :param filter_params: Параметры фильтрации для выборки
        :param order_params: Параметры сортировки последовательности элементов
        :param raise_if_empty: Бросать ли исключение, если ни одного объекта не найдено
        :return: Один элемент
        :raise NotFoundException:
        """

    @abc.abstractmethod
    def fetch_many(
            self,
            filter_params: Optional[ABSQueryObject] = None,
            order_params: Optional[ABSOrderObject] = None,
            offset: int = 0,
            limit: Optional[int] = None,
            chunk_size: int = 1000) -> DBResultGenerator[EntityTypeVar]:
        """
        Получить несколько элементов из хранилища
        :param filter_params: Параметры фильтрации для выборки
        :param order_params: Параметры сортировки последовательности элементов
        :param offset: Смещение относительно начала элементов
        :param limit: Количество элементов в выборке
        :param chunk_size: Какое количество элементов за раз выбирать из хранилища
        :return: Генератор отдающий по одному значению
        """

    @abc.abstractmethod
    def add(self, domain_model: EntityTypeVar) -> None:
        """
        Сохранить один элемент в хранилище
        :param domain_model: Объект, на основе которого будет создана запись в хранилище
        :return: Ничего не возвращает, потому что не все хранилища поддерживают RETURNING
        """

    @abc.abstractmethod
    def add_many(self, domain_model_sequence: Iterable[EntityTypeVar]) -> None:
        """
        Добавить несколько записей в хранилище
        :param domain_model_sequence: Список сущностей, на основе которыхз будут созданы записи в базе
        :return:
        """
    @abc.abstractmethod
    def update_one(self, domain_model: EntityTypeVar) -> None:
        """
        Обновить одну запись
        :param domain_model: Объект, запись на основе которого нужно обновить
        :return: Ничего не возвращает, потому что не все хранилища поддерживают RETURNING
        """

    @abc.abstractmethod
    def update_many(self, domain_model: Iterable[EntityTypeVar]) -> None:
        """
        Обновить несколько записей в хранилище
        :param domain_model:
        :return: Ничего не возвращает, потому что не все хранилища поддерживают RETURNING
        """
