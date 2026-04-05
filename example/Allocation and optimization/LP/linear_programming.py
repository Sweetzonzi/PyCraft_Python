"""
线性规划求解器 - 实现单纯形法
"""

import numpy as np
from typing import List, Tuple, Dict, Any


class LinearProgrammingSolver:
    """单纯形法线性规划求解器"""

    def __init__(self, c: List[float], A: List[List[float]], b: List[float]):
        """
        初始化线性规划问题
        c: 目标函数系数 [c1, c2, ..., cn]
        A: 约束矩阵 m×n
        b: 约束右端项 [b1, b2, ..., bm]
        """
        self.c = np.array(c, dtype=float)
        self.A = np.array(A, dtype=float)
        self.b = np.array(b, dtype=float)
        self.n = len(c)  # 决策变量个数
        self.m = len(b)  # 约束个数

    def simplex(self) -> Tuple[np.ndarray, float, List[Dict]]:
        """
        实现单纯形法求解
        返回: (最优解, 最优值, 迭代历史)
        """
        # 转换为标准形式（最大化问题）
        c_std = np.concatenate([self.c, np.zeros(self.m)])  # 添加松弛变量
        A_std = np.hstack([self.A, np.eye(self.m)])  # 添加单位矩阵

        # 初始基本可行解（松弛变量作为基变量）
        basis = list(range(self.n, self.n + self.m))  # 松弛变量索引
        non_basis = list(range(self.n))  # 决策变量索引

        iterations = []
        iteration = 0

        while True:
            # 计算当前基的逆矩阵
            c_b = c_std[basis]
            try:
                B_inv = np.linalg.inv(A_std[:, basis])
            except np.linalg.LinAlgError:
                # 矩阵不可逆，可能退化，尝试添加小扰动
                B_inv = np.linalg.pinv(A_std[:, basis])

            # 计算当前解：x_B = B_inv @ b, 非基变量为0
            x_B = B_inv @ self.b
            x = np.zeros(self.n + self.m)
            x[basis] = x_B

            # 计算目标值
            z = c_b @ x_B

            # 记录迭代信息
            iterations.append({
                'iteration': iteration,
                'basis': basis.copy(),
                'solution': x[:self.n].copy(),  # 只保留决策变量
                'objective': z,
                'status': 'in_progress'
            })

            # 计算检验数
            reduced_costs = c_std[non_basis] - c_b @ B_inv @ A_std[:, non_basis]

            # 检查最优性
            if np.all(reduced_costs <= 1e-10):  # 考虑数值误差
                iterations[-1]['status'] = 'optimal'
                return x[:self.n], z, iterations

            # 选择进基变量（最大正检验数）
            entering_idx = np.argmax(reduced_costs)
            entering_var = non_basis[entering_idx]

            # 计算进基列
            d = B_inv @ A_std[:, entering_var]

            # 检查无界性
            if np.all(d <= 1e-10):
                iterations[-1]['status'] = 'unbounded'
                raise ValueError("问题无界")

            # 选择离基变量（最小比值测试）
            ratios = np.where(d > 1e-10, x[basis] / d, np.inf)
            leaving_idx = np.argmin(ratios)
            leaving_var = basis[leaving_idx]

            # 更新基变量
            basis[leaving_idx] = entering_var
            non_basis[entering_idx] = leaving_var

            iteration += 1

            # 防止无限循环（防止退化循环）
            if iteration > 100:
                iterations[-1]['status'] = 'max_iterations'
                raise ValueError("达到最大迭代次数，可能发生退化循环")

    def solve(self) -> Tuple[np.ndarray, float, List[Dict]]:
        """求解线性规划问题的封装方法"""
        try:
            return self.simplex()
        except Exception as e:
            print(f"单纯形法求解失败: {e}")
            # 尝试使用numpy的线性规划求解器作为备选
            try:
                from scipy.optimize import linprog
                result = linprog(-self.c, A_ub=self.A, b_ub=self.b, method='highs')
                if result.success:
                    solution = result.x
                    objective = -result.fun
                    iterations = [{'iteration': 0, 'solution': solution,
                                 'objective': objective, 'status': 'optimal'}]
                    return solution, objective, iterations
                else:
                    raise ValueError(f"Scipy求解失败: {result.message}")
            except ImportError:
                raise ValueError(f"单纯形法失败且未安装scipy: {e}")


def test_simplex():
    """测试函数"""
    # 测试问题：最大化 3x1 + 5x2
    # 约束：x1 ≤ 4, 2x2 ≤ 12, 3x1 + 2x2 ≤ 18
    c = [3, 5]
    A = [[1, 0], [0, 2], [3, 2]]
    b = [4, 12, 18]

    solver = LinearProgrammingSolver(c, A, b)
    solution, objective, iterations = solver.solve()

    print("测试问题:")
    print(f"  目标函数: max 3x1 + 5x2")
    print(f"  约束: x1 ≤ 4, 2x2 ≤ 12, 3x1 + 2x2 ≤ 18")
    print(f"  最优解: x1={solution[0]:.2f}, x2={solution[1]:.2f}")
    print(f"  最优值: {objective:.2f}")
    print(f"  迭代次数: {len(iterations)}")

    return solution, objective


if __name__ == "__main__":
    test_simplex()