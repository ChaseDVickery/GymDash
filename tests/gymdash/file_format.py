import unittest
import random
import logging
from src.gymdash.backend.core.utils.file_format import *

gif1 = b'\x47\x49\x46\x38\x37\x61'
gif2 = b'\x47\x49\x46\x38\x39\x61'
png = b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'
wav_, _wav = b'\x52\x49\x46\x46', b'\x57\x41\x56\x45'
mp41 = b'\x66\x74\x79\x70\x4D\x53\x4E\x56'
mp42 = b'\x66\x74\x79\x70\x69\x73\x6F\x6D'

logger = logging.getLogger("testing")

class ByteSignatureBuilder:
    def __init__(self, offset, bytes1, any_bytes=0, bytes2=None) -> None:
        self.offset = offset
        self.bytes1 = bytes1
        self.bytes2 = bytes2
        self.any_bytes = any_bytes

    def create_matching_bytes(self):
        matched_bytes = random.randbytes(self.offset) \
                        + self.bytes1 \
                        + (b'' if self.any_bytes == 0 else random.randbytes(self.any_bytes)) \
                        + (self.bytes2 if self.bytes2 else b'')
        return matched_bytes

class TestMagicByteGuesser(unittest.TestCase):
    hyper_pad = random.randbytes(pow(2, 25))

    def setUp(self) -> None:
        self.big_pad = random.randbytes(pow(2, 20))

    def create_matching_bytes(self, signature: Signature):
        test_bytes = ''
        # Test if the signature is split
        if len(signature.signature.any_byte_idxs) > 0:
            # This is the index at which the "any"-bytes would begin
            # in the query bytes
            first_any_byte = min(signature.signature.any_byte_idxs)
            test_bytes = ByteSignatureBuilder(
                signature.offset,
                signature.data[:first_any_byte],
                len(signature.signature.any_byte_idxs),
                signature.data[first_any_byte:]
            ).create_matching_bytes()
        # Test if the signature is whole
        else:
            test_bytes = ByteSignatureBuilder(
                signature.offset,
                signature.data
            ).create_matching_bytes()
        return test_bytes

    def _test_signature_positive(self, signature: Signature, pad_end=None):
        test_bytes = self.create_matching_bytes(signature)
        self._test_signature_positive_custom_test(signature, test_bytes, pad_end)

    def _test_signature_positive_custom_test(self, signature: Signature, custom_test_bytes, pad_end=None):
        desired_extension = signature.extension
        desired_mime = signature.mimetype
        test_bytes = custom_test_bytes
        test_bytes += pad_end if pad_end else b''
        logger.info(f"Extension '{desired_extension}': test bytes='{test_bytes.hex(' ')}' vs signature bytes='{signature.signature.__str__()}'")
        found_extension = extension_from_bytes(test_bytes)
        found_mimetype = mimetype_from_bytes(test_bytes)
        self.assertEqual(found_extension, desired_extension, f"Bytes for desired extension '{desired_extension}' returned '{found_extension}' instead. Test bytes='{test_bytes.hex(' ')}'")
        self.assertEqual(found_mimetype, desired_mime, f"Bytes for desired mimetype '{desired_mime}' returned '{found_mimetype}' instead. Test bytes='{test_bytes.hex(' ')}'")

    # Manual
    def test_gif1_positive_custom1(self):
        custom_bytes = gif1 + b'\x11\x22\x33\x44\x2a'
        self._test_signature_positive_custom_test(SIG_GIF1, custom_bytes)
    def test_gif2_positive_custom1(self):
        custom_bytes = gif2 + b'\x11\x22\x33\x44\x2a'
        self._test_signature_positive(SIG_GIF2, custom_bytes)
    def test_png_positive_custom1(self):
        custom_bytes = png + b'\x11\x22\x33\x44\x2a'
        self._test_signature_positive(SIG_PNG, custom_bytes)
    def test_wav_positive_custom1(self):
        custom_bytes = wav_ + b'\x11\x22\x33\x44' + _wav + b'\x2a'
        self._test_signature_positive(SIG_WAV, custom_bytes)
    def test_mp41_positive_custom1(self):
        custom_bytes = b'\x11\x22\x33\x44' + mp41 + b'\x11\x22\x33\x44\x2a'
        self._test_signature_positive(SIG_MP41, custom_bytes)
    def test_mp42_positive_custom1(self):
        custom_bytes = b'\x11\x22\x33\x44' + mp42 + b'\x11\x22\x33\x44\x2a'
        self._test_signature_positive(SIG_MP42, custom_bytes)
    # Automatic
    def test_gif1_positive(self):
        self._test_signature_positive(SIG_GIF1)
    def test_gif2_positive(self):
        self._test_signature_positive(SIG_GIF2)
    def test_png_positive(self):
        self._test_signature_positive(SIG_PNG)
    def test_wav_positive(self):
        self._test_signature_positive(SIG_WAV)
    def test_mp41_positive(self):
        self._test_signature_positive(SIG_MP41)
    def test_mp42_positive(self):
        self._test_signature_positive(SIG_MP42)
    # Big end padding
    def test_gif1_positive_pad_end(self):
        self._test_signature_positive(SIG_GIF1, self.big_pad)
    def test_gif2_positive_pad_end(self):
        self._test_signature_positive(SIG_GIF2, self.big_pad)
    def test_png_positive_pad_end(self):
        self._test_signature_positive(SIG_PNG, self.big_pad)
    def test_wav_positive_pad_end(self):
        self._test_signature_positive(SIG_WAV, self.big_pad)
    def test_mp41_positive_pad_end(self):
        self._test_signature_positive(SIG_MP41, self.big_pad)
    def test_mp42_positive_pad_end(self):
        self._test_signature_positive(SIG_MP42, self.big_pad)
    # Hyper end padding
    def test_gif1_positive_pad_end_hyper(self):
        self._test_signature_positive(SIG_GIF1, TestMagicByteGuesser.hyper_pad)
    def test_gif2_positive_pad_end_hyper(self):
        self._test_signature_positive(SIG_GIF2, TestMagicByteGuesser.hyper_pad)
    def test_png_positive_pad_end_hyper(self):
        self._test_signature_positive(SIG_PNG, TestMagicByteGuesser.hyper_pad)
    def test_wav_positive_pad_end_hyper(self):
        self._test_signature_positive(SIG_WAV, TestMagicByteGuesser.hyper_pad)
    def test_mp41_positive_pad_end_hyper(self):
        self._test_signature_positive(SIG_MP41, TestMagicByteGuesser.hyper_pad)
    def test_mp42_positive_pad_end_hyper(self):
        self._test_signature_positive(SIG_MP42, TestMagicByteGuesser.hyper_pad)


if __name__ == "__main__":
    unittest.main()