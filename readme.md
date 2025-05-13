# Game Đánh Quái (Monster-Fighting Game)

## Mục lục (Table of Contents)

* [Giới thiệu (Introduction)](#giới-thiệu-introduction)
* [Gameplay & Tính năng (Gameplay & Features)](#gameplay--tính-năng-gameplay--features)
* [Cách chơi (How to Play)](#cách-chơi-how-to-play)
* [GIF Gameplay](#gif-gameplay)
* [Cài đặt & Chạy game (Installation & Running the Game)](#cài-đặt--chạy-game-installation--running-the-game)
* [Công nghệ sử dụng và Thuật toán (Technologies Used and Algorithms)](#công-nghệ-sử-dụng-và-thuật-toán-technologies-used-and-algorithms)

---

## Giới thiệu (Introduction)

Đây là một trò chơi phiêu lưu hành động được phát triển bằng Pygame, nơi người chơi sẽ chiến đấu với quái vật, sử dụng vũ khí và phép thuật, đồng thời có thể tương tác với các NPC. Trò chơi có một menu chính để bắt đầu và giao diện người dùng để hiển thị thông tin của người chơi như máu, năng lượng và kinh nghiệm.

## Gameplay & Tính năng (Gameplay & Features)

* **Điều khiển nhân vật (Player Control)**: Người chơi có thể di chuyển nhân vật lên, xuống, trái, phải.
* **Hệ thống chiến đấu (Combat System)**:
    * **Tấn công**: Người chơi có thể tấn công bằng vũ khí. Có nhiều loại vũ khí với các chỉ số cooldown và sát thương khác nhau (ví dụ: kiếm, giáo, rìu).
    * **Phép thuật (Magic)**: Người chơi có thể sử dụng các loại phép thuật khác nhau như "flame" (lửa) và "heal" (hồi máu), tiêu tốn năng lượng.
    * **Kẻ thù (Enemies)**: Có nhiều loại quái vật với các chỉ số máu, kinh nghiệm, sát thương, và hành vi khác nhau (ví dụ: squid, raccoon, spirit, bamboo, và các loại Minotaur, Samurai). Kẻ thù sử dụng các thuật toán tìm đường để di chuyển và tấn công người chơi.
    * **NPCs**: Có các nhân vật không phải người chơi (NPC) trong game, ví dụ như "2BlueWizard" và "Demon". NPC có thể có các hành vi riêng, thuật toán tìm đường riêng và thậm chí hỗ trợ người chơi.
* **Hệ thống nâng cấp (Upgrade System)**: Người chơi có thể nâng cấp các chỉ số như máu, năng lượng, sức tấn công, phép thuật và tốc độ bằng cách sử dụng điểm kinh nghiệm.
* **Giao diện người dùng (UI)**:
    * Hiển thị thanh máu, năng lượng, và điểm kinh nghiệm của người chơi.
    * Hiển thị vũ khí và phép thuật đang được chọn.
    * Cho phép chuyển đổi thuật toán tìm đường cho NPC.
    * Cho phép bật/tắt chế độ "Partial Observability" và "Enemy Aggression Mode".
    * Hiển thị thông báo khi tất cả quái vật trong màn chơi đã bị tiêu diệt.
* **Bản đồ và Môi trường (Map & Environment)**:
    * Bản đồ được tạo từ các tệp CSV.
    * Có các đối tượng tương tác như cỏ có thể bị phá hủy.
    * Sử dụng hệ thống camera YSortCameraGroup để vẽ các đối tượng theo thứ tự chiều sâu.
* **Hiệu ứng hạt (Particle Effects)**: Trò chơi sử dụng hiệu ứng hạt cho các đòn tấn công, phép thuật, và khi quái vật bị tiêu diệt.

## Cách chơi (How to Play)

### Điều khiển cơ bản:
* **Di chuyển Nhân vật:**
    * `Mũi tên Lên`: Đi lên
    * `Mũi tên Xuống`: Đi xuống
    * `Mũi tên Trái`: Sang trái
    * `Mũi tên Phải`: Sang phải
* **Chiến đấu:**
    * `Phím Space`: Tấn công bằng vũ khí.
    * `Phím Left Control (LCtrl)`: Sử dụng phép thuật.
    * `Phím Q`: Đổi vũ khí.
    * `Phím E`: Đổi phép thuật.
* **Hệ thống & Giao diện:**
    * `Phím M`: Mở/Đóng bảng nâng cấp nhân vật.
    * `Phím P`: Bật/Tắt chế độ Quan sát Cục bộ (Partial Observability) cho NPC.
    * `Phím G`: Bật/Tắt chế độ Hung hãn (Aggression Mode) của kẻ thù.
    * `Phím C`: Chuyển đổi camera theo dõi (giữa người chơi và NPC).
    * `Chuột Trái`: Nhấn nút "CHƠI NGAY" ở menu chính để vào game; tương tác với các yếu tố UI trong game (ví dụ: chọn thuật toán cho NPC).
    * `Cuộn chuột (lên/xuống)`: Cuộn trong danh sách chọn thuật toán NPC khi menu đó đang mở.

### Mục tiêu trò chơi:
* **Tiêu diệt kẻ thù:** Đánh bại tất cả các loại quái vật xuất hiện trên bản đồ.
* **Nâng cấp nhân vật:** Sử dụng điểm kinh nghiệm (EXP) kiếm được từ việc tiêu diệt quái vật để tăng các chỉ số cơ bản như máu, năng lượng, sức tấn công, sức mạnh phép thuật và tốc độ di chuyển.
* **Sống sót:** Giữ cho nhân vật của bạn không bị hết máu trước sự tấn công của kẻ thù.
* Khi tất cả quái vật trong màn chơi bị tiêu diệt, một thông báo chiến thắng sẽ xuất hiện.

## GIF Gameplay
![Simple Hill Climbing](https://raw.githubusercontent.com/vothnha26/Monster-Fighting/main/graphics/hill_clibing_lor.gif)

Simple Hill Climbing

![Partially Observable Environment](https://raw.githubusercontent.com/vothnha26/Monster-Fighting/main/graphics/PO.gif)

Partially Observable Environment

![A*](https://raw.githubusercontent.com/vothnha26/Monster-Fighting/main/graphics/A_star.gif)

A*

![Forward Checking](https://raw.githubusercontent.com/vothnha26/Monster-Fighting/main/graphics/forward_checking.gif)

Forward Checking

![UCS](https://raw.githubusercontent.com/vothnha26/Monster-Fighting/main/graphics/ucs.gif)

UCS

## Cài đặt & Chạy game (Installation & Running the Game)

1.  **Yêu cầu (Prerequisites)**:
    * Cài đặt Python (Phiên bản cụ thể không được đề cập, nhưng các game Pygame thường tương thích tốt với Python 3.x).
    * Cài đặt thư viện Pygame:
        ```bash
        pip install pygame
        ```
2.  **Tải mã nguồn (Download Source Code)**:
    * Tải hoặc clone toàn bộ thư mục dự án.
3.  **Cấu trúc thư mục dự kiến (Expected Directory Structure)**:
    Dựa trên các đường dẫn trong mã nguồn, cấu trúc thư mục có thể trông giống như sau:
    ```
    Game_Project/
    ├── code/
    │   ├── main.py
    │   ├── player.py
    │   ├── enemy.py
    │   ├── npc.py
    │   ├── level.py
    │   ├── settings.py
    │   ├── tile.py
    │   ├── weapon.py
    │   ├── magic.py
    │   ├── particles.py
    │   ├── entity.py
    │   ├── support.py
    │   ├── ui.py
    │   ├── upgrade.py
    │   └── pathfinding_algorithms.py
    ├── graphics/
    │   ├── player/
    │   ├── monsters/
    │   ├── npcs/
    │   ├── weapons/
    │   ├── particles/
    │   ├── objects/
    │   ├── tilemap/
    │   └── font/
    ├── audio/
    │   ├── attack/
    │   └── main.ogg (và các file âm thanh khác)
    └── map/
        └── map_FloorBlocks.csv (và các file map khác)
    ```
    *Lưu ý*: Đảm bảo rằng các đường dẫn đến tài nguyên (hình ảnh, âm thanh, font, map) trong file `settings.py` và các file mã nguồn khác là chính xác so với cấu trúc thư mục của bạn. Các đường dẫn hiện tại trong code sử dụng `../graphics/` hoặc `../audio/`, cho thấy thư mục `code` nằm song song với `graphics` và `audio`.

4.  **Chạy game (Run the Game)**:
    * Mở terminal hoặc command prompt.
    * Điều hướng đến thư mục `code` của dự án.
    * Chạy file `main.py`:
        ```bash
        python main.py
        ```

## Công nghệ sử dụng và Thuật toán (Technologies Used and Algorithms)

* **Công nghệ (Technology)**:
    * **Python**: Ngôn ngữ lập trình chính.
    * **Pygame**: Thư viện để phát triển game.
* **Thuật toán (Algorithms)**:
    * **Tìm đường (Pathfinding)**:
        * **A\***: Được sử dụng làm thuật toán tìm đường chính cho NPC và có thể là cả Enemy.
        * **BFS (Breadth-First Search)**: Có sẵn và được sử dụng bởi một số Enemy.
        * **Hill Climbing**: Được sử dụng bởi một số Enemy.
        * **RTAA\* (Real-Time Adaptive A\*)**: Có sẵn và được sử dụng bởi một số Enemy.
        * Các thuật toán khác được định nghĩa trong `pathfinding_algorithms.txt` bao gồm: DFS, UCS, Backtracking, Forward Checking Backtracking, MinConflict-like Step Search, Beam Search, và Genetic Algorithm (hiện tại dùng A\* làm fallback).
    * **Quản lý trạng thái (State Management)**: Các thực thể (Player, Enemy, NPC) có các trạng thái khác nhau (ví dụ: idle, move, attack) ảnh hưởng đến hành vi và hoạt ảnh.
    * **Xử lý va chạm (Collision Detection)**: Pygame được sử dụng để phát hiện va chạm giữa các thực thể và vật cản.
    * **Steering Behaviors (Tách bầy - Separation)**: Kẻ thù và NPC có thể có hành vi tách bầy để tránh chồng chéo.
    * **Partial Observability (Quan sát cục bộ)**: NPC có thể hoạt động dưới cơ chế quan sát cục bộ, nơi chúng chỉ phản ứng với những gì "nhìn thấy" trong một bán kính và góc nhìn nhất định, và ghi nhớ vị trí đã biết cuối cùng (LKP) của mục tiêu.

---
