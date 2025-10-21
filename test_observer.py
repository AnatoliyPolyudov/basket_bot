from observer import Subject, Observer

class PrintObserver(Observer):
    def update(self, data):
        print("Received:", data)

if __name__ == "__main__":
    s = Subject()
    o = PrintObserver()
    s.attach(o)
    s.notify("Hello Observer Pattern")
