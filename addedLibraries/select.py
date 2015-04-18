import time
import _socket



def select(readlist, writelist, xlist, timeout=None):
    print 7
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
            if fno<3:
                continue
            so=_socket.sockets.get(fno,None)
            if so:
                if so.pullFromJS():
                    print 26, so._stringIO.getvalue()
                    read_out.append(i)
        for i in (xlist):
            if isinstance(i, int):
                fno=i
            else:
                fno=i.fileno()
            if fno<3:
                continue
            so=_socket.sockets.get(fno,None)
            if so:
                if so._sock.closed:
                    xlist_out.append(i)
        for i in (writelist):
            if isinstance(i, int):
                fno=i
            else:
                fno=i.fileno()
            so=_socket.sockets.get(fno,None)
            if so:
                if not so._sock.ready:
                    continue
            write_out.append(i)
            
            
        if read_out or write_out or xlist_out or time.time() > timeout:
            print 38, read_out, write_out, xlist_out
            return read_out, write_out, xlist_out
        time.sleep(0.1)
        

class error(Exception): pass
