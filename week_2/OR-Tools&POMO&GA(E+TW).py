# -*- coding: utf-8 -*-
"""
Created on Fri Jun 19 00:46:13 2026

@author: xuhan
"""

import numpy as np
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
import random
import time
from copy import deepcopy
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# ====================== 1. VRP算例生成器（自带容量E、时间窗TW） ======================
class VRPInstance:
    def __init__(self, n_customers=50, vehicle_cap=30):
        self.n = n_customers
        self.capacity_E = vehicle_cap  # 容量约束E
        # 坐标：0=仓库，1~n客户
        self.coords = np.random.rand(self.n + 1, 2)
        # 客户需求量
        self.demands = np.random.randint(1, 10, self.n + 1)
        self.demands[0] = 0
        # 时间窗约束 TW [最早到达时间, 最晚到达时间]
        self.time_window_TW = np.zeros((self.n + 1, 2))
        self.time_window_TW[0] = [0, 2000]  # 仓库无时间限制
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
        """校验单条路线是否满足 E容量 + TW时间窗 双约束"""
        total_dist = 0.0
        current_load = 0
        current_time = 0.0
        prev_node = 0
        for node in route[1:]:
            d = self.get_distance(prev_node, node)
            total_dist += d
            current_time += d * 10  # 距离换算行驶时间
            # 约束E：车辆载重不能超限
            current_load += self.demands[node]
            if current_load > self.capacity_E:
                return total_dist, False
            # 约束TW：客户时间窗
            tw_early, tw_late = self.time_window_TW[node]
            if current_time < tw_early:
                current_time = tw_early  # 早到等待
            if current_time > tw_late:
                return total_dist, False  # 迟到，不可行
            prev_node = node
        return total_dist, True

# ====================== 2. OR-Tools 基准求解器（原生E+TW硬约束） ======================
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
        # 初始化路由模型
        manager = pywrapcp.RoutingIndexManager(self.node_num, data["vehicle_num"], data["depot"])
        routing = pywrapcp.RoutingModel(manager)

        # 距离代价回调
        def dist_callback(from_idx, to_idx):
            f_node = manager.IndexToNode(from_idx)
            t_node = manager.IndexToNode(to_idx)
            return data["dist_matrix"][f_node][t_node]
        dist_transit = routing.RegisterTransitCallback(dist_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(dist_transit)

        # 约束E：车辆容量维度
        def demand_callback(from_idx):
            node = manager.IndexToNode(from_idx)
            return data["demands"][node]
        demand_transit = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_transit, 0, data["vehicle_cap"], True, "Capacity_E"
        )

        # 约束TW：时间窗维度
        def time_callback(from_idx, to_idx):
            f_node = manager.IndexToNode(from_idx)
            t_node = manager.IndexToNode(to_idx)
            return int(self.dist_matrix[f_node][t_node] * 10)
        time_transit = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(time_transit, 3000, 2000, False, "Time_TW")
        time_dim = routing.GetDimensionOrDie("Time_TW")
        for node_id in range(self.node_num):
            idx = manager.NodeToIndex(node_id)
            e, l = data["time_windows"][node_id]
            time_dim.CumulVar(idx).SetRange(e, l)

        # 搜索参数
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
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

# ====================== 3. GA遗传算法（手动实现E容量、TW时间窗约束） ======================
class GA_CVRPTW:
    def __init__(self, inst: VRPInstance, pop_size=200, gen=500):
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
        """分割客户序列为多条车辆路径，处理容量E约束"""
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
        """适应度：总距离 + 违规惩罚（E超载、TW迟到）"""
        route_list = self.split_sequence_to_routes(seq)
        total_cost = 0.0
        penalty = 0
        for r in route_list:
            dist, feasible = self.inst.check_single_route_valid(r)
            total_cost += dist
            if not feasible:
                penalty += 10000  # 违规大幅惩罚
        return total_cost + penalty

    def selection(self):
        fits = [self.calculate_fitness(ind) for ind in self.population]
        sorted_idx = np.argsort(fits)
        new_pop = [deepcopy(self.population[i]) for i in sorted_idx[:self.pop_size//2]]
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
        # 初始化种群
        self.population = [self.create_individual() for _ in range(self.pop_size)]
        for g in range(self.max_gen):
            new_pop = self.selection()
            # 交叉生成子代
            while len(new_pop) < self.pop_size:
                p1, p2 = random.sample(new_pop, 2)
                child = self.crossover_order(p1, p2)
                new_pop.append(self.mutate_swap(child))
            self.population = new_pop
            # 更新全局最优
            fit_list = [(self.calculate_fitness(ind), ind) for ind in self.population]
            min_fit, min_ind = min(fit_list, key=lambda x: x[0])
            if min_fit < self.best_fitness:
                self.best_fitness = min_fit
                self.best_seq = min_ind.copy()
        # 计算真实距离与可行性
        best_routes = self.split_sequence_to_routes(self.best_seq)
        real_dist = 0
        is_feasible = True
        for r in best_routes:
            d, valid = self.inst.check_single_route_valid(r)
            real_dist += d
            if not valid:
                is_feasible = False
        return real_dist, is_feasible

# ====================== 4. POMO深度学习模型（手动添加E容量、TW时间窗约束） ======================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class AttentionEncoder(nn.Module):
    def __init__(self, embed_dim=128):
        super().__init__()
        # 输入特征：x坐标, y坐标, 需求量, 时间窗中点
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
        visited[:, 0] = True  # 仓库已访问
        route_record = [torch.zeros(batch_size, dtype=torch.long, device=device)]
        load_state = torch.zeros(batch_size, device=device)
        time_state = torch.zeros(batch_size, device=device)
        cap_limit = inst.capacity_E
        tw_tensor = torch.tensor(inst.time_window_TW, device=device)
        dem_tensor = torch.tensor(inst.demands, device=device)

        for _ in range(inst.n):
            mask = visited.unsqueeze(1)
            logits = self.decoder(emb, mask)
            next_node = torch.argmax(logits, dim=-1).squeeze(1)
            route_record.append(next_node)

            # 逐样本校验 E容量 + TW时间窗约束
            for b_idx in range(batch_size):
                curr_node = next_node[b_idx].item()
                prev_node = route_record[-2][b_idx].item()
                # 更新载重
                load_state[b_idx] += dem_tensor[curr_node]
                # 更新行驶时间
                dist_step = np.linalg.norm(inst.coords[prev_node] - inst.coords[curr_node])
                time_state[b_idx] += dist_step * 10
                tw_e, tw_l = tw_tensor[curr_node]
                # 早到等待
                if time_state[b_idx] < tw_e:
                    time_state[b_idx] = tw_e
                # 超载 or 迟到：强制返回仓库重置所有约束状态
                if load_state[b_idx] > cap_limit or time_state[b_idx] > tw_l:
                    visited[b_idx] = torch.zeros_like(visited[b_idx])
                    visited[b_idx, 0] = True
                    load_state[b_idx] = 0
                    time_state[b_idx] = 0
            visited[torch.arange(batch_size), next_node] = True

        full_path = torch.stack(route_record, dim=1)
        total_dist, feasible = inst.check_single_route_valid(full_path[0].cpu().numpy().tolist())
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

# ====================== 5. 批量实验 + 三算法对比绘图 ======================
def run_lab_experiment():
    scale_list = [50, 100, 200]
    # 存储三类算法指标：距离、耗时、可行率
    res_ort = {"dist": [], "time": [], "feasible": []}
    res_pomo = {"dist": [], "time": [], "feasible": []}
    res_ga = {"dist": [], "time": [], "feasible": []}

    for customer_scale in scale_list:
        print(f"\n===== 测试算例规模：{customer_scale} 客户 (E容量+TW时间窗约束) =====")
        vrp_inst = VRPInstance(n_customers=customer_scale, vehicle_cap=30)

        # 1. OR-Tools 精确求解
        t_start = time.time()
        ort_solver = ORToolsCVRPTW(vrp_inst)
        ort_dist, ort_valid = ort_solver.solve()
        ort_time = time.time() - t_start
        res_ort["dist"].append(ort_dist)
        res_ort["time"].append(ort_time)
        res_ort["feasible"].append(100 if ort_valid else 0)
        print(f"OR-Tools | 总距离:{ort_dist:.2f} | 耗时:{ort_time:.2f}s | 可行解:{ort_valid}")

        # 2. POMO 深度学习求解（自实现E、TW约束）
        t_start = time.time()
        pomo_dist, pomo_valid = pomo_infer(vrp_inst)
        pomo_time = time.time() - t_start
        res_pomo["dist"].append(pomo_dist)
        res_pomo["time"].append(pomo_time)
        res_pomo["feasible"].append(100 if pomo_valid else 0)
        print(f"POMO     | 总距离:{pomo_dist:.2f} | 耗时:{pomo_time:.2f}s | 可行解:{pomo_valid}")

        # 3. GA 遗传算法（自实现E、TW约束）
        t_start = time.time()
        ga_solver = GA_CVRPTW(vrp_inst, pop_size=100, gen=300)
        ga_dist, ga_valid = ga_solver.run_optimize()
        ga_time = time.time() - t_start
        res_ga["dist"].append(ga_dist)
        res_ga["time"].append(ga_time)
        res_ga["feasible"].append(100 if ga_valid else 0)
        print(f"GA       | 总距离:{ga_dist:.2f} | 耗时:{ga_time:.2f}s | 可行解:{ga_valid}")

    # 绘制三张对比图表
    fig, axes = plt.subplots(1, 3, figsize=(21, 6))
    x_axis = np.arange(len(scale_list))
    bar_width = 0.25

    # 图1：目标总行驶距离对比
    axes[0].bar(x_axis - bar_width, res_ort["dist"], bar_width, label="OR-Tools (基准最优)", color="#1f77b4")
    axes[0].bar(x_axis, res_pomo["dist"], bar_width, label="POMO (DL, 自实现E+TW)", color="#d62728")
    axes[0].bar(x_axis + bar_width, res_ga["dist"], bar_width, label="GA (元启发, 自实现E+TW)", color="#ff7f0e")
    axes[0].set_title("Total Travel Distance (Objective Value)")
    axes[0].set_xlabel("Number of Customers")
    axes[0].set_xticks(x_axis)
    axes[0].set_xticklabels(scale_list)
    axes[0].legend()
    axes[0].grid(axis="y", alpha=0.3)

    # 图2：运行时间折线对比
    axes[1].plot(scale_list, res_ort["time"], marker="o", linewidth=2, label="OR-Tools")
    axes[1].plot(scale_list, res_pomo["time"], marker="s", linewidth=2, label="POMO")
    axes[1].plot(scale_list, res_ga["time"], marker="^", linewidth=2, label="GA")
    axes[1].set_title("Average Solving Runtime (Seconds)")
    axes[1].set_xlabel("Number of Customers")
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    # 图3：可行解占比（E+TW双约束下）
    axes[2].bar(x_axis - bar_width, res_ort["feasible"], bar_width, color="#1f77b4")
    axes[2].bar(x_axis, res_pomo["feasible"], bar_width, color="#d62728")
    axes[2].bar(x_axis + bar_width, res_ga["feasible"], bar_width, color="#ff7f0e")
    axes[2].set_title("Feasible Solution Rate (E+TW Constraints) %")
    axes[2].set_xlabel("Number of Customers")
    axes[2].set_xticks(x_axis)
    axes[2].set_xticklabels(scale_list)
    axes[2].legend(["OR-Tools", "POMO", "GA"])
    axes[2].set_ylim(0, 105)
    axes[2].grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.show()
    return res_ort, res_pomo, res_ga

if __name__ == "__main__":
    ort_res, pomo_res, ga_res = run_lab_experiment()
    print("\n===== 全部实验汇总结果 =====")
    print("OR-Tools 结果：", ort_res)
    print("POMO 结果：", pomo_res)
    print("GA 结果：", ga_res)