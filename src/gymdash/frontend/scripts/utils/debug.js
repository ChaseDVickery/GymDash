const shouldDebug = true;

function debug(message, doTrace=true) {
    if (shouldDebug) {
        console.log(message);
    }
}
