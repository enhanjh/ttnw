from abc import ABC, abstractmethod

class BaseExecutor(ABC):
    """
    Abstract base class for all executors.
    An executor takes signals from a strategy and acts on them.
    """
    @abstractmethod
    def run(self):
        pass
