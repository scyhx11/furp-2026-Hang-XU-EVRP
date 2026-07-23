import numpy as np
import random
import time
import matplotlib.pyplot as plt


random.seed(42)
np.random.seed(42)

class ECVRPTWInstance:
    def __init__(self, n_customers=50, instance_type="C", vehicle_cap=25, max_battery=250):
        self.n = n_customers
        self.vehicle_cap = vehicle_cap
        self.max_battery = max_battery
        self.service_time = 3

        
        self.coords = np.zeros((self.n + 1, 2))
        if instance_type == "C":
            centers = [(25, 25), (75, 25), (50, 75)]
            for i in range(1, self.n + 1):
                cx, cy = random.choice(centers)
                self.coords[i] = [cx + random.gauss(0, 10), cy + random.gauss(0, 10)]
        elif instance_type == "R":
            self.coords[1:] = np.random.rand(self.n, 2) * 100
        else:
            half = self.n // 2
            centers = [(30, 50), (70, 50)]
            for i in range(1, half + 1):
                cx, cy = random.choice(centers)
                self.coords[i] = [cx + random.gauss(0, 8), cy + random.gauss(0, 8)]
            self.coords[half+1:] = np.random.rand(self.n - half, 2) * 100

       
        self.dist_matrix = np.linalg.norm(
            self.coords[:, np.newaxis, :] - self.coords[np.newaxis, :, :], axis=2
        )

        
        self.demand = np.zeros(self.n + 1)
        self.demand[1:] = np.random.randint(1, 6, self.n)

        
        self.tw_start = np.zeros(self.n + 1)
        self.tw_end = np.zeros(self.n + 1)
        self.tw_start[0] = 0
        self.tw_end[0] = 2000
        for i in range(1, self.n + 1):
            dist_from_depot = self.dist_matrix[0, i]
            earliest = dist_from_depot + random.randint(20, 80)
            latest = earliest + random.randint(150, 300)
            self.tw_start[i] = earliest
            self.tw_end[i] = latest

    def get_dist(self, a, b):
        return self.dist_matrix[int(a), int(b)]


def split_to_routes(seq, ins):

    routes = []
    current_route = [0]
    current_load = 0
    for cust in seq:
        dem = ins.demand[cust]
        if current_load + dem > ins.vehicle_cap:
            current_route.append(0)
            routes.append(current_route)
            current_route = [0, cust]
            current_load = dem
        else:
            current_route.append(cust)
            current_load += dem
    current_route.append(0)
    routes.append(current_route)
    return routes


def evaluate_routes(routes, ins):
   
    total_dist = 0.0
    tw_vio = 0
    batt_vio = 0
    load_vio = 0

    for route in routes:
        battery = ins.max_battery
        time_clock = 0.0
        load = 0
        prev = 0
        for node in route[1:]:
            dist = ins.get_dist(prev, node)
            total_dist += dist
            battery -= dist
            time_clock += dist

            if node != 0:
                load += ins.demand[node]
                if load > ins.vehicle_cap:
                    load_vio += 1
                if time_clock < ins.tw_start[node]:
                    time_clock = ins.tw_start[node]
                if time_clock > ins.tw_end[node]:
                    tw_vio += 1
                time_clock += ins.service_time
            else:
                battery = ins.max_battery
                load = 0

            if battery < 0:
                batt_vio += 1
            prev = node

    feasible = (tw_vio == 0 and batt_vio == 0 and load_vio == 0)
    return total_dist, tw_vio, batt_vio, load_vio, feasible


def joint_repair(seq, ins):
    
    routes = split_to_routes(seq, ins)
    repaired_routes = []
    for rt in routes:
       
        new_rt = [0]
        battery = ins.max_battery
        for node in rt[1:-1]:
            dist = ins.get_dist(new_rt[-1], node)
            if battery - dist < 0:
                new_rt.append(0)
                battery = ins.max_battery
                dist = ins.get_dist(0, node)
            new_rt.append(node)
            battery -= dist
        new_rt.append(0)
       
        cleaned = []
        for n in new_rt:
            if n != 0 or not cleaned or cleaned[-1] != 0:
                cleaned.append(n)
        
        
        time_clock = 0.0
        late_nodes = []
        final_rt = [0]
        for node in cleaned[1:-1]:
            dist = ins.get_dist(final_rt[-1], node)
            time_clock += dist
            if time_clock > ins.tw_end[node]:
                late_nodes.append(node)
            else:
                if time_clock < ins.tw_start[node]:
                    time_clock = ins.tw_start[node]
                time_clock += ins.service_time
                final_rt.append(node)
        final_rt.extend(late_nodes)
        final_rt.append(0)
        repaired_routes.append(final_rt)
    
    new_seq = []
    for rt in repaired_routes:
        for node in rt:
            if node != 0:
                new_seq.append(node)
    return new_seq


def two_opt_local_search(seq, ins):
    
    best_seq = seq.copy()
    best_dist, _, _, _, _ = evaluate_routes(split_to_routes(best_seq, ins), ins)
    improved = True
    max_iter = 5
    it = 0
    while improved and it < max_iter:
        improved = False
        it += 1
        for i in range(len(best_seq) - 1):
            for j in range(i + 1, min(i + 20, len(best_seq))):
                new_seq = best_seq[:i] + best_seq[i:j+1][::-1] + best_seq[j+1:]
                new_dist, _, _, _, _ = evaluate_routes(split_to_routes(new_seq, ins), ins)
                if new_dist < best_dist:
                    best_seq = new_seq
                    best_dist = new_dist
                    improved = True
    return best_seq



def greedy_initial_solution(ins):
    
    unvisited = set(range(1, ins.n + 1))
    seq = []
    current_node = 0
    current_load = 0

    while unvisited:
       
        next_node = None
        min_dist = float('inf')
        for cust in unvisited:
            if current_load + ins.demand[cust] <= ins.vehicle_cap:
                d = ins.get_dist(current_node, cust)
                if d < min_dist:
                    min_dist = d
                    next_node = cust
        
        if next_node is not None:
            seq.append(next_node)
            unvisited.remove(next_node)
            current_load += ins.demand[next_node]
            current_node = next_node
        else:
           
            current_node = 0
            current_load = 0
    
    return seq



class BaseGA:
    def __init__(self, ins, pop_size=50, max_iter=200, time_limit=15):
        self.ins = ins
        self.N = ins.n
        self.pop_size = pop_size
        self.max_iter = max_iter
        self.time_limit = time_limit
        self.p_cross = 0.85
        self.p_mut = 0.12
        self.penalty = 500
        self.convergence = []

    def create_individual(self):
        seq = list(range(1, self.N + 1))
        random.shuffle(seq)
        return seq

    def calc_fitness(self, seq):
        routes = split_to_routes(seq, self.ins)
        dist, tw, batt, load, _ = evaluate_routes(routes, self.ins)
        penalty = (tw + batt + load) * self.penalty
        return dist + penalty, dist

    def selection(self, pop, fits):
        candidates = random.sample(list(zip(pop, fits)), k=3)
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0].copy()

    def ox_crossover(self, p1, p2):
        n = len(p1)
        a, b = sorted(random.sample(range(n), 2))
        child = [-1] * n
        child[a:b+1] = p1[a:b+1]
        ptr = 0
        for gene in p2:
            if gene not in child:
                while child[ptr] != -1:
                    ptr += 1
                child[ptr] = gene
        return child

    def swap_mutate(self, ind):
        if random.random() < self.p_mut:
            i, j = random.sample(range(len(ind)), 2)
            ind[i], ind[j] = ind[j], ind[i]
        return ind

    def run(self):
        pop = [self.create_individual() for _ in range(self.pop_size)]
        best_cost = float('inf')
        best_dist = float('inf')
        best_seq = None
        best_feasible = False
        start = time.time()

        for it in range(self.max_iter):
            if time.time() - start > self.time_limit:
                break
            evals = [self.calc_fitness(ind) for ind in pop]
            fits = [e[0] for e in evals]
            min_idx = int(np.argmin(fits))
            if fits[min_idx] < best_cost:
                best_cost = fits[min_idx]
                best_dist = evals[min_idx][1]
                best_seq = pop[min_idx].copy()
                routes = split_to_routes(best_seq, self.ins)
                _, _, _, _, best_feasible = evaluate_routes(routes, self.ins)
            self.convergence.append(best_dist if best_feasible else best_cost)

            new_pop = [best_seq.copy()]
            while len(new_pop) < self.pop_size:
                p1 = self.selection(pop, fits)
                p2 = self.selection(pop, fits)
                if random.random() < self.p_cross:
                    c = self.ox_crossover(p1, p2)
                else:
                    c = p1.copy()
                c = self.swap_mutate(c)
                new_pop.append(c)
            pop = new_pop

        runtime = time.time() - start
        routes = split_to_routes(best_seq, self.ins)
        dist, tw, batt, load, feasible = evaluate_routes(routes, self.ins)
        return {
            "dist": dist, "feasible": feasible, "runtime": runtime,
            "tw_vio": tw, "batt_vio": batt, "convergence": self.convergence
        }


class UnifiedHybridSolver(BaseGA):
    def run(self):
        
        pop = []
        
        greedy_seq = greedy_initial_solution(self.ins)
        pop.append(greedy_seq)
        
        for _ in range(4):
            seq = greedy_seq.copy()
            i, j = random.sample(range(len(seq)), 2)
            seq[i], seq[j] = seq[j], seq[i]
            pop.append(seq)
       
        while len(pop) < self.pop_size:
            pop.append(self.create_individual())

        
        pop = [joint_repair(seq, self.ins) for seq in pop]

        best_cost = float('inf')
        best_dist = float('inf')
        best_seq = None
        best_feasible = False
        start = time.time()

        
        for it in range(self.max_iter):
            if time.time() - start > self.time_limit:
                break
            evals = [self.calc_fitness(ind) for ind in pop]
            fits = [e[0] for e in evals]
            min_idx = int(np.argmin(fits))
            if fits[min_idx] < best_cost:
                best_cost = fits[min_idx]
                best_dist = evals[min_idx][1]
                best_seq = pop[min_idx].copy()
                routes = split_to_routes(best_seq, self.ins)
                _, _, _, _, best_feasible = evaluate_routes(routes, self.ins)
            self.convergence.append(best_dist if best_feasible else best_cost)

            new_pop = [best_seq.copy()]
            while len(new_pop) < self.pop_size:
                p1 = self.selection(pop, fits)
                p2 = self.selection(pop, fits)
                if random.random() < self.p_cross:
                    c = self.ox_crossover(p1, p2)
                else:
                    c = p1.copy()
                c = self.swap_mutate(c)
                
                if it % 5 == 0 and random.random() < 0.2:
                    c = two_opt_local_search(c, self.ins)
                new_pop.append(c)
            pop = new_pop

        runtime = time.time() - start
        routes = split_to_routes(best_seq, self.ins)
        dist, tw, batt, load, feasible = evaluate_routes(routes, self.ins)
        return {
            "dist": dist, "feasible": feasible, "runtime": runtime,
            "tw_vio": tw, "batt_vio": batt, "convergence": self.convergence
        }



def run_track_b():
    scales = [30, 60, 100]
    labels = ["Small (30)", "Medium (60)", "Large (100)"]
    base_res = []
    hybrid_res = []

    for n, label in zip(scales, labels):
        print(f"\n===== 测试 {label} =====")
        ins = ECVRPTWInstance(n_customers=n, instance_type="C")

       
        ga = BaseGA(ins)
        res1 = ga.run()
        base_res.append(res1)
        print(f"基线GA | 可行:{res1['feasible']} | 距离:{res1['dist']:.2f} | 耗时:{res1['runtime']:.2f}s")

        
        hybrid = UnifiedHybridSolver(ins)
        res2 = hybrid.run()
        hybrid_res.append(res2)
        print(f"混合工作流 | 可行:{res2['feasible']} | 距离:{res2['dist']:.2f} | 耗时:{res2['runtime']:.2f}s")

  
    x = np.arange(len(labels))
    width = 0.35
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    axes[0,0].bar(x - width/2, [r["dist"] for r in base_res], width, label="Baseline GA", color="#ff7f0e")
    axes[0,0].bar(x + width/2, [r["dist"] for r in hybrid_res], width, label="Unified Hybrid", color="#2ca02c")
    axes[0,0].set_title("Total Travel Distance Comparison")
    axes[0,0].set_ylabel("Distance")
    axes[0,0].set_xticks(x)
    axes[0,0].set_xticklabels(labels)
    axes[0,0].legend()
    axes[0,0].grid(axis="y", alpha=0.3, linestyle="--")

    
    axes[0,1].bar(x - width/2, [r["runtime"] for r in base_res], width, label="Baseline GA", color="#ff7f0e")
    axes[0,1].bar(x + width/2, [r["runtime"] for r in hybrid_res], width, label="Unified Hybrid", color="#2ca02c")
    axes[0,1].set_title("Runtime Comparison (Seconds)")
    axes[0,1].set_ylabel("Time (s)")
    axes[0,1].set_xticks(x)
    axes[0,1].set_xticklabels(labels)
    axes[0,1].legend()
    axes[0,1].grid(axis="y", alpha=0.3, linestyle="--")

    
    base_vio = [r["tw_vio"] + r["batt_vio"] for r in base_res]
    hybrid_vio = [r["tw_vio"] + r["batt_vio"] for r in hybrid_res]
    axes[1,0].bar(x - width/2, base_vio, width, label="Baseline GA", color="#ff7f0e")
    axes[1,0].bar(x + width/2, hybrid_vio, width, label="Unified Hybrid", color="#2ca02c")
    axes[1,0].set_title("Total Constraint Violations")
    axes[1,0].set_ylabel("Violation Count")
    axes[1,0].set_xticks(x)
    axes[1,0].set_xticklabels(labels)
    axes[1,0].legend()
    axes[1,0].grid(axis="y", alpha=0.3, linestyle="--")

    
    axes[1,1].plot(base_res[1]["convergence"], label="Baseline GA", color="#ff7f0e", linewidth=1.5)
    axes[1,1].plot(hybrid_res[1]["convergence"], label="Unified Hybrid", color="#2ca02c", linewidth=1.5)
    axes[1,1].set_title("Convergence Curve (Medium Instance)")
    axes[1,1].set_xlabel("Generation")
    axes[1,1].set_ylabel("Best Objective Value")
    axes[1,1].legend()
    axes[1,1].grid(alpha=0.3, linestyle="--")

    plt.tight_layout()
    plt.show()
    return base_res, hybrid_res


if __name__ == "__main__":
    base, hybrid = run_track_b()
    