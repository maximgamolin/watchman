class GroupMemberNotFound(Exception):
    """Участник группы не найден в базе данных."""


class GroupMemberAlreadyExists(Exception):
    """Участник группы уже существует в базе данных."""


class OptimisticLockError(Exception):
    """
    Оптимистичная блокировка: версия сущности в БД изменилась с момента последнего SELECT.
    Другой поток успел сохранить изменения раньше — текущая операция отклоняется.
    """
