/* Boolean per-frame Bresenham evidence. No oracle geometry, threading or RNG. */
#include <stdint.h>
#include <stdlib.h>

void trace_rays(int ox, int oy, const int32_t *endpoints, const uint8_t *kind,
                int count, int width, int height, uint8_t *free_cells,
                uint8_t *hit_cells, uint8_t *observed) {
    for (int i = 0; i < count; ++i) {
        int x = ox, y = oy, ex = endpoints[2*i], ey = endpoints[2*i+1];
        int dx = abs(ex-x), sx = x < ex ? 1 : -1;
        int dy = -abs(ey-y), sy = y < ey ? 1 : -1, error = dx+dy;
        while (1) {
            int last = (x == ex && y == ey);
            if (x >= 0 && x < width && y >= 0 && y < height) {
                int j = y*width+x;
                observed[j] = 1;
                /* kind 0=floor (free endpoint), 1=occupied endpoint,
                   2=surface outside occupancy range (endpoint not updated). */
                if (last && kind[i] == 1) hit_cells[j] = 1;
                else if (!last || kind[i] == 0) free_cells[j] = 1;
            }
            if (last) break;
            int twice = 2*error;
            if (twice >= dy) { error += dy; x += sx; }
            if (twice <= dx) { error += dx; y += sy; }
        }
    }
}
