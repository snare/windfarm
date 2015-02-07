import argparse

from .bot import WindfarmBot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--clear', '-c', action='store_true', help='clear timeline')
    args = parser.parse_args()

    with WindfarmBot() as b:
        try:
            b.auth()
            if args.clear:
                b.clear()
            else:
                b.loop()
        except KeyboardInterrupt:
            b.terminate()