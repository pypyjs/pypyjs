
function Sleep(delay){
    //self.postMessage({cmd:"start sleep"});
    self.processingMessages=false;
    while (self.processingMessages){
        try{
            var r = new XMLHttpRequest();
            r.timeout=delay*1000;
            r.open('GET', '/sleep/'+delay, false);
            r.send(null);
            
        }catch(e){
        }
    }
    
    return null;
}

function set_time_sleep(vm){
    vm.exec('import time,js;time.sleep=lambda x:[js.globals["Sleep"](x),None][1];');
}
