# Week_1 Report
# Main Content
- Baseline Tool Selection
- Environment Record
- Smoke Test
- Reflection
---
## 1. Baseline Tool Selection
- Selected tool: Google OR-Tools Routing Library
- Selected path: OR-Tools VRPTW path (starting with TSP as the minimal baseline instance)
---
## 2. Environment Record
| Item               | Details                      |
|--------------------|------------------------------|
| Operating system   | Windows 11                   |
| Python version     | 3.12.11                      |
| Package manager    | Conda                        |
| Solver version     | OR-Tools 9.15.6755           |
| Runtime hardware   | Intel Core ULTRA 9           |
## 3. Smoke Test
### 3.1 Test Instance
- Instance name: Tiny TSP Test Instance
- Problem type: Traveling Salesman Problem (single-vehicle routing)
- Instance size: 4 nodes (1 depot + 3 customer nodes), 1 vehicle
- Input: Symmetric 4×4 integer distance matrix
### 3.2 Run Command
![alt text](<Run Command-1.png>)
### 3.3 Test Results
- Feasibility status: Feasible
- Objective value: 13 miles
- Runtime: 0.0040 seconds
- Textual route output:\
![alt text](<Textual route output-1.png>)
- Visual output:\
![alt text](<Visual output -1.png>) 
### 3.4 Solution Strategy
- First solution heuristic: PATH_CHEAPEST_ARC (greedy nearest-neighbor construction heuristic)
---
## 4. Reflection
- The most intuitive constraint in this TSP baseline is the depot constraint: the route must start and end at the designated depot node (index 0). This parameter is directly passed to RoutingIndexManager and can be easily verified from the output route sequence.
- The initially confusing part was the solver's dual index system: the routing model uses internal variable indices instead of raw node indices, so the IndexToNode method is required to map back to the original node numbering. This logic became clear after tracing the print_solution function step by step
- For Week 2, the baseline target is to extend this single-vehicle TSP model to a multi-vehicle Capacitated VRP (CVRP) by adding vehicle capacity constraints and customer demand values, then validate on a larger standard benchmark instance.