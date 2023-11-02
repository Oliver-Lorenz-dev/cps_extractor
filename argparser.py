import argparse


class Parser:
    @classmethod
    def parse_args(cls, vargs=None):
        parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        required = parser.add_argument_group("required")
        required.add_argument(
            "-r",
            "--reference",
            required=True,
            help="Path of reference blastn database",
        )
        required.add_argument(
            "-q",
            "--query",
            required=True,
            help="Path to query sequence",
        )
        required.add_argument(
            "-o",
            "--output",
            required=True,
            help="Name of output cps sequence file",
        )
        required.add_argument(
            "-t",
            "--training-file",
            required=True,
            help="Name of prodigal training file used for annotation",
        )
        optional = parser.add_argument_group("optional")
        optional.add_argument(
            "-l",
            "--hit-length",
            required=False,
            help="Length of blast hits to add to the cps sequence",
            default=5000,
            type=int
        )

        args = parser.parse_args(vargs)

        return args
