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
            self.coords[:, np.newaxis, :] - self.coords[np.newaxis, :, :],
            axis=2
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



class BaseGA:
    def __init__(self, ins: ECVRPTWInstance, pop_size=60, max_iter=250, time_limit=12):
        self.ins = ins
        self.N = ins.n
        self.pop_size = pop_size
        self.max_iter = max_iter
        self.time_limit = time_limit
        self.p_cross = 0.85
        self.p_mut = 0.12
       
        self.penalty_tw = 800
        self.penalty_batt = 800
        self.penalty_load = 800
        self.convergence_curve = []

    def create_individual(self):
        
        cust = list(range(1, self.N + 1))
        random.shuffle(cust)
        return cust

    def split_to_routes(self, seq):
       
        routes = []
        current_route = [0]
        current_load = 0
        for cust in seq:
            dem = self.ins.demand[cust]
            if current_load + dem > self.ins.vehicle_cap:
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

    def evaluate_route(self, route):
        
        total_dist = 0.0
        tw_vio = 0
        batt_vio = 0
        load_vio = 0

        battery = self.ins.max_battery
        time_clock = 0.0
        load = 0
        prev = 0

        for node in route[1:]:  
            dist = self.ins.get_dist(prev, node)
            total_dist += dist
            battery -= dist
            time_clock += dist

            if node != 0:  
                load += self.ins.demand[node]
                if load > self.ins.vehicle_cap:
                    load_vio += 1

                if time_clock < self.ins.tw_start[node]:
                    time_clock = self.ins.tw_start[node]
                if time_clock > self.ins.tw_end[node]:
                    tw_vio += 1

                time_clock += self.ins.service_time
            else:  
                battery = self.ins.max_battery
                load = 0

            if battery < 0:
                batt_vio += 1

            prev = node

        return total_dist, tw_vio, batt_vio, load_vio

    def evaluate(self, seq):
        
        routes = self.split_to_routes(seq)
        total_dist = 0.0
        total_tw = 0
        total_batt = 0
        total_load = 0

        for rt in routes:
            d, tw, batt, load = self.evaluate_route(rt)
            total_dist += d
            total_tw += tw
            total_batt += batt
            total_load += load

        total_penalty = total_tw * self.penalty_tw + total_batt * self.penalty_batt + total_load * self.penalty_load
        feasible = (total_tw == 0 and total_batt == 0 and total_load == 0)
        return total_dist + total_penalty, total_dist, feasible, total_tw, total_batt

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
        best_sol = None
        best_feasible = False
        best_tw = 0
        best_batt = 0
        start_time = time.time()

        for it in range(self.max_iter):
            if time.time() - start_time > self.time_limit:
                break

            evals = [self.evaluate(ind) for ind in pop]
            fits = [e[0] for e in evals]

            min_idx = int(np.argmin(fits))
            if fits[min_idx] < best_cost:
                best_cost = fits[min_idx]
                best_dist = evals[min_idx][1]
                best_sol = pop[min_idx].copy()
                best_feasible = evals[min_idx][2]
                best_tw = evals[min_idx][3]
                best_batt = evals[min_idx][4]

            self.convergence_curve.append(best_dist if best_feasible else best_cost)

            
            new_pop = [best_sol.copy()]
            while len(new_pop) < self.pop_size:
                p1 = self.selection(pop, fits)
                p2 = self.selection(pop, fits)
                if random.random() < self.p_cross:
                    c1 = self.ox_crossover(p1, p2)
                else:
                    c1 = p1.copy()
                c1 = self.swap_mutate(c1)
                new_pop.append(c1)
            pop = new_pop

        runtime = time.time() - start_time
        return {
            "cost": best_dist if best_feasible else best_cost,
            "real_dist": best_dist,
            "feasible": best_feasible,
            "runtime": runtime,
            "tw_violations": best_tw,
            "batt_violations": best_batt,
            "convergence": self.convergence_curve
        }



class ImprovedGA(BaseGA):
    def repair_route_tw(self, route):
        
        new_route = [0]
        time_clock = 0.0
        late_nodes = []

        for node in route[1:-1]:  
            dist = self.ins.get_dist(new_route[-1], node)
            time_clock += dist

            if time_clock > self.ins.tw_end[node]:
                late_nodes.append(node)
            else:
                if time_clock < self.ins.tw_start[node]:
                    time_clock = self.ins.tw_start[node]
                time_clock += self.ins.service_time
                new_route.append(node)

        
        for node in late_nodes:
            new_route.append(node)
        new_route.append(0)
        return new_route

    def repair_route_battery(self, route):
        
        new_route = [0]
        battery = self.ins.max_battery

        for node in route[1:-1]:
            dist = self.ins.get_dist(new_route[-1], node)
            if battery - dist < 0:
                new_route.append(0)  
                battery = self.ins.max_battery
                dist = self.ins.get_dist(0, node)
            new_route.append(node)
            battery -= dist

        new_route.append(0)
        
        cleaned = []
        for n in new_route:
            if n != 0 or not cleaned or cleaned[-1] != 0:
                cleaned.append(n)
        return cleaned

    def evaluate(self, seq):
        
        routes = self.split_to_routes(seq)
        total_dist = 0.0
        total_tw = 0
        total_batt = 0
        total_load = 0

        for rt in routes:
            rt_fixed_tw = self.repair_route_tw(rt)
            rt_fixed = self.repair_route_battery(rt_fixed_tw)
            d, tw, batt, load = self.evaluate_route(rt_fixed)
            total_dist += d
            total_tw += tw
            total_batt += batt
            total_load += load

        total_penalty = total_tw * self.penalty_tw + total_batt * self.penalty_batt + total_load * self.penalty_load
        feasible = (total_tw == 0 and total_batt == 0 and total_load == 0)
        return total_dist + total_penalty, total_dist, feasible, total_tw, total_batt



def run_experiment():
    test_configs = [
        ("Small (30)", 30, "C"),
        ("Medium (60)", 60, "C"),
        ("Large (100)", 100, "C")
    ]

    base_res = []
    imp_res = []
    base_conv = []
    imp_conv = []

    for label, n, typ in test_configs:
        print(f"\n===== 正在测试 {label} 客户 =====")
        ins = ECVRPTWInstance(n_customers=n, instance_type=typ)

        
        ga1 = BaseGA(ins)
        r1 = ga1.run()
        base_res.append(r1)
        base_conv.append(r1["convergence"])
        print(f"基线GA | 可行:{r1['feasible']} | 真实距离:{r1['real_dist']:.2f} | 耗时:{r1['runtime']:.2f}s | TW违规:{r1['tw_violations']} | 电池违规:{r1['batt_violations']}")

        
        ga2 = ImprovedGA(ins)
        r2 = ga2.run()
        imp_res.append(r2)
        imp_conv.append(r2["convergence"])
        print(f"改进GA | 可行:{r2['feasible']} | 真实距离:{r2['real_dist']:.2f} | 耗时:{r2['runtime']:.2f}s | TW违规:{r2['tw_violations']} | 电池违规:{r2['batt_violations']}")

    
    labels = [c[0] for c in test_configs]
    x = np.arange(len(labels))
    width = 0.35

    plt.rcParams['font.size'] = 10
    fig = plt.figure(figsize=(14, 9))

    
    ax1 = plt.subplot(2, 2, 1)
    ax1.bar(x - width/2, [r["real_dist"] for r in base_res], width, label="Baseline GA", color="#ff7f0e")
    ax1.bar(x + width/2, [r["real_dist"] for r in imp_res], width, label="Improved GA", color="#1f77b4")
    ax1.set_title("Real Travel Distance Comparison")
    ax1.set_ylabel("Total Distance")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3, linestyle="--")

    
    ax2 = plt.subplot(2, 2, 2)
    ax2.bar(x - width/2, [r["runtime"] for r in base_res], width, label="Baseline GA", color="#ff7f0e")
    ax2.bar(x + width/2, [r["runtime"] for r in imp_res], width, label="Improved GA", color="#1f77b4")
    ax2.set_title("Runtime Comparison (Seconds)")
    ax2.set_ylabel("Runtime (s)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.legend()
    ax2.grid(axis="y", alpha=0.3, linestyle="--")

    
    ax3 = plt.subplot(2, 2, 3)
    base_vio = [r["tw_violations"] + r["batt_violations"] for r in base_res]
    imp_vio = [r["tw_violations"] + r["batt_violations"] for r in imp_res]
    ax3.bar(x - width/2, base_vio, width, label="Baseline GA", color="#ff7f0e")
    ax3.bar(x + width/2, imp_vio, width, label="Improved GA", color="#1f77b4")
    ax3.set_title("Total Constraint Violations")
    ax3.set_ylabel("Violation Count")
    ax3.set_xticks(x)
    ax3.set_xticklabels(labels)
    ax3.legend()
    ax3.grid(axis="y", alpha=0.3, linestyle="--")

    
    ax4 = plt.subplot(2, 2, 4)
    ax4.plot(base_conv[1], label="Baseline GA", color="#ff7f0e", linewidth=1.5)
    ax4.plot(imp_conv[1], label="Improved GA", color="#1f77b4", linewidth=1.5)
    ax4.set_title("Convergence Curve (Medium Instance)")
    ax4.set_xlabel("Generation")
    ax4.set_ylabel("Best Objective Value")
    ax4.legend()
    ax4.grid(alpha=0.3, linestyle="--")

    plt.tight_layout()
    plt.show()
    return base_res, imp_res



if __name__ == "__main__":
    base, imp = run_experiment()
    print("\n" + "="*60)
    print("实验完成！图表已在 Plots 面板生成")
    print("预期趋势：小规模均可行，中规模基线不可行/改进可行，大规模改进部分可行")
    print("="*60)