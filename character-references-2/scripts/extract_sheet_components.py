#!/usr/bin/env python3
"""Extract transparent character components from a white reference sheet."""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image


MATEO_COMPONENTS = {
    "centaur-full-body": (150, 0, 680, 665),
    "reverse-full-body": (840, 0, 1235, 665),
    "human-neutral": (0, 640, 178, 1024),
    "human-curious": (190, 640, 337, 1024),
    "human-happy": (349, 640, 495, 1024),
    "human-worried": (509, 640, 650, 1024),
    "human-thoughtful": (650, 640, 800, 1024),
    "reverse-neutral": (814, 640, 945, 1024),
    "reverse-curious": (956, 640, 1083, 1024),
    "reverse-happy": (1095, 640, 1225, 1024),
    "reverse-worried": (1225, 640, 1364, 1024),
    "reverse-thoughtful": (1385, 640, 1536, 1024),
}


def is_background_candidate(pixel: tuple[int, int, int, int]) -> bool:
    red, green, blue, _ = pixel
    return min(red, green, blue) >= 218 and max(red, green, blue) - min(
        red, green, blue
    ) <= 24


def remove_connected_white(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    queue: deque[tuple[int, int]] = deque()
    visited = bytearray(width * height)

    def enqueue(x: int, y: int) -> None:
        index = y * width + x
        if visited[index] or not is_background_candidate(pixels[x, y]):
            return
        visited[index] = 1
        queue.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)
    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    while queue:
        x, y = queue.popleft()
        red, green, blue, _ = pixels[x, y]
        distance = max(255 - red, 255 - green, 255 - blue)
        alpha = max(0, min(255, round((distance - 5) * 10)))
        pixels[x, y] = (red, green, blue, alpha)
        if x:
            enqueue(x - 1, y)
        if x + 1 < width:
            enqueue(x + 1, y)
        if y:
            enqueue(x, y - 1)
        if y + 1 < height:
            enqueue(x, y + 1)

    return rgba


def trim_transparent(image: Image.Image, padding: int = 10) -> Image.Image:
    alpha = image.getchannel("A")
    bounds = alpha.getbbox()
    if bounds is None:
        return image
    left, top, right, bottom = bounds
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(image.width, right + padding)
    bottom = min(image.height, bottom + padding)
    return image.crop((left, top, right, bottom))


def remove_small_islands(image: Image.Image, minimum_ratio: float = 0.03) -> Image.Image:
    """Remove disconnected fragments introduced by neighbouring sheet crops."""
    alpha = image.getchannel("A")
    width, height = image.size
    alpha_pixels = alpha.load()
    visited = bytearray(width * height)
    components: list[list[tuple[int, int]]] = []

    for start_y in range(height):
        for start_x in range(width):
            index = start_y * width + start_x
            if visited[index] or alpha_pixels[start_x, start_y] == 0:
                continue
            visited[index] = 1
            queue = deque([(start_x, start_y)])
            component: list[tuple[int, int]] = []
            while queue:
                x, y = queue.popleft()
                component.append((x, y))
                for next_x, next_y in (
                    (x - 1, y),
                    (x + 1, y),
                    (x, y - 1),
                    (x, y + 1),
                ):
                    if not (0 <= next_x < width and 0 <= next_y < height):
                        continue
                    next_index = next_y * width + next_x
                    if visited[next_index] or alpha_pixels[next_x, next_y] == 0:
                        continue
                    visited[next_index] = 1
                    queue.append((next_x, next_y))
            components.append(component)

    if not components:
        return image
    minimum_size = len(max(components, key=len)) * minimum_ratio
    output = image.copy()
    output_pixels = output.load()
    for component in components:
        if len(component) >= minimum_size:
            continue
        for x, y in component:
            red, green, blue, _ = output_pixels[x, y]
            output_pixels[x, y] = (red, green, blue, 0)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    with Image.open(args.input) as sheet:
        if sheet.size != (1536, 1024):
            raise ValueError(f"Expected a 1536x1024 sheet, got {sheet.size}")
        for name, crop_box in MATEO_COMPONENTS.items():
            component = sheet.crop(crop_box)
            component = remove_connected_white(component)
            if "full-body" not in name:
                component = remove_small_islands(component)
            component = trim_transparent(component)
            output = args.out / f"{name}.png"
            component.save(output)
            print(f"{output}: {component.size}")


if __name__ == "__main__":
    main()
