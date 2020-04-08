"""
Здесь реализован наследник для класса ForeignKey из фреймворка Django.

Используется для того, чтобы уменьшить обращение к базе на наличие записи в базе и
ускорить валидацию

Если модель на которую ссылается, имеет много атрибутов, то может работать медленее,
стоит в таком случае использовать класс ForeignKeyWithOutCacheInstance, в нем
реализована логика по кешированию только PK модели на которую сделана ссылка
"""
from django import forms
from django.core import exceptions
from django.core.serializers.json import DjangoJSONEncoder
from django.core.serializers import serialize, deserialize
from django.db import router, models
from django_redis import get_redis_connection

cache = get_redis_connection('django_fk_fasted')


def get_instance(remote_field: object, value: str, cache_time: int):
    """
    Получает объект модели

    :param remote_field: объект поля на который делается ссылка
    :param value: значение, которое является значениет на который ссылка сделана
    :param cache_time: время хранения в кеше
    """
    using = router.db_for_read(remote_field.model)
    if clean_field(remote_field, value, None, cache_time) is None:
        qs = remote_field.model._default_manager.using(using).filter(
            **{remote_field.field_name: value}
        )
        result_instance = qs.first()
        if result_instance is not None:
            cache.sadd(
                f'set_{remote_field.field_name}_for_{remote_field.model.__name__}',
                str(getattr(result_instance, remote_field.field_name))
            )
    else:
        result_instance = remote_field.model(**{remote_field.field_name: value})

    return result_instance


def clean_field(remote_field: object, value: str, instance: object, cache_time: int):
    """
    Метод по валидации с использованием множества в кеше
    В случае если, значение есть в кеше, вернется значение, если нет, то проверяет.
    что у нас в instance, если объект, то вернется значение,
    иначе вернется None
    :param remote_field: объект поля на который делается ссылка
    :param value: значение, которое является значениет на который ссылка сделана
    :param instance: Model`s instance
    :param cache_time: время хранения в кеше
    """
    key_for_pk = \
        f'set_{remote_field.field_name}_for_{remote_field.model.__name__}'
    using = router.db_for_read(remote_field.model)
    if not cache.exists(key_for_pk):
        qs = remote_field.model._default_manager.using(using)
        for pk in qs.values_list(remote_field.field_name, flat=True):
            cache.sadd(key_for_pk, str(pk), cache_time)
    if not cache.sismember(key_for_pk, str(value)):
        if instance:
            cache.sadd(
                key_for_pk,
                str(getattr(instance, remote_field.field_name)),
                cache_time
            )
        else:
            return
    return value


class ModelChoiceField(forms.ModelChoiceField):
    """
    Класс наследник с измененным методом пребразования строки в объект модели
    """
    def __init__(self, *args, **kwargs):
        self.kwargs_for_clean_field = kwargs.pop('kwargs_for_clean_field', dict())
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        """
        Метод используется в валидации для приведения строки в объект instance
        Если при запросе на получение instance получает None, то формирует ошибку
        о том нет валидного значения
        """
        if value in self.empty_values:
            return None
        instance = get_instance(value=value, **self.kwargs_for_clean_field)
        if instance is None:
            raise exceptions.ValidationError(
                self.error_messages['invalid_choice'],
                code='invalid_choice'
            )
        return instance


class ForeignKeyWithOutCacheInstance(models.ForeignKey):
    """
    Класс наследник с измененной логикой валидации.
    Теперь вместо каждого обращения в базу, будет формироваться список этих значений
    в кеше и обращаться туда для выявления pk в базе, если его там нет, то будет
    делаться запрос в базу и в случае если он там есть, добавлять в кеш
    """
    def __init__(self, *args, cache_time=3*60*60, **kwargs):
        """

        :param cache_time:
        :param args:
        :param kwargs:
        """
        self.cache_time = cache_time
        super().__init__(*args, **kwargs)
        self.kwargs_for_clean_field = {
            'remote_field': self.remote_field,
            'cache_time': self.cache_time
        }

    def validate(self, value, model_instance):
        """
        Валидация после валидации формы, которая заменяет логику обращения к базе
        """
        # логика джанговская
        if self.remote_field.parent_link:
            return

        if value is None and not self.null:
            raise exceptions.ValidationError(self.error_messages['null'], code='null')

        if not self.blank and value in self.empty_values:
            raise exceptions.ValidationError(
                self.error_messages['blank'], code='blank'
            )

        if value is None:
            return
        # тут начинается наша кастомная проверка на валидность даннных
        if clean_field(
                value=value, instance=model_instance, **self.kwargs_for_clean_field
        ) is None:
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={
                    'model': self.remote_field.model._meta.verbose_name,
                    'pk': value,
                    'field': self.remote_field.field_name,
                    'value': value,
                },
            )
        return value


class ForeignKey(ForeignKeyWithOutCacheInstance):
    """
    Класс, в котором использует измененную ModelForm, которая использует кеш для
    хранения готовых объектов модели на которую сделана ссылка
    """
    def formfield(self, *, using=None, **kwargs):
        """
        Полностью повторяет родительский метод, меняя только kwargs для новой
        ModelForm
        """
        if isinstance(self.remote_field.model, str):
            raise ValueError(
                f"Cannot create form field for {self.name} yet, because "
                f"its related model {self.remote_field.model} has not been loaded yet"
            )
        return super(models.ForeignKey, self).formfield(**{
            'form_class': ModelChoiceField,
            'kwargs_for_clean_field': self.kwargs_for_clean_field,
            'queryset': self.remote_field.model._default_manager.using(using),
            'to_field_name': self.remote_field.field_name,
            **kwargs,
        })
