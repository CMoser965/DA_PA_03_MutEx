from abc import ABC, abstractmethod

class IDistributedMutex(ABC):
    @abstractmethod
    def GlobalInitialize(self, thisHost, hosts):
        pass

    @abstractmethod
    def QuitAndCleanup(self):
        pass

    @abstractmethod
    def MInitialize(self, votingGroupHosts: list[int]):
        pass

    @abstractmethod
    def MLockMutex(self):
        pass

    @abstractmethod
    def MReleaseMutex(self):
        pass

    @abstractmethod
    def MCleanup(self):
        pass
