import unittest
import logging
import src.tests.utils.file_format

logging.basicConfig(level=logging.WARNING)

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromModule(src.tests.utils.file_format)
    unittest.TextTestRunner(verbosity=2).run(suite)