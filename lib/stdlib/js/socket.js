sockets = new Array();



function socketConnect(server){
    var this_socket = {}
    this_socket.id = sockets.length;
    sockets.push(this_socket);
    this_socket.queue=new Array();
    self.postMessage({cmd:'create WebSocket', server:server, id:this_socket.id});
    
    this_socket.send=function(txt){
        self.postMessage({cmd:'data for socket', data:txt, id:this_socket.id});
    }
    this_socket.onrecv=function(msg){
        this_socket.queue.push(msg);
        };
    this_socket.ready=false;
    this_socket.closed=false;
    return this_socket
}
