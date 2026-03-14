class BaseUnitOfWork:
    """
    Базовый UOW, работает по принципу дескриптора, при выходе из которого откатывается все, что не закоммичено
    Содержит в себе знания о способе конвертации (либо ссылки на BaseEntityFromRepoBuilder либо функция фнутри UOW)
    Содержит в себе специфичные выборки под конкретный кейс. Может быть более одного UOW принадлежащего разным агрегатам

    """
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.rollback()

    def rollback(self):
        """
        Откатить все изменения
        :return:
        """
        pass

    def commit(self):
        """
        Закоммитить все изменения в хранилища
        :return:
        """
        pass
