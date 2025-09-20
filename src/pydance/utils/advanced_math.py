"""
Advanced mathematical utilities for PyDance
High-performance mathematical functions and algorithms
"""

import math
import cmath
import statistics
import numpy as np
from typing import List, Tuple, Union, Optional, Callable, Any
from decimal import Decimal, getcontext
from functools import lru_cache, reduce
import operator
from itertools import combinations, permutations
from collections import Counter, defaultdict


class AdvancedMathUtils:
    """Advanced mathematical utilities with high performance"""

    @staticmethod
    @lru_cache(maxsize=1000)
    def fibonacci_optimized(n: int) -> int:
        """Optimized Fibonacci calculation using matrix exponentiation"""
        if n < 0:
            raise ValueError("Negative Fibonacci numbers not supported")
        if n == 0:
            return 0
        if n == 1 or n == 2:
            return 1

        def multiply_matrices(a: List[List[int]], b: List[List[int]]) -> List[List[int]]:
            return [
                [a[0][0] * b[0][0] + a[0][1] * b[1][0], a[0][0] * b[0][1] + a[0][1] * b[1][1]],
                [a[1][0] * b[0][0] + a[1][1] * b[1][0], a[1][0] * b[0][1] + a[1][1] * b[1][1]]
            ]

        def matrix_power(matrix: List[List[int]], exp: int) -> List[List[int]]:
            result = [[1, 0], [0, 1]]  # Identity matrix
            while exp > 0:
                if exp % 2 == 1:
                    result = multiply_matrices(result, matrix)
                matrix = multiply_matrices(matrix, matrix)
                exp //= 2
            return result

        # Fibonacci matrix: [[1, 1], [1, 0]]
        fib_matrix = [[1, 1], [1, 0]]
        powered = matrix_power(fib_matrix, n - 1)
        return powered[0][0]

    @staticmethod
    def prime_factors(n: int) -> List[Tuple[int, int]]:
        """Get prime factors with their exponents"""
        factors = []
        # Check for factor 2
        count = 0
        while n % 2 == 0:
            count += 1
            n //= 2
        if count > 0:
            factors.append((2, count))

        # Check for odd factors
        for i in range(3, int(math.sqrt(n)) + 1, 2):
            count = 0
            while n % i == 0:
                count += 1
                n //= i
            if count > 0:
                factors.append((i, count))

        # If n is a prime number greater than 2
        if n > 2:
            factors.append((n, 1))

        return factors

    @staticmethod
    def gcd_extended(a: int, b: int) -> Tuple[int, int, int]:
        """Extended Euclidean algorithm - returns gcd and coefficients"""
        if a == 0:
            return b, 0, 1

        gcd, x1, y1 = AdvancedMathUtils.gcd_extended(b % a, a)
        x = y1 - (b // a) * x1
        y = x1

        return gcd, x, y

    @staticmethod
    def modular_inverse(a: int, m: int) -> int:
        """Calculate modular inverse using extended Euclidean algorithm"""
        gcd, x, y = AdvancedMathUtils.gcd_extended(a, m)
        if gcd != 1:
            raise ValueError("Modular inverse does not exist")
        return (x % m + m) % m

    @staticmethod
    def chinese_remainder_theorem(a: List[int], m: List[int]) -> int:
        """Solve system of congruences using Chinese Remainder Theorem"""
        if len(a) != len(m):
            raise ValueError("Lists must have same length")

        # Calculate M = m1 * m2 * ... * mk
        M = reduce(operator.mul, m)

        result = 0
        for ai, mi in zip(a, m):
            Mi = M // mi
            inv = AdvancedMathUtils.modular_inverse(Mi, mi)
            result += ai * Mi * inv

        return result % M

    @staticmethod
    def matrix_multiply(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
        """Matrix multiplication"""
        if len(A[0]) != len(B):
            raise ValueError("Matrix dimensions don't match for multiplication")

        result = [[0 for _ in range(len(B[0]))] for _ in range(len(A))]

        for i in range(len(A)):
            for j in range(len(B[0])):
                for k in range(len(B)):
                    result[i][j] += A[i][k] * B[k][j]

        return result

    @staticmethod
    def matrix_determinant(matrix: List[List[float]]) -> float:
        """Calculate matrix determinant"""
        n = len(matrix)
        if n != len(matrix[0]):
            raise ValueError("Matrix must be square")

        if n == 1:
            return matrix[0][0]
        if n == 2:
            return matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]

        det = 0
        for j in range(n):
            sub_matrix = [row[:j] + row[j+1:] for row in matrix[1:]]
            det += ((-1) ** j) * matrix[0][j] * AdvancedMathUtils.matrix_determinant(sub_matrix)

        return det

    @staticmethod
    def matrix_inverse(matrix: List[List[float]]) -> List[List[float]]:
        """Calculate matrix inverse"""
        det = AdvancedMathUtils.matrix_determinant(matrix)
        if det == 0:
            raise ValueError("Matrix is singular")

        n = len(matrix)
        adjugate = [[0 for _ in range(n)] for _ in range(n)]

        for i in range(n):
            for j in range(n):
                # Calculate cofactor
                sub_matrix = [row[:j] + row[j+1:] for row in (matrix[:i] + matrix[i+1:])]
                cofactor = ((-1) ** (i + j)) * AdvancedMathUtils.matrix_determinant(sub_matrix)
                adjugate[j][i] = cofactor  # Transpose

        return [[adjugate[i][j] / det for j in range(n)] for i in range(n)]

    @staticmethod
    def solve_linear_system(A: List[List[float]], b: List[float]) -> List[float]:
        """Solve linear system Ax = b using Gaussian elimination"""
        n = len(A)
        if len(A[0]) != n or len(b) != n:
            raise ValueError("Invalid matrix dimensions")

        # Create augmented matrix
        augmented = [row[:] + [b[i]] for i, row in enumerate(A)]

        # Forward elimination
        for i in range(n):
            # Find pivot
            pivot_row = i
            for j in range(i + 1, n):
                if abs(augmented[j][i]) > abs(augmented[pivot_row][i]):
                    pivot_row = j

            # Swap rows
            augmented[i], augmented[pivot_row] = augmented[pivot_row], augmented[i]

            # Eliminate
            for j in range(i + 1, n):
                factor = augmented[j][i] / augmented[i][i]
                for k in range(i, n + 1):
                    augmented[j][k] -= factor * augmented[i][k]

        # Back substitution
        x = [0] * n
        for i in range(n - 1, -1, -1):
            x[i] = augmented[i][n]
            for j in range(i + 1, n):
                x[i] -= augmented[i][j] * x[j]
            x[i] /= augmented[i][i]

        return x

    @staticmethod
    def polynomial_roots(coefficients: List[float]) -> List[complex]:
        """Find roots of polynomial using numpy"""
        return np.roots(coefficients).tolist()

    @staticmethod
    def numerical_integration(func: Callable[[float], float], a: float, b: float,
                            n: int = 1000) -> float:
        """Numerical integration using Simpson's rule"""
        if n % 2 != 0:
            n += 1  # Simpson's rule requires even number of intervals

        h = (b - a) / n
        integral = func(a) + func(b)

        for i in range(1, n):
            x = a + i * h
            if i % 2 == 0:
                integral += 2 * func(x)
            else:
                integral += 4 * func(x)

        return integral * h / 3

    @staticmethod
    def newton_method(func: Callable[[float], float],
                     derivative: Callable[[float], float],
                     initial_guess: float,
                     tolerance: float = 1e-10,
                     max_iterations: int = 100) -> float:
        """Newton-Raphson method for finding roots"""
        x = initial_guess
        for _ in range(max_iterations):
            fx = func(x)
            if abs(fx) < tolerance:
                return x
            dfx = derivative(x)
            if dfx == 0:
                raise ValueError("Derivative is zero")
            x = x - fx / dfx
        raise ValueError("Maximum iterations reached")

    @staticmethod
    def monte_carlo_integration(func: Callable[[float], float], a: float, b: float,
                               num_samples: int = 10000) -> float:
        """Monte Carlo integration"""
        total = 0
        for _ in range(num_samples):
            x = a + (b - a) * np.random.random()
            total += func(x)
        return (b - a) * total / num_samples

    @staticmethod
    def fast_fourier_transform(signal: List[complex]) -> List[complex]:
        """Fast Fourier Transform implementation"""
        n = len(signal)
        if n <= 1:
            return signal

        # Split into even and odd
        even = AdvancedMathUtils.fast_fourier_transform(signal[::2])
        odd = AdvancedMathUtils.fast_fourier_transform(signal[1::2])

        # Combine
        result = [0] * n
        for k in range(n // 2):
            t = cmath.exp(-2j * cmath.pi * k / n) * odd[k]
            result[k] = even[k] + t
            result[k + n // 2] = even[k] - t

        return result

    @staticmethod
    def statistical_tests(data1: List[float], data2: List[float]) -> Dict[str, float]:
        """Perform statistical tests between two datasets"""
        # T-test
        mean1, mean2 = statistics.mean(data1), statistics.mean(data2)
        std1, std2 = statistics.stdev(data1), statistics.stdev(data2)
        n1, n2 = len(data1), len(data2)

        t_statistic = (mean1 - mean2) / math.sqrt(std1**2/n1 + std2**2/n2)

        # F-test for variance equality
        if std1 > std2:
            f_statistic = std1**2 / std2**2
        else:
            f_statistic = std2**2 / std1**2

        return {
            't_statistic': t_statistic,
            'f_statistic': f_statistic,
            'mean_difference': mean1 - mean2,
            'pooled_std': math.sqrt(((n1-1)*std1**2 + (n2-1)*std2**2) / (n1 + n2 - 2))
        }

    @staticmethod
    def combinatorial_optimization(items: List[Any], weights: List[float],
                                 values: List[float], capacity: float) -> Tuple[List[Any], float]:
        """0/1 Knapsack problem using dynamic programming"""
        n = len(items)
        dp = [[0 for _ in range(int(capacity) + 1)] for _ in range(n + 1)]

        for i in range(1, n + 1):
            for w in range(int(capacity) + 1):
                if weights[i-1] <= w:
                    dp[i][w] = max(dp[i-1][w], dp[i-1][w - int(weights[i-1])] + values[i-1])
                else:
                    dp[i][w] = dp[i-1][w]

        # Backtrack to find selected items
        selected = []
        w = int(capacity)
        for i in range(n, 0, -1):
            if dp[i][w] != dp[i-1][w]:
                selected.append(items[i-1])
                w -= int(weights[i-1])

        return selected[::-1], dp[n][int(capacity)]

    @staticmethod
    def graph_shortest_path(adjacency_matrix: List[List[float]], start: int) -> List[float]:
        """Dijkstra's algorithm for shortest path"""
        n = len(adjacency_matrix)
        distances = [float('inf')] * n
        distances[start] = 0
        visited = [False] * n

        for _ in range(n):
            # Find unvisited node with minimum distance
            min_distance = float('inf')
            min_index = -1

            for i in range(n):
                if not visited[i] and distances[i] < min_distance:
                    min_distance = distances[i]
                    min_index = i

            if min_index == -1:
                break

            visited[min_index] = True

            # Update distances
            for i in range(n):
                if (not visited[i] and
                    adjacency_matrix[min_index][i] != 0 and
                    distances[min_index] + adjacency_matrix[min_index][i] < distances[i]):
                    distances[i] = distances[min_index] + adjacency_matrix[min_index][i]

        return distances

    @staticmethod
    def complex_analysis(func: Callable[[complex], complex], z0: complex,
                        iterations: int = 50) -> List[complex]:
        """Newton's method for complex functions"""
        z = z0
        result = [z]

        for _ in range(iterations):
            try:
                # Simple numerical derivative for complex functions
                h = 1e-8
                fz = func(z)
                fz_h = func(z + h)
                derivative = (fz_h - fz) / h

                if derivative == 0:
                    break

                z = z - fz / derivative
                result.append(z)

                # Check for convergence
                if abs(result[-1] - result[-2]) < 1e-12:
                    break

            except (ZeroDivisionError, OverflowError):
                break

        return result

    @staticmethod
    def fractal_dimension(points: List[Tuple[float, float]], epsilon: float = 0.1) -> float:
        """Estimate fractal dimension using box counting"""
        if not points:
            return 0

        # Find bounds
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)

        # Calculate number of boxes needed
        width = max_x - min_x
        height = max_y - min_y
        max_dim = max(width, height)

        if max_dim == 0:
            return 0

        # Number of boxes along each dimension
        n_boxes = int(max_dim / epsilon) + 1

        # Count boxes that contain points
        boxes = set()
        for x, y in points:
            box_x = int((x - min_x) / epsilon)
            box_y = int((y - min_y) / epsilon)
            boxes.add((box_x, box_y))

        # Fractal dimension estimation
        N = len(boxes)
        if N == 0:
            return 0

        return math.log(N) / math.log(1/epsilon)
