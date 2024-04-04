import pygame
import json
import math
import numpy as np
import pygame.freetype


WIDTH = 1024
HEIGHT = 768
MOVE_STEP = 3 #krok
ZOOM_STEP = 30
ROTATION_STEP = math.pi / 30 #krok obrót
COLORS = [(255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 255, 255), (255, 255, 0), (255, 0, 255)]
OUTLINE_COLOR = (255, 255, 255)
show_numbers = False

with open('state.json') as f:
    state = json.load(f)

color_cuboids = True
pygame.freetype.init()
font = pygame.freetype.Font(None, 24)


def zoom(positive): #zoom, zmieniamy odelgłość od sceny ale nie połozenie kamery
    new_distance = state['distance'] + (ZOOM_STEP if positive else -ZOOM_STEP)
    min_distance = 50
    max_distance = 500

    if min_distance <= new_distance <= max_distance:
        state['distance'] = new_distance

def move(vector):
    def translate(point): #dodajemy wektor przesunięcia do danego punktu
        return list(np.add(point, vector))
    state['polygons'] = list(map(lambda p: list(map(translate, p)), state['polygons'])) #przesuwamy wszystkie punkty


def turn(axis, direction): #oś i kierunek obrotu
    angle = direction * ROTATION_STEP
    matrix = { #definujemy macierz obrotu i przesuniecia
        'x': [
            [1, 0, 0, 0],
            [0, math.cos(angle), -1 * math.sin(angle), 0],
            [0, math.sin(angle), math.cos(angle), 0],
            [0, 0, 0, 1]
        ],
        'y': [
            [math.cos(angle), 0, math.sin(angle), 0],
            [0, 1, 0, 0],
            [-1 * math.sin(angle), 0, math.cos(angle), 0],
            [0, 0, 0, 1]
        ],
        'z': [
            [math.cos(angle), -1 * math.sin(angle), 0, 0],
            [math.sin(angle), math.cos(angle), 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ]
    }.get(axis)

    def rotate(point): #mnożymy macierz obrotu przez punkt
        return list(np.matmul(matrix, point + [1])[:-1]) #dodanie 1 umożliwa translacje
    state['polygons'] = list(map(lambda p: list(map(rotate, p)), state['polygons'])) #obracamy wszystkie punkty

def toggle_color():
    global color_cuboids
    color_cuboids = not color_cuboids

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))


def priority(polygon):
    center_of_mass = [sum(point[i] for point in polygon) / 3 for i in range(3)]
    return np.linalg.norm(center_of_mass)

def divide_polygon(polygon):
    center = [sum(point[i] for point in polygon) / len(polygon) for i in range(3)]
    midpoints = [[(polygon[i][j] + polygon[(i+1)%4][j]) / 2 for j in range(3)] for i in range(4)]
    diagonals = [[(midpoints[i][j] + midpoints[(i+2)%4][j]) / 2 for j in range(3)] for i in range(4)]
    return [
        [polygon[0], midpoints[0], diagonals[0], midpoints[3]],
        [midpoints[0], polygon[1], midpoints[1], diagonals[0]],
        [diagonals[0], midpoints[1], polygon[2], midpoints[2]],
        [midpoints[3], diagonals[0], midpoints[2], polygon[3]],
        [midpoints[0], diagonals[0], center, midpoints[1]],
        [midpoints[1], diagonals[0], center, midpoints[2]],
        [midpoints[2], diagonals[0], center, midpoints[3]],
        [midpoints[3], diagonals[0], center, midpoints[0]]
    ]
def project(point): #rzutujemy punkt na płaszczyznę
    return (WIDTH / 2 + (state['distance'] * point[0] / point[2]),
            HEIGHT / 2 - (state['distance'] * point[1] / point[2]))

def render():
    screen.fill((0, 0, 0))
    polygons = list(state['polygons'])
    colors = [COLORS[i % len(COLORS)] for i in range(len(polygons))]

    divided_polygons = [(color, polygon) for color, polygon in zip(colors, polygons)]
    for _ in range(3):
        divided_polygons = [(color, smaller_polygon) for color, polygon in divided_polygons for smaller_polygon in
                            divide_polygon(polygon)]
    sorted_polygons = sorted(enumerate(divided_polygons), key=lambda x: (priority(x[1][1]), x[0]), reverse=True)

    for original_index, (color, polygon) in map(lambda p: (p[0], (p[1][0], list(filter(lambda point: point[2] > 0, p[1][1])))), sorted_polygons):  # Filter points by z
        if not polygon:
            continue
        projected_polygon = list(map(project, polygon))
        if len(projected_polygon) > 2:
            pygame.draw.polygon(screen, color, projected_polygon, 0 if color_cuboids else 1)
            if original_index < len(polygons):
                pygame.draw.polygon(screen, OUTLINE_COLOR, projected_polygon, 1)
            if show_numbers:
                center_x = sum(point[0] for point in projected_polygon) / len(projected_polygon)
                center_y = sum(point[1] for point in projected_polygon) / len(projected_polygon)
                text_surface, rect = font.render(str(original_index), (255, 255, 255))
                screen.blit(text_surface, (center_x, center_y))

    pygame.display.flip()


render()
running = True
pygame.event.set_grab(True)
pygame.mouse.set_visible(False)
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            handler = {
                pygame.K_w: lambda: move([0, 0, -MOVE_STEP]),
                pygame.K_s: lambda: move([0, 0, MOVE_STEP]),
                pygame.K_a: lambda: move([MOVE_STEP, 0, 0]),
                pygame.K_d: lambda: move([-MOVE_STEP, 0, 0]),
                pygame.K_r: lambda: move([0, -MOVE_STEP, 0]),
                pygame.K_f: lambda: move([0, MOVE_STEP, 0]),
                pygame.K_KP7: lambda: turn('z', 1),
                pygame.K_KP9: lambda: turn('z', -1),
                pygame.K_KP4: lambda: turn('y', 1),
                pygame.K_KP6: lambda: turn('y', -1),
                pygame.K_KP8: lambda: turn('x', 1),
                pygame.K_KP5: lambda: turn('x', -1),
                pygame.K_RETURN: lambda: toggle_color(),
                pygame.K_ESCAPE: lambda: setattr(running, False),
                pygame.K_UP: lambda: zoom(True),
                pygame.K_DOWN: lambda: zoom(False),
            }.get(event.key)

            if handler:
                handler()
                render()


pygame.quit()


