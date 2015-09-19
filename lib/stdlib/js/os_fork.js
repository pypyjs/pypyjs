processes = new Object();
processes.nextid=1;
function fork(obj){
    var newProc = {};
    newProc.id=processes.nextid++;
    processes[newProc.id]=newProc;
    self.postMessage({cmd:'fork', data:obj, id:newProc.id});
    newProc.stdin=function(e){
        self.postMessage({cmd: 'subprocess stdin', data:e, id:newProc.id});
    };
    newProc.stderr={}
    newProc.stderr.queue=new Array();
    newProc.stderr.write=function(msg){
        newProc.stderr.queue.push(msg);
    };
    newProc.stderr.read=function(n){
        var txt=newProc.stderr.queue.join('');
        var ret = txt.substring(0,n);
        txt = txt.substring(n);
        newProc.stderr.queue.length=1;
        newProc.stderr.queue[0]=txt;
        return ret
    };
    newProc.stdout={};
    newProc.stdout.queue=new Array();
    newProc.stdout.write=function(msg){
        newProc.stdout.queue.push(msg);
    };
    newProc.stdout.read=function(n){
        var txt=newProc.stdout.queue.join('');
        var ret = txt.substring(0,n);
        txt = txt.substring(n);
        newProc.stdout.queue.length=1;
        newProc.stdout.queue[0]=txt;
        return ret
    };
    newProc.exit=vm.stdout;
    return newProc;
}

