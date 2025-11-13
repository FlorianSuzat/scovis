import argparse


__all__ = ["main"]


def main():
    # get args
    args = get_args()
    import toolbox

    function = getattr(toolbox, args.score)
    rc = function(args.ref, args.test)
    return rc


def get_args():
    parser = argparse.ArgumentParser(
        description="A simple command aggregate scores json files"
    )
    parser.add_argument(
        "-r", "--ref", help="path to ref json folder", dest="ref", required=True
    )
    parser.add_argument(
        "-t", "--test", help="path to test json folder", dest="test", required=True
    )
    parser.add_argument(
        "-s", "--score", help="score to compute", dest="score", default="scoreGeoLvlObs"
    )

    args = parser.parse_args()
    return args


main()
