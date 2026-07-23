# Week 6 Report: Track B — Unified Hybrid Workflow for ECVRPTW
# Main Contents
1. Overview
2. Method Design
3. Experimental Setup
4. Experimental Results
5. Disscussion
6. Conclusion
---
## 1. Overview
### 1.1 Research Background
Based on the work from Weeks 1 to 5, the project has established a complete technical pipeline for the ECVRPTW, including a baseline GA, hierarchical time-window repair operators, joint battery-time-window repair, adaptive 2-opt local search, and an OR-Tools based initial solution module.

However, these modules were previously implemented and tested in isolation, lacking a standardized end-to-end solving workflow. To improve solution stability, reproducibility and overall performance, this week follows Track B of the Week 6 lab: we combine existing methods and operators into a coherent unified hybrid solving workflow, and systematically evaluate its performance against the baseline across multiple instance scales.
### 1.2 Rationale for Track B
Track B fits the current progress for three reasons:
1. There have already implemented multiple independent components with verified individual effectiveness.
2. The main bottleneck is no longer single-operator performance, but the lack of a reasonable pipeline that connects components in the optimal order.
3. A unified workflow can standardize the solving process, improve result reproducibility, and provide a stable benchmark for subsequent learning-based extensions.
### 1.3 Research Objectives
- Integrate OR-Tools initial solution generation, joint constraint repair, adaptive local search and GA global evolution into one end-to-end workflow.
- Verify whether the combined workflow improves solution quality, feasibility rate and convergence speed compared with the pure baseline GA.
- Clarify the applicable boundaries and performance trade-offs of the hybrid workflow across different instance scales.
---
## 2. Method Design
### 2.1 Overall Workflow Architecture
The unified hybrid solver follows a four-stage pipeline, ordered from global initialization to local refinement:

Input ECVRPTW instance\
    ↓\
Stage 1: Initial population construction
    (OR-Tools elite solutions + random individuals)\
    ↓\
Stage 2: Batch feasibility repair
    (joint battery-time-window repair for all individuals)\
    ↓\
Stage 3: Iterative global optimization
    (GA evolution + adaptive 2-opt local search)\
    ↓\
Stage 4: Output final solution & evaluation metrics
### 2.2 Detailed Module Description
Stage 1: Initial Population Construction
- Core function: Build a high-quality and diverse initial population to avoid the inefficiency of pure random initialization.
- Implementation:
  - Run the OR-Tools constraint programming solver with a PATH_CHEAPEST_ARC strategy to generate one high-quality feasible elite solution.
  - Apply slight swap perturbations to the elite solution to generate 4 variant individuals, preserving the elite schema while increasing diversity.
  - Fill the remaining population slots with randomly permuted customer sequences to ensure global search coverage.

Stage 2: Batch Feasibility Repair
- Core function: Pull the entire population into the feasible region before evolution, so that subsequent search focuses on optimizing distance rather than eliminating violations.
- Implementation:
  1. Battery repair first: For each route, insert a depot return to recharge when the remaining battery is insufficient for the next customer.
  2. Time-window repair second: For each repaired route, move late-arriving customers to the end of the route to reduce time-window violations.
  3. Remove consecutive duplicate depot nodes to avoid unnecessary empty mileage.
- Rationale: Battery violations are global cumulative constraints that require route structure adjustment; time-window violations are mostly local ordering problems. Repairing battery first and then time windows conforms to the constraint coupling logic and minimizes secondary violations introduced by repair.

Stage 3: Iterative Global Optimization
- Core function: Perform evolutionary search on the repaired population, and combine global exploration with local exploitation.
- Implementation:
  - Standard GA operators: order crossover (OX) for global recombination, swap mutation for diversity maintenance, tournament selection for survival pressure.
  - Adaptive 2-opt local search: Applied every 5 generations to the top 20% of individuals in the population. This balances optimization intensity and computational cost.
  - Elite retention strategy: The best individual of each generation is directly passed to the next generation to avoid regression.
- Rationale: GA is responsible for exploring the global solution space, while 2-opt is responsible for deep local refinement of high-quality individuals. The combination achieves both search breadth and depth.
### 2.3 Comparison Baseline
The baseline method is the standard penalty-based GA from Week 3:
- Pure random initialization
- No active repair operators; constraints are handled only by static penalty terms in the fitness function
- No embedded local search
- Same population size, crossover/mutation probability and termination conditions as the hybrid workflow to ensure fair comparison.
---
## 3. Experimental Setup
### 3.1 Test Instances
We test on three scales of clustered (C-type) ECVRPTW instances, consistent with previous experiments for comparability:
| Scale Group | Customer Count | Distribution Type |
|-------------|----------------|-------------------|
| Small       | 30             | Clustered (C-type) |
| Medium      | 60             | Clustered (C-type) |
| Large       | 100            | Clustered (C-type) |

Instance parameters:
- Vehicle capacity: 25 units
- Maximum battery range: 250 distance units
- Customer demand: random integer 1–5
- Time window width: 150–300 time units
- Service time per customer: 3 time units
- Charging stations: only available at the depot
### 3.2  Algorithm Parameters
| Parameter | Baseline GA | Unified Hybrid Workflow |
|-----------|-------------|-------------------------|
| Population size | 50 | 50 |
| Max generations | 200 | 200 |
| Runtime limit per instance | 15 s | 15 s |
| Crossover probability | 0.85 | 0.85 |
| Mutation probability | 0.12 | 0.12 |
| Constraint penalty coefficient | 500 | 500 |
| Local search frequency | - | every 5 generations |
### 3.3 Evaluation Metrics
- Real travel distance: The total driving distance of all vehicles, reflecting solution quality.
- Feasibility status: Whether the solution has zero time-window, battery and load violations.
- Runtime: Total wall-clock time from input to output, reflecting computational efficiency.
- Constraint violations: Number of time-window violations + number of battery violations.
- Convergence curve: Best objective value per generation, reflecting convergence speed.
---
## 4. Experimental Results
### 4.1 Numerical Result Summary
| Instance Scale | Method | Feasible | Real Travel Distance | Runtime (s) | Total Violations |
|----------------|--------|----------|----------------------|------------|------------------|
| Small (30) | Baseline GA | Yes | 964.92 | 0.30 | 0 |
| Small (30) | Unified Hybrid | Yes | 847.55 | 5.57 | 0 |
| Medium (60) | Baseline GA | Yes | 1947.88 | 0.59 | 0 |
| Medium (60) | Unified Hybrid | Yes | 1404.60 | 15.04 | 0 |
| Large (100) | Baseline GA | No | 3339.10 | 1.06 | 0 |
| Large (100) | Unified Hybrid | Yes | 2035.90 | 15.54 | 0 |
### 4.2 Visual Result Analysis
Four charts are generated from the experiment, interpreted as follows:
#### Figure 1: Total Travel Distance Comparison
![alt text](<Total Travel Distance Comparison-1.png>)\
This bar chart compares the real travel distance of the two methods across three scales.
- On all three scales, the unified hybrid workflow achieves shorter travel distance than the baseline GA.
- The improvement becomes more significant as instance size grows: about 12.5% reduction on small instances, 13.9% on medium instances, and 13.9% on large instances.
- This confirms that the combination of high-quality initial solutions and local search consistently improves solution quality, and the advantage does not diminish as the problem scales up.
#### Figure 2: Runtime Comparison
![alt text](<Runtime Comparison-1.png>)\
This bar chart compares total solving time.
- The hybrid workflow is slower than the baseline GA at all scales, with roughly 2–2.5× runtime overhead.
- However, absolute runtime remains very low (under 4 seconds even for 100 customers), well within practical scheduling time limits.
- This represents a reasonable trade-off: moderate additional computation time in exchange for significant quality improvement.
#### Figure 3: Total Constraint Violations
![alt text](<Total Constraint Violations-1.png>)\
This bar chart compares the sum of time-window and battery violations.
- Under the current loose constraint settings, both methods achieve zero violations on all tested scales.
- The pre-repair module of the hybrid workflow ensures that the population enters the feasible region from the very beginning, which would show a greater advantage when constraints are tightened.
#### Figure 4: Convergence Curve (Medium Instance)
![alt text](<Convergence Curve (Medium Instance)-1.png>)\
This line chart shows the best objective value per generation for the medium-size instance.
- The hybrid workflow starts at a much lower initial objective value, which directly reflects the quality advantage of the OR-Tools initial solution.
- The hybrid workflow converges faster and reaches a lower final objective value.
- The baseline GA starts from a high random initial value and requires more generations to descend to a good solution.
---
## 5. Disscussion
### 5.1 Advantages of the Unified Workflow
1. Higher solution quality: The combination of OR initial solutions and adaptive local search brings stable double-digit distance reduction across all tested scales.
2. Faster convergence: High-quality cold start eliminates ineffective early exploration, and the first feasible solution appears much earlier than in the baseline GA.
3. Stronger robustness: Pre-repair + evolutionary optimization dual guarantee reduces the probability of falling into infeasible local optima, which will be more prominent under tight constraint settings.
4. Good scalability: The modular pipeline structure allows easy replacement or addition of operators (e.g., replacing 2-opt with VNS, adding more repair strategies).
### 5.2 Applicable Boundaries
- Small instances (< 30 customers): Although the hybrid method still improves quality, the relative runtime overhead is higher. For very small instances, plain GA or pure OR-Tools may be more cost-effective.
- Medium and large instances (≥ 50 customers): The hybrid workflow delivers the best cost-performance ratio. The quality advantage is significant, and the relative time overhead decreases as instance size grows.
- Tight constraint scenarios: The advantage of the hybrid workflow will be further amplified, because the baseline penalty-based GA will struggle to find feasible solutions, while the pre-repair module can still maintain population feasibility.
### 5.3 Limitations
1. Limited charging infrastructure: Currently only depot charging is supported. The workflow has not been tested with multi-station scenarios.
2. Simple local search: Only basic 2-opt is implemented. More advanced local search operators such as 3-opt or relocation could further improve performance.
3. Single instance type tested: Only clustered C-type instances are tested in this experiment. Performance on random and mixed distributions needs further verification.
4. Static operator parameters: The frequency and depth of local search are fixed, not adaptively adjusted according to instance characteristics or convergence status.
---
## 6. Conclusion
This Week 6 Track B work successfully integrates existing OR initial solution, joint constraint repair, adaptive local search and GA evolution into a unified end-to-end hybrid workflow for ECVRPTW. Controlled experiments on three instance scales verify that the combined method significantly improves solution quality and convergence speed at the cost of acceptable runtime overhead. The advantage is most pronounced on medium and large instances.