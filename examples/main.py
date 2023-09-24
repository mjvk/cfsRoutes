"""Example of using the cfsroutes module in a local script."""
from cfsroutes import Routes
from pathlib import Path

def main():
    here = Path(__file__).parent # Path to 'examples' directory
    config_file = here / "example_config.json" # Path to config file
    csv_input = here / "YOUR_INPUT_FILE.csv" # Provide your own .csv input
    slips_outfile = here / "slips_output.csv" # Name of the results file to output

    # Instantiate a cfsroutes.Routes object with given configuration.
    routing = Routes(config=config_file)
    # Get the slips as a list and also write them to './slips_output.csv'
    slips = routing.get_slips(infile=csv_input, outfile=slips_outfile)
    print(slips)

if __name__ == "__main__":
    main()
