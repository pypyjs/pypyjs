importScripts('/lib/Promise.min.js');
importScripts('/lib/FunctionPromise.js');
importScripts('/lib/pypyjs.js');
importScripts('/lib/PyPyPipe.js');
importScripts('/lib/PyPySemaphore.js');
importScripts('/lib/PyPySocket.js');
importScripts('/lib/PyPySleep.js');
importScripts('/lib/PyPyStdinWrapper.js');

function mainThreadEval(s){
    self.postMessage({cmd:'eval',data:s});
}

threads = new Array();

function initializeVM(data){
    vm = new pypyjs();
    vm.stdout=function(msg){
        self.postMessage({cmd:'stdout', id:self.id, msg:''+msg});
    }
    vm.stderr=function(msg){
        self.postMessage({cmd:'stderr', id:self.id, msg:''+msg});
    }
    vm.ready().then(function() {
        set_time_sleep(vm);
        
        set_stdin_wrapper(vm).then(function(){
            vm.stdin(data);
            vm.exec('import pickle,code;c=code.InteractiveConsole();c.push("""import pickle,code,sys;o = pickle.loads(sys.stdin.read());import multiprocessing,multiprocessing.forking;\n""")').then(function(){
                vm.exec('c.push("""multiprocessing.forking.Popen(o, True)\n""")');});
        });
    
    }, 
    function(err) {
            vm.stderr(err)
    });
}


evals = new Array();
        



self.addEventListener('message', function(e){
    var data=e.data;
    switch (data.cmd){
        case 'subprocess upstart':
            self.id=data.id;
            initializeVM(data.data);
            break;
        case 'subprocess stdin':
            vm.stdin(data.msg);
            break;
        case 'data for pipe':
            pipes_by_id[data.id].data(data.data);
            break;
        case 'set buffer':
            pipes_by_id[data.id].buffer=(data.data);
            break;
        case 'eval return':
            evals.push(data.data);
            break;
        }
}
);
