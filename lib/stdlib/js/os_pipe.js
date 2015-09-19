
pipes = new Array();
pipes_by_id = new Object();




function FLOBuffer(pipeid){
    if (pipeid==undefined){
        pipes.push(this);
        self.postMessage({cmd:'create Pipe'});
    }
    else{
        pipes_by_id[pipeid]=this;
        this.id=pipeid;
        self.postMessage({cmd:'watch pipe', id:this.id});
    }
    this.buffer = '';
    this.data = function(bytes){
        this.buffer+=bytes;
    }
    this.sendData = function(bytes){
        self.postMessage({cmd:'data for pipe', id:this.id, data:bytes});
    }
    this.requestData = function(amt){
        self.postMessage({cmd:'request data for pipe', id:this.id, data:amt});
    }
}

FLOBuffer.prototype.setID=function(id){
    this.id=id;
    pipes_by_id[id]=this;
    self.postMessage({cmd:'watch pipe', id:this.id});
}

FLOBuffer.prototype.fileno=function(){
    return this.id;
}



function FLOPipe(writable, readable, buffer){
    this.buffer=buffer;
    if (writable){
        this.write=function(data){
            this.buffer.sendData(data);
        }
    }
    if (readable){
        this.read=function(amt){
            this.buffer.requestData(amt);
            
            var ret = this.buffer.buffer.substring(0, amt);
            if (!amt){
                this.buffer.buffer='';
            }
            else{
                this.buffer.buffer=this.buffer.buffer.substring(amt);
            }
            return ret;
        }
    }
}



function pipe(pipeid){
    this.buffer = new FLOBuffer(pipeid);
    this.read_end=new FLOPipe(false,true, this.buffer);
    this.write_end=new FLOPipe(true,false, this.buffer);
    
}
