import random
import string


def generate_random_string(length):
    """
    Сгенерировать случаю строку из символов
    :param length: необходимая длинна строки
    :return:
    """
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


class Empty:
    """
    Пустое значение для фабрик доменных моделей
    """

