"""Entry point for python -m manus_cine."""

import sys

from .main import main

if __name__ == "__main__":
    if "--list-chats" in sys.argv:
        from . import list_chats_cmd

        list_chats_cmd.run()
    else:
        main()
