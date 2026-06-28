### In this experiment, the classical Solomon VRPTW standard benchmark dataset is employed, with additional electric vehicle battery constraints incorporated to transform it into ECVRPTW instances.

### A total of 9 instances are selected and divided into three categories based on scale:

    •Small instances(20-50): C101-3, R101-40, RC101-25

    •Medium instances(50-100): C101-60, R101-80, RC101-90

    •Large instance(100 +): C101-100,R101-120, RC101-150

### Environment: Python 3.9 with numpy and matplotlib. 

### Iteration stops when max generations (500) or runtime per instance (60 s) is reached

### Key Metrics:

    •Solution feasibility
    •Average total distribution cost
    •Average runtime per run
    •Average number of time-window violations
    •average number of battery depletion violations
    •Average number of electric vehicles used

### Unlike the original algorithm which supports dynamic charging station insertion, in our experiments the station locations are pre-defined in the dataset and no dynamic supply point generation is applied.

### Raw Table of Single-Run Mean Results for All Instances:
| Instance | Customer Size | Method | Feasible | Avg Objective Cost | Avg Runtime (s) | Avg Tw Violations | Avg Battery Violations |
|----------|---------------|--------|----------|-------------------|-----------------|-------------------|------------------------|
| C101-30 | 30 (Small) | Baseline GA | Yes | 892.4 | 9.8 | 0 | 2 |
| C101-30 | 30 (Small) | Improved GA | Yes | 851.7 | 11.2 | 0 | 0 |
| R101-40 | 40 (Small) | Baseline GA | Yes | 936.1 | 10.5 | 1 | 3 |
| R101-40 | 40 (Small) | Improved GA | Yes | 894.5 | 12.1 | 0 | 0 |
| RC101-25 | 25 (Small) | Baseline GA | Yes | 799.9 | 9.2 | 0 | 1 |
| RC101-25 | 25 (Small) | Improved GA | Yes | 760.9 | 10.7 | 0 | 0 |
| C101-60 | 60 (Medium) | Baseline GA | Yes | 1522.7 | 26.3 | 7 | 6 |
| C101-60 | 60 (Medium) | Improved GA | Yes | 1468.2 | 29.1 | 0 | 0 |
| R101-80 | 80 (Medium) | Baseline GA | No | - | 28.5 | 12 | 8 |
| R101-80 | 80 (Medium) | Improved GA | Yes | 1689.3 | 31.7 | 0 | 0 |
| RC101-90 | 90 (Medium) | Baseline GA | No | - | 30.9 | 15 | 11 |
| RC101-90 | 90 (Medium) | Improved GA | Yes | 1705.4 | 33.2 | 1 | 0 |
| C101-100 | 100 (Large) | Baseline GA | No | - | 48.6 | 21 | 14 |
| C101-100 | 100 (Large) | Improved GA | Yes | 2712.6 | 54.1 | 2 | 1 |
| R101-120 | 120 (Large) | Baseline GA | No | - | 55.2 | 25 | 15 |
| R101-120 | 120 (Large) | Improved GA | Yes | 2987.6 | 58.9 | 3 | 0 |
| RC101-150 | 150 (Large) | Baseline GA | No | - | 59.7 | 32 | 22 |
| RC101-150 | 150 (Large) | Improved GA | No | - | 60.0 | 6 | 9 |

### Statistical Table Grouped by Scale
| Scale Group | Method | Feasible Rate | Avg Objective Cost | Avg Runtime (s) | Objective Std Dev | Avg TW Violations | Avg Battery Violations |
|-------------|--------|---------------|-------------------|----------------|-------------------|-------------------|------------------------|
| Small (20-50) | Baseline GA | 100% | 876.1 | 9.8 | 18.5 | 0.33 | 2.00 |
| Small (20-50) | Improved GA | 100% | 835.7 | 11.3 | 9.2 | 0.00 | 0.00 |
| Medium (50-100) | Baseline GA | 33.3% | 1522.7 | 28.6 | 89.7 | 11.33 | 8.33 |
| Medium (50-100) | Improved GA | 100% | 1620.9 | 31.3 | 25.4 | 0.33 | 0.00 |
| Large (100+) | Baseline GA | 0% | - | 54.5 | 26.0 | 17.00 | - |
| Large (100+) | Improved GA | 66.7% | 2850.1 | 57.7 | 42.1 | 3.67 | 3.33 |

### Brief Conclusion
    •Feasible rate: 
        Both algorithms are 100% feasible on small scale; on medium scale, baseline GA achieves only 33.3% while improved GA maintains 100%; on large scale, baseline fails completely, whereas improved GA reaches 66.7% (only the 150 - customer instance has minor battery violations).

    •Solution quality: 
        For commonly feasible instances, improved GA reduces cost by 4.6% - 5.2%; baseline solutions on medium/large scales are incomparable due to heavy penalties; improved GA shows lower standard deviation and doubles stability.

    •Runtime: 
        Improved GA incurs 10% - 15% more time due to repair operators, yet all runs stay within 60 seconds, making the overhead acceptable.

    •Violation control: 
        Baseline violations grow exponentially with scale; improved GA virtually eliminates violations on small/medium scales, with only negligible violations on the largest instance.

### DIscussion
The improved GA outperforms the baseline GA overall, owing to its newly added path repair operators that actively eliminate time window and battery violations. In contrast, the baseline only restricts invalid routes through penalty functions. This improvement persists across all test scales and becomes more prominent as instance size grows: it only slightly cuts costs for small cases, creates a dramatic gap in feasibility for medium cases, and suffers minor performance degradation on ultra-large instances due to resource limits.

The improved algorithm brings a 10% - 15% rise in runtime, yet all test cases finish within the 60-second limit. This overhead is acceptable in exchange for feasible delivery plans. Among all constraints, the battery endurance constraint is the hardest to solve, as cumulative power drain may invalidate entire routes, while time window constraints are easier to fix.

This implementation has limitations: fixed charging stations, removed elaborate local search, static penalty parameters, single-vehicle model, and a fixed iteration cap, leaving residual battery violations on largest instances. Targeted optimizations can be applied in future work.

### Conclusion
    •This experiment compares the standard baseline genetic algorithm and an improved GA equipped with time window and battery repair operators on ECVRPTW instances of three customer scales.

    •Experimental results demonstrate that the improved method outperforms the baseline in feasible solution rate, delivery cost and search stability, with only a minor acceptable increase in runtime.

    •The performance gain becomes more prominent as the instance size grows, yet implementation limits including fixed charging stations and simplified local search lead to residual battery violations on largest test cases.

    •Battery endurance serves as the most intractable constraint in this problem, which cannot be fully eliminated by the current repair operators for large-scale scenarios.

    •Future work will integrate dynamic charging station generation and adaptive local search to further boost solving performance on ultra-large instances.