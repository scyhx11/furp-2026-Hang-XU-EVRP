from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import matplotlib.pyplot as plt
import time

def create_data_model():
    
    data = {}
    data["distance_matrix"] = [
        [0, 2, 5, 7],
        [2, 0, 3, 4],
        [5, 3, 0, 2],
        [7, 4, 2, 0]
    ]
    
    data["coords"] = [(0, 0), (2, 0), (5, 0), (7, 2)]
    data["num_vehicles"] = 1
    data["depot"] = 0
    return data

def distance_callback(from_index, to_index, manager, data):
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    return data["distance_matrix"][from_node][to_node]

def print_solution(manager, routing, solution):
    print("=" * 40)
    print(f"Objective value: {solution.ObjectiveValue()} miles")
    index = routing.Start(0)
    route_str = "Route for vehicle 0:\n  "
    route_dist = 0

    while not routing.IsEnd(index):
        route_str += f"{manager.IndexToNode(index)} -> "
        prev_index = index
        index = solution.Value(routing.NextVar(index))
        route_dist += routing.GetArcCostForVehicle(prev_index, index, 0)

    route_str += f"{manager.IndexToNode(index)}"
    print(route_str)
    print(f"Total route distance: {route_dist} miles")
    print("=" * 40)

def plot_route(data, manager, routing, solution):
    coords = data["coords"]
    depot = data["depot"]

    route_nodes = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        route_nodes.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    route_nodes.append(manager.IndexToNode(index))

    plt.figure(figsize=(8, 5), dpi=100)

    for i, (x, y) in enumerate(coords):
        if i == depot:
            plt.scatter(x, y, c="red", s=150, zorder=5, label="Depot")
        else:
            plt.scatter(x, y, c="blue", s=120, zorder=5)
        plt.text(x + 0.15, y + 0.15, f"Node {i}", fontsize=10)

    for k in range(len(route_nodes) - 1):
        x1, y1 = coords[route_nodes[k]]
        x2, y2 = coords[route_nodes[k + 1]]
        plt.arrow(x1, y1, x2 - x1, y2 - y1,
                  head_width=0.2, length_includes_head=True,
                  fc="orange", ec="orange", linewidth=2)

    plt.title("TSP Smoke Test - Optimized Route")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.axis("equal")
    plt.tight_layout()
    plt.show()

def main():
    data = create_data_model()

    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]),
        data["num_vehicles"],
        data["depot"]
    )
    routing = pywrapcp.RoutingModel(manager)

    def callback_wrapper(from_idx, to_idx):
        return distance_callback(from_idx, to_idx, manager, data)
    
    transit_index = routing.RegisterTransitCallback(callback_wrapper)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_index)

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    t0 = time.time()
    solution = routing.SolveWithParameters(search_params)
    t1 = time.time()

    if solution:
        print_solution(manager, routing, solution)
        print(f"Runtime: {t1 - t0:.4f} seconds")
        plot_route(data, manager, routing, solution)
    else:
        print("No solution found.")

if __name__ == "__main__":
    main()