import unittest
import logging
import tests.gymdash.file_format
import tests.gymdash.simulation

logging.basicConfig(level=logging.WARNING)

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromModule(tests.gymdash.file_format)
    unittest.TextTestRunner(verbosity=2).run(suite)
    suite = unittest.TestLoader().loadTestsFromModule(tests.gymdash.simulation)
    unittest.TextTestRunner(verbosity=2).run(suite)