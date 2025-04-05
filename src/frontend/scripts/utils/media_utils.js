
const mediaUtils = (
    function() {

        const conversionUtils = (
            function() {
                const binaryToBase64 = function(binary) {
                    let base64 = "";
                    const bytes = new Uint8Array(binary);
                    const len = bytes.byteLength;
                    for (let i = 0; i < len; i++) {
                        base64 += String.fromCharCode(bytes[i]);
                    }
                    return btoa(base64);
                }

                return {
                    binaryToBase64
                };
            }
        )();

        const createImageMediaSourceURL = function(mime, base64) {
            return `data:image/${mime};base64,${base64}`;
        }

        const binaryToImageMediaSourceURL = function(mime, binary) {
            const base64 = conversionUtils.binaryToBase64(binary);
            return createImageMediaSourceURL(mime, base64);
        }

        // Check here for more Image media MIME types:
        // https://www.iana.org/assignments/media-types/media-types.xhtml#image
        const binaryToGIF = function(binary) { return binaryToImageMediaSourceURL("gif", binary); }
        const binaryToPNG = function(binary) { return binaryToImageMediaSourceURL("png", binary); }
        const binaryToJPEG = function(binary) { return binaryToImageMediaSourceURL("jpeg", binary); }
        const binaryToTIFF = function(binary) { return binaryToImageMediaSourceURL("tiff", binary); }


        return {
            binaryToGIF,
            binaryToPNG,
            binaryToJPEG,
            binaryToTIFF,
            conversionUtils
        };
    }
)();

export { mediaUtils };