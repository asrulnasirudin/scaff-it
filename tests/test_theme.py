"""Interactive colour, output preservation, and terminal cleanup boundaries."""
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from scaffolder import theme  # noqa: E402


class Terminal(io.StringIO):
    def isatty(self):
        return True


class ThemeTests(unittest.TestCase):
    def test_redirected_output_stays_plain(self):
        out = io.StringIO()
        with redirect_stdout(out), theme.terminal_theme():
            print(theme.paint("Project settings"))
        self.assertEqual(out.getvalue(), "Project settings\n")

    def test_no_colour_and_dumb_terminal_stay_plain(self):
        for env in ({"NO_COLOR": ""}, {"TERM": "dumb"}):
            with self.subTest(env=env), patch.dict("os.environ", env, clear=True):
                out = Terminal()
                with redirect_stdout(out), theme.terminal_theme():
                    print(theme.paint("Project settings"))
                self.assertEqual(out.getvalue(), "Project settings\n")

    def test_unsupported_console_stays_plain(self):
        out = Terminal()
        with patch.dict("os.environ", {}, clear=True), redirect_stdout(out):
            with patch.object(theme, "_enable_terminal", return_value=None):
                with theme.terminal_theme():
                    print(theme.paint("Settings"))
        self.assertEqual(out.getvalue(), "Settings\n")

    def test_nested_menu_and_exception_restore_terminal_once(self):
        out, restore = Terminal(), Mock()
        with patch.dict("os.environ", {}, clear=True), redirect_stdout(out):
            with patch.object(theme, "_enable_terminal", return_value=restore) as enable:
                with self.assertRaisesRegex(ValueError, "cancel"):
                    with theme.terminal_theme():
                        with theme.terminal_theme():
                            print(theme.paint("Settings"))
                        raise ValueError("cancel")
                enable.assert_called_once()
        restore.assert_called_once()
        self.assertTrue(out.getvalue().endswith("\033[0m"))
        self.assertIsNone(theme._stream.get())

    def test_theme_does_not_leak_into_separate_output(self):
        out, other = Terminal(), io.StringIO()
        with patch.dict("os.environ", {}, clear=True), redirect_stdout(out):
            with patch.object(theme, "_enable_terminal", return_value=lambda: None):
                with theme.terminal_theme():
                    self.assertEqual(theme.paint("Saved report", out=other), "Saved report")
                    self.assertIn("38;2;176;144;80", theme.paint("Heading"))
                    self.assertIn("48;2;160;40;56", theme.paint("Action", "action"))

    def test_body_and_highlight_pairs_have_readable_contrast(self):
        def luminance(value):
            channels = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
                      for v in channels]
            return sum(v * w for v, w in zip(linear, (.2126, .7152, .0722)))

        for fg, bg in [(theme.CREAM, theme.INK), (theme.CREAM, theme.RED),
                       (theme.CREAM, theme.BURGUNDY), (theme.GOLD, theme.INK)]:
            with self.subTest(foreground=fg, background=bg):
                light, dark = sorted((luminance(fg), luminance(bg)), reverse=True)
                self.assertGreaterEqual((light + .05) / (dark + .05), 4.5)


if __name__ == "__main__":
    unittest.main()
