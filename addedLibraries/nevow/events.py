# Copyright (c) 2004 Divmod.
# See LICENSE for details.


DEBUG = False


class EventNotification:
    def __init__(self):
        self._subscribers = {}
        self._currentId = 0

    def subscribe(self, identifier, subscriber):
        """Subscribe to events sent to the given identifier.
        
        Returns a token which should be passed to unsubscribe when done.
        """
        if DEBUG:
            print "SUBSCRIBE", self, identifier, subscriber
        self._subscribers.setdefault(identifier, []).append(subscriber)
        return identifier, subscriber

    def unsubscribe(self, token):
        """Unsubscribe the given token from events.
        """
        if DEBUG:
            print "UNSUBSCRIBE", token
        identifier, reference = token
        self._subscribers[identifier].remove(reference)

    def publish(self, identifier, *args):
        """Notify the listeners on a given identifier that an event has occurred.
        """
        if DEBUG:
            print "PUBLISH", self, identifier,
        subscribers = self._subscribers.get(identifier, [])
        for sub in subscribers:
            sub(*args)
            if DEBUG:
                print "NOTIFY SUBSCRIBER", sub
        if DEBUG:
            print "done"

    def nextId(self):
        self._currentId += 1
        return str(self._currentId)

    def __getstate__(self):
        d = self.__dict__.copy()
        d['_subscribers'] = {}
        d['_currentId'] = 0
        return d


