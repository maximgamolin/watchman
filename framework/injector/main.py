import os
from importlib import import_module
from warnings import warn

import yaml


class ClassDoesNotExists(Exception):
    pass


class ClassExists(Exception):
    pass


class InjectorLine:
    """
    Утилитарный класс, который разбирает строку пути до класса из yaml файла
    """
    def __init__(self, path):
        self.path = path

    def module(self) -> str:
        """
        :return: модуль из строки пути
        """
        return '.'.join(self.path.split('.')[:-1])

    def class_name(self) -> str:
        """
        :return: имя класса из строки пути
        """
        return self.path.split('.')[-1]


class InjectorStorage:
    """
    Хранилище ссылок на классы, которые можно будет инжектить.
    Настройки хранятся в yaml файле, путь до которого указывается в переменной окружения 'INJECTION_CFG_PATH'
    Пример yaml файла
    injections:
      repo:
        - name: IdeaRepository
          path: app.dal.idea_exchange.repo.IdeaRepository
        - name: ChainRepository
          path: app.dal.idea_exchange.repo.ChainRepository

    Как инжектить, можно посмотреть в функции inject
    """
    def __new__(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = super(InjectorStorage, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        TODO прикрутить неймспейсы вместо тупого извлечения параметров
        """
        self.map: dict[str: InjectorLine] = {}
        try:
            config_path = os.environ['INJECTION_CFG_PATH']
        except KeyError:
            warn('INJECTION_CFG_PATH in environ is not set')
            return
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        for i in cfg['injections']['repo']:
            name = i['name']
            path = i['path']
            if name in self.map:
                raise ClassExists(f'Class for {name} was registered')
            self.map[name] = InjectorLine(path)

    def fetch_resource(self, name: str):
        """
        Получить класс по имени класса обозначенного в yaml классе
        :param name:
        :return:
        """
        if name not in self.map:
            raise ClassDoesNotExists(f'Class for {name} is not registered')
        return self.map[name]


class Wrapper:
    """
    Ленивая обертка, которая возвращает класс при ее вызове
    """

    def __init__(self, name: str):
        self.name = name

    def __call__(self, *args, **kwargs):
        storage = InjectorStorage()
        line = storage.fetch_resource(self.name)
        module = import_module(line.module())
        klass = getattr(module, line.class_name())
        return klass(*args, **kwargs)


def inject(name: str):
    """
    Инжектор зависимости, названия взяты из примера про yml файлы

    >>> class IdeaUOW:
    >>>
    >>>     def __init__(
    >>>         self,
    >>>         idea_repo_cls: Type[ABSRepository] = inject('IdeaRepository'),
    >>>         chain_repo_cls: Type[ABSRepository] = inject('ChainRepository')
    >>>         ):
    >>>         self._idea_repo = idea_repo_cls()
    >>>         self._chain_repo = chain_repo_cls()

    :param name: назвние класса обозначенное в секции name в файле с настройками yml
    :return:
    """
    return Wrapper(name)


s = InjectorStorage()



