"""Read single key presses (no Enter needed) from the terminal."""
import select
import sys
import termios
import tty


class Keyboard:
    """Use as `with Keyboard() as kb: key = kb.get()`. get() returns None on timeout."""

    def __enter__(self):
        self.is_tty = sys.stdin.isatty()
        if self.is_tty:
            self.old = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin)
        return self

    def __exit__(self, *exc):
        if self.is_tty:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old)

    def get(self, timeout=0.2):
        if not self.is_tty:                     # piped input: one key per line
            line = sys.stdin.readline()
            return (line[:1] or 'q') if line else 'q'
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        return sys.stdin.read(1) if ready else None
