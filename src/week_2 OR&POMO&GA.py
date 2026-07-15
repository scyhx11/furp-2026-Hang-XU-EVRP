# open Anaconda PowerShell Prompt
# conda activate or-tools-env
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# spyder
import numpy as np
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
import random
import time
from copy import deepcopy
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

random.seed(42)
np.random.seed(42)
torch.manual_seed(42)


class VRPInstance:
    def __init__(self, n_customers=50, vehicle_cap=30):
        self.n = n_customers
        self.capacity_E = vehicle_cap  
        
        self.coords = np.random.rand(self.n + 1, 2)
        
        self.demands = np.random.randint(1, 10, self.n + 1)
        self.demands[0] = 0
        
        self.time_window_TW = np.zeros((self.n + 1, 2))
        self.time_window_TW[0] = [0, 2000]  
        for i in range(1, self.n + 1):
            t_start = random.randint(20, 600)
            t_end = t_start + random.randint(80, 300)
            self.time_window_TW[i] = [t_start, t_end]

    def get_distance(self, a, b):
        
        return np.linalg.norm(self.coords[a] - self.coords[b])

    def build_distance_matrix(self):
        
        n_node = len(self.coords)
        dist_mat = np.zeros((n_node, n_node))
        for i in range(n_node):
            for j in range(n_node):
                dist_mat[i][j] = self.get_distance(i, j)
        return dist_mat

    def check_single_route_valid(self, route):
        
        total_dist = 0.0
        current_load = 0
        current_time = 0.0
        prev_node = route[0]
        for node in route[1:]:
            d = self.get_distance(prev_node, node)
            total_dist += d
            current_time += d * 10 
            
            current_load += self.demands[node]
            if current_load > self.capacity_E:
                return total_dist, False
            
            tw_early, tw_late = self.time_window_TW[node]
            if current_time < tw_early:
                current_time = tw_early  
            if current_time > tw_late:
                return total_dist, False  
            prev_node = node
        return total_dist, True

    def check_multi_route_valid(self, routes):
        
        total_dist = 0.0
        all_feasible = True
        for route in routes:
            d, valid = self.check_single_route_valid(route)
            total_dist += d
            if not valid:
                all_feasible = False
        return total_dist, all_feasible



class ORToolsCVRPTW:
    def __init__(self, inst: VRPInstance):
        self.inst = inst
        self.dist_matrix = inst.build_distance_matrix()
        self.node_num = inst.n + 1

    def solve(self):
       
        data = {
            "dist_matrix": (self.dist_matrix * 1000).astype(int),
            "demands": self.inst.demands.tolist(),
            "vehicle_cap": [self.inst.capacity_E] * self.inst.n,
            "vehicle_num": self.inst.n,
            "depot": 0,
            "time_windows": [(int(tw[0]), int(tw[1])) for tw in self.inst.time_window_TW]
        }

        
        manager = pywrapcp.RoutingIndexManager(
            self.node_num, data["vehicle_num"], data["depot"]
        )
        routing = pywrapcp.RoutingModel(manager)

        
        def dist_callback(from_idx, to_idx):
            f_node = manager.IndexToNode(from_idx)
            t_node = manager.IndexToNode(to_idx)
            return data["dist_matrix"][f_node][t_node]
        dist_transit = routing.RegisterTransitCallback(dist_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(dist_transit)

        
        def demand_callback(from_idx):
            node = manager.IndexToNode(from_idx)
            return data["demands"][node]
        demand_transit = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_transit, 0, data["vehicle_cap"], True, "Capacity_E"
        )

       
        def time_callback(from_idx, to_idx):
            f_node = manager.IndexToNode(from_idx)
            t_node = manager.IndexToNode(to_idx)
            return int(self.dist_matrix[f_node][t_node] * 10)
        time_transit = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(time_transit, 2000, 2000, False, "Time_TW")
        time_dim = routing.GetDimensionOrDie("Time_TW")
        for node_id in range(self.node_num):
            idx = manager.NodeToIndex(node_id)
            e, l = data["time_windows"][node_id]
            time_dim.CumulVar(idx).SetRange(e, l)

        
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_params.time_limit.seconds = 10

       
        solution = routing.SolveWithParameters(search_params)
        if solution:
            total_distance = 0.0
            for v in range(data["vehicle_num"]):
                idx = routing.Start(v)
                while not routing.IsEnd(idx):
                    next_idx = solution.Value(routing.NextVar(idx))
                    total_distance += routing.GetArcCostForVehicle(idx, next_idx, v) / 1000
                    idx = next_idx
            return total_distance, True
        else:
            return float("inf"), False



class GA_CVRPTW:
    def __init__(self, inst: VRPInstance, pop_size=100, gen=300):
        self.inst = inst
        self.customer_num = inst.n
        self.pop_size = pop_size
        self.max_gen = gen
        self.population = []
        self.best_seq = None
        self.best_fitness = float("inf")

    def create_individual(self):
        
        seq = list(range(1, self.customer_num + 1))
        random.shuffle(seq)
        return seq

    def split_sequence_to_routes(self, seq):
        
        routes = []
        current_route = [0]
        load = 0
        for cust in seq:
            req = self.inst.demands[cust]
            if load + req > self.inst.capacity_E:
                current_route.append(0)
                routes.append(current_route)
                current_route = [0, cust]
                load = req
            else:
                current_route.append(cust)
                load += req
        current_route.append(0)
        routes.append(current_route)
        return routes

    def calculate_fitness(self, seq):
       
        route_list = self.split_sequence_to_routes(seq)
        total_cost = 0.0
        penalty = 0
        for r in route_list:
            dist, feasible = self.inst.check_single_route_valid(r)
            total_cost += dist
            if not feasible:
                penalty += 10000  
        return total_cost + penalty

    def selection(self):
       
        fits = [self.calculate_fitness(ind) for ind in self.population]
        sorted_idx = np.argsort(fits)
        new_pop = [deepcopy(self.population[i]) for i in sorted_idx[:self.pop_size // 2]]
        return new_pop

    def crossover_order(self, p1, p2):
       
        length = len(p1)
        i, j = sorted(random.sample(range(length), 2))
        child = [-1] * length
        child[i:j] = p1[i:j]
        ptr = 0
        for val in p2:
            if val not in child:
                while child[ptr] != -1:
                    ptr += 1
                child[ptr] = val
        return child

    def mutate_swap(self, seq):
        
        i, j = random.sample(range(len(seq)), 2)
        seq[i], seq[j] = seq[j], seq[i]
        return seq

    def run_optimize(self):
        
        self.population = [self.create_individual() for _ in range(self.pop_size)]
        for g in range(self.max_gen):
            new_pop = self.selection()
            
            while len(new_pop) < self.pop_size:
                p1, p2 = random.sample(new_pop, 2)
                child = self.crossover_order(p1, p2)
                new_pop.append(self.mutate_swap(child))
            self.population = new_pop
           
            fit_list = [(self.calculate_fitness(ind), ind) for ind in self.population]
            min_fit, min_ind = min(fit_list, key=lambda x: x[0])
            if min_fit < self.best_fitness:
                self.best_fitness = min_fit
                self.best_seq = min_ind.copy()

        
        best_routes = self.split_sequence_to_routes(self.best_seq)
        real_dist, is_feasible = self.inst.check_multi_route_valid(best_routes)
        return real_dist, is_feasible



device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class AttentionEncoder(nn.Module):
    def __init__(self, embed_dim=128):
        super().__init__()
        
        self.embed_layer = nn.Linear(4, embed_dim)
        self.multi_head_attn = nn.MultiheadAttention(embed_dim, num_heads=8, batch_first=True)

    def forward(self, node_features):
        embedding = self.embed_layer(node_features)
        attn_out, _ = self.multi_head_attn(embedding, embedding, embedding)
        return embedding + attn_out  


class POMODecoder(nn.Module):
    def __init__(self, embed_dim=128):
        super().__init__()
        self.W_q = nn.Linear(embed_dim, embed_dim)
        self.W_k = nn.Linear(embed_dim, embed_dim)

    def forward(self, embeds, mask):
        query = self.W_q(embeds[:, 0:1])
        key = self.W_k(embeds)
        score = torch.matmul(query, key.transpose(-1, -2)) / np.sqrt(128)
        score.masked_fill_(mask, -1e10)
        logits = torch.softmax(score, dim=-1)
        return logits


class POMO_CVRPTW(nn.Module):
    def __init__(self, embed_dim=128):
        super().__init__()
        self.encoder = AttentionEncoder(embed_dim)
        self.decoder = POMODecoder(embed_dim)

    def forward(self, feat_tensor, inst: VRPInstance):
        batch_size, node_num, _ = feat_tensor.shape
        emb = self.encoder(feat_tensor)

        
        visited = torch.zeros((batch_size, node_num), dtype=torch.bool, device=device)
        visited[:, 0] = True  
        route_record = [torch.zeros(batch_size, dtype=torch.long, device=device)]
        load_state = torch.zeros(batch_size, device=device)
        time_state = torch.zeros(batch_size, device=device)
        cap_limit = inst.capacity_E
        tw_tensor = torch.tensor(inst.time_window_TW, device=device, dtype=torch.float32)
        dem_tensor = torch.tensor(inst.demands, device=device, dtype=torch.float32)

        for _ in range(inst.n):
            mask = visited.unsqueeze(1)
            logits = self.decoder(emb, mask)
            next_node = torch.argmax(logits, dim=-1).squeeze(1)
            route_record.append(next_node)

            
            for b_idx in range(batch_size):
                curr_node = next_node[b_idx].item()
                prev_node = route_record[-2][b_idx].item()
               
                load_state[b_idx] += dem_tensor[curr_node]
                
                dist_step = np.linalg.norm(inst.coords[prev_node] - inst.coords[curr_node])
                time_state[b_idx] += dist_step * 10
                tw_e, tw_l = tw_tensor[curr_node]

                
                if time_state[b_idx] < tw_e:
                    time_state[b_idx] = tw_e

                
                if load_state[b_idx] > cap_limit or time_state[b_idx] > tw_l:
                    next_node[b_idx] = 0
                    load_state[b_idx] = 0
                    time_state[b_idx] = 0
                    visited[b_idx, curr_node] = False  

            visited[torch.arange(batch_size), next_node] = True

        
        full_path = torch.stack(route_record, dim=1).cpu().numpy().tolist()[0]
        
        routes = []
        current_route = [0]
        for node in full_path[1:]:
            if node == 0:
                if len(current_route) > 1:
                    current_route.append(0)
                    routes.append(current_route)
                current_route = [0]
            else:
                if node not in current_route:
                    current_route.append(node)
        if len(current_route) > 1:
            current_route.append(0)
            routes.append(current_route)

        total_dist, feasible = inst.check_multi_route_valid(routes)
        return total_dist, feasible


def pomo_infer(inst: VRPInstance):
    
    model = POMO_CVRPTW().to(device)
    model.eval()
    n_node = inst.n + 1
    feat_matrix = np.zeros((1, n_node, 4))
    for i in range(n_node):
        x, y = inst.coords[i]
        d = inst.demands[i]
        tw_mid = (inst.time_window_TW[i, 0] + inst.time_window_TW[i, 1]) / 2
        feat_matrix[0, i] = [x, y, d, tw_mid]

    input_tensor = torch.tensor(feat_matrix, dtype=torch.float32, device=device)
    with torch.no_grad():
        dist_result, valid_flag = model(input_tensor, inst)
    return dist_result, valid_flag



def run_lab_experiment():
    scale_list = [50, 100, 200]

    res_ort = {"dist": [], "time": [], "feasible": []}
    res_pomo = {"dist": [], "time": [], "feasible": []}
    res_ga = {"dist": [], "time": [], "feasible": []}

    for customer_scale in scale_list:
        print(f"\n===== 测试算例规模：{customer_scale} 客户 (E容量+TW时间窗约束) =====")
        vrp_inst = VRPInstance(n_customers=customer_scale, vehicle_cap=30)

        
        t_start = time.time()
        ort_solver = ORToolsCVRPTW(vrp_inst)
        ort_dist, ort_valid = ort_solver.solve()
        ort_time = time.time() - t_start
        res_ort["dist"].append(round(ort_dist, 2))
        res_ort["time"].append(round(ort_time, 2))
        res_ort["feasible"].append(100 if ort_valid else 0)
        print(f"OR-Tools | 总距离:{ort_dist:.2f} | 耗时:{ort_time:.2f}s | 可行解:{ort_valid}")

        
        t_start = time.time()
        pomo_dist, pomo_valid = pomo_infer(vrp_inst)
        pomo_time = time.time() - t_start
        res_pomo["dist"].append(round(pomo_dist, 2))
        res_pomo["time"].append(round(pomo_time, 2))
        res_pomo["feasible"].append(100 if pomo_valid else 0)
        print(f"POMO     | 总距离:{pomo_dist:.2f} | 耗时:{pomo_time:.2f}s | 可行解:{pomo_valid}")

       
        t_start = time.time()
        ga_solver = GA_CVRPTW(vrp_inst, pop_size=100, gen=300)
        ga_dist, ga_valid = ga_solver.run_optimize()
        ga_time = time.time() - t_start
        res_ga["dist"].append(round(ga_dist, 2))
        res_ga["time"].append(round(ga_time, 2))
        res_ga["feasible"].append(100 if ga_valid else 0)
        print(f"GA       | 总距离:{ga_dist:.2f} | 耗时:{ga_time:.2f}s | 可行解:{ga_valid}")

  
    fig, axes = plt.subplots(1, 3, figsize=(21, 6))
    x_axis = np.arange(len(scale_list))
    bar_width = 0.25
    colors = {"OR-Tools": "#1f77b4", "POMO": "#d62728", "GA": "#ff7f0e"}

    
    axes[0].bar(x_axis - bar_width, res_ort["dist"], bar_width,
                label="OR-Tools", color=colors["OR-Tools"])
    axes[0].bar(x_axis, res_pomo["dist"], bar_width,
                label="POMO (untrained)", color=colors["POMO"])
    axes[0].bar(x_axis + bar_width, res_ga["dist"], bar_width,
                label="GA", color=colors["GA"])
    axes[0].set_title("Total Travel Distance (Objective Value)", fontsize=12, pad=10)
    axes[0].set_xlabel("Number of Customers", fontsize=10)
    axes[0].set_ylabel("Distance (Euclidean unit)", fontsize=10)
    axes[0].set_xticks(x_axis)
    axes[0].set_xticklabels(scale_list)
    axes[0].legend(framealpha=0.9)
    axes[0].grid(axis="y", alpha=0.3, linestyle="--")

    
    axes[1].plot(scale_list, res_ort["time"], marker="o", linewidth=2,
                 label="OR-Tools", color=colors["OR-Tools"])
    axes[1].plot(scale_list, res_pomo["time"], marker="s", linewidth=2,
                 label="POMO (untrained)", color=colors["POMO"])
    axes[1].plot(scale_list, res_ga["time"], marker="^", linewidth=2,
                 label="GA", color=colors["GA"])
    axes[1].set_title("Average Solving Runtime", fontsize=12, pad=10)
    axes[1].set_xlabel("Number of Customers", fontsize=10)
    axes[1].set_ylabel("Time (seconds)", fontsize=10)
    axes[1].legend(framealpha=0.9)
    axes[1].grid(alpha=0.3, linestyle="--")

    axes[2].bar(x_axis - bar_width, res_ort["feasible"], bar_width,
                color=colors["OR-Tools"])
    axes[2].bar(x_axis, res_pomo["feasible"], bar_width,
                color=colors["POMO"])
    axes[2].bar(x_axis + bar_width, res_ga["feasible"], bar_width,
                color=colors["GA"])
    axes[2].set_title("Feasible Solution Rate (E+TW Dual Constraints)", fontsize=12, pad=10)
    axes[2].set_xlabel("Number of Customers", fontsize=10)
    axes[2].set_ylabel("Feasibility Rate (%)", fontsize=10)
    axes[2].set_xticks(x_axis)
    axes[2].set_xticklabels(scale_list)
    axes[2].legend(["OR-Tools", "POMO (untrained)", "GA"], framealpha=0.9)
    axes[2].set_ylim(0, 105)
    axes[2].grid(axis="y", alpha=0.3, linestyle="--")

    plt.tight_layout()
    plt.show()
    return res_ort, res_pomo, res_ga


if __name__ == "__main__":
    ort_res, pomo_res, ga_res = run_lab_experiment()
    print("\n" + "=" * 50)
    print("===== 全部实验汇总结果 =====")
    print(f"OR-Tools 距离: {ort_res['dist']} | 耗时: {ort_res['time']} | 可行率: {ort_res['feasible']}")
    print(f"POMO     距离: {pomo_res['dist']} | 耗时: {pomo_res['time']} | 可行率: {pomo_res['feasible']}")
    print(f"GA       距离: {ga_res['dist']} | 耗时: {ga_res['time']} | 可行率: {ga_res['feasible']}")
    print("=" * 50)