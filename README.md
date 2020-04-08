# django-fk-fasted

Пакет с наследниками класса поля модели - ForeignKey с измененной логикой валидации.

Ускоряет проведения валидации заменяя запросы к базе, на обращение в кеш

Стек:

    - Django2.2]2.3
    - Redis


## Содержание

- [Предусловия для корректной работы пакета](#предусловия-для-корректной-работы-пакета)
- [Описание существующих классов](#описание-существующих-классов)
    * [ForeignKeyWithOutInstance](#ForeignKeyWithOutInstance)
    * [ForeignKey](#ForeignKey)
- [Установка](#установка)
    * [Как развернуть проект для разработки](#как-развернуть-проект-для-разработки)
    * [Как использовать](#как-использовать)
    
- [Конфигурация](#конфигурация)

- [Разработчики](#разработчики)


### Предусловия для корректной работы пакета

* Должен быть установлен python3.7 глобально.
* Проект использует фреймворк `Django` 
* Должен быть запущен `Redis`
* В проекте сконфигурирован кеш (указано в [конфигурации](#конфигурация))

---
### Описание существующих классов

##### ForeignKeyWithOutInstance

Заменена логика метода `is_valid`, которая по спец ключу хранит множество из PK(primary key) модели, на которую сделана связь. 

##### ForeignKey

Для этого класса заменяется `ModelChoiceField`, на наследника у которого заменен 
метод `to_python`, и берет данные из базы в самый крайний случай: если нет данных в 
кеше.

---

### Установка

#### Как использовать

1. Указать в `requirements.txt` зависимость от пакета:
    ```text
    git+ssh://git@github.com/Ikudza/django-fk-fasted.git@v0.0.1#egg=django-fk-fasted
     ```
2. Установить зависимость:
    ```bash
    pip install -r requirements.txt
    ```
3. Для того чтобы можно было использовать переопредленный класс `ForeingKey`, нужно: 

* определить кеш в проекте(см. [конфигурация пакета](#конфигурация)).
4. Для использования импортируем класс `ForeingKey` и указать его:

    ```python
   from django.db import models
   
   from django_fk_fasted import ForeignKey
   
   class MyModel(models.Model):
      parent = ForeignKey(
          to='self', 
          cache_time=3*60, 
          null=True, 
          blank=True, 
          on_delete=models.DO_NOTHING
      )
   ```
3. Создать и накатить миграции:

    ```bash
    ../bin/python3 bin/manage makemigrations
    ../bin/python3 bin/manage migrate
    ```

### Конфигурация

В обязательном порядке, в переменной `CACHES`, должен быть ключ `django_fk_fasted`, по этому ключу будет получен кеш, для сохранения в него ключей для выполнения логики пакета.

Пример:

    ```python
    'django_fk_fasted': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/0',
        'KEY_PREFIX': 'fk_fasted',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
    ```

### Разработчики

Ответственный за пакет разработчик - [Кудашин Иван](https://github.com/Ikudza) (Kudashin-Ivan@yandex.ru).
