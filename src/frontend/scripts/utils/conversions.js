
const bToGiBConstant = 1 / Math.pow(2, 30);
const bToMiBConstant = 1 / Math.pow(2, 20);
const bTokiBConstant = 1 / Math.pow(2, 10);
const GiBTobConstant = Math.pow(2, 30);
const MiBTobConstant = Math.pow(2, 20);
const kiBTobConstant = Math.pow(2, 10);

const bitsToBytes = function(numBits) { return numBits / 8; }
const bytesToBits = function(numBytes) { return numBytes * 8; }
const bytesToGibibytes = function(numBytes) { return numBytes * bToGiBConstant; }
const bytesToMebibytes = function(numBytes) { return numBytes * bToMiBConstant; }
const bytesToKibibytes = function(numBytes) { return numBytes * bTokiBConstant; }
const gibibytesToBytes = function(numBytes) { return numBytes * GiBTobConstant; }
const mebibytesToBytes = function(numBytes) { return numBytes * MiBTobConstant; }
const kibibytesToBytes = function(numBytes) { return numBytes * kiBTobConstant; }

const byteConversions = (
    function() {

        const B2GiB = function(numBytes) { return bytesToGibibytes(numBytes); }
        const B2MiB = function(numBytes) { return bytesToMebibytes(numBytes); }
        const B2KiB = function(numBytes) { return bytesToKibibytes(numBytes); }
        const GiB2B = function(numValue) { return gibibytesToBytes(numValue); }
        const MiB2B = function(numValue) { return mebibytesToBytes(numValue); }
        const KiB2B = function(numValue) { return kibibytesToBytes(numValue); }

        const b2GiB = function(numBits) { return bytesToGibibytes(bitsToBytes(numBits)); }
        const b2MiB = function(numBits) { return bytesToMebibytes(bitsToBytes(numBits)); }
        const b2KiB = function(numBits) { return bytesToKibibytes(bitsToBytes(numBits)); }
        const GiB2b = function(numValue) { return bytesToBits(gibibytesToBytes(numValue)); }
        const MiB2b = function(numValue) { return bytesToBits(mebibytesToBytes(numValue)); }
        const KiB2b = function(numValue) { return bytesToBits(kibibytesToBytes(numValue)); }

        return {
            B2GiB,
            B2MiB,
            B2KiB,
            GiB2B,
            MiB2B,
            KiB2B,
            b2GiB,
            b2MiB,
            b2KiB,
            GiB2b,
            MiB2b,
            KiB2b
        };
    }
)();

export { byteConversions };