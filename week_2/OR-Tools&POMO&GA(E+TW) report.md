For the Vehicle Routing Problem with Time Windows, this code implements three distinct solution approaches: the OR-Tools, GA, and POMO. Comparative performance tests are conducted across three problem scales with 50, 100, and 200 customers, and the core experimental metrics of each algorithm are presented in the picture below:

![alt text]({EDEA851F-47DC-4E0E-A7ED-D50D7EE4D2AF}.png)

To clearly compare the solving performance and constraint satisfaction of the three algorithms under different customer scales, the above running results are summarized in the following comparison table and diagrams:

|Instance problem scale|Method|Total travel distance|Runtime(s)|Dual constraint Feasibility|
| :---                   | :---   | :---                  |:---         | :---             |
|50|OR-Tool|14.75|10.01|True|
|50|POMO|3.35|0.01|False|
|50|GA|19.70|5.91|False|
|100|OR-Tools|32.42|10.02|True|
|100|POMO|2.69|0.01|False|
|100|GA|61.37|12.61|False|
|200|OR-Tools|55.13|10.08|True|
|200|POMO|2.83|0.03|False|
|200|GA|98.05|23.45|False|

![alt text](<Figure 2026-06-19 011316-1.png>)

# Conclusion
This experiment reproduces three baseline solution methods for VRP: the OR-Tools, GA, and POMO. Comparative tests are conducted on three problem scales with 50, 100, and 200 customers respectively. The three methods exhibit significant discrepancies in solution quality, computational efficiency, and constraint satisfaction capability. The experiment also identifies core technical barriers in extending practical constraints to unconstrained baselines, providing clear optimization directions and empirical references for the subsequent development of the target Electric Vehicle Routing Problem with Time Windows model.

## Differences in results (objective value, runtime) among POMO, GA and OR-Tools methods

### Objective value and solution quality

OR-Tools yields the only valid feasible solutions that fully satisfy both E and TW constraints across all test scales. Its objective values grow linearly with customer count, delivering the highest optimization quality which serves as the performance benchmark for this experiment. Constrained by basic crossover/mutation operators and limited iteration budget, GA is prone to converging to local optima, with notably higher objective values than OR-Tools. As the problem scale expands, the solution space grows exponentially, widening the performance gap between GA and the benchmark. For the 200-customer instance, the total travel distance of GA reaches approximately 1.78 times that of OR-Tools. The abnormally low objective values output by POMO are misleading: they are derived from constraint-violating routes with incomplete customer coverage, and thus are invalid solutions not comparable in terms of optimization performance. The original POMO framework is designed exclusively for unconstrained CVRP; without targeted training on constrained scenarios, it cannot produce operationally meaningful optimized routes.

### Runtime performance

POMO completes inference through a single forward pass of the neural network, with millisecond-level runtime that is barely affected by increasing problem size. This order-of-magnitude speed advantage is the core value proposition of deep reinforcement learning for routing problems. OR-Tools maintains a stable runtime of approximately 10 seconds across all scales, bounded by the preset time limit. It iteratively improves solutions via guided local search within the time budget, offering high controllability over solving time. GA requires full-population fitness evaluation and evolutionary operations in each generation. Its runtime scales approximately linearly with customer count, exceeding 23 seconds for the 200-customer instance, representing the lowest efficiency among the three methods for large-scale problems

## Main challenges when adding E and/or TW constraints to the baselines

### Exponential growth of solution space complexity

Beyond the core route sequencing decision of basic VRP, it introduces two additional decision dimensions: route splitting governed by capacity constraints, and node scheduling governed by time window constraints. The proportion of feasible solutions in the overall solution space shrinks drastically, raising the search difficulty exponentially. Merely finding a single legal feasible solution is non-trivial, let alone locating the global optimum.

### Constraint handling trade-off for metaheuristic algorithms

Metaheuristic methods such as GA cannot embed hard constraints directly into their solution encoding. They can only steer the population toward the feasible region indirectly via penalty functions. Tuning the penalty weight involves an inherent trade-off: an excessively low penalty fails to filter out infeasible solutions effectively, while an excessively high penalty causes rapid population homogenization and premature convergence to local optima. Furthermore, capacity and time window constraints are mutually coupled, and a uniform penalty mechanism can hardly regulate both types of violations simultaneously.

### Constraint embedding difficulty for neural combinatorial optimization

Neural combinatorial optimization models like POMO can natively handle simple capacity constraints via feasibility masking. For temporally coupled, globally dependent constraints such as time windows, however, stepwise greedy decoding cannot anticipate the downstream impact of current decisions, frequently resulting in locally valid but globally infeasible routes. Computing accurate stepwise feasibility masks for time window constraints is itself NP-hard, which limits the effectiveness of naive masking approaches. Without targeted training on constrained distributions, the model suffers severe generalization degradation, and simplistic dynamic reset logic breaks route coherence and fails to construct valid multi-vehicle schedules.

### Elevated repair complexity from constraint coupling

Capacity and time windows are not independent constraints. Load allocation determines how routes are split, which in turn determines segment travel times and customer arrival times. A time window violation at a single node often originates from upstream load distribution decisions. This coupling effect makes violation diagnosis and route repair far more logically complex than in single-constraint VRP variants.

## Valuable insights gained when building the target EVRPTW model

### Constraint compliance takes priority over optimization in practical deployment

Optimal routes for pure VRP have limited direct value in real-world logistics operations. Capacity limits and time window requirements are fundamental business constraints for last-mile delivery: constraint satisfaction ranks higher than objective minimization, and optimization without guaranteed feasibility carries no engineering utility. When extending to EVRPTW, the coupling between energy constraints and time constraints becomes even tighter, requiring constraint modeling to be placed at a more central position than pure route optimization.

### Each technical approach has distinct applicable boundaries

For small-scale, high-precision static scheduling scenarios, exact solvers such as OR-Tools are the preferred choice, guaranteeing both solution optimality and constraint compliance. For medium-scale scenarios with diverse customized constraints, metaheuristic algorithms offer better cost-effectiveness and flexibility. The speed advantage of deep learning only materializes in large-scale, high-throughput real-time dynamic scheduling scenarios, and even then it requires sufficient training data and post-optimization pipelines to deliver deployable results.

### Neural combinatorial optimization cannot replace traditional operations research end-to-end
Pure end-to-end neural inference cannot reliably guarantee solution feasibility under complex constraints. It must be combined with traditional optimization post-processing - such as local search and constraint repair - into a hybrid framework: the neural network generates high-quality initial solutions rapidly, and traditional algorithms refine and correct them to ensure feasibility. The core role of deep learning is to accelerate the solving pipeline, not to fully replace classical operations research methods.

### Baseline reproduction is an essential foundation for extended research

Reproducing baseline methods like POMO and GA and augmenting them with custom constraints clearly reveals the constraint-handling weaknesses of each approach, which provides concrete improvement directions for EVRPTW model design. Examples include incorporating energy and time state features into node embeddings, adding constraint-aware look-ahead mechanisms to the decoder, and designing mixed training strategies that cover varying constraint tightness levels.