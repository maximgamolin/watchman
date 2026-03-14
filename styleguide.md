# Style Guide: Архитектура, классы, функции

Эталон — проект `sz`. Документ совмещает описание слоёв архитектуры,
морфемы классов и морфемы функций в единое руководство с примерами.

---

## Содержание

1. [Принципы](#принципы)
2. [Структура директорий](#структура-директорий)
3. [Слои архитектуры](#слои-архитектуры)
4. [Морфемы классов](#морфемы-классов)
5. [Морфемы функций и методов](#морфемы-функций-и-методов)
6. [Правила зависимостей](#правила-зависимостей)
7. [Поток выполнения](#поток-выполнения)
8. [Логирование](#логирование)
9. [Тестирование](#тестирование)
10. [Сводные таблицы](#сводные-таблицы)

---

## Принципы

- **Один слой — одна ответственность.** Не смешивать доменную логику с инфраструктурой.
- **Морфема = ответственность.** Имя класса/функции сразу говорит, что он делает и к какому слою относится.
- **Вычисления отдельно от последовательностей.** Функция либо считает, либо оркестрирует вызовы — не оба разом.
- **Бизнес-правила требуют комментариев.** Бизнес-логика непрозрачна для разработчика — всегда объясняй, что и почему.
- **Тестируемость — первый класс.** Классы без внешних зависимостей тестируются без моков; с зависимостями — получают их через конструктор.
- **Логируй все внешние вызовы.** До и после каждого обращения к внешнему хранилищу/сервису.
- **Не изобретай синонимы.** Каждому понятию предметной области — одно английское слово; зафиксировать в глоссарии.

---

## Структура директорий

```
app/
├── framework/                  # Базовые абстракции (переиспользуются проектом)
│   ├── domain/
│   │   └── abs.py              # IEntity, IAggregate, IDTO
│   ├── data_logic_layer/
│   │   ├── uow.py              # BaseUnitOfWork
│   │   ├── builders.py         # ABSEntityFromRepoBuilder
│   │   └── meta.py             # BaseMeta, MetaManipulation
│   ├── data_access_layer/
│   │   ├── repository.py       # ABSRepository
│   │   ├── lazy.py             # LazyWrapper, LazyLoaderInEntity
│   │   ├── db_result_generator.py
│   │   ├── query_object/       # ABSQueryObject, QueryParamComparison, GTE, IN
│   │   ├── order_object/       # ABSOrderObject, ASC, DESC
│   │   └── vendor/django/
│   │       └── repository.py   # DjangoRepository, QoOrmMapperLine
│   └── mapper.py               # ABSMapper
│
├── domain/                     # Бизнес-модель (Entity, ValueObject)
│   └── <domain>/
│       ├── main.py             # Сущности и агрегаты
│       └── types.py            # NewType-значения (ChainID, IdeaID, ...)
│
├── dal/                        # Data Access Layer
│   └── <domain>/
│       ├── repo.py             # *Repository
│       ├── mapper.py           # *Mapper
│       ├── qo.py               # *QO (QueryObject)
│       ├── oo.py               # *OO (OrderObject)
│       └── dto.py              # *DalDto
│
├── dll/                        # Data Logic Layer
│   └── <domain>/
│       ├── uow.py              # *UOW
│       └── builders.py         # *Builder
│
├── cases/                      # Связующий слой (Use Cases)
│   └── <domain>/
│       ├── <entity>.py         # *Case
│       └── dto.py              # *UiDto, *UoDto
│
├── exceptions/                 # Доменные и прикладные исключения
│   └── <domain>.py
│
└── tests/
    ├── factories/
    │   └── <domain>.py         # *Factory
    └── fakes/
        └── dll/
            └── uow.py          # Fake*UOW
```

**ORM-модели** живут в Django-приложениях рядом с миграциями:

```
<django_app>/
├── models.py                   # Django ORM (Модель хранения данных)
└── migrations/
```

---

## Слои архитектуры

Архитектура делится на две оси:

- **Горизонтальная (слева направо)** — интерфейсная сторона: от внешнего мира до бизнес-кейса
- **Вертикальная (сверху вниз)** — глубина: от ядра домена до физического хранилища

```
┌────────────────────┬──────────────────────────┬───────────────┬──────────────────────────────┐
│ Модель общения     │ Логика обработки общения │ Связующий     │ Бизнес модель                │
│ с внешним миром    │ с внешним миром          │ слой          ├──────────────────────────────┤
│  *UiDto / *UoDto   │  (внутри *Case)          │  *Case        │ Entity / ValueObject         │
│  cases/*/dto.py    │                          │  cases/*/     ├──────────────────────────────┤
│                    │                          │               │ Бизнес логика                │
│                    │                          │               │ методы Entity + *Case        │
│                    │                          │               ├──────────────────────────────┤
│                    │                          │               │ Логика чтения и записи       │
│                    │                          │               │ *UOW + *Builder  (dll/)      │
│                    │                          │               ├──────────────────────────────┤
│                    │                          │               │ Логика доступа к данным      │
│                    │                          │               │ *Repository  (dal/)          │
│                    │                          │               ├──────────────────────────────┤
│                    │                          │               │ Модель хранения данных       │
│                    │                          │               │ Django models + *Mapper      │
└────────────────────┴──────────────────────────┴───────────────┴──────────────────────────────┘
```

### Модель общения с внешним миром (`*UiDto` / `*UoDto`)

Контракты сервиса: входящие и исходящие сообщения в виде Python dataclass.
Покрывает два сценария:
- API-запрос/ответ (HTTP, WebSocket, RPC)
- Сообщение из шины событий (Kafka, RabbitMQ и т.д.)

```python
# cases/idea_exchange/dto.py

@dataclass
class IdeaUiDto:          # Входные данные от пользователя
    name: str
    body: str
    chain_id: int

@dataclass
class IdeaUoDto:          # Исходящие данные пользователю
    idea_id: int
    name: str
    body: str
    is_accepted: bool
    idea_uid: str
    chain_links: list[IdeaChainLinkUoDto]
```

### Логика обработки общения с внешним миром (внутри `*Case`)

Отвечает за:
- Конвертацию сырых данных (JSON) в `*UiDto` с проверкой **базовых типов**
- Простые ограничения, видные из входных данных (длина строки, диапазон числа)
- Формирование `*UoDto` из результата бизнес-логики

**Не включает** бизнес-проверки — уникальность, права, лимиты — это зона `Entity` и `*Case`.

### Связующий слой (`*Case`)

Инициируется при поступлении запроса. Оркестрирует один бизнес-кейс:
принимает `*UiDto` → готовит агрегаты через UOW → вызывает методы Entity → сохраняет → возвращает `*UoDto`.

```python
# cases/idea_exchange/idea.py

class IdeaCase:
    def __init__(self, uow_cls: Type[IdeaUOW] = IdeaUOW):
        self.idea_uow = uow_cls()

    def create_idea(self, user_id: int, body: str, chain_id: int, name: str) -> Idea:
        with self.idea_uow:
            author = self.idea_uow.fetch_author(author_id=UserID(user_id))
            chain = self.idea_uow.fetch_chain(chain_id=ChainID(chain_id))
            idea = Idea.initialize_new_idea(
                body=body, author=author, chain=chain, name=name,
            )
            idea.set_created_at_as_now()
            self.idea_uow.add_idea_for_save(idea=idea)
            self.idea_uow.commit()
            return idea

    def edit_idea(self, user_id: int, idea_id: int, body: str) -> None:
        with self.idea_uow:
            author = self.idea_uow.fetch_author(UserID(user_id))
            idea = self.idea_uow.fetch_idea(IdeaQO(idea_id=IdeaID(idea_id)))
            if not author.can_edit_idea(idea):       # Проверка прав — бизнес-логика
                raise PermissionDenied()
            if not idea.is_editable():               # Бизнес-проверка состояния
                raise IdeaIsNotEditable()
            idea.update(body=body)
            self.idea_uow.add_idea_for_save(idea)
            self.idea_uow.commit()
```

### Бизнес модель (`Entity` / `ValueObject`)

Набор сущностей, агрегатов и value object. Каждый объект работает со своими полями
и методами, а также с методами сущностей, от которых зависит.
Не знает ни о хранилище, ни о транспорте.

```python
# domain/idea_exchange/main.py

class Idea(MetaManipulation):
    chain: LazyLoaderInEntity[Chain] = LazyLoaderInEntity()

    @classmethod
    def initialize_new_idea(
        cls, author: IdeaAuthor, body: str, chain: Chain, name: str
    ) -> 'Idea':
        idea = cls(
            body=body, author=author, chain=chain,
            current_chain_link=chain.first_chain_link(),
            name=name, idea_uid=str(uuid4()),
        )
        idea.mark_changed()
        return idea

    def is_editable(self) -> bool:
        return self.chain.element_position(self.current_chain_link) == Idea.FIRST_POSITION

    def update(self, body: str) -> None:
        if self.body != body:
            self.body = body
            self.mark_changed()
```

Value object — `NewType` или dataclass только из stdlib-типов:

```python
# domain/idea_exchange/types.py

IdeaID = NewType('IdeaID', int)
ChainID = NewType('ChainID', int)
IdeaUid = NewType('IdeaUid', str)
```

### Логика чтения и записи (`*UOW` + `*Builder`)

`*UOW` знает, как подготовить агрегаты для конкретного бизнес-кейса и как сохранить результат.
`*Builder` собирает сложный агрегат из частей, не делая запросов к БД самостоятельно.

```python
# dll/idea_exchange/uow.py

class IdeaUOW(BaseUnitOfWork):
    def __init__(self, idea_repo_cls=IdeaRepository, chain_repo_cls=ChainRepository,
                 actor_repo_cls=ActorRepository):
        self._idea_repo = idea_repo_cls(None)
        self._chain_repo = chain_repo_cls(None)
        self._actor_repo = actor_repo_cls(None)
        self._domain_objects_for_save: list = []

    def fetch_idea(self, query_object: IdeaQO) -> Idea:
        idea_dal_dto = self._idea_repo.fetch_one(filter_params=query_object)
        return IdeaBuilder(idea_dal_dto=idea_dal_dto, ...).build_one()

    def fetch_chain(self, chain_id: ChainID) -> Chain:
        return ChainBuilder(
            chain_repo=self._chain_repo,
            chain_qo=ChainQO(chain_id=chain_id),
            chain_link_builder_class=ChainLinkBuilder,
        ).build_one()

    def add_idea_for_save(self, idea: Idea) -> None:
        idea.set_updated_at_as_now()
        idea.mark_changed()
        self._domain_objects_for_save.append(idea)

    def commit(self) -> None:
        ideas = [o for o in self._domain_objects_for_save if isinstance(o, Idea)]
        self._idea_repo.add_many(ideas)
        self._domain_objects_for_save = []
```

```python
# dll/idea_exchange/builders.py

class ChainBuilder(ABSEntityFromRepoBuilder):
    def __init__(self, chain_repo, chain_qo, chain_link_builder_class, ...):
        self._chain_repo = chain_repo
        self._chain_qo = chain_qo
        self._chain_link_builder_class = chain_link_builder_class

    def build_one(self) -> Chain:
        chain_dal_dto = self._chain_repo.fetch_one(filter_params=self._chain_qo)
        return self._build_chain(chain_dal_dto)

    def build_lazy_many(self) -> LazyWrapper[Iterable[Chain]]:
        # Возвращает обёртку; фактический запрос — только при первом обращении к полю
        return LazyWrapper(method=self._build_lazy_many, params={})

    def _build_chain(self, dto: ChainDalDto) -> Chain:
        return Chain(
            chain_id=dto.chain_id,
            chain_links=self._chain_link_builder_class(...).build_lazy_many(),
            author=ChainEditor.from_user(self._fetch_author(dto.author_id)),
            reject_chain_link=self._fetch_one_chain_link(dto.reject_chain_link_id),
            accept_chain_link=self._fetch_one_chain_link(dto.accept_chain_link_id),
        )
```

### Логика доступа к данным (`*Repository`)

Единственное место SQL-запросов. Принимает `*QO` / `*OO`, возвращает `*DalDto`.

```python
# dal/idea_exchange/repo.py

class IdeaRepository(DjangoRepository):
    model = IdeaORM  # Django ORM-модель

    @property
    def _qo_orm_fields_mapping(self) -> list[QoOrmMapperLine]:
        return [
            QoOrmMapperLine(orm_field_name='id', qo_field_name='idea_id', modifier=int),
            QoOrmMapperLine(orm_field_name='author_id', qo_field_name='author_id', modifier=int),
            QoOrmMapperLine(orm_field_name='chain_id', qo_field_name='chain_id', modifier=int),
            QoOrmMapperLine(orm_field_name='is_deleted', qo_field_name='is_deleted'),
        ]

    def _orm_to_dto(self, orm_obj: IdeaORM) -> IdeaDalDto:
        return IdeaDalDto(
            idea_id=IdeaID(orm_obj.id),
            author_id=UserID(orm_obj.author_id),
            name=orm_obj.name,
            body=orm_obj.body,
            chain_id=ChainID(orm_obj.chain_id),
            is_deleted=orm_obj.is_deleted,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def _dto_to_orm(self, idea: DomainIdea) -> IdeaORM:
        return IdeaORM(
            id=idea.idea_id,
            author_id=idea.get_author_id(),
            name=idea.name,
            body=idea.body,
            is_deleted=idea.is_deleted(),
        )
```

### Модель хранения данных (Django ORM)

ORM-модели живут в Django-приложениях. Только колонки и маппинг — никакой логики.
Не знают о доменных сущностях.

```python
# idea/models.py  (Django app)

class IdeaORM(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    chain = models.ForeignKey('Chain', on_delete=models.PROTECT)
    current_chain_link = models.ForeignKey('ChainLink', on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    body = models.TextField()
    idea_uid = models.UUIDField(default=uuid4, unique=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'idea'
```

Для Redis, внешних HTTP-сервисов и других хранилищ создаётся аналогичная вертикаль:
собственные модели + репозиторий.

---

## Морфемы классов

Имя класса: `<BusinessName><Morpheme>`

### `Entity` (неявная морфема — суффикса нет)

**Слой**: `domain/<domain>/main.py`

Хранит состояние бизнес-сущности. Содержит бизнес-методы, изменяющие
собственное состояние или вызывающие методы зависимых сущностей.

```python
class Idea(MetaManipulation): ...     # Агрегат
class Chain(MetaManipulation): ...    # Агрегатный корень
class ChainLink(MetaManipulation): ...
class Actor: ...                      # Простая сущность
```

**Зависит от**: других `Entity`, `ValueObject`, `MetaManipulation`, протоколов из `domain/`.
**Не зависит от**: `Repository`, `Mapper`, `ORM`, `UOW`, `Builder`, `Case`.

Методы на Entity:

| Паттерн | Пример | Назначение |
|---|---|---|
| `initialize_new*` | `Idea.initialize_new_idea(...)` | Фабричный classmethod |
| `is_*` | `idea.is_editable()` | Предикат состояния |
| `can_*` | `author.can_edit_idea(idea)` | Проверка разрешения |
| `mark_*` | `chain_link.mark_deleted()` | Смена мета-состояния |
| `set_*` | `idea.set_for_change()` | Сеттер |
| `get_*` | `idea.get_author_id()` | Геттер |

---

### `ValueObject` / `NewType` (неявная морфема)

**Слой**: `domain/<domain>/types.py`

Типизирует примитивные значения с доменным смыслом. Неизменяемы.

```python
IdeaID = NewType('IdeaID', int)
ChainID = NewType('ChainID', int)
IdeaUid = NewType('IdeaUid', str)
```

**Зависит от**: только stdlib.

---

### `MetaManipulation` + `BaseMeta`

**Слой**: `framework/data_logic_layer/meta.py`

Миксин для трекинга технических полей (`is_changed`, `is_deleted`, `created_at`, `updated_at`).
Подключается к `Entity` как базовый класс.

```python
class Idea(MetaManipulation):
    ...
    # После инициализации — изменения через методы MetaManipulation:
    idea.mark_changed()     # устанавливает _meta.is_changed = True
    # Состояние читается через is_*:
    idea.is_changed()       # True
    idea.is_deleted()       # False
```

---

### `<Business>Case`

**Слой**: `cases/<domain>/<entity>.py`

Связующий слой: оркестрирует один бизнес-кейс. Инициируется при входящем запросе.
Содержит методы-действия (`create_*`, `edit_*`, `delete_*`).
Не содержит бизнес-вычислений — только последовательность вызовов.

```python
class IdeaCase:
    def __init__(self, uow_cls: Type[IdeaUOW] = IdeaUOW): ...
    def create_idea(self, user_id: int, body: str, chain_id: int, name: str) -> Idea: ...
    def edit_idea(self, user_id: int, idea_id: int, body: str) -> None: ...
    def delete_idea(self, user_id: int, idea_id: int) -> None: ...
```

---

### `<Business>UOW`

**Слой**: `dll/<domain>/uow.py`

Оркестрирует транзакцию: управляет несколькими `Repository` и `Builder`.
Используется как контекстный менеджер. Один `UOW` = один бизнес-кейс.

```python
class IdeaUOW(BaseUnitOfWork):
    # fetch_* — получение агрегатов
    def fetch_idea(self, query_object: IdeaQO) -> Idea: ...
    def fetch_chain(self, chain_id: ChainID) -> Chain: ...
    def fetch_author(self, author_id: UserID) -> IdeaAuthor: ...

    # add_*_for_save — регистрация объекта для сохранения
    def add_idea_for_save(self, idea: Idea) -> None: ...

    # commit / rollback — управление транзакцией
    def commit(self) -> None: ...
```

Использование в `Case`:
```python
with self.idea_uow:
    idea = self.idea_uow.fetch_idea(IdeaQO(idea_id=idea_id))
    idea.update(body=dto.body)
    self.idea_uow.add_idea_for_save(idea)
    self.idea_uow.commit()
```

**Зависит от**: `Repository`, `Builder`, `ISession`, `Entity`, `QO`.
**Не зависит от**: `Case`, другие `UOW`, `Mapper` напрямую.

---

### `<Business>Builder`

**Слой**: `dll/<domain>/builders.py`

Собирает сложный доменный объект из нескольких частей.
Все данные получает через конструктор — сам не ходит в БД.
Поддерживает ленивую сборку через `build_lazy_one()` / `build_lazy_many()`.

```python
class ChainBuilder(ABSEntityFromRepoBuilder):
    def build_one(self) -> Chain: ...
    def build_many(self) -> Iterable[Chain]: ...
    def build_lazy_one(self) -> LazyWrapper[Chain]: ...
    def build_lazy_many(self) -> LazyWrapper[Iterable[Chain]]: ...
```

**Зависит от**: `Entity`, `ValueObject`, `DalDto`, `Repository` (через конструктор).
**Не зависит от**: `UOW`, `ISession`, `Case`.

---

### `<Business>Repository`

**Слой**: `dal/<domain>/repo.py`

Единственное место SQL-запросов. Возвращает `*DalDto`, не `Entity`.
Принимает `*QO` / `*OO`.

Стандартные методы:

| Метод | Назначение |
|---|---|
| `fetch_one(filter_params, order_params, raise_if_empty)` | Один объект |
| `fetch_many(filter_params, order_params, offset, limit, chunk_size)` | Список/генератор |
| `add(domain_model)` | Создать |
| `add_many(sequence)` | Создать несколько |
| `update_one(domain_model)` | Обновить |
| `update_many(sequence)` | Обновить несколько |

**Зависит от**: ORM-модель, `Mapper`, `ISession`, `QO`, `OO`.
**Не зависит от**: `UOW`, `Builder`, `Case`, другие `Repository`.

---

### `<Business>Mapper`

**Слой**: `dal/<domain>/mapper.py`

Конвертирует ORM-объект → `*DalDto` и обратно. Только преобразование формата.
Статические методы, без состояния.

```python
class ManagerMapper(ABSMapper):
    @staticmethod
    def from_orm_to_domain(orm_model: CustomUser) -> Manager:
        return Manager(user_id=UserID(orm_model.id))
```

Внутри `Repository` конвертация реализуется методами `_orm_to_dto` / `_dto_to_orm`.

**Зависит от**: ORM-модель, `Entity`, `ValueObject`.
**Не зависит от**: `Repository`, `UOW`, `Case`.

---

### `<Business>QO` (QueryObject)

**Слой**: `dal/<domain>/qo.py`

Dataclass с параметрами фильтрации. `Empty()` = поле не задано → не попадает в WHERE.
Поддерживает `QueryParamComparison` (`GTE`, `IN`) для операторов сравнения.

```python
@dataclass
class IdeaQO(ABSQueryObject):
    idea_id: Optional[Union[IdeaID, Empty, QueryParamComparison[IdeaID]]] = field(default_factory=Empty)
    author_id: Optional[Union[UserID, Empty]] = field(default_factory=Empty)
    chain_id: Optional[Union[ChainID, Empty]] = field(default_factory=Empty)
    is_deleted: Optional[Union[bool, Empty]] = field(default_factory=Empty)
```

**Зависит от**: `ValueObject`, `ABSQueryObject`, `QueryParamComparison`.
**Не зависит от**: `Repository`, `Entity`, `UOW`.

---

### `<Business>OO` (OrderObject)

**Слой**: `dal/<domain>/oo.py`

Dataclass с параметрами сортировки. Передаётся отдельно в `fetch_many`.

```python
@dataclass
class IdeaOO(ABSOrderObject):
    created_at: Optional[Union[OrderParamComparison, Empty]] = field(default_factory=Empty)
    # Пример: IdeaOO(created_at=DESC())
```

---

### `<Business>DalDto`

**Слой**: `dal/<domain>/dto.py`

Промежуточный dataclass между ORM и доменным слоем.
Используется, когда `Repository` возвращает частичные данные или `Builder` работает
с сырыми данными из БД без зависимости от ORM.

```python
@dataclass
class IdeaDalDto(IDTO):
    idea_id: IdeaID
    author_id: UserID
    name: str
    body: str
    chain_id: ChainID
    current_chain_link_id: ChainLinkID
    idea_uid: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
```

**Зависит от**: только stdlib, `ValueObject`.
**Не зависит от**: `Entity`, `ORMModel`, `Repository`.

---

### `<Business>UiDto` / `<Business>UoDto`

**Слой**: `cases/<domain>/dto.py`

- `*UiDto` — входные данные от пользователя (User Input)
- `*UoDto` — исходящие данные пользователю (User Output)

```python
@dataclass
class IdeaUiDto:         # Входящий контракт
    name: str
    body: str
    chain_id: int

@dataclass
class IdeaUoDto:         # Исходящий контракт
    idea_id: int
    name: str
    body: str
    idea_uid: str
    is_accepted: bool
    chain_links: list[IdeaChainLinkUoDto]
```

---

### Ленивые обёртки: `LazyWrapper` / `LazyLoaderInEntity`

**Слой**: `framework/data_access_layer/lazy.py`

`LazyWrapper` — откладывает выполнение запроса до первого обращения к полю.
`LazyLoaderInEntity` — дескриптор, который прозрачно раскрывает `LazyWrapper`
при обращении к полю `Entity`.

```python
# Объявление поля в Entity:
class Chain(MetaManipulation):
    chain_links: LazyLoaderInEntity[Iterable[ChainLink]] = LazyLoaderInEntity()
    author: LazyLoaderInEntity[IdeaAuthor] = LazyLoaderInEntity()

# Builder передаёт ленивую обёртку:
chain = Chain(
    chain_links=chain_link_builder.build_lazy_many(),  # LazyWrapper
    author=author_builder.build_lazy_one(),            # LazyWrapper
    ...
)

# При первом обращении к chain.chain_links — автоматически выполняется запрос:
for link in chain.chain_links:   # Запрос происходит здесь
    ...
```

---

## Морфемы функций и методов

Паттерн имени: `<primary_morpheme>_<?secondary_morpheme>_<business_morpheme>`

Морфемы можно комбинировать без `and`: `fetch_recache_vehicle`, не `fetch_and_recache_vehicle`.
Существительные переводятся на английский и фиксируются в глоссарии — синонимы запрещены.

---

### `fetch_*`

**Слой**: Repository (DAL), UOW (DLL), Case

Получает данные из внешнего источника (БД, API, кэш-промах).

**Правила**:
- Только чтение — запись запрещена.
- Никаких бизнес-вычислений, конвертаций типов (если только ORM не делает это нативно).
- Не вызывает другие `fetch_*` — для сборки из нескольких источников использовать `build_*`.
- Логирование: `debug` до, `info` после успеха, `error` при исключении.

```python
# dal/idea_exchange/repo.py — в Repository через fetch_one / fetch_many

# dll/idea_exchange/uow.py — в UOW оборачивает вызов Repository + Builder
def fetch_idea(self, query_object: IdeaQO) -> Idea:
    idea_dal_dto: IdeaDalDto = self._idea_repo.fetch_one(filter_params=query_object)
    return self.build_idea(idea_dal_dto=idea_dal_dto)

def fetch_author(self, author_id: UserID) -> IdeaAuthor:
    logger.debug('[IdeaUOW.fetch_author] [%s] Attempting to fetch author id=%s', self._log_id, author_id)
    try:
        user_qo = UserQO(user_id=author_id)
        user = self._user_repo.fetch_one(filter_params=user_qo)
        logger.info('[IdeaUOW.fetch_author] [%s] Successfully fetched author id=%s', self._log_id, author_id)
        return IdeaAuthor.from_user(user)
    except Exception as e:
        logger.error('[IdeaUOW.fetch_author] [%s] Error fetching author id=%s: %s', self._log_id, author_id, str(e))
        raise
```

С кэшем: `fetch_decache_vehicle` (только кэш), `fetch_recache_vehicle` (кэш → БД → кэш).

---

### `persist_*`

**Слой**: Repository (DAL)

Сохраняет данные во внешнее хранилище (create / update / delete).

**Правила**:
- Только запись — никаких вычислений, конвертаций, чтения.
- Суффиксы `_created_`, `_updated_`, `_deleted_` обязательны — чтобы не путать с бизнес-морфемами.
- Логирование: `debug` до (с количеством/ID), `info` после, `error` при исключении.

```python
def persist_created_vehicle(vehicles: list) -> list:
    logger.debug('[persist_created_vehicle] Attempting to create %s vehicles', len(vehicles))
    try:
        created = Vehicle.objects.bulk_create(vehicles)
        logger.info('[persist_created_vehicle] Created %s vehicles, IDs: %s',
                    len(created), [v.id for v in created])
        return created
    except Exception as e:
        logger.error('[persist_created_vehicle] Error creating vehicles: %s', str(e))
        raise
```

---

### `build_*` / `build_one` / `build_many` / `build_lazy_one` / `build_lazy_many`

**Слой**: Builder (DLL), UOW (DLL)

Собирает сложный доменный объект из нескольких источников.

**Правила**:
- Разрешено: вызывать `fetch_*`, `recache_*`, `encache_*`, `decache_*`, `convert_*`; фильтрация и объединение; ленивые генераторы.
- Запрещено: прямые ORM-вызовы, `calc_*`, `initialize_*`, сохранение в хранилище.
- Логирование: необязательно; `debug` на входе, `info` на выходе, `error` при сбое соединения.

Стандартное API класса `*Builder`:

```python
# framework/data_logic_layer/builders.py
class ABSEntityFromRepoBuilder:
    def build_lazy_one(self) -> LazyWrapper[T]: ...      # Один объект, ленивый
    def build_lazy_many(self) -> LazyWrapper[Iterable[T]]: ...  # Многие, ленивые
    def build_one(self) -> T: ...                         # Один объект, немедленно
    def build_many(self) -> Iterable[T]: ...              # Многие, немедленно
```

`build_lazy` (без суффикса one/many) допустим, когда Builder всегда возвращает одну сущность.

```python
# dll/idea_exchange/builders.py
class ChainBuilder(ABSEntityFromRepoBuilder):

    def build_one(self) -> Chain:
        chain_dto = self._chain_repo.fetch_one(filter_params=self._chain_qo)
        return self._build_chain(chain_dto)

    def build_lazy_one(self) -> LazyWrapper[Chain]:
        return LazyWrapper(method=self._build_lazy_one, params={})

    def build_lazy_many(self) -> LazyWrapper[Iterable[Chain]]:
        return LazyWrapper(method=self._build_lazy_many, params={})

    def _build_chain(self, dto: ChainDalDto) -> Chain:
        # Приватный метод — собирает Chain из DTO, вызывая дочерние Builder
        return Chain(
            chain_id=dto.chain_id,
            chain_links=self._chain_link_builder_class(...).build_lazy_many(),
            author=ChainEditor.from_user(self._user_repo.fetch_one(filter_params=UserQO(user_id=dto.author_id))),
            reject_chain_link=self._fetch_one_chain_link(dto.reject_chain_link_id),
            accept_chain_link=self._fetch_one_chain_link(dto.accept_chain_link_id),
            _meta_is_deleted=dto.is_deleted,
        )

    def _fetch_one_chain_link(self, chain_link_id: ChainLinkID) -> LazyWrapper[ChainLink]:
        # Приватный fetch внутри Builder — допустим, т.к. использует переданный репозиторий
        qo = ChainLinkQO(chain_link_id=chain_link_id, is_deleted=False)
        return self._chain_link_builder_class(..., chain_link_qo=qo).build_lazy_one()
```

В UOW `build_*` используется для сборки агрегата из DTO перед возвратом в Case:

```python
# dll/idea_exchange/uow.py
def build_idea(self, idea_dal_dto: IdeaDalDto) -> Idea:
    chain = self.fetch_chain(idea_dal_dto.chain_id)
    user = self._user_repo.fetch_one(filter_params=UserQO(user_id=idea_dal_dto.author_id))
    current_chain_link = chain.chain_link_by_id(idea_dal_dto.current_chain_link_id)
    return Idea(
        idea_storage_id=idea_dal_dto.idea_id,
        author=IdeaAuthor.from_user(user),
        name=idea_dal_dto.name,
        body=idea_dal_dto.body,
        chain=chain,
        idea_uid=idea_dal_dto.idea_uid,
        current_chain_link=current_chain_link,
        _meta_is_deleted=idea_dal_dto.is_deleted,
    )
```

---

### `convert_*`

**Слой**: UOW (DLL), Mapper (DAL), Case

Преобразует данные из одного формата в другой без изменения информации.

**Правила**:
- Разрешено: дефолтные значения, приведение типов, извлечение поля
  (`vehicle.model.name if vehicle.model else '-'`), нетехнические преобразования единиц.
- Запрещено: бизнес-вычисления (`vehicle_full_weight = model.weight + current_ore_weight` — это `calc_`), запросы к хранилищу, валидация.
- Исключения не перехватывает — пробрасывает вверх.
- Логирование: необязательно.

```python
# dll/idea_exchange/uow.py
def convert_idea_to_output(self, idea: Idea) -> IdeaUoDto:
    return IdeaUoDto(
        idea_id=idea.idea_id,
        name=idea.name,
        body=idea.body,
        is_accepted=idea.is_accepted(),
        is_rejected=idea.is_rejected(),
        chain_links=[self.convert_chain_link_to_uo(cl, idea) for cl in idea.chain.chain_links],
        idea_uid=idea.idea_uid,
    )

def convert_chain_link_to_uo(self, chain_link: ChainLink, idea: Idea) -> IdeaChanLinkUoDto:
    return IdeaChanLinkUoDto(
        chain_link_id=int(chain_link.chain_link_id),
        name=chain_link.name,
        is_current=idea.is_chain_link_current(chain_link),
    )
```

---

### `calc_*`

**Слой**: Entity (domain)

Выполняет вычисления: арифметику, координатные преобразования, метрики.

**Правила**:
- Обязателен комментарий с объяснением бизнес-смысла.
- Разрешено: вызывать `verify_*`, другие `calc_*`.
- Запрещено: `fetch_*`, `build_*`, `persist_*`, `send_*`, `initialize_*`, `validate_*`.
- Исключения не перехватывает. Может выбрасывать доменные исключения при нарушении бизнес-правил.
- Документировать выбрасываемые исключения: `:raises ValueError: ...`.

```python
# domain/idea_exchange/main.py
class Chain(MetaManipulation):
    def calc_next_chain_link(self, chain_link: ChainLink) -> ChainLink:
        # Возвращает следующее звено в цепочке согласования.
        # Если текущее звено — последнее, возвращает accept_chain_link.
        # :raises IncorrectChainLink: Если звено не принадлежит этой цепочке.
        chain_links = list(self.chain_links)
        try:
            idx = chain_links.index(chain_link)
        except ValueError:
            raise IncorrectChainLink(
                f"Звено {chain_link.chain_link_id}:{chain_link.name} не принадлежит этой цепочке"
            )
        if idx == len(chain_links) - 1:
            return self.accept_chain_link
        return chain_links[idx + 1]
```

---

### `verify_*`

**Слой**: Entity (domain), модульные функции

Проверяет бизнес-правило. По умолчанию выбрасывает исключение при нарушении.
Если возвращает `bool` — имя должно быть `verify_is_*`.

**Правила**:
- Обязателен комментарий с объяснением правила и причиной.
- Запрещено: `calc_*`, `build_*`, другие `verify_*`, обращение к хранилищам.
- Документировать: `:raises ...: Если ...`.

```python
# Модульные функции:
def verify_user_age(user: User) -> None:
    # Пользователь обязан быть старше 18 лет (юридическое требование).
    # :raises ValueError: Если возраст меньше 18.
    if user.age < 18:
        raise ValueError("User must be at least 18 years old.")

def verify_is_admin_role(user: User) -> bool:
    # Проверяет роль администратора для допуска к управлению предприятием.
    return user.role == Role.ADMIN
```

Отличие от `can_*`: `verify_*` — внешняя функция или метод агрегата, выбрасывает исключение;
`can_*` — метод сущности, возвращает `bool` (см. ниже).

---

### `validate_*`

**Слой**: Entity (domain), модульные функции

Технические проверки: корректность типа, формата, структуры. Не для бизнес-правил.

**Правила**:
- Запрещено: `verify_*`, `calc_*`, `fetch_*`, `build_*`, рекурсия, мутация аргументов, внешние вызовы.
- По умолчанию — выбрасывает исключение. Если возвращает `bool` — имя `validate_is_*`.
- Документировать: `:raises ValueError: ...`.

Отличие от `verify_*`: `validate_*` проверяет, можно ли технически обработать данные
(можно ли строку `"10"` привести к `int`?). `verify_*` проверяет бизнес-правила
(достиг ли пользователь 18 лет?).

```python
def validate_string_as_int(value: str) -> int:
    """
    :raises ValueError: Если строку нельзя привести к int.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValueError(f"Cannot convert '{value}' to int.")

# Структурная проверка на Entity — тоже validate_*, не verify_*:
# domain/idea_exchange/main.py
class Chain(MetaManipulation):
    def validate_chain_links(self, chain_links: list[ChainLink]) -> None:
        # Все переданные звенья структурно принадлежат этой цепочке.
        # :raises IncorrectChainLink: Если хотя бы одно звено чужое.
        chain_links_ids_in_chain = {
            i.chain_link_id for i in self.chain_links if i.chain_link_id is not None
        }
        for chain_link in chain_links:
            if chain_link.chain_link_id is not None and \
                    chain_link.chain_link_id not in chain_links_ids_in_chain:
                raise IncorrectChainLink(
                    f"Звено {chain_link.chain_link_id}:{chain_link.name} не принадлежит этой цепочке"
                )
```

---

### `initialize_*`

**Слой**: Entity (domain) — classmethod

Создаёт новый объект с предзаданными бизнес-значениями.

**Правила**:
- Запрещено: внешние вызовы (БД, API, файлы), `verify_*`, `calc_*`, `generate_*`, `validate_*`.
- Возвращает новый объект — не мутирует аргументы.
- Вызывает `mark_changed()` на созданном объекте.

```python
# domain/idea_exchange/main.py
class Idea(MetaManipulation):
    @classmethod
    def initialize_new_idea(
            cls, author: IdeaAuthor, body: str, chain: Chain, name: str
    ) -> 'Idea':
        idea = cls(
            body=body,
            author=author,
            chain=chain,
            current_chain_link=chain.first_chain_link(),
            name=name,
            idea_uid=str(uuid4()),
        )
        idea.mark_changed()
        return idea

class ChainLink(MetaManipulation):
    @classmethod
    def initialize_technical(cls, name: str) -> 'ChainLink':
        # Технические звенья (Одобрено/Отклонено) создаются без актора.
        return cls(
            chain_link_id=None,
            actor=None,
            is_technical=True,
            name=name,
            _meta_is_changed=True,
            number_of_related_ideas=0,
        )
```

---

### `send_*`

**Слой**: модульные функции, инфраструктурный слой

Отправляет данные во внешние системы (шина, очередь, HTTP).

**Правила**:
- Все данные должны быть готовы до вызова — подготовка не входит в `send_*`.
- Сериализация и генерация ключей — отдельные функции.
- Асинхронная версия: явно указывать `async` в имени: `send_async_order_to_queue`.
- Логирование: `debug` до (что и куда), `info` после успеха, `error` при исключении.

```python
def send_user_event_to_bus(event_data: dict) -> None:
    logger.debug('[send_user_event_to_bus] Attempting to send event: %s', event_data.get('type'))
    try:
        bus.publish('user_events', event_data)
        logger.info('[send_user_event_to_bus] Event sent successfully')
    except Exception as e:
        logger.error('[send_user_event_to_bus] Error sending event: %s', str(e))
        raise
```

---

### `encache_*` / `decache_*` / `recache_*`

**Слой**: модульные функции (инфраструктура кэша)

Работа с кэшем. Без конвертаций и бизнес-логики.

- `decache_*` — только чтение из кэша. Возвращает `None` при промахе — логировать это.
- `encache_*` — только запись в кэш. Может быть первичной (`encache_user`) или вторичной (`persist_encache_vehicle`).
- `recache_*` — кэш → при промахе: БД → запись в кэш → возврат.
- Генерацию ключей выносить в `generate_*`, не встраивать в `encache_*` / `decache_*`.
- Логирование обязательно: `debug` до + ключ, `info` после (с результатом/`None`), `error` при исключении.

```python
def fetch_decache_vehicle(vehicle_id: int):
    logger.debug('[fetch_decache_vehicle] Attempting to get vehicle id=%s from cache', vehicle_id)
    try:
        vehicle = cache.get(vehicle_id)
        if vehicle:
            logger.info('[fetch_decache_vehicle] Vehicle id=%s retrieved from cache', vehicle_id)
        else:
            logger.debug('[fetch_decache_vehicle] Vehicle id=%s not found in cache', vehicle_id)
        return vehicle
    except Exception as e:
        logger.error('[fetch_decache_vehicle] Error reading cache for vehicle id=%s: %s', vehicle_id, str(e))
        raise
```

---

### `generate_*`

**Слой**: модульные функции, утилиты

Генерирует значения: ID, ключи кэша, токены, временные метки.

**Правила**:
- Без обращения к внешним хранилищам.
- Возвращает значение — не мутирует аргументы.
- Сложные формулы выносить в `calc_*`.
- Документировать правила генерации в docstring.

```python
def generate_cache_key(vehicle_id: int, enterprise_id: int) -> str:
    """Ключ для кэширования объекта Vehicle: vehicle_{vehicle_id}_{enterprise_id}"""
    return f'vehicle_{vehicle_id}_{enterprise_id}'
```

---

### `filter_*`

**Слой**: модульные функции

Фильтрует коллекцию, возвращает подмножество.

**Правила**: без внешних вызовов, без вычислений. Бизнес-правила фильтрации делегировать в `verify_is_*` / `validate_is_*`.

```python
def filter_active_users(users: list[User]) -> list[User]:
    return [u for u in users if verify_is_admin_role(u)]
```

---

### `find_*`

**Слой**: модульные функции

Бизнес-поиск внутри коллекции в памяти. Возвращает **один объект** (или `tuple` связанных).

**Правила**: без внешних вызовов. Не создаёт объекты через `build_*`, `initialize_*`, `generate_*`.
Документировать алгоритм поиска и бизнес-правила.

```python
def find_driver_by_date(drivers: list[Driver], date: date) -> Driver:
    """Возвращает водителя, чья смена совпадает с датой. Первый подходящий."""
    for driver in drivers:
        if driver.shift_date == date:
            return driver
    raise NotFoundException(f'No driver found for date {date}')
```

---

### `map_*` / `group_*`

**Слой**: модульные функции

Строят словари для быстрого поиска / группировки коллекции.

**Правила**: не модифицируют коллекцию, без внешних вызовов, без бизнес-логики.

```python
def map_vehicle_to_enterprise(vehicles: list[Vehicle]) -> dict[EnterpriseID, Vehicle]:
    return {v.enterprise_id: v for v in vehicles}

def group_vehicles_by_enterprise(vehicles: list[Vehicle]) -> dict[EnterpriseID, list[Vehicle]]:
    result: dict[EnterpriseID, list[Vehicle]] = {}
    for v in vehicles:
        result.setdefault(v.enterprise_id, []).append(v)
    return result
```

---

### `can_*` — проверка разрешения от сущности

**Слой**: Entity (domain)

Метод сущности, инкапсулирующий право на действие над другой сущностью.
Возвращает `bool`. Отличается от `verify_*`: не выбрасывает исключений.

**Правила**:
- Только на `Entity`.
- Принимает связанную сущность как аргумент.
- Без обращения к хранилищам.
- Имя: `can_<действие>_<сущность>`.

```python
# domain/idea_exchange/main.py
class IdeaAuthor(User):
    def can_delete_idea(self, idea: 'Idea') -> bool:
        # Удалить идею может только её автор.
        return idea.author == self

    def can_edit_idea(self, idea: 'Idea') -> bool:
        # Редактировать идею может только её автор.
        return idea.author == self
```

Применение в Case — всегда проверять через `can_*`, бросать исключение вручную:

```python
# cases/idea_exchange/idea.py
if not author.can_delete_idea(idea):
    raise PermissionDenied()
```

---

### `is_*` — предикат состояния сущности

**Слой**: Entity (domain), MetaManipulation (framework)

Проверяет внутреннее состояние или принадлежность. Возвращает `bool`.
Отличается от `verify_is_*`: `is_*` — самодиагностика сущности без контекста правил.

**Правила**: только на `Entity`, без обращения к хранилищам.

```python
# framework/data_logic_layer/meta.py (MetaManipulation — стандартные предикаты)
def is_deleted(self) -> bool: return self._meta.is_deleted
def is_changed(self) -> bool: return self._meta.is_changed
def is_new(self) -> bool: return self._meta.id_from_storage is None

# domain/idea_exchange/main.py (бизнес-предикаты)
class Idea(MetaManipulation):
    def is_editable(self) -> bool:
        # Идея редактируема только на первом этапе согласования.
        return self.chain.element_position(self.current_chain_link) == Idea.FIRST_POSITION

    def is_accepted(self) -> bool:
        return self.current_chain_link.chain_link_id == self.chain.accept_chain_link.chain_link_id

    def is_rejected(self) -> bool:
        return self.current_chain_link.chain_link_id == self.chain.reject_chain_link.chain_link_id

    def is_chain_link_current(self, chain_link: ChainLink) -> bool:
        return self.current_chain_link.chain_link_id == chain_link.chain_link_id

class Actor:
    def is_manager_valid_actor(self, manager: Manager) -> bool:
        # Менеджер валиден для этапа, если входит в список допустимых или в группу этапа.
        return self.is_manager_team_member(manager) or \
               self.is_manager_in_admissible_managers(manager)
```

---

### `mark_*` — пометка технического состояния

**Слой**: Entity (domain), MetaManipulation (framework)

Изменяет технические флаги сущности в `_meta`. Не содержит бизнес-логики.

**Правила**: только изменение `_meta`-флагов, без обращения к хранилищам.
Стандартные методы определены в `MetaManipulation` и могут быть переопределены в `Entity`.

```python
# framework/data_logic_layer/meta.py
class MetaManipulation:
    def mark_deleted(self):
        """Пометить сущность как удалённую"""
        self._meta.is_deleted = True

    def mark_changed(self):
        """Пометить сущность как изменённую"""
        self._meta.is_changed = True

# domain/idea_exchange/main.py — переопределение с расширением
class Idea(MetaManipulation):
    def mark_deleted(self):
        # Удаление идеи влечёт и пометку об изменении для последующего сохранения.
        super().mark_deleted()
        self.mark_changed()
```

---

### `set_*` — сеттер поля с фиксацией изменения

**Слой**: Entity (domain)

Устанавливает значение поля и обязательно фиксирует факт изменения через `set_for_change()`.

**Правила**: без обращения к хранилищам. `set_for_change` — технический метод-маркер.

```python
# domain/idea_exchange/main.py
class ChainLink(MetaManipulation):
    def set_for_change(self):
        """Явная пометка: объект изменён, требует сохранения."""
        self._meta.is_changed = True

    def set_name(self, name: str) -> None:
        self._name = name
        self.set_for_change()

    def set_actor(self, actor: Actor) -> None:
        self._actor = actor
        self.set_for_change()

    def set_as_deleted(self) -> None:
        # Удалить звено можно только если нет связанных идей.
        # :raises ChainLinkCantBeDeleted: Если есть активные идеи на этом звене.
        if self.number_of_related_ideas > 0:
            raise ChainLinkCantBeDeleted()
        self.mark_deleted()
        self.mark_changed()
```

**`set_as_deleted`** отличается от `mark_deleted`: содержит бизнес-проверку перед удалением.

**`set_*_as_now`** — специальный паттерн для временны́х меток:

```python
# framework/data_logic_layer/meta.py
class MetaManipulation:
    def set_created_at_as_now(self):
        self.set_created_at(datetime.now())

    def set_updated_at_as_now(self):
        self.set_updated_at(datetime.now())
```

Вызывается в UOW при регистрации объекта для сохранения:

```python
# dll/idea_exchange/uow.py
def add_idea_for_save(self, idea: Idea) -> None:
    idea.set_updated_at_as_now()   # ← set_*_as_now
    idea.mark_changed()
    self._domain_object_for_save.append(idea)
```

---

### `get_*` — геттер приватного поля

**Слой**: Entity (domain)

Возвращает значение поля, хранящегося под приватным именем (`_field`), или выполняет
тривиальное приведение типа для внешних слоёв.

**Правила**: без вычислений, без обращения к хранилищам.
Если поле публично и не требует приведения — использовать `property`, не `get_*`.

```python
# domain/idea_exchange/main.py
class ChainLink(MetaManipulation):
    def get_name(self) -> str:
        return self._name              # Скрытое поле

    def get_actor(self) -> Actor:
        return self._actor

class Idea(MetaManipulation):
    def get_author_id(self) -> int:
        return self.author.user_id     # Приведение ValueObject → int для внешних слоёв

    def get_chain_id(self) -> int:
        return self.chain.chain_id

    def get_current_chain_link_id(self) -> int:
        return self.current_chain_link.chain_link_id
```

---

### `from_*` — фабричный classmethod из другого доменного типа

**Слой**: Entity (domain) — classmethod

Создаёт экземпляр Entity из объекта другого доменного типа.
Отличается от `initialize_*`: `initialize_*` создаёт новый объект с бизнес-дефолтами,
`from_*` конвертирует уже существующий объект смежного типа.

**Правила**: только `classmethod` на `Entity`. Без обращения к хранилищам. Без бизнес-логики — только маппинг полей. Имя: `from_<source_type>`.

```python
# domain/idea_exchange/main.py
class IdeaAuthor(User):
    @classmethod
    def from_user(cls, user: User) -> 'IdeaAuthor':
        return cls(user_id=user.user_id)

class Manager(User):
    @classmethod
    def from_user(cls, user: User) -> 'Manager':
        return Manager(user_id=user.user_id)
```

Используется в UOW при конвертации данных из репозитория в доменный тип:

```python
# dll/idea_exchange/uow.py
user = self._user_repo.fetch_one(filter_params=user_qo)
return IdeaAuthor.from_user(user)
```

---

### `update` / `update_*` — частичное обновление полей

**Слой**: Entity (domain)

Обновляет поля сущности, проверяя факт реального изменения перед пометкой `is_changed`.

**Правила**: без обращения к хранилищам. Помечать `is_changed` только при реальном изменении.

```python
# domain/idea_exchange/main.py
class Idea(MetaManipulation):
    def update(self, body: str) -> None:
        if self.body != body:          # Флаг ставится только при реальном изменении
            self.body = body
            self.mark_changed()
```

---

### `replace_*` — замена коллекции с управлением побочными эффектами

**Слой**: Entity (domain)

Полностью заменяет коллекцию или поле. В отличие от простого `set_*`,
управляет судьбой старых элементов (помечает их удалёнными, собирает для последующего сохранения).

```python
# domain/idea_exchange/main.py
class Chain(MetaManipulation):
    def replace_chain_links(self, chain_links: list[ChainLink]) -> None:
        # Заменить список звеньев цепочки. Звенья, не вошедшие в новый список,
        # помечаются удалёнными и собираются в dropped_chain_links для сохранения.
        old_chain_links = list(self.chain_links)
        used_chain_links: set[ChainLinkID] = set()
        for chain_link in chain_links:
            chain_link.set_for_change()
            if chain_link.chain_link_id:
                used_chain_links.add(chain_link.chain_link_id)
        self.chain_links = chain_links
        for old_chain_link in old_chain_links:
            if old_chain_link.chain_link_id not in used_chain_links:
                old_chain_link.set_as_deleted()
                self.dropped_chain_links.append(old_chain_link)
```

**`replace_id_from_meta`** — инфраструктурный паттерн: вызывается Repository/UOW после `INSERT`
для простановки нового ID из хранилища:

```python
# framework/data_logic_layer/meta.py (определение)
class MetaManipulation:
    def replace_id_from_meta(self):
        raise NotImplementedError()

# domain/idea_exchange/main.py (реализация в каждой Entity)
class Idea(MetaManipulation):
    def replace_id_from_meta(self):
        self.idea_id = self._meta.id_from_storage

class Chain(MetaManipulation):
    def replace_id_from_meta(self):
        self.chain_id = self._meta.id_from_storage
```

---

### `add_*_for_save` — регистрация объекта в UOW

**Слой**: UOW (DLL)

Регистрирует сущность в списке для сохранения при следующем `commit()`.
Может выполнять предварительные действия: `set_updated_at_as_now()`, `mark_changed()`.

**Правила**: только в `UOW`. Не делает запросов к хранилищам. Имя: `add_<entity>_for_save`.

```python
# dll/idea_exchange/uow.py
def add_idea_for_save(self, idea: Idea) -> None:
    idea.set_updated_at_as_now()
    idea.mark_changed()
    self._domain_object_for_save.append(idea)

def add_chain_for_save(self, chain: Chain) -> None:
    self._domain_object_for_save.append(chain)
```

---

### Методы `*Case`: `create_*`, `delete_*`, `edit_*`, доменные действия

**Слой**: Case (cases/)

Методы `*Case` — публичный API связующего слоя. Имя = глагол + сущность по бизнес-смыслу.

| Группа | Паттерн | Пример | Структура |
|---|---|---|---|
| Создание | `create_<entity>` | `create_idea` | `initialize_new_*` → `add_*_for_save` → `commit` |
| Удаление | `delete_<entity>` | `delete_idea` | `fetch` → `can_*` → `mark_deleted` → `add_*_for_save` → `commit` |
| Изменение | `edit_<entity>` | `edit_idea` | `fetch` → `can_*` → `is_*` → `update` → `add_*_for_save` → `commit` |
| Доменное действие | `<action>_<entity>` | `accept_idea`, `reject_idea` | `fetch` → `is_*` → метод Entity → `add_*_for_save` → `commit` |
| Чтение | `fetch_<entity/ies>` | `fetch_idea`, `fetch_allowed_chains` | `fetch` через UOW → `convert_*` → `UoDto` |
| Список пользователя | `<scope>_<entities>` | `user_ideas` | `fetch_many` → `convert_*` → список `UoDto` |

**Правила для всех методов Case**:
- Нет бизнес-вычислений — только последовательность вызовов.
- Проверка прав: `entity.can_*` → `raise` при `False`.
- Проверка состояния: `entity.is_*` → `raise` при `False`.
- Открывать UOW через `with self.uow:`.

```python
# cases/idea_exchange/idea.py
class IdeaCase:

    def create_idea(self, user_id: int, body: str, chain_id: int, name: str) -> Idea:
        with self.idea_uow:
            author = self.idea_uow.fetch_author(author_id=UserID(user_id))
            chain = self.idea_uow.fetch_chain(chain_id=ChainID(chain_id))
            idea = Idea.initialize_new_idea(body=body, author=author, chain=chain, name=name)
            idea.set_created_at_as_now()
            self.idea_uow.add_idea_for_save(idea=idea)
            self.idea_uow.commit()
            return idea

    def delete_idea(self, user_id: int, idea_id: IdeaID):
        with self.idea_uow:
            author = self.idea_uow.fetch_author(UserID(user_id))
            idea = self.idea_uow.fetch_idea(IdeaQO(idea_id=idea_id))
            if not author.can_delete_idea(idea):
                raise PermissionDenied()
            idea.mark_deleted()
            self.idea_uow.add_idea_for_save(idea)
            self.idea_uow.commit()

    def edit_idea(self, user_id: int, body: str, idea_id: int):
        with self.idea_uow:
            author = self.idea_uow.fetch_author(UserID(user_id))
            idea = self.idea_uow.fetch_idea(IdeaQO(idea_id=IdeaID(idea_id)))
            if not author.can_edit_idea(idea):
                raise PermissionDenied()
            if not idea.is_editable():
                raise IdeaIsNotEdiatable()
            idea.update(body=body)
            self.idea_uow.add_idea_for_save(idea)
            self.idea_uow.commit()

    def accept_idea(self, user_id: int, idea_id: int):
        with self.idea_uow:
            manager = self.idea_uow.fetch_manager(ManagerQO(user_id=UserID(user_id)))
            idea = self.idea_uow.fetch_idea(IdeaQO(idea_id=IdeaID(idea_id)))
            if not idea.is_manager_valid_actor(manager):
                raise HasNoPermissions('User cant manage this idea')
            idea.move_to_next_chain_link()
            self.idea_uow.add_idea_for_save(idea)
            self.idea_uow.commit()
```

---

### Семантические методы Entity (без технической морфемы)

**Слой**: Entity (domain)

Методы, чьё имя описывает бизнес-смысл напрямую, без технического префикса.
Применяются для бизнес-запросов к состоянию агрегата и доменных действий.

**Правила**:
- Без обращения к хранилищам.
- Не вызывают `fetch_*`, `persist_*`, `build_*`.
- Имя — глагол или существительное, понятное из предметной области.

```python
# domain/idea_exchange/main.py
class Chain(MetaManipulation):
    def element_position(self, chain_link: ChainLink) -> int:
        """Позиция звена в цепочке (1-based). ChainLinkNotInChain если не найдено."""
        ...

    def first_chain_link(self) -> ChainLink:
        """Первое звено для постановки новой идеи. NoChainLinksInChain если пусто."""
        ...

    def chain_link_by_id(self, chain_link_id: ChainLinkID) -> Optional[ChainLink]:
        """Поиск звена по ID, включая технические (accept/reject)."""
        ...

class Idea(MetaManipulation):
    def move_to_next_chain_link(self) -> None:
        """Перевести идею на следующий этап согласования."""
        self.current_chain_link = self.chain.calc_next_chain_link(self.current_chain_link)
        self.mark_changed()

    def reject_idea(self) -> None:
        """Отклонить идею — перевести на этап reject_chain_link."""
        self.current_chain_link = self.chain.reject_chain_link

class ManagerGroup:
    def manager_in(self, manager: Manager) -> bool:
        """Входит ли менеджер в эту группу."""
        ...
```

---

## Правила зависимостей

| Слой | Зависит от | Не зависит от |
|---|---|---|
| `Entity` / `ValueObject` | других `Entity`, `ValueObject`, протоколов | `Repository`, `Mapper`, `ORM`, `UOW`, `Case` |
| `ORMModel` (Django) | ORM Base, Django-типы | `Entity`, `Mapper`, `Repository`, `UOW` |
| `Mapper` / `_orm_to_dto` | `ORMModel`, `Entity`, `ValueObject` | `Repository`, `UOW`, `Case` |
| `QO` / `OO` | `ValueObject`, `ABSQueryObject` | `Entity`, `ORMModel`, `Repository` |
| `DalDto` | stdlib, `ValueObject` | `Entity`, `ORMModel`, `Repository` |
| `Repository` | `ORMModel`, `Mapper`, `ISession`, `QO`/`OO` | `UOW`, `Builder`, `Case` |
| `Builder` | `Entity`, `DalDto`, `Repository` (через конструктор) | `ISession` напрямую, `UOW`, `Case` |
| `UOW` | `Repository`, `Builder`, `ISession`, `Entity`, `QO` | `Case`, другие `UOW` |
| `Case` | `UOW`, `Entity`, `UiDto`, `UoDto`, `convert_*` | `Repository`, `Mapper`, `ORMModel` напрямую |

Ключевые правила:

1. **`Entity` — ядро, ни от чего не зависит.** Все остальные слои могут знать о ней.
2. **`Case` — единственный, кто знает обо всех слоях.** Оркестрирует, но не содержит бизнес-вычислений.
3. **Зависимости направлены от интерфейса к ядру**, но не обратно.
4. **Логика обработки общения не делает бизнес-проверок.** Уникальность, лимиты — зона `Entity` и `Case`.
5. **Билдеры изолируют бизнес-слой от деталей выборки.** `Entity` получает готовые агрегаты или ленивые обёртки.
6. **Каждое хранилище — своя вертикаль.** Redis, HTTP-сервис — свои модели, репозитории, DTO.

---

## Поток выполнения

### HTTP-запрос (пример: создание идеи)

```
1. Фреймворк принимает POST /ideas/, авторизует пользователя через сессию

2. View создаёт IdeaCase и передаёт ему сырой JSON + user_id:
   dto = IdeaUiDto(name=request.data['name'], body=request.data['body'],
                   chain_id=request.data['chain_id'])   # Базовая проверка типов
   case = IdeaCase()

3. Case открывает UOW и запрашивает агрегаты:
   with self.idea_uow:
       author = self.idea_uow.fetch_author(UserID(user_id))
       chain = self.idea_uow.fetch_chain(ChainID(dto.chain_id))
       # chain.chain_links — LazyWrapper, запрос ещё не выполнен

4. Case создаёт новую сущность через фабричный метод Entity:
   idea = Idea.initialize_new_idea(body=dto.body, author=author,
                                   chain=chain, name=dto.name)
   # Бизнес-проверки выполняются внутри Entity/Case (права, лимиты)

5. Case регистрирует объект для сохранения и фиксирует транзакцию:
   self.idea_uow.add_idea_for_save(idea)
   self.idea_uow.commit()
   # UOW → Repository._dto_to_orm → Django ORM bulk_create/save

6. Case конвертирует результат в UoDto и возвращает:
   return convert_idea_to_uo(idea)   # IdeaUoDto

7. View сериализует UoDto в JSON и возвращает 201 Created
```

### Сообщение из шины

```
1. Консьюмер получает сообщение, десериализует в *UiDto
2. Создаёт *Case, вызывает нужный метод, передаёт UiDto
3. Далее — тот же поток, что и для HTTP-запроса
```

---

## Логирование

Обязательно для всех функций, обращающихся к внешним источникам.

```python
# До вызова:
logger.debug('[ClassName.method_name] [<log_id>] Attempting to fetch vehicle id=%s', vehicle_id)

# После успеха:
logger.info('[ClassName.method_name] [<log_id>] Successfully fetched vehicle id=%s', vehicle_id)

# При ошибке:
logger.error('[ClassName.method_name] [<log_id>] Error fetching vehicle id=%s: %s', vehicle_id, str(e))
raise
```

**`log_id`** — уникальный идентификатор операции (`timestamp + uuid4[:8]`), генерируется
в точке входа (`Case`/`UOW`), передаётся вниз или хранится в `thread.locals()`.
Позволяет связать все строки одной операции в логах.

По возможности добавлять второй идентификатор — бизнес-сущности:
```python
logger.info('[IdeaCase.create_idea] [%s] [idea_uid=%s] Successfully created', log_id, idea.idea_uid)
```

---

## Тестирование

### Структура тестов

```
tests/
├── factories/<domain>.py       # Фабрики доменных объектов
├── fakes/dll/uow.py            # Fake*UOW — подменяет реальный UOW
└── <domain>/
    ├── cases/test_*.py         # Тесты Case (use cases)
    └── domain/test_*.py        # Тесты Entity (бизнес-логика)
```

### Fake UOW

Подменяет реальный UOW в тестах. Методы `fetch_*` возвращают заготовленные объекты.
Методы `add_*_for_save` сохраняют объект как атрибут для последующей проверки.

```python
class FakeIdeaUOW(FakeUOW):
    def __init__(self, chain=None, author=None, idea=None):
        self.__chain = chain
        self.__author = author
        self.__idea = idea
        self.idea = None  # Здесь будет сохранён объект после add_idea_for_save

    def fetch_chain(self, *args, **kwargs) -> Chain:
        return self.__chain

    def fetch_author(self, *args, **kwargs) -> IdeaAuthor:
        return self.__author

    def fetch_idea(self, *args, **kwargs) -> Idea:
        return self.__idea

    def add_idea_for_save(self, idea: Idea) -> None:
        self.idea = idea

    def commit(self) -> None:
        pass
```

### Фабрики

Создают доменные объекты с разумными дефолтами. Принимают `Empty()` как «не задано».

```python
class IdeaFactory:
    @staticmethod
    def create_idea(
        author: IdeaAuthor,
        chain: Chain,
        current_chain_link: ChainLink,
        idea_id: Union[IdeaID, Empty] = Empty(),
        body: Union[str, Empty] = Empty(),
        name: Union[str, Empty] = Empty(),
    ) -> Idea:
        return Idea(
            idea_id=idea_id if not isinstance(idea_id, Empty) else IdeaID(randrange(1, 1000)),
            author=author,
            body=body if not isinstance(body, Empty) else generate_random_string(10),
            chain=chain,
            current_chain_link=current_chain_link,
            name=name if not isinstance(name, Empty) else generate_random_string(10),
        )
```

### Тест Case

```python
class TestIdeaCase(TestCase):
    def setUp(self):
        self.author = IdeaAuthorFactory.create()
        self.chain = ChainFactory.create()
        self.idea = IdeaFactory.create_idea(
            author=self.author, chain=self.chain,
            current_chain_link=self.chain.first_chain_link(),
        )

    def test_create_new_idea(self):
        uow = FakeIdeaUOW(chain=self.chain, author=self.author)
        case = IdeaCase(uow_cls=lambda: uow)
        dto = IdeaUiDto(name='Test', body='Body', chain_id=int(self.chain.chain_id))

        case.create_idea(
            user_id=int(self.author.user_id),
            body=dto.body,
            chain_id=dto.chain_id,
            name=dto.name,
        )

        self.assertIsNotNone(uow.idea)
        self.assertTrue(uow.idea.is_changed())

    def test_edit_idea_permission_denied(self):
        other_author = IdeaAuthorFactory.create()
        uow = FakeIdeaUOW(chain=self.chain, author=other_author, idea=self.idea)
        case = IdeaCase(uow_cls=lambda: uow)

        with self.assertRaises(PermissionDenied):
            case.edit_idea(
                user_id=int(other_author.user_id),
                idea_id=int(self.idea.idea_id),
                body='New body',
            )
```

---

## Сводные таблицы

### Морфемы классов

| Морфема | Директория | Пример | БД | Бизнес | Мутация |
|---|---|---|---|---|---|
| `Entity` (без суффикса) | `domain/` | `Idea`, `Chain` | Нет | Да | Да (своей) |
| `ValueObject` / `NewType` | `domain/types.py` | `IdeaID`, `ChainID` | Нет | Нет | Нет |
| `ORMModel` (Django) | `<app>/models.py` | `IdeaORM` | Нет | Нет | Нет |
| `*Mapper` | `dal/*/mapper.py` | `ManagerMapper` | Нет | Нет | Нет |
| `*QO` | `dal/*/qo.py` | `IdeaQO` | Нет | Нет | Нет |
| `*OO` | `dal/*/oo.py` | `IdeaOO` | Нет | Нет | Нет |
| `*DalDto` | `dal/*/dto.py` | `IdeaDalDto` | Нет | Нет | Нет |
| `*Repository` | `dal/*/repo.py` | `IdeaRepository` | R+W | Нет | Нет |
| `*Builder` | `dll/*/builders.py` | `ChainBuilder` | Через конструктор | Минимум | Нет |
| `*UOW` | `dll/*/uow.py` | `IdeaUOW` | Через Repository | Нет | Нет (только flush) |
| `*Case` | `cases/*/` | `IdeaCase` | Через UOW | Оркестрация | Нет |
| `*UiDto` | `cases/*/dto.py` | `IdeaUiDto` | Нет | Нет | Нет |
| `*UoDto` | `cases/*/dto.py` | `IdeaUoDto` | Нет | Нет | Нет |

### Морфемы функций и методов

| Морфема | Слой | Хранилище | Бизнес | Вычисления | Вызывает |
|---|---|---|---|---|---|
| `fetch` | Repository, UOW, Case | Только чтение | Нет | Нет | Нет других `fetch` |
| `persist` | Repository | Только запись | Нет | Нет | — |
| `encache` | Инфраструктура | Кэш запись | Нет | Нет | `generate` для ключей |
| `decache` | Инфраструктура | Кэш чтение | Нет | Нет | — |
| `recache` | Инфраструктура | Кэш R/W + БД R | Нет | Нет | — |
| `send` | Инфраструктура | Внешняя запись | Нет | Нет | — |
| `convert` | UOW, Mapper, Case | Нет | Нет | Технические | — |
| `build` / `build_one` / `build_many` | Builder, UOW | Через `fetch/*cache` | Нет | Нет | `fetch`, `convert`, `build_lazy_*` |
| `build_lazy_one` / `build_lazy_many` / `build_lazy` | Builder | Через конструктор | Нет | Нет | возвращает `LazyWrapper` |
| `calc` | Entity | Нет | Да | Да | `calc`, `verify` |
| `verify` | Entity, модульные | Нет | Да | Минимум | — |
| `validate` | Entity, модульные | Нет | Нет | Нет | — |
| `initialize` | Entity (classmethod) | Нет | Нет | Нет | — |
| `generate` | Утилиты | Нет | Нет | Да | `calc` |
| `filter` | Утилиты | Нет | Минимум | Нет | `verify_is`, `validate_is` |
| `find` | Утилиты | Нет | Да (поиск) | Технические | `calc`, `filter` |
| `map` | Утилиты | Нет | Нет | Нет | — |
| `group` | Утилиты | Нет | Нет | Нет | — |
| `can_*` | Entity | Нет | Да | Нет | — возвращает `bool` |
| `is_*` | Entity, MetaManipulation | Нет | Да | Нет | — возвращает `bool` |
| `mark_*` | Entity, MetaManipulation | Нет | Нет | Нет | — мутирует `_meta` |
| `set_*` / `set_for_change` / `set_as_deleted` | Entity | Нет | `set_as_deleted` — да | Нет | `set_for_change` |
| `set_*_as_now` | MetaManipulation | Нет | Нет | Нет | `set_*` |
| `get_*` | Entity | Нет | Нет | Нет | — возвращает поле |
| `from_*` | Entity (classmethod) | Нет | Нет | Нет | — маппинг типов |
| `update` / `update_*` | Entity | Нет | Нет | Нет | — мутирует поля |
| `replace_*` | Entity | Нет | Нет | Нет | `set_for_change`, `set_as_deleted` |
| `replace_id_from_meta` | Entity | Нет | Нет | Нет | — инфраструктурный |
| `add_*_for_save` | UOW | Нет | Нет | Нет | `set_updated_at_as_now`, `mark_changed` |
| `create_*` / `delete_*` / `edit_*` | Case | Через UOW | Оркестрация | Нет | UOW, Entity, `convert` |
| `<action>_<entity>` (доменные) | Case | Через UOW | Оркестрация | Нет | UOW, Entity |
| Семантические методы Entity | Entity | Нет | Да | Да / Нет | Entity-методы |
