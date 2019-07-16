from abc import abstractmethod


class IutCtl:
    @abstractmethod
    def start(self):
        raise NotImplementedError

    @abstractmethod
    def reset(self):
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        raise NotImplementedError

    @abstractmethod
    def wait_iut_ready_event(self):
        raise NotImplementedError

    @property
    def btp_worker(self):
        raise NotImplementedError

    @property
    def stack(self):
        raise NotImplementedError
