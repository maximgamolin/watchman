class Empty:
    """
    Используется как пустое значение, потому что None это тоже валидное значение. Синглтон.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Empty, cls).__new__(cls)
        return cls._instance
