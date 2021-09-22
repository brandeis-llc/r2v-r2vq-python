"""
r2vq command line interface provides some shell-based operations to 
navigate and manipulate r2vq dataset.
"""

import argparse


def cli():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__
    )
    parser.add_argument(
        '-i', '--input',
        action='store',
        nargs='?',
        required=True,
        help='input CoNLL-U CSV file'
    )
    parser.add_argument(
        '-s', '--subset',
        action='store',
        nargs='+',
        help='recipe IDs to form a new subset'
    )
    parser.add_argument(
        '-o', '--output',
        default='',
        action='store',
        nargs='?',
        help='output path, defaults to STDOUT if not given'
    )
    args = parser.parse_args()
    if args.subset:
        import r2vq.dataset
        r2vq.dataset.subset(dataset_fname=args.input, out_fname=args.output, recipe_ids=args.subset)

if __name__ == '__main__':
    cli()
