import os
import random
import requests
import google.generativeai as genai # <-- Новая библиотека

# --- Константы и загрузка секретов ---
VK_API_VERSION = '5.131'
VK_API_URL = 'https://api.vk.com/method/'
VK_ACCESS_TOKEN = os.getenv('VK_TOKEN')
VK_GROUP_ID = os.getenv('VK_GROUP_ID')

UNSPLASH_API_URL = 'https://api.unsplash.com/photos/random'
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')

# --- НОВЫЙ БЛОК: Настройка Gemini ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Темы для поиска изображений
IMAGE_QUERIES = ['office', 'workplace', 'business meeting', 'laptop', 'teamwork', 'coffee break']

def get_random_prompt(filename="posts.txt"):
    """Читает файл с промптами и возвращает случайную строку."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return random.choice(lines).strip()
    except FileNotFoundError:
        return "Напиши короткий пост про продуктивный рабочий день."

# --- НОВАЯ ФУНКЦИЯ: Генерация текста с помощью Gemini ---
def generate_text_with_gemini(prompt):
    """Отправляет промпт в Gemini и возвращает сгенерированный текст."""
    if not GEMINI_API_KEY:
        print("Ключ GEMINI_API_KEY не найден. Используем промпт как текст.")
        return prompt
    
    print(f"Отправляем промпт в Gemini: '{prompt}'")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        # Добавим проверку, что ответ не пустой
        if response.text:
            return response.text.strip()
        else:
            print("Gemini вернул пустой ответ. Используем исходный промпт.")
            return prompt
    except Exception as e:
        print(f"Ошибка при обращении к Gemini API: {e}")
        print("Используем исходный промпт в качестве запасного варианта.")
        return prompt

def get_image_from_unsplash():
    """Получает случайное изображение с Unsplash по заданной теме."""
    params = {
        'query': random.choice(IMAGE_QUERIES),
        'orientation': 'landscape',
        'client_id': UNSPLASH_ACCESS_KEY
    }
    response = requests.get(UNSPLASH_API_URL, params=params)
    response.raise_for_status()
    data = response.json()
    image_url = data['urls']['regular']
    print(f"Найдено изображение: {image_url}")
    
    image_response = requests.get(image_url)
    image_response.raise_for_status()
    return image_response.content

def upload_photo_to_vk(image_content):
    """Загружает фото на сервер VK."""
    params = {
        'group_id': VK_GROUP_ID,
        'access_token': VK_ACCESS_TOKEN,
        'v': VK_API_VERSION
    }
    upload_url_response = requests.get(f'{VK_API_URL}photos.getWallUploadServer', params=params).json()

    if 'error' in upload_url_response:
        print("ОШИБКА от API VK при получении адреса для загрузки:")
        print(upload_url_response['error'])
        raise ValueError(f"VK API Error: {upload_url_response['error']['error_msg']}")

    upload_url = upload_url_response['response']['upload_url']
    files = {'photo': ('photo.jpg', image_content, 'image/jpeg')}
    upload_response = requests.post(upload_url, files=files).json()

    save_params = {
        'group_id': VK_GROUP_ID,
        'server': upload_response['server'],
        'photo': upload_response['photo'],
        'hash': upload_response['hash'],
        'access_token': VK_ACCESS_TOKEN,
        'v': VK_API_VERSION
    }
    save_response = requests.post(f'{VK_API_URL}photos.saveWallUploadPhoto', data=save_params).json()
    
    if 'error' in save_response:
        print("ОШИБКА от API VK при сохранении фото:")
        print(save_response['error'])
        raise ValueError(f"VK API Error: {save_response['error']['error_msg']}")

    photo_data = save_response['response'][0]
    owner_id = photo_data['owner_id']
    photo_id = photo_data['id']
    
    return f'photo{owner_id}_{photo_id}'

def post_to_vk_wall(message, attachment):
    """Публикует пост на стене сообщества."""
    params = {
        'owner_id': f'-{VK_GROUP_ID}',
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
    
    # --- ИЗМЕНЕННАЯ ЛОГИКА ---
    # Шаг 1: Получаем промпт для нейросети
    prompt_text = get_random_prompt()
    
    # Шаг 2: Генерируем текст поста с помощью Gemini
    final_post_text = generate_text_with_gemini(prompt_text)
    print(f"Сгенерированный текст поста: {final_post_text}")

    # Шаг 3: Получаем и скачиваем изображение
    image_bytes = get_image_from_unsplash()

    # Шаг 4: Загружаем фото в VK
    photo_attachment_id = upload_photo_to_vk(image_bytes)
    print(f"Фото загружено. ID для вложения: {photo_attachment_id}")

    # Шаг 5: Публикуем пост
    post_to_vk_wall(final_post_text, photo_attachment_id)
