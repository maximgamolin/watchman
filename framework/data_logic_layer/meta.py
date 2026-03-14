from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any


@dataclass
class BaseMeta:
    """
    Дополнительная информация из хранилища, помещаемая в сущность
    """
    id_from_storage: Optional[Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: Optional[int] = None
    is_deleted: bool = False
    is_changed: bool = False


class MetaManipulation:
    """
    Класс отвечающий за работу с доп информацией из хранилища, находящейся в сущности/агрегате
    """

    _meta: BaseMeta

    def update_meta(self, new_meta: BaseMeta):
        """
        Обновить метаинформацию
        :param new_meta:
        :return:
        """
        self._meta = new_meta

    def replace_id_from_meta(self):
        raise NotImplementedError()

    def mark_deleted(self):
        """
        Пометить сущность как удаленную
        :return:
        """
        self._meta.is_deleted = True

    def mark_changed(self):
        """
        Пометить сущность как измененную
        :return:
        """
        self._meta.is_changed = True

    def is_deleted(self) -> bool:
        """
        Проверить, помечена ли сущность как удаленная
        :return:
        """
        return self._meta.is_deleted

    def is_changed(self) -> bool:
        """
        Проверить, помечена ли сущность как измененная
        :return:
        """
        return self._meta.is_changed

    def is_new(self) -> bool:
        """
        Проверить, является ли сущность новой
        :return:
        """
        return self._meta.id_from_storage is None

    def get_created_at(self) -> Optional[datetime]:
        """
        Получить дату создания
        :return:
        """
        return self._meta.created_at

    def set_created_at(self, created_at: datetime):
        """
        Установить дату создания
        :param created_at:
        :return:
        """
        self._meta.created_at = created_at

    def set_created_at_as_now(self):
        """
        Установить дату создания как текущую
        :return:
        """
        self.set_created_at(datetime.now())

    def set_updated_at(self, updated_at: datetime):
        """
        Установить дату обновления
        :param updated_at:
        :return:
        """
        self._meta.updated_at = updated_at

    def get_updated_at(self) -> Optional[datetime]:
        """
        Получить дату обновления
        :return:
        """
        return self._meta.updated_at

    def set_updated_at_as_now(self):
        """
        Установить дату обновления как текущую
        :return:
        """
        self.set_updated_at(datetime.now())

    def get_version(self) -> Optional[int]:
        """
        Получить текущую версию сущности для оптимистичной блокировки.
        None — сущность новая, версия ещё не присвоена хранилищем.
        :return:
        """
        return self._meta.version

    def set_version(self, version: int) -> None:
        """
        Установить версию сущности (вызывается Builder-ом после загрузки из хранилища).
        :param version:
        :return:
        """
        self._meta.version = version
