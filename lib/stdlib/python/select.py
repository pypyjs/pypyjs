import time
import _socket
import os


def select(readlist, writelist, xlist, timeout=None):
    readlist=list(readlist)
    writelist=list(writelist)
    xlist=list(xlist)
    endtime=time.time()+timeout
    read_out=[]
    write_out=[]
    xlist_out=[]
    while True:
        for i in (readlist):
            if isinstance(i, int):
                fno=i
            else:
                fno=i.fileno()
            if fno==0:
                if (hasattr(os.fileNumbers[fno], 'buffer') and hasattr(os.fileNumbers[fno].buffer,'len')):
                    if os.fileNumbers[fno].buffer.len>0:
                        read_out.append(fno)
                        continue
            if fno >= len(os.fileNumbers):
                continue
            so=os.fileNumbers[fno]
            if isinstance(so, _socket._fileobject):
                if so.pullFromJS():
                    read_out.append(i)
            else:
                if getattr(so, 'buffer', None) and so.buffer.buffer:
                    read_out.append(i)
        for i in (xlist):
            if isinstance(i, int):
                fno=i
            else:
                fno=i.fileno()
            if fno<3:
                continue
            if fno >= len(os.fileNumbers):
                continue
            so=os.fileNumbers[fno]
            if isinstance(so, _socket._socket):
                if so._sock.closed:
                    xlist_out.append(i)
        for i in (writelist):
            if isinstance(i, int):
                fno=i
            else:
                fno=i.fileno()
            if fno >= len(os.fileNumbers):
                continue
            so=os.fileNumbers[fno]
            if isinstance(so, _socket._fileobject):
                if not so._sock.ready:
                    continue
            write_out.append(i)
        if read_out or write_out or xlist_out or time.time() > timeout:
            return read_out, write_out, xlist_out
        time.sleep(0.1)
        

class error(Exception): pass
