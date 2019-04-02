import js
from multiprocessing import Queue





def echoTest(a, b):
    global inQ, outQ
    inQ,outQ=a,b
    js.globals['setTimeout'](echoLoop, 5000)

def echoLoop():
    print "running test"
    try:
        v=inQ.get(False)
        print "got value",v
        outQ.put(v)
    except Exception as e:
        print e
    finally:
        print js.globals['setTimeout'](echoLoop, 5000)


def helloWorld():
    print "Hello From Subprocess"
