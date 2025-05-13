# pathfinding_algorithms.py
from collections import deque
import heapq
import math
import random


# --- CÁC HÀM HEURISTIC ---
def heuristic_manhattan(a, b):
    """Tính khoảng cách Manhattan."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def heuristic_diagonal(a, b):
    """Tính khoảng cách đường chéo (Chebyshev)."""
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return max(dx, dy)


def heuristic_euclidean(a, b):
    """Tính khoảng cách Euclidean."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


# --- HÀM TIỆN ÍCH ---
def get_neighbors(node, is_walkable_func, include_diagonals=True):
    """Lấy các ô hàng xóm hợp lệ của một ô."""
    neighbors = []
    primary_moves = [(0, 1, 1), (0, -1, 1), (1, 0, 1), (-1, 0, 1)]  # dx, dy, cost
    diagonal_moves = [(1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    all_moves = primary_moves
    if include_diagonals:
        all_moves.extend(diagonal_moves)
    for dx, dy, cost in all_moves:
        neighbor_pos = (node[0] + dx, node[1] + dy)
        if is_walkable_func(neighbor_pos):
            neighbors.append((neighbor_pos, cost))
    return neighbors


def reconstruct_path(came_from, current_node):
    """Xây dựng lại đường đi từ dictionary came_from."""
    path = deque()
    temp = current_node
    while temp is not None:
        path.appendleft(temp)
        temp = came_from.get(temp)
    return path


# --- CÁC THUẬT TOÁN TÌM ĐƯỜNG CƠ BẢN ---
def a_star_pathfinding(start_node, end_node, is_walkable_func, heuristic_func=heuristic_diagonal):
    """Thuật toán A* (A-Star)."""
    open_set = []  # Priority queue (min-heap)
    heapq.heappush(open_set, (heuristic_func(start_node, end_node) + 0, start_node))  # (f_cost, node)
    came_from = {start_node: None}  # Stores parent of each node in the path
    g_cost = {start_node: 0}  # Cost from start to current node

    while open_set:
        _, current_node = heapq.heappop(open_set)

        if current_node == end_node:
            return reconstruct_path(came_from, current_node)

        for neighbor, move_cost in get_neighbors(current_node, is_walkable_func):
            tentative_g_cost = g_cost.get(current_node, float('inf')) + move_cost
            if tentative_g_cost < g_cost.get(neighbor, float('inf')):
                came_from[neighbor] = current_node
                g_cost[neighbor] = tentative_g_cost
                f_cost_neighbor = tentative_g_cost + heuristic_func(neighbor, end_node)
                heapq.heappush(open_set, (f_cost_neighbor, neighbor))
    return None  # No path found


def bfs_pathfinding(start_node, end_node, is_walkable_func):
    """Thuật toán Breadth-First Search (BFS)."""
    queue = deque([(start_node, deque([start_node]))])  # (current_node, path_to_current_node)
    visited = {start_node}

    while queue:
        current_node, path = queue.popleft()

        if current_node == end_node:
            return path  # Path includes start_node

        for neighbor_pos, _ in get_neighbors(current_node, is_walkable_func):
            if neighbor_pos not in visited:
                visited.add(neighbor_pos)
                new_path = path.copy()
                new_path.append(neighbor_pos)
                queue.append((neighbor_pos, new_path))
    return None


def dfs_pathfinding(start_node, end_node, is_walkable_func):
    """Thuật toán Depth-First Search (DFS)."""
    stack = [(start_node, deque([start_node]))]  # (current_node, path_to_current_node)
    visited = {start_node}

    while stack:
        current_node, path = stack.pop()

        if current_node == end_node:
            return path  # Path includes start_node

        # Reversed to explore in a more standard DFS order (e.g. up, left, down, right if neighbors are ordered that way)
        for neighbor_pos, _ in reversed(get_neighbors(current_node, is_walkable_func)):
            if neighbor_pos not in visited:
                visited.add(neighbor_pos)
                new_path = path.copy()
                new_path.append(neighbor_pos)
                stack.append((neighbor_pos, new_path))
    return None


def ucs_pathfinding(start_node, end_node, is_walkable_func):
    """Thuật toán Uniform Cost Search (UCS) - Tương tự Dijkstra."""
    open_set = []  # Priority queue (min-heap) for g_cost
    heapq.heappush(open_set, (0, start_node))  # (g_cost, node)
    came_from = {start_node: None}
    g_cost = {start_node: 0}

    while open_set:
        current_g, current_node = heapq.heappop(open_set)

        if current_node == end_node:
            return reconstruct_path(came_from, current_node)

        # Optimization: if we found a shorter path to current_node already, skip
        if current_g > g_cost.get(current_node, float('inf')):
            continue

        for neighbor, move_cost in get_neighbors(current_node, is_walkable_func):
            tentative_g_cost = current_g + move_cost
            if tentative_g_cost < g_cost.get(neighbor, float('inf')):
                came_from[neighbor] = current_node
                g_cost[neighbor] = tentative_g_cost
                heapq.heappush(open_set, (tentative_g_cost, neighbor))
    return None


# --- THUẬT TOÁN CSP: QUAY LUI (BACKTRACKING) ---
def backtracking_pathfinding(start_node, end_node, is_walkable_func, max_depth=None):
    """Thuật toán Quay lui (Backtracking) cho tìm đường, có giới hạn độ sâu."""

    if max_depth is None:
        estimated_distance = heuristic_diagonal(start_node, end_node)
        # Adjust multiplier and additive constant based on typical map sizes and complexity
        # A higher multiplier allows for more detours.
        # A higher additive constant gives more leeway for smaller maps.
        max_depth_calculated = int(estimated_distance * 2.5) + 30
        max_depth = max(30, min(max_depth_calculated, 750))  # Min 30 steps, Max 750 steps
        # print(f"Backtracking: start={start_node}, end={end_node}, estimated_dist={estimated_distance:.2f}, calculated_max_depth={max_depth}")

    def solve(current_node, current_path_deque, visited_on_current_branch_set):
        if len(current_path_deque) > max_depth:
            return None

        if current_node == end_node:
            return current_path_deque

        # Sort neighbors by heuristic to potentially find path faster
        sorted_neighbors = sorted(
            get_neighbors(current_node, is_walkable_func),
            key=lambda item: heuristic_diagonal(item[0], end_node)
        )

        for neighbor_pos, _ in sorted_neighbors:
            if neighbor_pos not in visited_on_current_branch_set:
                new_path_for_recursion = current_path_deque.copy()
                new_path_for_recursion.append(neighbor_pos)
                new_visited_for_recursion = visited_on_current_branch_set.copy()
                new_visited_for_recursion.add(neighbor_pos)
                found_path = solve(neighbor_pos, new_path_for_recursion, new_visited_for_recursion)
                if found_path:
                    return found_path
        return None

    initial_path = deque([start_node])
    initial_visited_on_branch = {start_node}
    if start_node == end_node: return initial_path
    return solve(start_node, initial_path, initial_visited_on_branch)


# --- THUẬT TOÁN CSP: QUAY LUI VỚI KIỂM TRA TIẾN (FORWARD CHECKING BACKTRACKING) ---
def forward_checking_backtracking_pathfinding(start_node, end_node, is_walkable_func, max_depth=None):
    """Thuật toán Quay lui với Kiểm tra Tiến, có giới hạn độ sâu."""

    if max_depth is None:
        estimated_distance = heuristic_diagonal(start_node, end_node)
        max_depth_calculated = int(estimated_distance * 2.5) + 30
        max_depth = max(30, min(max_depth_calculated, 750))
        # print(f"Forward Checking BS: start={start_node}, end={end_node}, estimated_dist={estimated_distance:.2f}, calculated_max_depth={max_depth}")

    def check_forward(node_being_considered, path_if_node_is_chosen_set):
        if node_being_considered == end_node:
            return True
        has_at_least_one_valid_forward_move = False
        for neighbor_of_considered, _ in get_neighbors(node_being_considered, is_walkable_func):
            if neighbor_of_considered not in path_if_node_is_chosen_set:  # If neighbor is a valid next step
                # Check if this neighbor itself has an escape route (not leading back to node_being_considered immediately or into path)
                is_escape_for_neighbor = False
                for escape_candidate, _ in get_neighbors(neighbor_of_considered, is_walkable_func):
                    if escape_candidate != node_being_considered and escape_candidate not in path_if_node_is_chosen_set:
                        is_escape_for_neighbor = True
                        break
                if is_escape_for_neighbor:
                    has_at_least_one_valid_forward_move = True
                    break
        return has_at_least_one_valid_forward_move

    def solve_fc(current_node, current_path_deque, visited_on_current_branch_set):
        if len(current_path_deque) > max_depth:
            return None

        if current_node == end_node:
            return current_path_deque

        sorted_neighbors = sorted(
            get_neighbors(current_node, is_walkable_func),
            key=lambda item: heuristic_diagonal(item[0], end_node)
        )

        for neighbor_pos, _ in sorted_neighbors:
            if neighbor_pos not in visited_on_current_branch_set:
                path_if_neighbor_chosen_deque = current_path_deque.copy()
                path_if_neighbor_chosen_deque.append(neighbor_pos)
                visited_if_neighbor_chosen_set = visited_on_current_branch_set.copy()
                visited_if_neighbor_chosen_set.add(neighbor_pos)

                if check_forward(neighbor_pos, visited_if_neighbor_chosen_set):
                    found_path = solve_fc(neighbor_pos, path_if_neighbor_chosen_deque, visited_if_neighbor_chosen_set)
                    if found_path:
                        return found_path
        return None

    initial_path = deque([start_node])
    initial_visited = {start_node}
    if start_node == end_node: return initial_path
    return solve_fc(start_node, initial_path, initial_visited)


# --- CÁC THUẬT TOÁN TÌM KIẾM CỤC BỘ VÀ HEURISTIC KHÁC ---
def min_conflict_like_step_search(start_node, end_node, is_walkable_func, heuristic_func=heuristic_diagonal):
    """
    Thuật toán "Tìm Bước Ít Xung Đột Nhất" (Step-by-step local search).
    LƯU Ý: Đây KHÔNG phải là thuật toán Min-Conflicts CSP cổ điển.
    Nó là một thuật toán tìm kiếm cục bộ, có thể bị kẹt.
    """
    path = deque([start_node])
    current_node = start_node
    visited_in_search = {start_node}  # Avoid immediate cycles in this local search
    max_steps_local_search = int(heuristic_diagonal(start_node, end_node) * 2.5) + 50  # Limit steps
    max_steps_local_search = max(30, min(max_steps_local_search, 500))
    step_count = 0

    while current_node != end_node and step_count < max_steps_local_search:
        step_count += 1
        candidates = []
        for neighbor_pos, _ in get_neighbors(current_node, is_walkable_func):
            if neighbor_pos not in visited_in_search:  # Consider only unvisited neighbors in this specific search instance
                h_val = heuristic_func(neighbor_pos, end_node)
                # Simple conflict: prefer more open areas
                unwalkable_around = 0
                all_8_dirs = [(dx, dy) for dx in [-1, 0, 1] for dy in [-1, 0, 1] if not (dx == 0 and dy == 0)]
                for dx_s, dy_s in all_8_dirs:
                    surr_node_of_neighbor = (neighbor_pos[0] + dx_s, neighbor_pos[1] + dy_s)
                    if surr_node_of_neighbor == current_node: continue  # Don't count the previous node as unwalkable for this purpose
                    if not is_walkable_func(surr_node_of_neighbor):
                        unwalkable_around += 1

                openness_penalty = (unwalkable_around / 8.0) * heuristic_func(start_node,
                                                                              end_node) * 0.1  # Small penalty
                conflict_score = h_val + openness_penalty
                candidates.append((conflict_score, neighbor_pos))

        if not candidates: return None  # Stuck

        candidates.sort(key=lambda x: x[0])  # Choose the one with the best (lowest) conflict score

        # Small chance to pick a random (but good) candidate to escape flat regions
        if len(candidates) > 1 and random.random() < 0.1:
            top_n = min(len(candidates), 3)
            current_node = random.choice(candidates[:top_n])[1]
        else:
            current_node = candidates[0][1]

        path.append(current_node)
        visited_in_search.add(current_node)  # Add to visited for THIS run of min_conflict_like_step_search

    return path if current_node == end_node else None


def hill_climbing_pathfinding(start_node, end_node, is_walkable_func, heuristic_func=heuristic_diagonal):
    """Thuật toán Hill Climbing (Leo đồi). Trả về một deque chỉ chứa (start_node, next_best_step) hoặc None."""
    if start_node == end_node: return deque([start_node])  # Already at goal

    best_next_step = None
    current_h = heuristic_func(start_node, end_node)

    possible_steps = []
    for neighbor_pos, _ in get_neighbors(start_node, is_walkable_func):
        possible_steps.append({'pos': neighbor_pos, 'h_cost': heuristic_func(neighbor_pos, end_node)})

    if not possible_steps: return None  # No walkable neighbors

    # Sort by heuristic value (ascending for minimization)
    possible_steps.sort(key=lambda x: x['h_cost'])

    # Select the best neighbor if it's not worse than the current state
    if possible_steps[0]['h_cost'] <= current_h:  # Allow moves to equally good states
        best_h_val = possible_steps[0]['h_cost']
        # Collect all steps that are equally good as the best one found
        equally_good_steps = [step['pos'] for step in possible_steps if step['h_cost'] == best_h_val]
        if equally_good_steps:
            best_next_step = random.choice(equally_good_steps)  # Randomly pick among the best to avoid bias

    if best_next_step:
        return deque([start_node, best_next_step])  # Return path of one step
    return None  # Stuck or no improvement


def rtaa_star_pathfinding(start_node, end_node, is_walkable_func, heuristic_func=heuristic_diagonal,
                          max_expansion=None):
    """Thuật toán RTAA* - Phiên bản giới hạn mở rộng, trả về đường đi đến biên giới khám phá."""
    if max_expansion is None:
        estimated_distance = heuristic_diagonal(start_node, end_node)
        max_expansion = int(estimated_distance * 1.5) + 20  # Heuristic for expansion limit
        max_expansion = max(20, min(max_expansion, 200))
        # print(f"RTAA* using max_expansion: {max_expansion}")

    open_list = []  # (f_cost, g_cost, node, path_deque_to_node)
    # Initial h_cost used as f_cost because g_cost is 0
    heapq.heappush(open_list, (heuristic_func(start_node, end_node), 0, start_node, deque([start_node])))

    # visited_this_search stores g_costs to avoid redundant expansions in THIS search iteration
    visited_this_search = {start_node: 0}
    iterations = 0

    # Keep track of the best leaf node found so far in the expansion
    # (f_cost_of_leaf, g_cost_of_leaf, leaf_node, path_to_leaf_node)
    best_leaf_info = (heuristic_func(start_node, end_node), 0, start_node, deque([start_node]))

    while open_list and iterations < max_expansion:
        f_curr, g_curr, node_curr, path_curr = heapq.heappop(open_list)
        iterations += 1

        # Update best_leaf_info if this node is better or closer to goal
        if f_curr < best_leaf_info[0]:  # Prioritize lower f_cost
            best_leaf_info = (f_curr, g_curr, node_curr, path_curr)
        elif f_curr == best_leaf_info[0] and g_curr > best_leaf_info[
            1]:  # If f_costs are same, prefer higher g_cost (more explored)
            best_leaf_info = (f_curr, g_curr, node_curr, path_curr)

        if node_curr == end_node:
            return path_curr  # Found goal within expansion limit

        for neighbor_pos, move_cost in get_neighbors(node_curr, is_walkable_func):
            new_g = g_curr + move_cost
            if new_g < visited_this_search.get(neighbor_pos, float('inf')):
                visited_this_search[neighbor_pos] = new_g
                new_h = heuristic_func(neighbor_pos, end_node)
                new_f = new_g + new_h

                new_path = path_curr.copy()
                new_path.append(neighbor_pos)
                heapq.heappush(open_list, (new_f, new_g, neighbor_pos, new_path))

    # If goal not reached, return path to the most promising leaf node found
    final_path_to_leaf = best_leaf_info[3]
    if len(final_path_to_leaf) > 1 or (len(final_path_to_leaf) == 1 and final_path_to_leaf[0] == end_node):
        return final_path_to_leaf

    return None  # Should not happen if start_node is valid, best_leaf_info always has at least start_node


def beam_search_pathfinding(start_node, end_node, is_walkable_func, heuristic_func=heuristic_diagonal, beam_width=None):
    """Thuật toán Beam Search."""
    if beam_width is None:
        beam_width = 3  # Default beam width
        # print(f"Beam Search using beam_width: {beam_width}")

    # Each element in beam: (h_cost_to_goal, g_cost_from_start, current_node, path_deque_to_node)
    # Sort by h_cost primarily
    beam = [(heuristic_func(start_node, end_node), 0, start_node, deque([start_node]))]

    # Max path length to prevent infinite loops in sparse graphs or with poor heuristics
    max_path_len_beam = int(heuristic_diagonal(start_node, end_node) * 3) + 75
    max_path_len_beam = max(50, min(max_path_len_beam, 1000))

    for _ in range(max_path_len_beam):  # Limit search depth
        if not beam: return None  # No more paths to explore

        candidates_next_beam = []
        # Generate all successors for all states in the current beam
        for h_cost_curr, g_cost_curr, node_curr, path_curr in beam:
            if node_curr == end_node:
                return path_curr  # Goal found

            for neighbor_pos, move_cost in get_neighbors(node_curr, is_walkable_func):
                # Avoid simple loops in the current path being built (unless it's the goal)
                if neighbor_pos in path_curr and neighbor_pos != end_node:
                    continue

                new_g_cost = g_cost_curr + move_cost
                new_h_cost = heuristic_func(neighbor_pos, end_node)
                new_path = path_curr.copy()
                new_path.append(neighbor_pos)
                candidates_next_beam.append((new_h_cost, new_g_cost, neighbor_pos, new_path))

        if not candidates_next_beam: return None  # No valid successors

        # Sort candidates by heuristic (primary key) and then g_cost (secondary, to break ties)
        candidates_next_beam.sort(key=lambda x: (x[0], x[1]))

        # Select the best 'beam_width' candidates for the next iteration
        beam = candidates_next_beam[:beam_width]

    return None  # Max path length reached or no solution found


# --- THUẬT TOÁN CSP: MIN-CONFLICTS (ĐỂ SỬA CHỮA ĐƯỜNG ĐI HIỆN CÓ) ---
def min_conflicts_csp_repair_path(initial_path_deque, is_walkable_func, TILESIZE,
                                  max_steps=None):  # TILESIZE not directly used here but kept for signature
    """
    Thuật toán Min-Conflicts cổ điển, được điều chỉnh để SỬA CHỮA một đường đi hiện có.
    """
    if max_steps is None:
        max_steps = 100 if initial_path_deque is None else len(initial_path_deque) * 2
        max_steps = max(50, min(max_steps, 300))
        # print(f"MinConflicts Repair using max_steps: {max_steps}")

    if not initial_path_deque or len(initial_path_deque) < 2:
        return initial_path_deque

    current_path = list(initial_path_deque)

    def count_conflicts_in_segment(path_list_segment):
        conflicts = 0
        if not path_list_segment: return float('inf')
        for node_idx, node in enumerate(path_list_segment):
            if not is_walkable_func(node):
                conflicts += 10  # Penalty for non-walkable nodes

            if node_idx < len(path_list_segment) - 1:
                next_node = path_list_segment[node_idx + 1]
                dx = abs(node[0] - next_node[0])
                dy = abs(node[1] - next_node[1])
                if not (dx <= 1 and dy <= 1 and (dx != 0 or dy != 0)):  # Not adjacent
                    conflicts += 5  # Penalty for breaks in path
        return conflicts

    for _ in range(max_steps):
        num_current_conflicts = count_conflicts_in_segment(current_path)
        if num_current_conflicts == 0:
            return deque(current_path)

        conflicted_indices = []
        # Identify nodes causing conflicts (either themselves non-walkable or part of a broken link)
        for k in range(len(current_path)):
            node_is_unwalkable = not is_walkable_func(current_path[k])
            link_is_broken_after_k = False
            if k < len(current_path) - 1:
                node1, node2 = current_path[k], current_path[k + 1]
                dx, dy = abs(node1[0] - node2[0]), abs(node1[1] - node2[1])
                if not (dx <= 1 and dy <= 1 and (dx != 0 or dy != 0)):
                    link_is_broken_after_k = True

            if node_is_unwalkable:
                if k not in conflicted_indices: conflicted_indices.append(k)
            if link_is_broken_after_k:
                if k not in conflicted_indices: conflicted_indices.append(k)
                if k + 1 < len(current_path) and (k + 1) not in conflicted_indices:
                    conflicted_indices.append(k + 1)

        if not conflicted_indices:  # Should not happen if num_current_conflicts > 0
            if len(current_path) > 2:  # Pick random internal node if no specific conflict found
                var_index_to_fix = random.randrange(1, len(current_path) - 1)
            else:
                continue  # Path too short to fix meaningfully
        else:
            var_index_to_fix = random.choice(conflicted_indices)

        node_to_fix = current_path[var_index_to_fix]
        best_alternative_node = node_to_fix
        min_conflicts_after_change = num_current_conflicts

        # Consider neighbors of the node_to_fix as alternatives
        # Also consider neighbors of its neighbors in the path (prev_node, next_node)
        # to try to bridge gaps or move away from obstacles.
        potential_alternatives_set = set()

        # 1. Neighbors of the node itself
        for neighbor_pos, _ in get_neighbors(node_to_fix, is_walkable_func):  # Get only walkable neighbors
            if neighbor_pos not in current_path or neighbor_pos == node_to_fix:  # Avoid re-adding existing path nodes
                potential_alternatives_set.add(neighbor_pos)

        # 2. Neighbors of the previous node in path (if exists)
        if var_index_to_fix > 0:
            prev_node_in_path = current_path[var_index_to_fix - 1]
            for neighbor_pos, _ in get_neighbors(prev_node_in_path, is_walkable_func):
                if neighbor_pos not in current_path or neighbor_pos == node_to_fix:
                    potential_alternatives_set.add(neighbor_pos)

        # 3. Neighbors of the next node in path (if exists)
        if var_index_to_fix < len(current_path) - 1:
            next_node_in_path = current_path[var_index_to_fix + 1]
            for neighbor_pos, _ in get_neighbors(next_node_in_path, is_walkable_func):
                if neighbor_pos not in current_path or neighbor_pos == node_to_fix:
                    potential_alternatives_set.add(neighbor_pos)

        if not potential_alternatives_set and not is_walkable_func(
                node_to_fix):  # If stuck on unwalkable, try any walkable neighbor
            for neighbor_pos, _ in get_neighbors(node_to_fix, lambda n: True):  # Check all physical neighbors
                if is_walkable_func(neighbor_pos) and (neighbor_pos not in current_path or neighbor_pos == node_to_fix):
                    potential_alternatives_set.add(neighbor_pos)

        for alt_node in potential_alternatives_set:
            original_node_at_index = current_path[var_index_to_fix]
            current_path[var_index_to_fix] = alt_node  # Try change
            conflicts_with_alt = count_conflicts_in_segment(current_path)
            if conflicts_with_alt < min_conflicts_after_change:
                min_conflicts_after_change = conflicts_with_alt
                best_alternative_node = alt_node
            current_path[var_index_to_fix] = original_node_at_index  # Revert

        current_path[var_index_to_fix] = best_alternative_node  # Commit best change found for this step

    return deque(current_path)


# --- THUẬT TOÁN DI TRUYỀN (PLACEHOLDER) ---
def genetic_algorithm_pathfinding(start_node, end_node, is_walkable_func,
                                  TILESIZE=64):  # Added TILESIZE for signature consistency
    """Thuật toán Di truyền (Genetic Algorithm) - Hiện tại dùng A* làm giải pháp tạm thời."""
    # print("Genetic Algorithm is currently using A* as a fallback.")
    return a_star_pathfinding(start_node, end_node, is_walkable_func, heuristic_diagonal)


# --- DANH SÁCH VÀ DICTIONARY ĐỂ ĐĂNG KÝ CÁC THUẬT TOÁN ---
ALGORITHM_NAMES = [
    'A*', 'BFS', 'DFS', 'UCS',
    'Backtracking', 'Forward Checking BS',
    'MinConflict-like Step',
    'Hill Climbing', 'RTAA*', 'Beam Search',
    'Genetic Algo (A*)',
    'MinConflicts Repair (BFS)'
]
PATHFINDING_ALGORITHMS = {
    'A*': a_star_pathfinding,
    'BFS': bfs_pathfinding,
    'DFS': dfs_pathfinding,
    'UCS': ucs_pathfinding,
    'Backtracking': backtracking_pathfinding,
    'Forward Checking BS': forward_checking_backtracking_pathfinding,
    'MinConflict-like Step': min_conflict_like_step_search,
    'Hill Climbing': hill_climbing_pathfinding,
    'RTAA*': rtaa_star_pathfinding,
    'Beam Search': beam_search_pathfinding,
    'Genetic Algo (A*)': genetic_algorithm_pathfinding,
    'MinConflicts Repair (BFS)': lambda start, end, is_walkable: min_conflicts_csp_repair_path(
        initial_path_deque=bfs_pathfinding(start, end, is_walkable),
        is_walkable_func=is_walkable,
        TILESIZE=64,  # Pass a TILESIZE, though not strictly used by current repair logic internally
        # max_steps can be configured here if needed, or use default within the function
    )
}