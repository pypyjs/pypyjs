import os
import pickle
class Connection(object):
    def __init__(self, fno, writeable=True, readable=True):
        self.fno=fno
        self.writeable=writeable
        self.readable=readable
        self._buffer=''
    def send(self, msg):
        if not self.writeable:
            raise OSError('not writable')
        return os.write(self.fno, pickle.dumps(pickle.dumps(msg)))
    def recv(self):
        if not self.readable:
            raise OSError('not readable')
        if os.fileNumbers[self.fno].buffer.buffer!='':
            self._buffer+=os.read(self.fno, len(os.fileNumbers[self.fno].buffer.buffer))
        if "\n." in self._buffer:
            obj, self._buffer = self._buffer.split('\n.',1)
            return pickle.loads(pickle.loads(obj+'\n.'))
        raise EOFError()
    def poll(self):
        if self.readable:
            import select
            s=select.select([self.fno],[],[],0)[0]
            return bool(s)
        return False
    def close(self):
        pass
