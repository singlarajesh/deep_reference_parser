# coding: utf8

"""
Modified from https://github.com/explosion/spaCy/blob/master/spacy/__main__.py

"""

if __name__ == "__main__":
    import plac
    import sys
    from wasabi import msg
    from deep_reference_parser.train import train
    from deep_reference_parser.predict import predict

    commands = {
        "train": train,
        "predict": predict,
    }

    if len(sys.argv) == 1:
        msg.info("Available commands", ", ".join(commands), exits=1)
    command = sys.argv.pop(1)
    sys.argv[0] = "deep_reference_parser %s" % command

    if command in commands:
        plac.call(commands[command], sys.argv[1:])
    else:
        available = "Available: {}".format(", ".join(commands))
        msg.fail("Unknown command: {}".format(command), available, exits=1)