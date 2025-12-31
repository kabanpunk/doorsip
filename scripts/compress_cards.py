#!/usr/bin/env python3
"""
Скрипт для сжатия карточек:
1. Масштабирует к стандартному размеру
2. Удаляет прозрачный разделитель
3. Уменьшает разрешение в 2 раза
4. Конвертирует в WebP для лучшего сжатия
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Установите Pillow: pip install Pillow")
    sys.exit(1)

# Целевые размеры
STANDARD_WIDTH = 2048
STANDARD_HEIGHT = 1424

# Координаты разбиения
LEFT_END = 996
RIGHT_START = 1051
HALF_WIDTH = 997

# Финальный размер (уменьшаем в 2 раза)
SCALE_FACTOR = 0.5
FINAL_WIDTH = int(HALF_WIDTH * 2 * SCALE_FACTOR)  # 997
FINAL_HEIGHT = int(STANDARD_HEIGHT * SCALE_FACTOR)  # 712

# WebP качество
WEBP_QUALITY = 85


def process_card(input_path: Path, output_path: Path) -> dict:
    img = Image.open(input_path)
    original_size = os.path.getsize(input_path)
    orig_width, orig_height = img.size

    # Масштабируем к стандартному размеру
    if orig_width != STANDARD_WIDTH or orig_height != STANDARD_HEIGHT:
        scale = STANDARD_WIDTH / orig_width
        new_height = int(orig_height * scale)
        img = img.resize((STANDARD_WIDTH, new_height), Image.Resampling.LANCZOS)

    scaled_height = img.size[1]

    # Вырезаем левую и правую части
    left_part = img.crop((0, 0, LEFT_END + 1, scaled_height))
    right_part = img.crop((RIGHT_START, 0, img.size[0], scaled_height))

    # Склеиваем без разделителя
    result = Image.new('RGBA', (HALF_WIDTH * 2, scaled_height))
    result.paste(left_part, (0, 0))
    result.paste(right_part, (HALF_WIDTH, 0))

    # Уменьшаем в 2 раза
    final_height = int(scaled_height * SCALE_FACTOR)
    result = result.resize((FINAL_WIDTH, final_height), Image.Resampling.LANCZOS)

    # Конвертируем в RGB для WebP
    if result.mode == 'RGBA':
        background = Image.new('RGB', result.size, (255, 255, 255))
        background.paste(result, mask=result.split()[3])
        result = background

    # Сохраняем как WebP
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, 'WEBP', quality=WEBP_QUALITY, method=6)

    new_size = os.path.getsize(output_path)

    return {
        'original_size': original_size,
        'new_size': new_size,
        'original_dimensions': (orig_width, orig_height),
        'new_dimensions': result.size,
    }


def main():
    cards_dir = Path(__file__).parent.parent / 'data' / 'cards' / 'mygame'
    output_dir = cards_dir.parent / 'mygame_webp'

    if not cards_dir.exists():
        print(f"Папка не найдена: {cards_dir}")
        sys.exit(1)

    png_files = list(cards_dir.glob('*.png'))
    if not png_files:
        print("PNG файлы не найдены")
        sys.exit(1)

    print(f"Найдено {len(png_files)} карточек")
    print(f"Целевой размер: {FINAL_WIDTH}x{FINAL_HEIGHT}")
    print("-" * 50)

    total_original = 0
    total_new = 0

    for png_file in sorted(png_files):
        output_file = output_dir / (png_file.stem + '.webp')

        try:
            result = process_card(png_file, output_file)
            total_original += result['original_size']
            total_new += result['new_size']

            orig_kb = result['original_size'] / 1024
            new_kb = result['new_size'] / 1024

            print(f"{png_file.name} -> {output_file.name}:")
            print(f"  {result['original_dimensions']} -> {result['new_dimensions']}")
            print(f"  {orig_kb:.0f} KB -> {new_kb:.0f} KB")
        except Exception as e:
            print(f"Ошибка {png_file.name}: {e}")

    print("-" * 50)
    print(f"Итого: {total_original / (1024*1024):.1f} MB -> {total_new / (1024*1024):.1f} MB")
    print(f"Сжатие: {total_original / total_new:.1f}x")


if __name__ == '__main__':
    main()
