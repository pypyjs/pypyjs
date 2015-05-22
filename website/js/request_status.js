function humanFileSize(bytes, si) {
    if(bytes < 1024) return bytes + ' Bytes';
    var units = ['kBytes','MBytes','GBytes','TBytes'];
    var u = -1;
    do {
        bytes /= 1024;
        ++u;
    } while(bytes >= 1024);
    return bytes.toFixed(1)+' '+units[u];
};
function XMLHttpRequestLoadStatus(event) {
    if (event.lengthComputable) {
        var percent = (event.loaded / event.total)*100;
        var msg = percent.toFixed(1) + "% loaded (" + humanFileSize(event.loaded) + ")";
    } else {
        var msg = humanFileSize(event.loaded) + " loaded";
    }
    console.log(msg);
    window.vm.stderr("\r"+msg);
};
//
//$.ajaxSetup({
//    beforeSend: function(xhr, settings) {
//        // Call every second a status callback
//        xhr.next_update = new Date().getTime() + 1000;
//        xhr.onprogress = function (event) {
//            throw "jep";
//            if (new Date().getTime()>xhr.next_update) {
//                XMLHttpRequestLoadStatus(event)
//                xhr.next_update = new Date().getTime() + 1000;
//            }
//        };
//    }
//});
//
//$( document ).ajaxComplete(function( event, xhr, settings ) {
//    console.log("jooj");
//});