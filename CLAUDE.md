# Спецификация для Claude Code — проект Watchman (Telegram Bot)


Этот документ — руководство для разработки. Следуй ему при написании любого кода.

---

## Принципы

- **Один слой — одна ответственность.** Не смешивать доменную логику с инфраструктурой.
- **Морфема = ответственность.** Имя класса/функции сразу говорит, что он делает и к какому слою относится.
- **Вычисления отдельно от последовательностей.** Функция либо считает, либо оркестрирует вызовы — не оба разом.
- **Бизнес-правила требуют комментариев.** Бизнес-логика непрозрачна для разработчика — всегда объясняй, что и почему.
- **Тестируемость — первый класс.** Классы без внешних зависимостей тестируются без моков; с зависимостями — получают их через конструктор.
- **Логируй все внешние вызовы.** До и после каждого обращения к внешнему хранилищу/сервису.
- **Не изобретай синонимы.** Каждому понятию предметной области — одно английское слово; зафиксировать в глоссарии.
- **Комментарии и докстринги — только на русском языке.** Идентификаторы (имена классов, методов, переменных) — только на английском. Смешение языков внутри одной единицы запрещено.
- Используй context7
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
│   │   └── vendor/sqlalchemy/
│   │       └── repository.py   # SQLAlchemyRepository, QoOrmMapperLine
│   └── mapper.py               # ABSMapper
│
├── domain/                     # Бизнес-модель (Entity, ValueObject)
│   └── <domain>/
│       ├── main.py             # Сущности и агрегаты
│       └── types.py            # NewType-значения (UserID, AlertID, ...)
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
├── bot/                        # Telegram-слой (handlers, keyboards, middlewares)
│   ├── handlers/
│   │   └── <domain>.py         # Aiogram-хэндлеры
│   ├── keyboards/
│   │   └── <domain>.py         # InlineKeyboard, ReplyKeyboard
│   └── middlewares/
│       └── *.py
│
├── infrastructure/
│   ├── db/
│   │   ├── models/             # SQLAlchemy ORM-модели
│   │   │   └── <domain>.py     # *ORM (Table + mapped_column)
│   │   ├── migrations/         # Alembic-миграции
│   │   │   └── versions/
│   │   └── session.py          # get_session, engine
│   └── config.py               # Настройки приложения
│
└── tests/
    ├── factories/
    │   └── <domain>.py         # *Factory
    └── fakes/
        └── dll/
            └── uow.py          # Fake*UOW
```

---

## Слои архитектуры

Архитектура делится на две оси:

- **Горизонтальная (слева направо)** — интерфейсная сторона: от внешнего мира (Telegram) до бизнес-кейса
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
│                    │                          │               │ SQLAlchemy ORM + *Mapper     │
└────────────────────┴──────────────────────────┴───────────────┴──────────────────────────────┘
```

### Telegram-слой (`bot/`)

Хэндлеры aiogram — аналог HTTP-View. Только парсинг `Update`/`Message` в `*UiDto` и вызов `*Case`. Никакой бизнес-логики.

```python
# bot/handlers/alert.py

@router.message(Command('create_alert'))
async def create_alert_handler(message: Message, session: AsyncSession):
    dto = AlertUiDto(
        user_id=message.from_user.id,
        text=message.text,
    )
    case = AlertCase(session=session)
    result = await case.create_alert(dto)
    await message.answer(f'Алерт создан: {result.alert_id}')
```

**Правило:** хэндлер не знает о домене — только парсит входные данные и форматирует ответ.

---

## SQLAlchemy — Модель хранения данных

### Объявление ORM-моделей

Модели живут в `infrastructure/db/models/<domain>.py`. Используем `DeclarativeBase` + `mapped_column`. Только колонки и маппинг — никакой логики. Не знают о доменных сущностях.

```python
# infrastructure/db/models/alert.py

from sqlalchemy import String, BigInteger, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from infrastructure.db.base import Base

class AlertORM(Base):
    __tablename__ = 'alert'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    text: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
```

```python
# infrastructure/db/base.py

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

### Сессия

```python
# infrastructure/db/session.py

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from infrastructure.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        yield session
```

Сессия передаётся через конструктор в `UOW`, а не создаётся внутри него.

### Правила SQLAlchemy

- **Только `AsyncSession`** — проект асинхронный (aiogram), синхронные сессии запрещены.
- **`expire_on_commit=False`** — объекты доступны после `commit()` без повторного SELECT.
- **Миграции через Alembic** — `alembic revision --autogenerate`. Вручную не менять схему.
- **Связи (`relationship`)** — объявлять только там, где ленивая загрузка явно нужна. По умолчанию — `lazy='raise'` или явный `selectinload`/`joinedload` в запросе.
- **Транзакция принадлежит UOW** — `session.commit()` / `session.rollback()` только в `*UOW`, не в Repository.

### SQLAlchemy Repository

```python
# dal/alert/repo.py

from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession
from framework.data_access_layer.vendor.sqlalchemy.repository import SQLAlchemyRepository
from infrastructure.db.models.alert import AlertORM
from dal.alert.dto import AlertDalDto
from dal.alert.qo import AlertQO

class AlertRepository(SQLAlchemyRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def fetch_one(self, filter_params: AlertQO) -> AlertDalDto:
        stmt = select(AlertORM)
        stmt = self._apply_filters(stmt, filter_params)
        result = await self._session.execute(stmt)
        orm_obj = result.scalar_one_or_none()
        if orm_obj is None:
            raise AlertNotFound()
        return self._orm_to_dto(orm_obj)

    async def fetch_many(self, filter_params: AlertQO) -> list[AlertDalDto]:
        stmt = select(AlertORM)
        stmt = self._apply_filters(stmt, filter_params)
        result = await self._session.execute(stmt)
        return [self._orm_to_dto(row) for row in result.scalars().all()]

    async def add(self, domain_obj) -> AlertDalDto:
        orm_obj = self._dto_to_orm(domain_obj)
        self._session.add(orm_obj)
        await self._session.flush()   # ID проставляется без commit
        return self._orm_to_dto(orm_obj)

    async def add_many(self, domain_objects: list) -> None:
        orm_objects = [self._dto_to_orm(obj) for obj in domain_objects]
        self._session.add_all(orm_objects)
        await self._session.flush()

    def _orm_to_dto(self, orm_obj: AlertORM) -> AlertDalDto:
        return AlertDalDto(
            alert_id=AlertID(orm_obj.id),
            user_id=UserID(orm_obj.user_id),
            text=orm_obj.text,
            is_active=orm_obj.is_active,
            is_deleted=orm_obj.is_deleted,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def _dto_to_orm(self, alert) -> AlertORM:
        return AlertORM(
            id=alert.alert_id if not alert.is_new() else None,
            user_id=alert.get_user_id(),
            text=alert.text,
            is_active=alert.is_active,
            is_deleted=alert.is_deleted(),
        )

    def _apply_filters(self, stmt, qo: AlertQO):
        if not isinstance(qo.alert_id, Empty):
            stmt = stmt.where(AlertORM.id == int(qo.alert_id))
        if not isinstance(qo.user_id, Empty):
            stmt = stmt.where(AlertORM.user_id == int(qo.user_id))
        if not isinstance(qo.is_deleted, Empty):
            stmt = stmt.where(AlertORM.is_deleted == qo.is_deleted)
        return stmt
```

### SQLAlchemy UOW

```python
# dll/alert/uow.py

from sqlalchemy.ext.asyncio import AsyncSession
from framework.data_logic_layer.uow import BaseUnitOfWork

class AlertUOW(BaseUnitOfWork):
    def __init__(self, session: AsyncSession,
                 alert_repo_cls=AlertRepository,
                 user_repo_cls=UserRepository):
        self._session = session
        self._alert_repo = alert_repo_cls(session)
        self._user_repo = user_repo_cls(session)
        self._domain_objects_for_save: list = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self._session.rollback()
        return False

    async def fetch_alert(self, query_object: AlertQO) -> Alert:
        alert_dal_dto = await self._alert_repo.fetch_one(filter_params=query_object)
        return AlertBuilder(alert_dal_dto=alert_dal_dto).build_one()

    async def fetch_user(self, user_id: UserID) -> TelegramUser:
        user_dal_dto = await self._user_repo.fetch_one(filter_params=UserQO(user_id=user_id))
        return TelegramUser(user_id=user_dal_dto.user_id, username=user_dal_dto.username)

    def add_alert_for_save(self, alert: Alert) -> None:
        alert.set_updated_at_as_now()
        alert.mark_changed()
        self._domain_objects_for_save.append(alert)

    async def commit(self) -> None:
        alerts = [o for o in self._domain_objects_for_save if isinstance(o, Alert)]
        await self._alert_repo.add_many(alerts)
        await self._session.commit()
        self._domain_objects_for_save = []
```

**Использование в `Case`:**

```python
async with self.alert_uow:
    alert = await self.alert_uow.fetch_alert(AlertQO(alert_id=alert_id))
    alert.deactivate()
    self.alert_uow.add_alert_for_save(alert)
    await self.alert_uow.commit()
```

### Alembic

- Конфиг: `alembic.ini` в корне проекта.
- Модели импортируются в `alembic/env.py` перед `target_metadata = Base.metadata`.
- Все миграции автогенерируются: `alembic revision --autogenerate -m "описание"`.
- Применять: `alembic upgrade head`.
- Никогда не делать `Base.metadata.create_all()` в продакшн-коде.

---

## Морфемы классов

Имя класса: `<BusinessName><Morpheme>`

### `Entity` (неявная морфема — суффикса нет)

**Слой**: `domain/<domain>/main.py`

Хранит состояние бизнес-сущности. Содержит бизнес-методы, изменяющие собственное состояние или вызывающие методы зависимых сущностей.

```python
class Alert(MetaManipulation): ...    # Агрегат
class TelegramUser(MetaManipulation): ...
```

**Зависит от**: других `Entity`, `ValueObject`, `MetaManipulation`, протоколов из `domain/`.
**Не зависит от**: `Repository`, `Mapper`, `ORM`, `UOW`, `Builder`, `Case`.

Методы на Entity:

| Паттерн | Пример | Назначение |
|---|---|---|
| `initialize_new*` | `Alert.initialize_new_alert(...)` | Фабричный classmethod |
| `is_*` | `alert.is_active()` | Предикат состояния |
| `can_*` | `user.can_delete_alert(alert)` | Проверка разрешения |
| `mark_*` | `alert.mark_deleted()` | Смена мета-состояния |
| `set_*` | `alert.set_text(text)` | Сеттер |
| `get_*` | `alert.get_user_id()` | Геттер |

---

### `ValueObject` / `NewType` (неявная морфема)

**Слой**: `domain/<domain>/types.py`

Типизирует примитивные значения с доменным смыслом. Неизменяемы.

```python
AlertID = NewType('AlertID', int)
UserID = NewType('UserID', int)
ChatID = NewType('ChatID', int)
```

**Зависит от**: только stdlib.

---

### `MetaManipulation` + `BaseMeta`

**Слой**: `framework/data_logic_layer/meta.py`

Миксин для трекинга технических полей (`is_changed`, `is_deleted`, `created_at`, `updated_at`).

```python
class Alert(MetaManipulation):
    ...
    alert.mark_changed()   # _meta.is_changed = True
    alert.is_changed()     # True
    alert.is_deleted()     # False
```

---

### `<Business>Case`

**Слой**: `cases/<domain>/<entity>.py`

Связующий слой: оркестрирует один бизнес-кейс. Содержит методы-действия (`create_*`, `edit_*`, `delete_*`). Не содержит бизнес-вычислений — только последовательность вызовов.

```python
class AlertCase:
    def __init__(self, session: AsyncSession, uow_cls=AlertUOW):
        self.alert_uow = uow_cls(session=session)

    async def create_alert(self, dto: AlertUiDto) -> AlertUoDto: ...
    async def delete_alert(self, user_id: int, alert_id: int) -> None: ...
    async def deactivate_alert(self, user_id: int, alert_id: int) -> None: ...
```

---

### `<Business>UOW`

**Слой**: `dll/<domain>/uow.py`

Оркестрирует транзакцию: управляет несколькими `Repository` и `Builder`. Используется как **асинхронный** контекстный менеджер (`async with`). Один `UOW` = один бизнес-кейс.

```python
class AlertUOW(BaseUnitOfWork):
    # fetch_* — получение агрегатов (async)
    async def fetch_alert(self, query_object: AlertQO) -> Alert: ...
    async def fetch_user(self, user_id: UserID) -> TelegramUser: ...

    # add_*_for_save — регистрация объекта (синхронный)
    def add_alert_for_save(self, alert: Alert) -> None: ...

    # commit — async
    async def commit(self) -> None: ...
```

**Зависит от**: `Repository`, `Builder`, `AsyncSession`, `Entity`, `QO`.
**Не зависит от**: `Case`, другие `UOW`.

---

### `<Business>Builder`

**Слой**: `dll/<domain>/builders.py`

Собирает сложный доменный объект из нескольких частей. Все данные получает через конструктор — сам не ходит в БД. Поддерживает ленивую сборку.

```python
class AlertBuilder(ABSEntityFromRepoBuilder):
    def build_one(self) -> Alert: ...
    def build_many(self) -> list[Alert]: ...
    def build_lazy_one(self) -> LazyWrapper[Alert]: ...
    def build_lazy_many(self) -> LazyWrapper[list[Alert]]: ...
```

**Зависит от**: `Entity`, `ValueObject`, `DalDto`, `Repository` (через конструктор).
**Не зависит от**: `UOW`, `AsyncSession`, `Case`.

---

### `<Business>Repository`

**Слой**: `dal/<domain>/repo.py`

Единственное место SQL-запросов. Возвращает `*DalDto`, не `Entity`. Принимает `*QO` / `*OO`. Все методы **async**.

| Метод | Назначение |
|---|---|
| `async fetch_one(filter_params, ...)` | Один объект |
| `async fetch_many(filter_params, ...)` | Список |
| `async add(domain_model)` | Создать |
| `async add_many(sequence)` | Создать несколько |
| `async update_one(domain_model)` | Обновить |

**Зависит от**: ORM-модель, `Mapper`, `AsyncSession`, `QO`, `OO`.
**Не зависит от**: `UOW`, `Builder`, `Case`, другие `Repository`.

---

### `<Business>Mapper`

**Слой**: `dal/<domain>/mapper.py`

Конвертирует ORM-объект → `*DalDto` и обратно. Только преобразование формата. Статические методы, без состояния. Внутри `Repository` конвертация реализуется методами `_orm_to_dto` / `_dto_to_orm`.

---

### `<Business>QO` (QueryObject)

**Слой**: `dal/<domain>/qo.py`

Dataclass с параметрами фильтрации. `Empty()` = поле не задано → не попадает в WHERE.

```python
@dataclass
class AlertQO(ABSQueryObject):
    alert_id: Optional[Union[AlertID, Empty]] = field(default_factory=Empty)
    user_id: Optional[Union[UserID, Empty]] = field(default_factory=Empty)
    is_deleted: Optional[Union[bool, Empty]] = field(default_factory=Empty)
    is_active: Optional[Union[bool, Empty]] = field(default_factory=Empty)
```

---

### `<Business>DalDto`

**Слой**: `dal/<domain>/dto.py`

Промежуточный dataclass между ORM и доменным слоем.

```python
@dataclass
class AlertDalDto(IDTO):
    alert_id: AlertID
    user_id: UserID
    text: str
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime]
```

**Зависит от**: только stdlib, `ValueObject`.
**Не зависит от**: `Entity`, `ORMModel`, `Repository`.

---

### `<Business>UiDto` / `<Business>UoDto`

**Слой**: `cases/<domain>/dto.py`

- `*UiDto` — входные данные от пользователя (из Telegram Update)
- `*UoDto` — исходящие данные пользователю (для формирования ответа в хэндлере)

```python
@dataclass
class AlertUiDto:
    user_id: int
    text: str

@dataclass
class AlertUoDto:
    alert_id: int
    text: str
    is_active: bool
    created_at: datetime
```

---

## Морфемы функций и методов

Паттерн имени: `<primary_morpheme>_<?secondary_morpheme>_<business_morpheme>`

Морфемы можно комбинировать без `and`. Существительные — в глоссарии, синонимы запрещены.

### `fetch_*`

**Слой**: Repository (DAL), UOW (DLL), Case

Получает данные из внешнего источника (БД, кэш). Только чтение. В проекте — **async**.

```python
# В UOW
async def fetch_alert(self, query_object: AlertQO) -> Alert:
    logger.debug('[AlertUOW.fetch_alert] Attempting to fetch alert id=%s', query_object.alert_id)
    try:
        alert_dal_dto = await self._alert_repo.fetch_one(filter_params=query_object)
        result = AlertBuilder(alert_dal_dto=alert_dal_dto).build_one()
        logger.info('[AlertUOW.fetch_alert] Successfully fetched alert id=%s', query_object.alert_id)
        return result
    except Exception as e:
        logger.error('[AlertUOW.fetch_alert] Error: %s', str(e))
        raise
```

### `persist_*`

**Слой**: Repository (DAL)

Сохраняет данные. Только запись. Суффиксы `_created_`, `_updated_`, `_deleted_` обязательны.

### `build_*` / `build_one` / `build_many` / `build_lazy_one` / `build_lazy_many`

**Слой**: Builder (DLL), UOW (DLL)

Собирает сложный доменный объект. Может вызывать `fetch_*`, `convert_*`. Не делает прямых ORM-вызовов.

### `convert_*`

**Слой**: UOW (DLL), Mapper (DAL), Case

Преобразует данные из одного формата в другой без изменения информации.

```python
def convert_alert_to_output(self, alert: Alert) -> AlertUoDto:
    return AlertUoDto(
        alert_id=alert.alert_id,
        text=alert.text,
        is_active=alert.is_active,
        created_at=alert.created_at,
    )
```

### `calc_*`

**Слой**: Entity (domain). Вычисления с бизнес-смыслом. Обязателен комментарий.

### `verify_*`

**Слой**: Entity (domain). Проверяет бизнес-правило, выбрасывает исключение при нарушении.

### `validate_*`

**Слой**: Entity, модульные функции. Технические проверки формата/типа. Не для бизнес-правил.

### `initialize_*`

**Слой**: Entity (classmethod). Создаёт новый объект с бизнес-дефолтами. Вызывает `mark_changed()`.

### `send_*`

**Слой**: инфраструктурный. Отправляет данные во внешние системы. В Telegram — вызов `bot.send_message()`.

### `can_*`

**Слой**: Entity. Возвращает `bool`. Инкапсулирует право на действие.

### `is_*`

**Слой**: Entity, MetaManipulation. Возвращает `bool`. Предикат внутреннего состояния.

### `mark_*`

**Слой**: Entity, MetaManipulation. Изменяет технические флаги `_meta`.

### `set_*`

**Слой**: Entity. Устанавливает поле, фиксирует изменение через `set_for_change()`.

### `get_*`

**Слой**: Entity. Геттер приватного поля или тривиальное приведение типа.

### `from_*`

**Слой**: Entity (classmethod). Создаёт Entity из объекта другого доменного типа.

### `update` / `update_*`

**Слой**: Entity. Обновляет поля, помечает `is_changed` только при реальном изменении.

### `add_*_for_save`

**Слой**: UOW (DLL). Регистрирует объект для сохранения при следующем `commit()`.

### Методы `*Case`

| Группа | Паттерн | Структура |
|---|---|---|
| Создание | `create_<entity>` | `initialize_new_*` → `add_*_for_save` → `commit` |
| Удаление | `delete_<entity>` | `fetch` → `can_*` → `mark_deleted` → `add_*_for_save` → `commit` |
| Изменение | `edit_<entity>` | `fetch` → `can_*` → `is_*` → `update` → `add_*_for_save` → `commit` |
| Доменное действие | `<action>_<entity>` | `fetch` → `is_*` → метод Entity → `add_*_for_save` → `commit` |
| Чтение | `fetch_<entity>` | `fetch` через UOW → `convert_*` → `UoDto` |

**Правила для всех методов Case:**
- Нет бизнес-вычислений — только последовательность вызовов.
- Проверка прав: `entity.can_*` → `raise` при `False`.
- Проверка состояния: `entity.is_*` → `raise` при `False`.
- Открывать UOW через `async with self.uow:`.

---

## Правила зависимостей

| Слой | Зависит от | Не зависит от |
|---|---|---|
| `Entity` / `ValueObject` | других `Entity`, `ValueObject`, протоколов | `Repository`, `Mapper`, `ORM`, `UOW`, `Case` |
| `ORMModel` (SQLAlchemy) | `Base`, SQLAlchemy-типы | `Entity`, `Mapper`, `Repository`, `UOW` |
| `Mapper` / `_orm_to_dto` | `ORMModel`, `Entity`, `ValueObject` | `Repository`, `UOW`, `Case` |
| `QO` / `OO` | `ValueObject`, `ABSQueryObject` | `Entity`, `ORMModel`, `Repository` |
| `DalDto` | stdlib, `ValueObject` | `Entity`, `ORMModel`, `Repository` |
| `Repository` | `ORMModel`, `Mapper`, `AsyncSession`, `QO`/`OO` | `UOW`, `Builder`, `Case` |
| `Builder` | `Entity`, `DalDto`, `Repository` (через конструктор) | `AsyncSession` напрямую, `UOW`, `Case` |
| `UOW` | `Repository`, `Builder`, `AsyncSession`, `Entity`, `QO` | `Case`, другие `UOW` |
| `Case` | `UOW`, `Entity`, `UiDto`, `UoDto`, `convert_*` | `Repository` (любой: SQL, Redis, HTTP), `Mapper`, `ORMModel` напрямую |
| `Handler` (bot/) | `Case`, `UiDto`, `UoDto` | `UOW`, `Repository`, `Entity` напрямую |

Ключевые правила:

1. **`Entity` — ядро, ни от чего не зависит.** Все остальные слои могут знать о ней.
2. **`Case` вызывает только `UOW`.** `Case` не знает ни о каких `Repository` напрямую — ни Postgres, ни Redis, ни HTTP. Единственный фасад для всех хранилищ — `UOW`. Прямой вызов репозитория из `Case` — протекание абстракции.
3. **`UOW` — единственный фасад хранилищ для `Case`.** Если `Case` работает с несколькими хранилищами (например, Postgres + Redis), все они инкапсулированы внутри одного `UOW` через соответствующие репозитории. `UOW` выставляет методы уровня домена (`fetch_captcha`, `create_captcha`), а не репозитории напрямую.
4. **`Handler` вызывает только `Case`.** Никаких прямых обращений к UOW, Repository, Entity.
5. **Зависимости направлены от интерфейса к ядру**, но не обратно.
6. **Транзакция принадлежит UOW.** `session.commit()` — только в `UOW.commit()`.
7. **Каждое хранилище — своя вертикаль внутри UOW.** Redis, внешний HTTP — свои репозитории, DTO, инжектируются в `UOW` через конструктор.

---

## Поток выполнения (Telegram-команда)

```
1. Пользователь отправляет команду /create_alert <текст>

2. Хэндлер aiogram парсит Update в UiDto:
   dto = AlertUiDto(user_id=message.from_user.id, text=message.text)

3. Хэндлер создаёт Case, передаёт session:
   case = AlertCase(session=session)

4. Case открывает UOW и запрашивает агрегаты:
   async with self.alert_uow:
       user = await self.alert_uow.fetch_user(UserID(dto.user_id))

5. Case создаёт новую сущность:
   alert = Alert.initialize_new_alert(user=user, text=dto.text)

6. Case регистрирует и сохраняет:
   self.alert_uow.add_alert_for_save(alert)
   await self.alert_uow.commit()
   # UOW → Repository._dto_to_orm → session.add → session.flush → session.commit

7. Case конвертирует результат в UoDto и возвращает:
   return convert_alert_to_output(alert)

8. Хэндлер форматирует ответ и отправляет пользователю:
   await message.answer(f'Алерт #{result.alert_id} создан.')
```

---

## Логирование

Обязательно для всех методов, обращающихся к внешним хранилищам (БД, Redis, HTTP и т.д.).

### Правило уровней

| Момент | Уровень | Содержание |
| --- | --- | --- |
| **До** обращения к хранилищу | `DEBUG` | Попытка выполнить операцию + ключевые параметры |
| **После** успешного обращения | `INFO` | Операция выполнена успешно + результат |
| **При ошибке** | `ERROR` | Описание ошибки, затем `raise` |

```python
# До обращения к хранилищу — debug:
logger.debug('[ClassName.method_name] Попытка получить сессию капчи key=%s', key)

result = await self._redis.get(key)  # ← обращение к хранилищу

# После успешного обращения — info:
logger.info('[ClassName.method_name] Сессия капчи получена key=%s', key)

# При ошибке — error + raise:
logger.error('[ClassName.method_name] Ошибка при получении сессии key=%s: %s', key, str(e))
raise
```

### Правила формата

- Префикс сообщения: `[ClassName.method_name]` — всегда, без исключений.
- `DEBUG` описывает **намерение**: «попытка сохранить», «попытка получить», «попытка удалить».
- `INFO` описывает **факт**: «сохранено», «получено», «удалено» — с ключевыми идентификаторами.
- Логировать нужно непосредственно вокруг вызова хранилища, не в начале/конце метода.
- Если метод не обращается к хранилищу — логировать не нужно.

---

## Тестирование

```
tests/
├── factories/<domain>.py       # Фабрики доменных объектов
├── fakes/dll/uow.py            # Fake*UOW
└── <domain>/
    ├── cases/test_*.py         # Тесты Case
    └── domain/test_*.py        # Тесты Entity
```

### Fake UOW

```python
class FakeAlertUOW(FakeUOW):
    def __init__(self, user=None, alert=None):
        self.__user = user
        self.__alert = alert
        self.alert = None  # сюда попадает объект после add_alert_for_save

    async def fetch_user(self, *args, **kwargs) -> TelegramUser:
        return self.__user

    async def fetch_alert(self, *args, **kwargs) -> Alert:
        return self.__alert

    def add_alert_for_save(self, alert: Alert) -> None:
        self.alert = alert

    async def commit(self) -> None:
        pass

    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
```

### Тест Case

```python
class TestAlertCase(IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = TelegramUserFactory.create()
        self.alert = AlertFactory.create_alert(user=self.user)

    async def test_create_alert(self):
        uow = FakeAlertUOW(user=self.user)
        case = AlertCase(session=None, uow_cls=lambda session: uow)
        dto = AlertUiDto(user_id=int(self.user.user_id), text='Test alert')

        await case.create_alert(dto)

        self.assertIsNotNone(uow.alert)
        self.assertTrue(uow.alert.is_changed())
        self.assertEqual(uow.alert.text, 'Test alert')

    async def test_delete_alert_permission_denied(self):
        other_user = TelegramUserFactory.create()
        uow = FakeAlertUOW(user=other_user, alert=self.alert)
        case = AlertCase(session=None, uow_cls=lambda session: uow)

        with self.assertRaises(PermissionDenied):
            await case.delete_alert(
                user_id=int(other_user.user_id),
                alert_id=int(self.alert.alert_id),
            )
```

---

## Сводная таблица морфем классов

| Морфема | Директория | Пример | БД | Бизнес | Мутация |
|---|---|---|---|---|---|
| `Entity` (без суффикса) | `domain/` | `Alert`, `TelegramUser` | Нет | Да | Да (своей) |
| `ValueObject` / `NewType` | `domain/types.py` | `AlertID`, `UserID` | Нет | Нет | Нет |
| `ORMModel` (SQLAlchemy) | `infrastructure/db/models/` | `AlertORM` | Нет | Нет | Нет |
| `*Mapper` | `dal/*/mapper.py` | `AlertMapper` | Нет | Нет | Нет |
| `*QO` | `dal/*/qo.py` | `AlertQO` | Нет | Нет | Нет |
| `*OO` | `dal/*/oo.py` | `AlertOO` | Нет | Нет | Нет |
| `*DalDto` | `dal/*/dto.py` | `AlertDalDto` | Нет | Нет | Нет |
| `*Repository` | `dal/*/repo.py` | `AlertRepository` | R+W | Нет | Нет |
| `*Builder` | `dll/*/builders.py` | `AlertBuilder` | Через конструктор | Минимум | Нет |
| `*UOW` | `dll/*/uow.py` | `AlertUOW` | Через Repository | Нет | Нет (только flush) |
| `*Case` | `cases/*/` | `AlertCase` | Через UOW | Оркестрация | Нет |
| `*UiDto` | `cases/*/dto.py` | `AlertUiDto` | Нет | Нет | Нет |
| `*UoDto` | `cases/*/dto.py` | `AlertUoDto` | Нет | Нет | Нет |
