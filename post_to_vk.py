import os
import random
import requests

# --- Константы и загрузка секретов из GitHub Actions ---
VK_API_VERSION = '5.131'
VK_API_URL = 'https://api.vk.com/method/'
VK_ACCESS_TOKEN = os.getenv('VK_TOKEN')
VK_GROUP_ID = os.getenv('VK_GROUP_ID')

UNSPLASH_API_URL = 'https://api.unsplash.com/photos/random'
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')

# Темы для поиска изображений
IMAGE_QUERIES = ['office', 'workplace', 'business meeting', 'laptop', 'teamwork']

def get_random_post_text(filename="posts.txt"):
    """Читает файл и возвращает случайную строку."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return random.choice(lines).strip()
    except FileNotFoundError:
        return "Всем хорошего дня! #автопост"

def get_image_from_unsplash():
    """Получает случайное изображение с Unsplash по заданной теме."""
    params = {
        'query': random.choice(IMAGE_QUERIES),
        'orientation': 'landscape',
        'client_id': UNSPLASH_ACCESS_KEY
    }
    response = requests.get(UNSPLASH_API_URL, params=params)
    response.raise_for_status()  # Вызовет ошибку, если запрос неудачный
    data = response.json()
    image_url = data['urls']['regular']
    print(f"Найдено изображение: {image_url}")
    
    # Скачиваем изображение
    image_response = requests.get(image_url)
    image_response.raise_for_status()
    return image_response.content

def upload_photo_to_vk(image_content):
    """Загружает фото на сервер VK."""
    # 1. Получаем адрес сервера для загрузки
    params = {
        'group_id': VK_GROUP_ID,
        'access_token': VK_ACCESS_TOKEN,
        'v': VK_API_VERSION
    }
    upload_url_response = requests.get(f'{VK_API_URL}photos.getWallUploadServer', params=params).json()
    upload_url = upload_url_response['response']['upload_url']

    # 2. Загружаем фото на полученный адрес
    files = {'photo': ('photo.jpg', image_content, 'image/jpeg')}
    upload_response = requests.post(upload_url, files=files).json()

    # 3. Сохраняем фото в альбоме сообщества
    save_params = {
        'group_id': VK_GROUP_ID,
        'server': upload_response['server'],
        'photo': upload_response['photo'],
        'hash': upload_response['hash'],
        'access_token': VK_ACCESS_TOKEN,
        'v': VK_API_VERSION
    }
    save_response = requests.post(f'{VK_API_URL}photos.saveWallUploadPhoto', data=save_params).json()
    
    photo_data = save_response['response'][0]
    owner_id = photo_data['owner_id']
    photo_id = photo_data['id']
    
    return f'photo{owner_id}_{photo_id}'

def post_to_vk_wall(message, attachment):
    """Публикует пост на стене сообщества."""
    params = {
        'owner_id': f'-{VK_GROUP_ID}',  # ID группы с минусом
        'from_group': 1,
        'message': message,
        'attachments': attachment,
        'access_token': VK_ACCESS_TOKEN,
        'v': VK_API_VERSION
    }
    response = requests.post(f'{VK_API_URL}wall.post', data=params)
    response.raise_for_status()
    print("Пост успешно опубликован в VK!")
    print(response.json())

if __name__ == "__main__":
    print("Начинаем процесс публикации...")
    
    # Шаг 1: Получаем текст для поста
    post_text = get_random_post_text()
    print(f"Текст поста: {post_text}")

    # Шаг 2: Получаем и скачиваем изображение
    image_bytes = get_image_from_unsplash()

    # Шаг 3: Загружаем фото в VK
    photo_attachment_id = upload_photo_to_vk(image_bytes)
    print(f"Фото загружено. ID для вложения: {photo_attachment_id}")

    # Шаг 4: Публикуем пост
    post_to_vk_wall(post_text, photo_attachment_id)
