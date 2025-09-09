#!/usr/bin/env -S uv run --quiet --script

# /// script
# dependencies = [
#   "Pillow",
# ]
# ///
"""
Скрипт для автоматической обрезки PNG изображений с белым или прозрачным фоном.
Удаляет пустое пространство вокруг объекта на изображении, сохраняя прозрачность.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image


def get_bounding_box(image):
    """
    Находит bounding box непрозрачного содержимого изображения.
    
    Args:
        image (PIL.Image): Изображение для анализа
        
    Returns:
        tuple: (left, top, right, bottom) или None если нет содержимого
    """
    # Если изображение имеет альфа-канал, используем его
    if image.mode in ('RGBA', 'LA') or 'transparency' in image.info:
        # Получаем альфа-канал или создаем его из transparency
        if image.mode == 'RGBA':
            alpha = image.split()[-1]
        elif image.mode == 'LA':
            alpha = image.split()[-1]
        else:
            # Преобразуем изображение в RGBA для получения альфа-канала
            image = image.convert('RGBA')
            alpha = image.split()[-1]
        
        # Находим bounding box непрозрачных пикселей
        bbox = alpha.getbbox()
        return bbox
    
    # Если альфа-канала нет, ищем по белому фону
    else:
        # Конвертируем в RGB если нужно
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Создаем маску где белый цвет (255,255,255) помечен как фон
        # Инвертируем логику: находим пиксели, которые НЕ белые
        width, height = image.size
        pixels = image.load()
        
        left, top, right, bottom = width, height, 0, 0
        found_content = False
        
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                # Если пиксель не белый, это содержимое
                if not (r == 255 and g == 255 and b == 255):
                    found_content = True
                    left = min(left, x)
                    top = min(top, y)
                    right = max(right, x + 1)
                    bottom = max(bottom, y + 1)
        
        return (left, top, right, bottom) if found_content else None


def get_center_of_mass(image):
    """
    Вычисляет центр масс непрозрачного содержимого изображения.
    
    Args:
        image (PIL.Image): Изображение для анализа
        
    Returns:
        tuple: (center_x, center_y) или None если нет содержимого
    """
    # Если изображение имеет альфа-канал, используем его
    if image.mode in ('RGBA', 'LA') or 'transparency' in image.info:
        if image.mode == 'RGBA':
            alpha = image.split()[-1]
        elif image.mode == 'LA':
            alpha = image.split()[-1]
        else:
            image = image.convert('RGBA')
            alpha = image.split()[-1]
        
        width, height = alpha.size
        pixels = alpha.load()
        
        total_mass = 0
        weighted_x = 0
        weighted_y = 0
        
        for y in range(height):
            for x in range(width):
                opacity = pixels[x, y]
                if opacity > 0:  # Непрозрачный пиксель
                    total_mass += opacity
                    weighted_x += x * opacity
                    weighted_y += y * opacity
    
    # Если альфа-канала нет, ищем по белому фону
    else:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        width, height = image.size
        pixels = image.load()
        
        total_mass = 0
        weighted_x = 0
        weighted_y = 0
        
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                # Если пиксель не белый, учитываем его
                if not (r == 255 and g == 255 and b == 255):
                    # Используем инверсию расстояния от белого как "массу"
                    mass = 255 - min(r, g, b)  # Чем темнее, тем больше масса
                    total_mass += mass
                    weighted_x += x * mass
                    weighted_y += y * mass
    
    if total_mass == 0:
        return None
    
    center_x = int(weighted_x / total_mass)
    center_y = int(weighted_y / total_mass)
    
    return (center_x, center_y)


def get_centered_crop_box(bbox, original_size, center_of_mass=None, padding=10):
    """
    Создает центрированный квадратный bounding box с отступами.
    
    Args:
        bbox (tuple): Исходный bounding box (left, top, right, bottom)
        original_size (tuple): Размер исходного изображения (width, height)
        center_of_mass (tuple): Центр масс объекта (x, y), если None - используется геометрический центр
        padding (int): Отступ в пикселях вокруг объекта
        
    Returns:
        tuple: Новый центрированный bounding box
    """
    left, top, right, bottom = bbox
    orig_width, orig_height = original_size
    
    # Размеры объекта
    obj_width = right - left
    obj_height = bottom - top
    
    # Используем центр масс если доступен, иначе геометрический центр
    if center_of_mass:
        obj_center_x, obj_center_y = center_of_mass
    else:
        obj_center_x = left + obj_width // 2
        obj_center_y = top + obj_height // 2
    
    # Определяем размер квадрата (больший из размеров + отступы)
    square_size = max(obj_width, obj_height) + 2 * padding
    
    # Убеждаемся, что квадрат не больше исходного изображения
    square_size = min(square_size, min(orig_width, orig_height))
    
    # Вычисляем новые координаты для центрированного квадрата
    half_square = square_size // 2
    new_left = max(0, obj_center_x - half_square)
    new_top = max(0, obj_center_y - half_square)
    new_right = min(orig_width, new_left + square_size)
    new_bottom = min(orig_height, new_top + square_size)
    
    # Корректируем, если квадрат выходит за границы
    if new_right - new_left < square_size:
        new_left = max(0, new_right - square_size)
    if new_bottom - new_top < square_size:
        new_top = max(0, new_bottom - square_size)
    
    return (new_left, new_top, new_right, new_bottom)


def crop_image(input_path):
    """
    Обрезает изображение, удаляя пустые области.
    
    Args:
        input_path (Path): Путь к исходному изображению
        
    Returns:
        bool: True если обрезка прошла успешно, False иначе
    """
    try:
        # Загружаем изображение
        with Image.open(input_path) as image:
            print(f"Загружено изображение: {image.size[0]}x{image.size[1]} ({image.mode})")
            
            # Находим границы содержимого
            bbox = get_bounding_box(image)
            
            if bbox is None:
                print("⚠️  Изображение полностью прозрачное или белое")
                return False
            
            # Вычисляем центр масс объекта
            center_of_mass = get_center_of_mass(image)
            
            left, top, right, bottom = bbox
            original_size = image.size
            
            print(f"Найдены границы объекта: ({left}, {top}) -> ({right}, {bottom})")
            if center_of_mass:
                print(f"Центр масс объекта: ({center_of_mass[0]}, {center_of_mass[1]})")
            
            # Получаем центрированный квадратный crop box с учетом центра масс
            centered_bbox = get_centered_crop_box(bbox, original_size, center_of_mass, padding=20)
            new_left, new_top, new_right, new_bottom = centered_bbox
            new_size = (new_right - new_left, new_bottom - new_top)
            
            print(f"Центрированные границы: ({new_left}, {new_top}) -> ({new_right}, {new_bottom})")
            print(f"Новый размер: {new_size[0]}x{new_size[1]}")
            
            # Если размеры не изменились, обрезка не нужна
            if new_size == original_size:
                print("✅ Изображение уже обрезано оптимально")
                return True
            
            # Обрезаем изображение с центрированными координатами
            cropped = image.crop(centered_bbox)
            
            # Генерируем имя выходного файла
            output_path = input_path.parent / f"{input_path.stem}_cropped{input_path.suffix}"
            
            # Сохраняем с теми же параметрами, что и оригинал
            save_kwargs = {}
            if image.format == 'PNG':
                save_kwargs['optimize'] = True
                # Сохраняем прозрачность если она есть
                if image.mode in ('RGBA', 'LA') or 'transparency' in image.info:
                    save_kwargs['transparency'] = 'transparency' if 'transparency' in image.info else None
            
            cropped.save(output_path, format='PNG', **save_kwargs)
            
            print(f"✅ Сохранено: {output_path}")
            print(f"📊 Размер уменьшен с {original_size[0]}x{original_size[1]} до {new_size[0]}x{new_size[1]}")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при обработке изображения: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Автоматическая обрезка PNG изображений с белым или прозрачным фоном"
    )
    parser.add_argument(
        "image_path",
        type=str,
        help="Путь к PNG файлу для обрезки"
    )
    
    args = parser.parse_args()
    
    # Проверяем входной файл
    input_path = Path(args.image_path)
    
    if not input_path.exists():
        print(f"❌ Файл не найден: {input_path}")
        sys.exit(1)
    
    if not input_path.is_file():
        print(f"❌ Указанный путь не является файлом: {input_path}")
        sys.exit(1)
    
    if input_path.suffix.lower() != '.png':
        print(f"❌ Поддерживаются только PNG файлы, получен: {input_path.suffix}")
        sys.exit(1)
    
    print(f"🖼️  Обрабатываю: {input_path}")
    
    # Выполняем обрезку
    success = crop_image(input_path)
    
    if success:
        print("✅ Обрезка завершена успешно")
        sys.exit(0)
    else:
        print("❌ Ошибка при обрезке")
        sys.exit(1)


if __name__ == "__main__":
    main()