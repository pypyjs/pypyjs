jQuery( document ).ready(function( $ ) {
    $("#actions").submit(function() {
        // never "submit" the actions-form
        return false;
    })
    CodeMirrorEditor = CodeMirror.fromTextArea($("#editor")[0], {
        mode: {
            name: "text/x-cython",
            version: 2,
            singleLineStringErrors: false
        },
        lineNumbers: true,
        indentUnit: 4,
        matchBrackets: true
    });
    CodeMirrorEditor.on("changes", function() {
        // remove last run info after code changes.
        $("#run_info").text("");
    });
    $("#wrap_output").prop( "checked", false );
    $("#wrap_output").change(function() {
        if($(this).is(":checked")) {
            $(".jqconsole").css("word-wrap", "break-word");
            $(".jqconsole").css("white-space", "pre-wrap");
        } else {
            $(".jqconsole").css("word-wrap", "");
            $(".jqconsole").css("white-space", "");
        }
    });
});

function verbose_exec(code, verbose=true) {
    $("#run_info").text("start vm...");
    jqconsole.Reset();

    var init_start = new Date();
    window.vm = new PyPyJS();

    // Send all VM output to the console.
    vm.stdout = vm.stderr = function(data) {
        jqconsole.Write(data, 'jqconsole-output');
    }
    vm.ready.then(function() {
        var duration = new Date() - init_start;
        $("#run_info").text("PyPy.js init in " + human_time(duration));

        // console.log("Start code:" + JSON.stringify(code));
        var start_time = new Date();
        vm.exec(code).then(function() {
            if (verbose) {
                var duration = new Date() - start_time;
                $("#run_info").text("Run in " + human_time(duration) + " (OK)");
            }
        }, function (err) {
            // err is an instance of PyPyJS.Error
            if (verbose) {
                var duration = new Date() - start_time;
                $("#run_info").text("Run in " + human_time(duration) + " ("+err.name+": "+err.message+"!)");
            }
            vm.stderr(err.trace); // the human-readable traceback, as a string
        });


    }, function(err) {
        jqconsole.Write('ERROR: ' + err);
    });




}

$(function () {
    // Global vars, for easy debugging in console.
    window.jqconsole = $('#console').jqconsole('', '>>> ');

    $("#run").click(function() {
        var code=CodeMirrorEditor.getValue();
        verbose_exec(code);
    });

    // Display a helpful message and twiddle thumbs as it loads.
    jqconsole.Write('Loading PyPy.js.\n', 'jqconsole-output');
    jqconsole.Write('It\'s big, so this might take a while...\n\n', 'jqconsole-output');

    verbose_exec(
        'print "Welcome to PyPy.js!\\n";import sys;print "Python v"+sys.version',
        verbose=false
    )

    $("#loading").slideUp();
    $("#actions").slideDown("slow");

});