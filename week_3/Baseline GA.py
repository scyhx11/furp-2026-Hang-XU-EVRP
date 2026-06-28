import numpy as np
import random
from solomon_data import SolomonInstance

class BaseGA:
    def __init__(self, ins: SolomonInstance, pop_size=100, max_iter=500, time_limit=60):
        self.ins = ins
        self.N = ins.n
        self.pop_size = pop_size
        self.max_iter = max_iter
        self.time_limit = time_limit
        self.p_cross = 0.8
        self.p_mut = 0.1
        self.penalty_tw = 1000    # 时间窗违规惩罚
        self.penalty_batt = 1000  # 电量耗尽惩罚
        self.penalty_load = 1000  # 载重惩罚

    def create_individual(self):
        # 随机客户排列
        cust = list(range(1, self.N+1))
        random.shuffle(cust)
        return cust

    def calc_fitness(self, route):
        total_cost = 0.0
        penalty = 0
        pos = 0
        load = 0
        battery = self.ins.max_battery
        time_clock = 0

        # 起点仓库0
        prev = 0
        for c in route:
            dist = self.ins.get_dist(prev, c)
            total_cost += dist
            battery -= dist
            time_clock += dist

            # 载重约束
            load += self.ins.demand[c]
            if load > self.ins.vehicle_cap:
                penalty += self.penalty_load

            # 时间窗违规
            if time_clock < self.ins.tw_start[c]:
                time_clock = self.ins.tw_start[c]
            if time_clock > self.ins.tw_end[c]:
                penalty += self.penalty_tw

            # 电量耗尽惩罚（基线仅罚，不修复）
            if battery < 0:
                penalty += self.penalty_batt

            time_clock += self.ins.service[c]
            prev = c

        # 返回仓库
        dist_back = self.ins.get_dist(prev, 0)
        total_cost += dist_back
        battery -= dist_back

        return total_cost + penalty

    # 轮盘赌选择
    def selection(self, pop, fits):
        total_fit = sum(1/(f+1e-6) for f in fits)
        r = random.random() * total_fit
        cum = 0
        for idx, f in enumerate(fits):
            cum += 1/(f+1e-6)
            if cum >= r:
                return pop[idx]
        return pop[-1]

    # OX顺序交叉
    def ox_crossover(self, p1, p2):
        n = len(p1)
        a, b = sorted(random.sample(range(n), 2))
        child = [-1]*n
        child[a:b+1] = p1[a:b+1]
        ptr = 0
        for gene in p2:
            if gene not in child:
                while child[ptr] != -1:
                    ptr += 1
                child[ptr] = gene
        return child

    # 交换变异
    def swap_mutate(self, ind):
        if random.random() < self.p_mut:
            i, j = random.sample(range(len(ind)), 2)
            ind[i], ind[j] = ind[j], ind[i]
        return ind

    def run(self):
        pop = [self.create_individual() for _ in range(self.pop_size)]
        best_cost = float('inf')
        best_sol = None

        for it in range(self.max_iter):
            fits = [self.calc_fitness(ind) for ind in pop]
            # 更新全局最优
            min_fit = min(fits)
            if min_fit < best_cost:
                best_cost = min_fit
                best_sol = pop[fits.index(min_fit)].copy()
            # 新一代
            new_pop = []
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
        # 判断可行解：惩罚=0则可行
        final_penalty = best_cost - (best_cost % min(self.penalty_tw, self.penalty_batt))
        feasible = True if final_penalty < 1e-3 else False
        return {
            "cost": best_cost,
            "feasible": feasible,
            "route": best_sol
        }