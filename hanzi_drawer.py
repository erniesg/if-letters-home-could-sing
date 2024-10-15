import numpy as np
from PIL import Image
from draw_rm import RemarkableDrawer

class HanziDrawer(RemarkableDrawer):
    def __init__(self, address, key=None, grid_size=256):
        super().__init__(address, key)
        self.grid_size = grid_size
        self.grid = np.zeros((grid_size, grid_size), dtype=np.uint8)
        self.strokes = []
        self.current_stroke = []

    def _map_to_grid(self, x, y):
        grid_x = int((x / self.rm_width) * self.grid_size)
        grid_y = int((y / self.rm_height) * self.grid_size)
        return grid_x, grid_y

    def _handle_event(self, e_type, e_code, e_value):
        super()._handle_event(e_type, e_code, e_value)
        if e_type == 3 and self.is_touching:  # EV_ABS
            if e_code == 0:  # ABS_X
                self.raw_x = e_value
            elif e_code == 1:  # ABS_Y
                self.raw_y = e_value
            grid_x, grid_y = self._map_to_grid(self.raw_x, self.raw_y)
            self.current_stroke.append((grid_x, grid_y))
            self._draw_on_grid(grid_x, grid_y)

    def _handle_pressure(self, pressure):
        if pressure > self.pressure_threshold and not self.is_touching:
            self.is_touching = True
            self.current_stroke = []
        elif pressure <= self.pressure_threshold and self.is_touching:
            self.is_touching = False
            if self.current_stroke:
                self.strokes.append(self.current_stroke)
            self.current_stroke = []

    def _draw_on_grid(self, x, y):
        self.grid[y, x] = 255

    def get_image(self):
        return Image.fromarray(self.grid)

    def get_strokes(self):
        return self.strokes

    def clear(self):
        self.grid = np.zeros((self.grid_size, self.grid_size), dtype=np.uint8)
        self.strokes = []
        self.current_stroke = []
