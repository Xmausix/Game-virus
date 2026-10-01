import unittest

from virus_exe.dsl.language import default_source, test_program


class VirusDslTests(unittest.TestCase):
    def test_default_program_passes(self) -> None:
        result = test_program(default_source())
        self.assertTrue(result.passed)
        self.assertIsNotNone(result.program)
        self.assertEqual(len(result.program.tools), 2)

    def test_invalid_program_fails(self) -> None:
        result = test_program("VIRUS BROKEN\nPOWER 140\nEND")
        self.assertFalse(result.passed)
        self.assertIsNone(result.program)
        self.assertTrue(result.errors)


if __name__ == "__main__":
    unittest.main()
