import json
from threading import local
import tkinter as tk
from tkinter import filedialog
from xml.etree.ElementTree import tostring
import numpy as np
from PIL import Image, ImageTk

# Размеры изображения
WIDTH, HEIGHT = 800, 600
# Цвет фона
BACKGROUND_COLOR = [200,200,200]

# Создаем кадровый буфер (frame buffer)
frame_buffer = np.full((HEIGHT, WIDTH, 3), BACKGROUND_COLOR, dtype=np.uint8)
# Список фигур
polygon_list = []

def calculate_plane_equation(vertices):
    """
    Вычисляет уравнение плоскости по методу Ньюэла, используя 3 точки.
    Аргументы:
    vertices -- Список из 3-х точек, каждая точка в виде (x, y, z)
    Возвращает:
    Коэффициенты уравнения плоскости: a, b, c, d, где уравнение плоскости: ax + by + cz + d = 0
    """
    v1 = np.array(vertices[1]) - np.array(vertices[0])
    v2 = np.array(vertices[2]) - np.array(vertices[0])
    normal = np.cross(v1, v2)
    a, b, c = normal
    d = -np.dot(normal, np.array(vertices[0]))
    return a, b, c, d

# Получаем всю необходимую информацию о фигуре и сохраняем её в список фигур
def add_polygon(vertices, color):
    global polygon_list
    edge_table = []
    # Вычисляем коэффициенты уравнения плоскости
    a, b, c, d = calculate_plane_equation(vertices)
    
    # Формирование таблицы рёбер
    for i in range(len(vertices)):
        if vertices[i][1] != vertices[i-1][1]:  # Исключаем горизонтальные рёбра
            edge_table.append([vertices[i], vertices[i-1]])

    polygon_list.append(
        {
        'a': a,
        'b': b,
        'c': c,
        'd': d,
        'edge_table': edge_table,
        'vertices': vertices,
        'color': color,
        'y_max': max(vertices, key=lambda x: x[1])[1],
        'y_min': min(vertices, key=lambda x: x[1])[1]
        }
    )

# Заполняем буфер экрана (отрисовывам фигуры)
def render():
    global WIDTH, polygon_list, frame_buffer, BACKGROUND_COLOR

    if not polygon_list:
        return

    # Получение максимального и минимального y (диапазон экрана в котором распологаются фигуры)
    y_max = max(polygon_list, key=lambda x: x['y_max'])['y_max']
    y_min = min(polygon_list, key=lambda x: x['y_min'])['y_min']

    # Обработка по строкам
    for y in range(y_min, y_max + 1):
        # Создание буферов для обрабатываемой строки
        frame_buffer_line = np.full((WIDTH, 3), BACKGROUND_COLOR, dtype=np.uint8)
        z_buffer = np.full((WIDTH, 1), 0, dtype=int)
        
        # Определение активных многоугольников на текущей строке
        active_polygon_list = []
        for polygon in polygon_list:
            if y >= polygon['y_min'] and y <= polygon['y_max']:
                active_polygon_list.append(polygon)

        # Для каждого активного многоугольника расчитываем значение в z буфере
        for polygon in active_polygon_list:
            # Поиск левого и правого края фигуры при текущем y
            value_x_list = []
            for edge in polygon['edge_table']:
                edge_y_max = max(edge, key=lambda x: x[1])[1]
                edge_y_min = min(edge, key=lambda x: x[1])[1]
                if y >= edge_y_min and y <= edge_y_max:
                    value_x_list.append(find_x_for_y(edge[0], edge[1], y))
            left_x = min(value_x_list)
            right_x = max(value_x_list)
            # Расчёт глубины (z)
            for x in range(left_x, right_x + 1):
                z = -(polygon['a'] * x + polygon['b'] * y + polygon['d']) / polygon['c']
                if z_buffer[x] < z:
                    frame_buffer_line[x] = polygon['color']
                    z_buffer[x] = z
        # Запись итогового значения буфера кадра линии в буфер кадра дисплея
        frame_buffer[-y] = frame_buffer_line
                
# Поиск координаты x при известной y на прямой между 2 точками
def find_x_for_y(point1, point2, y):
    if point1[0] == point2[0]:
        return point1[0]
    m = (point2[1] - point1[1]) / (point2[0] - point1[0])
    b = point1[1] - m * point1[0]
    x = (y - b) / m
    return int(x)

# Отображение изображения на экране
def update_image():
    global frame_buffer, polygon_list, HEIGHT
    render()
    img = Image.fromarray(frame_buffer)
    img_tk = ImageTk.PhotoImage(img)
    
    canvas.create_image(0, 0, anchor="nw", image=img_tk)  
    canvas.image = img_tk 
    
    # Отрисовка осей OX и OY
    axis_color = "black"  # Цвет осей
    # Ось OX
    canvas.create_line(15, HEIGHT - 15, 150, HEIGHT - 15, fill=axis_color, width=3)
    canvas.create_line(140, HEIGHT - 20, 150, HEIGHT - 15, fill=axis_color, width=3)
    canvas.create_line(140, HEIGHT - 10, 150, HEIGHT - 15, fill=axis_color, width=3)
    canvas.create_text(150, HEIGHT - 25, anchor="nw", text="X", fill="black", font=("Helvetica", 15))
    # Ось OY
    canvas.create_line(15, HEIGHT - 15, 15, HEIGHT - 150, fill=axis_color, width=3)
    canvas.create_line(10, HEIGHT - 140, 15, HEIGHT - 150, fill=axis_color, width=3)
    canvas.create_line(20, HEIGHT - 140, 15, HEIGHT - 150, fill=axis_color, width=3)
    canvas.create_text(10, HEIGHT - 170, anchor="nw", text="Y", fill="black", font=("Helvetica", 15))

    # Отрисовка координат вершин
    point_list = []        # Массив с точками которые уже отображены на экране
    for polygon in polygon_list:
        for vertice in polygon['vertices']:
            move_x = 0
            move_y = 0
            # Если точка расположена в месте где уже нарисованна точка, то сдвигаем её
            if [vertice[0], vertice[1]] in point_list:  
                move_x += 16
                move_y += 16
            point_info = f"({vertice[0]}, {vertice[1]}, {vertice[2]})"
            canvas.create_text(move_x + vertice[0], move_y + HEIGHT - vertice[1], anchor="nw", text=point_info, fill="black", font=("Helvetica", 12))
            point_list.append([vertice[0], vertice[1]])

# Обработчик для загрузки новой фигуры
def load_polygon():
    global frame_buffer, BACKGROUND_COLOR
    file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if file_path:
        with open(file_path, 'r') as f:
            data = json.load(f)

        vertices = data["vertices"]
        color = tuple(data["color"])

        vertices = scale_polygon(vertices, 20)
        frame_buffer.fill(BACKGROUND_COLOR[0])  # Очистка буфера
        add_polygon(vertices, color)
        update_image()

# Функция для увиеличения фигуры
def scale_polygon(vertices, scale_factor):
    scaled_vertices = []
    for x, y, z in vertices:
        scaled_x = x * scale_factor
        scaled_y = y * scale_factor
        scaled_z = z * scale_factor
        scaled_vertices.append((int(scaled_x), int(scaled_y), int(scaled_z)))
    return scaled_vertices

# Удаляет все загруженные в программу фигуры
def delete_all_polygon():
    global polygon_list, frame_buffer, BACKGROUND_COLOR
    polygon_list = []
    frame_buffer.fill(BACKGROUND_COLOR[0])
    update_image()

# Настройка Tkinter
root = tk.Tk()
root.title("Polygon Drawer")

canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT)
canvas.pack()

button_frame = tk.Frame(root)
button_frame.pack()

load_button = tk.Button(button_frame, text="Загрузить фигуру", command=load_polygon)
load_button.pack(side="left")

delete_button = tk.Button(button_frame, text="Удалить фигуры", command=delete_all_polygon)
delete_button.pack(side="left")

update_image()
root.mainloop()