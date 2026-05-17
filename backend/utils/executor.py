from abc import ABC, abstractmethod
from typing import Optional


class Executor(ABC):

    @abstractmethod
    def execute(self, *args: Optional[any], **kwargs: Optional[any]) -> None:
        pass
