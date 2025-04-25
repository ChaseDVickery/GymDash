
// Adapted from:
// https://stackoverflow.com/questions/1344500/efficient-way-to-insert-a-number-into-a-sorted-array-of-numbers
// Added objProcessor, a function that processes each
// array element to extract the "key" value for sort criterion.
function sortedIndex(array, value, objProcessor) {
    if (!objProcessor) {
        objProcessor = (x) => x;
    }
    var low = 0,
        high = array.length;

    while (low < high) {
        var mid = (low + high) >>> 1;
        if (objProcessor(array[mid]) < objProcessor(value)) low = mid + 1;
        else high = mid;
    }
    return low;
}