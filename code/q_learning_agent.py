# q_learning_agent.py
import random
import json
from collections import defaultdict  # Sử dụng defaultdict để dễ dàng thêm trạng thái mới vào Q-Table


class QLearningAgent:
    def __init__(self, num_actions, learning_rate=0.1, discount_factor=0.9,
                 epsilon=0.9, epsilon_decay=0.999, epsilon_min=0.05):
        self.num_actions = num_actions
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min

        self.q_table = defaultdict(lambda: [0.0] * self.num_actions)

    def choose_action(self, state_tuple):
        """
        Chọn một hành động từ trạng thái hiện tại dựa trên chiến lược epsilon-greedy.

        Args:
            state_tuple (tuple): Trạng thái hiện tại của agent, được biểu diễn dưới dạng một tuple.

        Returns:
            int: Index của hành động được chọn (ví dụ: 0 cho 'lên', 1 cho 'xuống', ...).
        """
        # Quyết định thăm dò hay khai thác
        if random.uniform(0, 1) < self.epsilon:
            # Thăm dò (Exploration): Chọn một hành động ngẫu nhiên
            return random.randrange(self.num_actions)
        else:
            # Khai thác (Exploitation): Chọn hành động tốt nhất dựa trên Q-values hiện tại
            q_values_for_state = self.q_table[state_tuple]

            # Tìm giá trị Q lớn nhất trong số các hành động có thể từ trạng thái này
            max_q_value = max(q_values_for_state)

            # Có thể có nhiều hành động cùng có giá trị Q lớn nhất.
            # Chọn ngẫu nhiên một trong số các hành động tốt nhất đó để tránh thiên vị.
            best_actions_indices = [i for i, q_val in enumerate(q_values_for_state) if q_val == max_q_value]
            return random.choice(best_actions_indices)

    def update(self, state_tuple, action_index, reward, next_state_tuple):
        """
        Cập nhật Q-value cho cặp (trạng thái, hành động) dựa trên kinh nghiệm (phần thưởng và trạng thái tiếp theo).
        Công thức cập nhật Q-Learning:
        Q(s, a) <- Q(s, a) + alpha * [R + gamma * max_a'(Q(s', a')) - Q(s, a)]

        Args:
            state_tuple (tuple): Trạng thái (s) trước khi thực hiện hành động.
            action_index (int): Index của hành động (a) đã thực hiện.
            reward (float): Phần thưởng (R) nhận được sau khi thực hiện hành động.
            next_state_tuple (tuple): Trạng thái mới (s') sau khi thực hiện hành động.
                                      Có thể là None nếu đây là trạng thái kết thúc (terminal state).
        """
        # Lấy Q-value hiện tại của cặp (trạng thái, hành động)
        current_q_value = self.q_table[state_tuple][action_index]

        # Tìm giá trị Q lớn nhất cho trạng thái tiếp theo (max_a' Q(s', a'))
        # Nếu next_state_tuple là None (trạng thái kết thúc), thì không có phần thưởng tương lai từ đó.
        next_max_q_value = 0.0
        if next_state_tuple is not None:
            # Nếu next_state_tuple chưa có trong q_table, defaultdict sẽ tạo ra nó với giá trị [0.0,...]
            # do đó max() sẽ trả về 0.0, điều này là hợp lý.
            next_max_q_value = max(self.q_table[next_state_tuple])

            # Áp dụng công thức cập nhật Q-Learning
        # new_q_value = current_q_value + self.lr * (reward + self.gamma * next_max_q_value - current_q_value)
        td_target = reward + self.gamma * next_max_q_value  # Giá trị mục tiêu (Temporal Difference Target)
        td_error = td_target - current_q_value  # Sai số dự đoán (Temporal Difference Error)
        new_q_value = current_q_value + self.lr * td_error  # Cập nhật Q-value

        self.q_table[state_tuple][action_index] = new_q_value

    def decay_epsilon(self):
        """
        Giảm giá trị epsilon sau mỗi episode để giảm dần việc thăm dò và tăng cường khai thác.
        """
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            self.epsilon = max(self.epsilon_min, self.epsilon)  # Đảm bảo epsilon không nhỏ hơn giá trị tối thiểu

    def save_q_table(self, filepath="q_table.json"):
        """Lưu Q-Table vào một file JSON."""
        # defaultdict không thể serialize trực tiếp thành JSON, cần chuyển nó thành dict thường.
        # Đồng thời, key của dict (là tuple trạng thái) cũng cần được chuyển thành string để lưu vào JSON.
        saveable_q_table = {str(k): v for k, v in self.q_table.items()}
        try:
            with open(filepath, 'w') as f:
                json.dump(saveable_q_table, f, indent=4)  # indent=4 để file JSON dễ đọc hơn
            # print(f"Q-Table đã được lưu vào {filepath}")
        except Exception as e:
            print(f"Lỗi khi lưu Q-Table vào file '{filepath}': {e}")

    def load_q_table(self, filepath="q_table.json"):
        """Tải Q-Table từ một file JSON."""
        try:
            with open(filepath, 'r') as f:
                loaded_q_table_str_keys = json.load(f)

            self.q_table.clear()  # Xóa Q-Table hiện tại trước khi tải
            for key_str, q_values_list in loaded_q_table_str_keys.items():
                # Chuyển key từ string (đã lưu trong JSON, ví dụ: "(x, y)") trở lại tuple (x, y)
                try:
                    # Loại bỏ dấu ngoặc đơn và khoảng trắng, sau đó split theo dấu phẩy và chuyển thành int
                    # Ví dụ: "(1, -2)" -> "1, -2" -> ["1", " -2"] -> [1, -2] -> (1, -2)
                    state_tuple = tuple(map(int, key_str.strip('()').split(',')))
                    self.q_table[state_tuple] = [float(q_val) for q_val in q_values_list]  # Đảm bảo Q-values là float
                except ValueError as ve:
                    print(f"Lỗi khi chuyển đổi key trạng thái từ file: '{key_str}'. Lỗi: {ve}. Bỏ qua trạng thái này.")
            # print(f"Q-Table đã được tải từ {filepath}")
        except FileNotFoundError:
            # print(f"Không tìm thấy file Q-Table: {filepath}. Sẽ sử dụng Q-Table mới (khởi tạo).")
            pass  # Không làm gì cả, q_table sẽ là defaultdict rỗng
        except json.JSONDecodeError as jde:
            print(f"Lỗi giải mã JSON khi tải Q-Table từ '{filepath}': {jde}. Sử dụng Q-Table mới.")
        except Exception as e:
            print(f"Lỗi không xác định khi tải Q-Table từ '{filepath}': {e}. Sử dụng Q-Table mới.")

