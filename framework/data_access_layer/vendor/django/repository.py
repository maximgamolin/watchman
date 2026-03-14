from abc import ABC
from typing import Iterable, Optional, Callable, Any

from app.exceptions.orm import NotFoundException
from app.framework.data_access_layer.basic import EntityTypeVar
from app.framework.data_access_layer.db_result_generator import DBResultGenerator
from app.framework.data_access_layer.order_object.base import ABSOrderObject
from app.framework.data_access_layer.order_object.values import ASC, DESC
from app.framework.data_access_layer.query_object.base import ABSQueryObject
from app.framework.data_access_layer.query_object.values import IN, GTE
from app.framework.data_access_layer.repository import ABSRepository, ORMModel, NoQueryBuilderRepositoryMixin
from app.framework.data_access_layer.values import Empty


class QoOrmMapperLine:
    """
    Хранит в себе настройку как конвертировать поле из ABSQueryObject в поле для фильтрации валидного для ORM

    Examples:
        >>> from app.framework.data_access_layer.query_object.base import ABSQueryObject
        >>> from dataclasses import dataclass
        >>> from typing import NewType
        >>>
        >>> SomeModelId = NewType('SomeModelId', int)
        >>>
        >>> @dataclass
        >>> class SomeQO(ABSQueryObject):
        >>>     some_model_id: SomeModelId
        >>>     some_string_value: str
        >>>
        >>> class DjangoDbModel:
        >>>     id = models.IntegerField(...)
        >>>     str_field = models.CharField(...)
        >>>
        >>> class DjangoDBModelRepository:
        >>>
        >>>     ...
        >>>
        >>>     @property
        >>>     def _qo_orm_fields_mapping(self) -> list[QoOrmMapperLine]:
        >>>         return [
        >>>             QoOrmMapperLine(orm_field_name='id',
        >>>                             qo_field_name='some_model_id',
        >>>                             modifier=int),
        >>>             QoOrmMapperLine(orm_field_name='str_field',
        >>>                             qo_field_name='some_string_value'),
        >>>         ]
        >>>
    """

    __slots__ = 'orm_field_name', 'qo_field_name', 'modifier'

    def __init__(self, orm_field_name: str, qo_field_name: str, modifier: Optional[Callable[[Any], Any]] = None):
        """
        :param orm_field_name: Название поля в ORM модели
        :param qo_field_name: Название поля в QueryObject
        :param modifier: Функция - модификатор, которая может конвертировать значение
            в валидное значение для фильтрации
        """
        self.orm_field_name = orm_field_name
        self.qo_field_name = qo_field_name
        self.modifier = modifier or (lambda x: x)


class OoOrmMapperLine:
    """
    Хранит в себе настройку, как конвертировать поле из ABSOrderObject в поле для сортировки ORM model

    Examples:
        >>> from app.framework.data_access_layer.order_object.base import ABSOrderObject
        >>> from dataclasses import dataclass
        >>> from datetime import datetime
        >>> from typing import NewType
        >>>
        >>> SomeModelId = NewType('SomeModelId', int)
        >>>
        >>> @dataclass
        >>> class SomeOO(ABSOrderObject):
        >>>     created_at: datetime
        >>>
        >>> class DjangoDbModel:
        >>>     created_at = models.DatetimeField(...)
        >>>
        >>> class DjangoDBModelRepository:
        >>>
        >>>     ...
        >>>
        >>>     @property
        >>>     def _oo_orm_fields_mapping(self) -> list[OoOrmMapperLine]:
        >>>         return [
        >>>             OoOrmMapperLine(orm_field_name='created_at',
        >>>                             oo_field_name='created_at')
        >>>         ]
        >>>
    """

    __slots__ = 'orm_field_name', 'oo_field_name'

    def __init__(self, orm_field_name: str, oo_field_name: str):
        self.orm_field_name = orm_field_name
        self.oo_field_name = oo_field_name


class DjangoNoQueryBuilderRepositoryMixin(NoQueryBuilderRepositoryMixin, ABC):
    """
    Миксин, который добавляет возможность простой конвертации полей ABSQueryObject и ABSOrderObject в поля ORM модели
    """

    @property
    def _qo_orm_fields_mapping(self) -> list[QoOrmMapperLine]:
        """
        Описываются правила конвертации ABSQueryObject -> ORM model, подробности в примерах QoOrmMapperLine
        :return: Список настроенных QoOrmMapperLine
        """
        raise NotImplementedError()

    @property
    def _oo_orm_fields_mapping(self) -> list[OoOrmMapperLine]:
        """
        Описываются правила конвертации ABSOrderObject -> ORM model, подробности в примерах OoOrmMapperLine
        :return: Список настроенных OoOrmMapperLine
        """
        raise NotImplementedError()

    def _extract_filter_val_for_orm(self, mapper_line: QoOrmMapperLine, val) -> dict:
        """
        Переводит специальные типы GTE, IN и тд в подходящие для orm
        :param mapper_line:
        :param val: значение из ABSQueryObject
        :return: словарь где в ключе название поля из orm, а в значении, значение поля валидное для django orm
        """
        if isinstance(val, IN):
            orm_query_param_name = f'{mapper_line.orm_field_name}__in'
            value = [mapper_line.modifier(i) for i in val.value]
        elif isinstance(val, GTE):
            orm_query_param_name = f'{mapper_line.orm_field_name}__gte'
            value = mapper_line.modifier(val.value)
        else:
            orm_query_param_name = mapper_line.orm_field_name
            value = mapper_line.modifier(val)
        return {orm_query_param_name: value}


    def _qo_to_filter_params(self, filter_params: Optional[ABSQueryObject]) -> dict:
        """
        Конвертация ABSQueryObject валидный для ORM объект
        :param filter_params: Заполненный объект фильтрации
        :return: Словарь, который можно вставить в django orm .filter()
        """
        if not filter_params:
            return {}
        filter_params_for_orm = {}
        for mapper_line in self._qo_orm_fields_mapping:
            field_val = getattr(filter_params, mapper_line.qo_field_name)  # TODO хрупко и непонятно упадет
            if field_val is Empty():
                continue
            filter_params_for_orm.update(
                self._extract_filter_val_for_orm(mapper_line, field_val)
            )
        return filter_params_for_orm

    def _extract_order_values_to_orm(self, mapper_line: OoOrmMapperLine, val) -> str:
        """
        Переводит конкретное поле ABSOrderObject в поле ORM
        :param mapper_line:
        :param val: Значение из ABSOrderObject
        :return:
        """
        if isinstance(val, ASC):
            return mapper_line.orm_field_name
        if isinstance(val, DESC):
            return f'-{mapper_line.orm_field_name}'

    def _oo_to_order_params(self, order_params: Optional[ABSOrderObject]) -> list:
        """
        Переработка ABSOrderObject в валидный список параметров сортировки для django orm .order_by()
        :param order_params:
        :return: список параметров сортировки, валидный для django
        """
        if not order_params:
            return []
        order_params_for_orm = []
        for mapper_line in self._oo_orm_fields_mapping:
            field_val = getattr(order_params, mapper_line.oo_field_name)
            if field_val is Empty():
                continue
            order_params_for_orm.append(self._extract_order_values_to_orm(mapper_line, field_val))
        return order_params_for_orm


class DjangoRepository(ABSRepository, DjangoNoQueryBuilderRepositoryMixin, ABC):
    """
    Репозиторий подходящий для django моделей

    Examples:
        >>> class UserRepository(DjangoRepository):
        >>>     model = CustomUser
        >>>     def _orm_to_dto(self, orm_model: CustomUser) -> User:
        >>>         return User(
        >>>             user_id=UserID(orm_model.id)
        >>>         )
        >>>
        >>>     @property
        >>>     def _qo_orm_fields_mapping(self) -> list[QoOrmMapperLine]:
        >>>         return [
        >>>             QoOrmMapperLine(
        >>>                 qo_field_name='user_id',
        >>>                 orm_field_name='id',
        >>>                 modifier=int
        >>>             )
        >>>
        >>>     @property
        >>>     def _oo_orm_fields_mapping(self) -> list[OoOrmMapperLine]:
        >>>         return []
    """

    model: ORMModel = None

    def exists(self, filter_params: Optional[ABSQueryObject]) -> bool:
        pass

    def count(self, filter_params: Optional[ABSQueryObject] = None) -> int:
        pass

    def fetch_one(
            self,
            filter_params: Optional[ABSQueryObject] = None,
            order_params: Optional[ABSOrderObject] = None,
            raise_if_empty: bool = True
    ) -> Optional[EntityTypeVar] | NotFoundException:
        if filter_params:
            filter_params_for_orm = self._qo_to_filter_params(filter_params)
        else:
            filter_params_for_orm = {}
        if order_params:
            order_params_for_orm = self._oo_to_order_params(order_params)
        else:
            order_params_for_orm = []
        orm_chan = self.model.objects.filter(
            **filter_params_for_orm
        ).order_by(
            *order_params_for_orm
        ).first()
        if not orm_chan:
            return
        return self._orm_to_dto(orm_chan)

    def fetch_many(
            self,
            filter_params: Optional[ABSQueryObject] = None,
            order_params: Optional[ABSOrderObject] = None,
            offset: int = 0,
            limit: Optional[int] = None,
            chunk_size: int = 1000
    ) -> DBResultGenerator[EntityTypeVar]:
        orm_ideas = self.model.objects
        if filter_params:
            filter_params_for_orm = self._qo_to_filter_params(filter_params)
            orm_ideas = orm_ideas.filter(**filter_params_for_orm)

        if order_params:
            order_params_for_orm = self._oo_to_order_params(order_params)
            orm_ideas = orm_ideas.order_by(*order_params_for_orm)

        orm_ideas.iterator(chunk_size=chunk_size)
        return DBResultGenerator((self._orm_to_dto(i) for i in orm_ideas))

    def add(self, domain_model: EntityTypeVar) -> None:
        pass

    def update_one(self, domain_model: EntityTypeVar) -> None:
        pass

    def add_many(self, domain_model_sequence: Iterable[EntityTypeVar]) -> None:
        self.model.objects.bulk_create(
            tuple(self._dto_to_orm(i) for i in domain_model_sequence)
        )

    def update_many(self, domain_model: Iterable[EntityTypeVar]) -> None:
        pass