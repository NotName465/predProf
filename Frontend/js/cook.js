document.addEventListener('DOMContentLoaded', () => {

    // --- 1. ЛОГИКА ВКЛАДОК (TABS) ---
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Убираем активный класс у всех
            tabs.forEach(t => t.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));

            // Добавляем активный класс нажатой кнопке
            tab.classList.add('active');

            // Показываем нужный контент
            const tabId = tab.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });

    // --- 2. ЛОГИКА БАЗЫ ДАННЫХ (ВЫПАДАЮЩИЙ СПИСОК) ---
    const dishSelect = document.getElementById('dishSelect');
    const dishCard = document.getElementById('dishCard');

    // Элементы карточки
    const cardName = document.getElementById('cardName');
    const cardStock = document.getElementById('cardStock');
    const cardCalories = document.getElementById('cardCalories');
    const cardImage = document.getElementById('cardImage');
    const cardIngredients = document.getElementById('cardIngredients');

    // Переменная для хранения всех загруженных блюд
    let allDishes = [];

    // Функция загрузки данных с сервера
    async function loadDishes() {
        try {
            const response = await fetch('/api/dishes');
            if (!response.ok) throw new Error('Ошибка сети');

            allDishes = await response.json();

            // Очищаем список
            dishSelect.innerHTML = '<option value="">-- Выберите блюдо --</option>';

            // Заполняем список
            allDishes.forEach(dish => {
                const option = document.createElement('option');
                option.value = dish.id; // ID из базы
                option.textContent = dish.name;
                dishSelect.appendChild(option);
            });

        } catch (error) {
            console.error(error);
            dishSelect.innerHTML = '<option>Ошибка загрузки данных</option>';
        }
    }

    // Загружаем данные сразу при открытии страницы
    loadDishes();

    // Слушаем изменение выбора в списке
    dishSelect.addEventListener('change', function() {
        const selectedId = this.value;

        if (!selectedId) {
            dishCard.style.display = 'none';
            return;
        }

        // Ищем выбранное блюдо в массиве allDishes
        // (Обратите внимание: id в select это строка, а в базе число, поэтому ==)
        const dish = allDishes.find(d => d.id == selectedId);

        if (dish) {
            // Заполняем карточку данными
            cardName.textContent = dish.name;
            cardStock.textContent = dish.stock_quantity;
            cardCalories.textContent = dish.calories;

            // Если есть картинка
            if (dish.image_url) {
                cardImage.style.backgroundImage = `url('${dish.image_url}')`;
            } else {
                cardImage.style.background = '#ccc';
            }

            // Заполняем ингредиенты
            cardIngredients.innerHTML = ''; // Очистить старые
            if (dish.ingredients && Array.isArray(dish.ingredients)) {
                dish.ingredients.forEach(ing => {
                    const li = document.createElement('li');
                    li.textContent = ing;
                    cardIngredients.appendChild(li);
                });
            } else {
                cardIngredients.innerHTML = '<li>Нет данных</li>';
            }

            // Показываем карточку
            dishCard.style.display = 'block';
        }
    });
});
