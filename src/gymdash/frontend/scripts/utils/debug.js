const shouldDebug = true;

function debug(message, doTrace=false) {
    if (shouldDebug) {
        console.log(message);
    }
    if (doTrace) {
        console.trace();
    }
}

// These methods should log the message somewhere the
// user can see in the future
function gd_log(message) {
    console.log(message);
}
function gd_info(message) {
    console.info(message);
}
function gd_warn(message) {
    console.warn(message);
}
function gd_error(message) {
    console.error(message);
}