from base_ga import BaseGA
import numpy as np
import random

class ImprovedGA(BaseGA):
    def __init__(self, ins, pop_size=100, max_iter=500, time_limit=60):
        super().__init__(ins, pop_size, max_iter, time_limit)

    # 修复算子1：时间窗违规重排修复
    def repair_time_window(self, route):
        new_route = route.copy()
        time_line = 0
        prev = 0
        for idx, c in enumerate(new_route):
            dist = self.ins.get_dist(prev, c)
            time_line += dist
            # 迟到，把该客户后移
            if time_line > self.ins.tw_end[c]:
                # 取出插入到末尾
                cust = new_route.pop(idx)
                new_route.append(cust)
                prev = new_route[idx-1] if idx>0 else 0
                time_line = self.ins.tw_end[prev] + self.ins.service[prev]
            else:
                if time_line < self.ins.tw_start[c]:
                    time_line = self.ins.tw_start[c]
                time_line += self.ins.service[c]
                prev = c
        return new_route

    # 修复算子2：电量不足时插入充电站
    def repair_battery(self, route):
        new_route = []
        battery = self.ins.max_battery
        prev = 0
        for c in route:
            dist = self.ins.get_dist(prev, c)
            if battery - dist < 0:
                # 插入充电站0（仓库充电）
                new_route.append(0)
                battery = self.ins.max_battery
            new_route.append(c)
            battery -= dist
            prev = c
        # 移除多余仓库节点（仅保留首尾）
        clean = []
        for node in new_route:
            if node != 0 or len(clean)==0:
                clean.append(node)
        return clean

    # 重写适应度：先修复再计算，几乎无惩罚
    def calc_fitness(self, route):
        # 两步主动修复
        rt1 = self.repair_time_window(route)
        rt2 = self.repair_battery(rt1)
        total_cost = 0.0
        penalty = 0
        load = 0
        battery = self.ins.max_battery
        time_clock = 0
        prev = 0
        for c in rt2:
            dist = self.ins.get_dist(prev, c)
            total_cost += dist
            battery -= dist
            time_clock += dist
            load += self.ins.demand[c] if c != 0 else 0
            if load > self.ins.vehicle_cap:
                penalty += self.penalty_load
            if c != 0:
                if time_clock < self.ins.tw_start[c]:
                    time_clock = self.ins.tw_start[c]
                if time_clock > self.ins.tw_end[c]:
                    penalty += self.penalty_tw
                time_clock += self.ins.service[c]
            prev = c
        dist_back = self.ins.get_dist(prev, 0)
        total_cost += dist_back
        return total_cost + penalty

    def run(self):
        pop = [self.create_individual() for _ in range(self.pop_size)]
        best_cost = float('inf')
        best_sol = None
        for it in range(self.max_iter):
            fits = [self.calc_fitness(ind) for ind in pop]
            min_fit = min(fits)
            if min_fit < best_cost:
                best_cost = min_fit
                best_sol = pop[fits.index(min_fit)].copy()
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
        final_penalty = best_cost - (best_cost % min(self.penalty_tw, self.penalty_batt))
        feasible = True if final_penalty < 1e-3 else False
        return {
            "cost": best_cost,
            "feasible": feasible,
            "route": best_sol
        }