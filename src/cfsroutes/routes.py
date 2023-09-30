from .convert import Converter
from . import matrix, solver

import csv
import argparse
from pathlib import Path


class Routes(Converter):

    def __init__(self, config=None, signup=None):
        super().__init__(config=config, signup=signup)


    def slips_list(self, paths, data, assignment={}):
        output = []
        header = self.slips_header or []
        if any(isinstance(column, str) for column in header):
            header = [header] 
        for n, path in enumerate(paths):
            output += [[f"DRIVER: {assignment.get(n, '')}"]]
            output += header
            for i in path:
                if i == 0:
                    continue
                output += [[data[i][k] for k in self.csv_keys]]
            output += [[" "]]
        return output


    def write_slips(self, outfile, rows):
        outfile = Path(outfile)
        with outfile.open(mode="w") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)


    def get_slips(self, infile, outfile=None):
        data, filtered = self.load_signups(infile)
        distance_matrix = matrix.distance_matrix(data)
        paths = solver.get_routes(distance_matrix)
        assignment = solver.assign_drivers(data, paths, self.drivers)
        slips = self.slips_list(paths, data, assignment)
        if outfile:
            self.write_slips(outfile, slips)
        return slips


def cli():
    """Command line entrypoint."""
    parser = argparse.ArgumentParser(description="Create routes from input files.")
    parser.add_argument("infile", help="Signup csv input file.")
    parser.add_argument("--config", help="Config file.")
    parser.add_argument("--outfile", help="Local file to write slips output.")
    parser.add_argument("--drivers", help="Drivers csv input file.")
    args = parser.parse_args()

    Routes(config=args.config).get_slips(infile=args.infile, outfile=args.outfile)
