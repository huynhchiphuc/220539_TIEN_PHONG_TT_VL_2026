import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
import random
import numpy as np

class Polygon:
    """Lớp đại diện cho một đa giác (panel)"""
    def __init__(self, vertices):
        self.vertices = np.array(vertices)  # [(x1,y1), (x2,y2), ...]
    
    def get_area(self):
        """Tính diện tích đa giác bằng công thức Shoelace"""
        x = self.vertices[:, 0]
        y = self.vertices[:, 1]
        return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
    
    def get_bounds(self):
        """Lấy hình chữ nhật bao quanh"""
        x_min, y_min = self.vertices.min(axis=0)
        x_max, y_max = self.vertices.max(axis=0)
        return x_min, y_min, x_max - x_min, y_max - y_min
    
    def split_diagonal(self):
        """Cắt đa giác bằng đường chéo ngẫu nhiên"""
        # Lấy 2 cạnh ngẫu nhiên (không liền kề)
        n = len(self.vertices)
        if n < 4:
            return None, None
        
        # Chọn 2 cạnh
        edge1 = random.randint(0, n - 1)
        edge2 = random.randint(0, n - 1)
        
        # Đảm bảo 2 cạnh không liền kề
        while abs(edge1 - edge2) < 2 or abs(edge1 - edge2) > n - 2:
            edge2 = random.randint(0, n - 1)
        
        # Lấy điểm trên mỗi cạnh
        p1 = self.vertices[edge1]
        p2 = self.vertices[(edge1 + 1) % n]
        t1 = random.uniform(0.2, 0.8)
        cut_point1 = p1 + t1 * (p2 - p1)
        
        p3 = self.vertices[edge2]
        p4 = self.vertices[(edge2 + 1) % n]
        t2 = random.uniform(0.2, 0.8)
        cut_point2 = p3 + t2 * (p4 - p3)
        
        # Tạo 2 đa giác mới
        if edge1 < edge2:
            poly1_vertices = np.vstack([
                self.vertices[edge1:edge2+1],
                [cut_point2],
                [cut_point1]
            ])
            poly2_vertices = np.vstack([
                [cut_point1],
                [cut_point2],
                self.vertices[edge2+1:],
                self.vertices[:edge1+1]
            ])
        else:
            poly1_vertices = np.vstack([
                self.vertices[edge2:edge1+1],
                [cut_point1],
                [cut_point2]
            ])
            poly2_vertices = np.vstack([
                [cut_point2],
                [cut_point1],
                self.vertices[edge1+1:],
                self.vertices[:edge2+1]
            ])
        
        return Polygon(poly1_vertices), Polygon(poly2_vertices)
    
    def draw(self, ax, gap=1.5):
        """Vẽ đa giác với khoảng cách gap"""
        # Thu nhỏ đa giác vào trong một chút
        center = self.vertices.mean(axis=0)
        shrunk_vertices = []
        for v in self.vertices:
            direction = v - center
            dist = np.linalg.norm(direction)
            if dist > 0:
                shrunk = center + direction * (1 - gap / dist)
                shrunk_vertices.append(shrunk)
            else:
                shrunk_vertices.append(v)
        
        polygon = patches.Polygon(shrunk_vertices, linewidth=2.5, 
                                 edgecolor='black', facecolor='white')
        ax.add_patch(polygon)


def create_comic_layout(num_panels=4, width=100, height=140, gap=1.5):
    """
    Tạo bố cục truyện tranh bằng thuật toán Recursive X-Y Cut
    
    Parameters:
    - num_panels: Số lượng ô muốn tạo
    - width, height: Kích thước canvas (đơn vị tùy ý)
    - gap: Khoảng cách giữa các ô
    """
    fig, ax = plt.subplots(1, figsize=(8.5, 11))  # Khổ giấy 8.5 x 11 inches
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    
    # Bắt đầu với 1 ô to (toàn bộ trang)
    panels = [[0, 0, width, height]]  # [x, y, width, height]
    
    # Cắt đệ quy đơn giản (chỉ cắt vuông góc)
    while len(panels) < num_panels:
        # Chọn 1 ô ngẫu nhiên để cắt (ưu tiên ô lớn)
        panels.sort(key=lambda p: p[2] * p[3], reverse=True)
        idx = 0  # Luôn cắt ô lớn nhất
        
        x, y, w, h = panels.pop(idx)
        
        # Quyết định cắt dọc hay ngang
        if w > h:  # Nếu ô đang bè ngang -> Cắt dọc
            split = random.uniform(0.35, 0.65) * w
            panels.append([x, y, split, h])
            panels.append([x + split, y, w - split, h])
        else:  # Nếu ô đang dài dọc -> Cắt ngang
            split = random.uniform(0.35, 0.65) * h
            panels.append([x, y, w, split])
            panels.append([x, y + split, w, h - split])

    # Vẽ các ô với đường viền đen
    for p in panels:
        rect = patches.Rectangle(
            (p[0] + gap, p[1] + gap), 
            p[2] - 2*gap, 
            p[3] - 2*gap, 
            linewidth=2.5, 
            edgecolor='black', 
            facecolor='white'
        )
        ax.add_patch(rect)
    
    plt.axis('off')
    plt.tight_layout()
    return fig, panels


def create_comic_layout_with_diagonals(num_panels=5, width=100, height=140, gap=1.5, diagonal_probability=0.4):
    """
    Tạo bố cục truyện tranh với cả đường cắt chéo (PHƯƠNG ÁN 2)
    
    Parameters:
    - num_panels: Số lượng ô muốn tạo
    - width, height: Kích thước canvas
    - gap: Khoảng cách giữa các ô
    - diagonal_probability: Xác suất cắt chéo (0-1)
    """
    fig, ax = plt.subplots(1, figsize=(8.5, 11))
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    
    # Bắt đầu với 1 đa giác hình chữ nhật
    initial_polygon = Polygon([
        [0, 0], [width, 0], [width, height], [0, height]
    ])
    polygons = [initial_polygon]
    
    # Cắt đệ quy với cả đường chéo
    while len(polygons) < num_panels:
        # Chọn đa giác lớn nhất để cắt
        polygons.sort(key=lambda p: p.get_area(), reverse=True)
        poly = polygons.pop(0)
        
        # Quyết định cắt chéo hay vuông góc
        use_diagonal = random.random() < diagonal_probability
        
        if use_diagonal and len(poly.vertices) >= 4:
            # Cắt chéo
            poly1, poly2 = poly.split_diagonal()
            if poly1 and poly2:
                polygons.extend([poly1, poly2])
            else:
                # Nếu cắt chéo thất bại, cắt vuông góc
                x, y, w, h = poly.get_bounds()
                if w > h:
                    split = random.uniform(0.35, 0.65) * w
                    poly1 = Polygon([[x, y], [x+split, y], [x+split, y+h], [x, y+h]])
                    poly2 = Polygon([[x+split, y], [x+w, y], [x+w, y+h], [x+split, y+h]])
                else:
                    split = random.uniform(0.35, 0.65) * h
                    poly1 = Polygon([[x, y], [x+w, y], [x+w, y+split], [x, y+split]])
                    poly2 = Polygon([[x, y+split], [x+w, y+split], [x+w, y+h], [x, y+h]])
                polygons.extend([poly1, poly2])
        else:
            # Cắt vuông góc (như phương án 1)
            x, y, w, h = poly.get_bounds()
            if w > h:
                split = random.uniform(0.35, 0.65) * w
                poly1 = Polygon([[x, y], [x+split, y], [x+split, y+h], [x, y+h]])
                poly2 = Polygon([[x+split, y], [x+w, y], [x+w, y+h], [x+split, y+h]])
            else:
                split = random.uniform(0.35, 0.65) * h
                poly1 = Polygon([[x, y], [x+w, y], [x+w, y+split], [x, y+split]])
                poly2 = Polygon([[x, y+split], [x+w, y+split], [x+w, y+h], [x, y+h]])
            polygons.extend([poly1, poly2])
    
    # Vẽ tất cả các đa giác
    for poly in polygons:
        poly.draw(ax, gap)
    
    plt.axis('off')
    plt.tight_layout()
    return fig, polygons


def create_multiple_layouts(num_layouts=6, panels_per_layout=5):
    """
    Tạo nhiều bố cục khác nhau để demo (Phương án 1: Chỉ vuông góc)
    """
    fig, axes = plt.subplots(2, 3, figsize=(15, 18))
    axes = axes.flatten()
    
    for idx, ax in enumerate(axes):
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 140)
        ax.set_aspect('equal')
        
        # Tạo panels cho mỗi layout
        panels = [[0, 0, 100, 140]]
        num_panels = random.randint(4, 7)
        
        while len(panels) < num_panels:
            panels.sort(key=lambda p: p[2] * p[3], reverse=True)
            x, y, w, h = panels.pop(0)
            
            if w > h:
                split = random.uniform(0.3, 0.7) * w
                panels.append([x, y, split, h])
                panels.append([x + split, y, w - split, h])
            else:
                split = random.uniform(0.3, 0.7) * h
                panels.append([x, y, w, split])
                panels.append([x, y + split, w, h - split])
        
        # Vẽ panels
        gap = 1.5
        for p in panels:
            rect = patches.Rectangle(
                (p[0] + gap, p[1] + gap), 
                p[2] - 2*gap, 
                p[3] - 2*gap, 
                linewidth=2, 
                edgecolor='black', 
                facecolor='white'
            )
            ax.add_patch(rect)
        
        ax.set_title(f'Layout {idx+1} - Vuông góc ({len(panels)} panels)', fontsize=9, fontweight='bold')
        ax.axis('off')
    
    plt.tight_layout()
    return fig


def create_multiple_layouts_with_diagonals(num_layouts=6):
    """
    Tạo nhiều bố cục với đường chéo (Phương án 2: Kết hợp)
    """
    fig, axes = plt.subplots(2, 3, figsize=(15, 18))
    axes = axes.flatten()
    
    for idx, ax in enumerate(axes):
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 140)
        ax.set_aspect('equal')
        
        # Tạo polygons với xác suất cắt chéo khác nhau
        diagonal_prob = random.uniform(0.3, 0.6)
        num_panels = random.randint(4, 7)
        
        initial_polygon = Polygon([[0, 0], [100, 0], [100, 140], [0, 140]])
        polygons = [initial_polygon]
        
        while len(polygons) < num_panels:
            polygons.sort(key=lambda p: p.get_area(), reverse=True)
            poly = polygons.pop(0)
            
            use_diagonal = random.random() < diagonal_prob
            
            if use_diagonal and len(poly.vertices) >= 4:
                poly1, poly2 = poly.split_diagonal()
                if poly1 and poly2:
                    polygons.extend([poly1, poly2])
                else:
                    x, y, w, h = poly.get_bounds()
                    if w > h:
                        split = random.uniform(0.35, 0.65) * w
                        poly1 = Polygon([[x, y], [x+split, y], [x+split, y+h], [x, y+h]])
                        poly2 = Polygon([[x+split, y], [x+w, y], [x+w, y+h], [x+split, y+h]])
                    else:
                        split = random.uniform(0.35, 0.65) * h
                        poly1 = Polygon([[x, y], [x+w, y], [x+w, y+split], [x, y+split]])
                        poly2 = Polygon([[x, y+split], [x+w, y+split], [x+w, y+h], [x, y+h]])
                    polygons.extend([poly1, poly2])
            else:
                x, y, w, h = poly.get_bounds()
                if w > h:
                    split = random.uniform(0.35, 0.65) * w
                    poly1 = Polygon([[x, y], [x+split, y], [x+split, y+h], [x, y+h]])
                    poly2 = Polygon([[x+split, y], [x+w, y], [x+w, y+h], [x+split, y+h]])
                else:
                    split = random.uniform(0.35, 0.65) * h
                    poly1 = Polygon([[x, y], [x+w, y], [x+w, y+split], [x, y+split]])
                    poly2 = Polygon([[x, y+split], [x+w, y+split], [x+w, y+h], [x, y+h]])
                polygons.extend([poly1, poly2])
        
        # Vẽ polygons
        gap = 1.5
        for poly in polygons:
            poly.draw(ax, gap)
        
        ax.set_title(f'Layout {idx+1} - Kết hợp chéo ({len(polygons)} panels)', fontsize=9, fontweight='bold')
        ax.axis('off')
    
    plt.tight_layout()
    return fig


if __name__ == "__main__":
    print("=" * 70)
    print("🎨 COMIC LAYOUT GENERATOR - KẾT HỢP 2 PHƯƠNG ÁN")
    print("=" * 70)
    
    # Demo 1: Phương án 1 - Chỉ cắt vuông góc
    print("\n[PHƯƠNG ÁN 1] Recursive X-Y Cut (Chỉ cắt vuông góc 90°)")
    print("-" * 70)
    fig1, panels = create_comic_layout(num_panels=5)
    plt.savefig('comic_layout_rectangular.png', dpi=150, bbox_inches='tight')
    print(f"✓ Đã tạo {len(panels)} ô vuông góc")
    print(f"  📁 Lưu tại: comic_layout_rectangular.png")
    
    # Demo 2: Phương án 2 - Có đường chéo
    print("\n[PHƯƠNG ÁN 2] Polygon Splitting (Có đường cắt chéo)")
    print("-" * 70)
    fig2, polygons = create_comic_layout_with_diagonals(num_panels=6, diagonal_probability=0.5)
    plt.savefig('comic_layout_diagonal.png', dpi=150, bbox_inches='tight')
    print(f"✓ Đã tạo {len(polygons)} ô với đường chéo")
    print(f"  📁 Lưu tại: comic_layout_diagonal.png")
    
    # Demo 3: So sánh 6 layouts vuông góc
    print("\n[SO SÁNH] 6 Layouts chỉ vuông góc")
    print("-" * 70)
    fig3 = create_multiple_layouts()
    plt.savefig('comic_layouts_rectangular_6x.png', dpi=150, bbox_inches='tight')
    print("✓ Đã tạo 6 layouts vuông góc")
    print(f"  📁 Lưu tại: comic_layouts_rectangular_6x.png")
    
    # Demo 4: So sánh 6 layouts có đường chéo
    print("\n[SO SÁNH] 6 Layouts kết hợp đường chéo")
    print("-" * 70)
    fig4 = create_multiple_layouts_with_diagonals()
    plt.savefig('comic_layouts_diagonal_6x.png', dpi=150, bbox_inches='tight')
    print("✓ Đã tạo 6 layouts có đường chéo")
    print(f"  📁 Lưu tại: comic_layouts_diagonal_6x.png")
    
    print("\n" + "=" * 70)
    print("✅ HOÀN THÀNH! Đã tạo 4 file hình ảnh")
    print("=" * 70)
    print("\n💡 Giải thích:")
    print("  • Phương án 1: Giống góc trái ảnh bạn gửi (chỉ vuông góc)")
    print("  • Phương án 2: Giống góc phải ảnh bạn gửi (có đường chéo)")
    print("  • Kết hợp 2 phương án tạo ra layouts đa dạng hơn!\n")
    
    plt.show()
