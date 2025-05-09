const shouldDebug = true;

function debug(message, doTrace=false) {
    if (shouldDebug) {
        console.log(message);
    }
    if (doTrace) {
        console.trace();
    }
}
