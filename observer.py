# observer.py
class Observer: """Observer interface.""" def 
    update(self, data):
        raise NotImplementedError("Observer subclasses 
        must implement 'update' method.")
class Subject: """Base class for observable objects.""" 
    def __init__(self):
        self._observers = [] def attach(self, observer: 
    Observer):
        if observer not in self._observers: 
            self._observers.append(observer)
    def detach(self, observer: Observer): if observer 
        in self._observers:
            self._observers.remove(observer) def 
    notify(self, data=None):
        for observer in self._observers: 
            observer.update(data)
