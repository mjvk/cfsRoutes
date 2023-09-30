# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file contains modified code samples from Google's OR-Tools documentation
# See https://developers.google.com/optimization/introduction
"""Find routes and driver assignments."""
from . import matrix

from ortools.constraint_solver import routing_enums_pb2, pywrapcp
from ortools.linear_solver import pywraplp

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def create_data_model(matrix):
    """Stores the data for the problem."""
    deliveries = len(matrix) - 2 # Subtract 2 to account for origin and final row of 0s
    cars = deliveries // 6 + bool(deliveries % 6) # Number of drivers required
    capacities = [6] * cars
    print(capacities)
    data = {
        'distance_matrix' : matrix,
        'num_vehicles' : cars,
        'starts' : [0] * cars,
        'ends' : [len(matrix) - 1] * cars,
        'demands' : [0] + [1] * deliveries + [0],
        'vehicle_capacities' : capacities
    }
    assert sum(data["demands"]) <= sum(capacities)
    return data

    
def get_solution(data, manager, routing, solution):
    """Get readable paths from route solution."""
    total_distance = 0
    total_load = 0
    paths = []
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
        route_distance = 0
        route_load = 0
        path = []
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_load += data['demands'][node_index]
            plan_output += ' {0}, '.format(node_index)
            path += [node_index]
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id)
        plan_output += '\n'
        paths += [path]
        plan_output += 'Distance of the route: {}m\n'.format(route_distance)
        plan_output += 'Load of the route: {}\n'.format(route_load)
        logger.info(plan_output)
        total_distance += route_distance
        total_load += route_load
    logger.info('Total distance of all routes: {}m'.format(total_distance))
    logger.info('Total load of all routes: {}'.format(total_load))
    return paths


def get_routes(matrix, flex=100):
    # Modified from https://developers.google.com/optimization/routing/vrp
    """Find delivery routes for all addresses."""
    # Instantiate the data problem.
    data = create_data_model(matrix)

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(
        len(data['distance_matrix']),
        data['num_vehicles'],
        data['starts'],
        data['ends']
        )
    
    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    #Add Distance constraint.
    dimension_name = 'Distance'
    routing.AddDimension(
        transit_callback_index,
        0,  # no slack
        1000000,  # vehicle maximum travel distance
        True,  # start cumul to zero
        dimension_name)
    distance_dimension = routing.GetDimensionOrDie(dimension_name)
    distance_dimension.SetGlobalSpanCostCoefficient(flex)

    # Add Capacity constraint.
    def demand_callback(from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        
    routing.AddDimensionWithVehicleCapacity(demand_callback_index,0, data['vehicle_capacities'], True, 'Capacity')

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.time_limit.seconds = 10

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        paths = get_solution(data, manager, routing, solution)
        return paths
    else:
        logger.error("get_routes failed")
        return None


def assign_drivers(data, paths, drivers):
    # Modified from https://developers.google.com/optimization/assignment/assignment_example
    """Assign drivers to a route that ends closest to given location."""

    if not drivers:
        return {}

    route_ends = [
        {"index": path[-1], "location": data[path[-1]].get("location")}
        for path in paths
    ]

    def assign_cost(source, dest):
        if not source or not dest:
            return 1
        return matrix.pair_euclid_distance(source.values(), dest.values())

    costs = [
        [assign_cost(driver["location"], route["location"]) for driver in drivers]
        for route in route_ends
    ]

    # Create the mip solver with the SCIP backend.
    solver = pywraplp.Solver.CreateSolver("SCIP")
    num_drivers = len(drivers)
    num_destinations = len(route_ends)

    # x[i, j] is an array of 0-1 variables, which will be 1 if driver i is assigned to destination j.
    x = {}
    for i in range(num_destinations):
        for j in range(num_drivers):
            x[i, j] = solver.IntVar(0, 1, "")

    # Each driver is assigned to exactly one destination
    for i in range(num_destinations):
        solver.Add(solver.Sum([x[i, j] for j in range(num_drivers)]) <= 1)

    # Each destination is assigned to at most one driver 
    for j in range(num_drivers):
        solver.Add(solver.Sum([x[i, j] for i in range(num_destinations)]) == 1)

    objective_terms = []
    for i in range(num_destinations):
        for j in range(num_drivers):
            objective_terms.append(costs[i][j] * x[i, j])
    solver.Minimize(solver.Sum(objective_terms))

    status = solver.Solve()

    assignments = {}
    if status != pywraplp.Solver.OPTIMAL and status != pywraplp.Solver.FEASIBLE:
        logger.warning("No driver assignment solution found.")
        return assignments
    
    logger.info("Total cost: %s", solver.Objective().Value())
    for i in range(num_destinations):
        for j in range(num_drivers):
            # Test if x[i,j] is 1 (with tolerance for floating point arithmetic).
            if x[i, j].solution_value() > 0.5:
                route_index = route_ends[i]["index"]
                name = drivers[j]["name"]
                print(f"Driver {name} assigned to {route_index}| {data[route_index]['address']}, cost = {costs[i][j]}")
                assignments[i] = name
    return assignments
