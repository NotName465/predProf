<script>
    let userData = null;
    let userAllergens = []; // Сюда загрузятся ID аллергенов [1, 5, 8]
    let allIngredients = [];

    document.addEventListener('DOMContentLoaded', () => {
        loadProfile();
        loadMenu();
        loadOrders();
        loadIngredients();
    });

    // ... (loadProfile, updateSubInfo, renderAllergens - без изменений) ...

    // --- МЕНЮ С ПОДСВЕТКОЙ АЛЛЕРГЕНОВ ---
    async function loadMenu() {
        const container = document.getElementById('menuContainer');
        try {
            const res = await fetch('/api/menu/today');
            const menu = await res.json();
            
            if(!menu.breakfast.length && !menu.lunch.length) {
                container.innerHTML = '<p style="text-align:center; color:#777;">Меню на сегодня еще не готово</p>';
                document.getElementById('menuLoading').style.display = 'none';
                return;
            }

            // Получаем просто массив ID аллергенов для удобства поиска
            const allergenIds = userAllergens.map(a => a.id);

            let html = '';
            
            const renderSection = (title, items) => {
                if(!items.length) return '';
                let sectionHtml = `<h3 style="color: #0d47a1; margin: 20px 0 10px;">${title}</h3>`;
                
                items.forEach(dish => {
                    // Проверка состава на аллергены
                    let isDangerous = false;
                    let ingredientsHtml = 'Нет данных о составе';

                    if (dish.ingredients && dish.ingredients.length > 0) {
                        ingredientsHtml = dish.ingredients.map(ing => {
                            // Если ID ингредиента есть в списке аллергенов пользователя
                            if (allergenIds.includes(ing.id)) {
                                isDangerous = true;
                                return `<span style="color: #d32f2f; font-weight: bold;">${ing.name} (Аллерген!)</span>`;
                            }
                            return ing.name;
                        }).join(', ');
                    }

                    // Стили для опасного блюда
                    const cardStyle = isDangerous ? 'border: 2px solid #ef5350; background: #ffebee;' : '';
                    const warningIcon = isDangerous ? '!' : '';

                    sectionHtml += `
                    <div class="menu-dish" style="${cardStyle}">
                        <div style="flex: 1;">
                            <div class="dish-name">${warningIcon}${dish.dish_name}</div>
                            <div class="dish-details">${dish.calories} ккал | ${dish.price} ₽</div>
                            <div class="dish-details" style="font-style: italic; color: #555;">
                                Состав: ${ingredientsHtml}
                            </div>
                        </div>
                        <button class="knopka knopka-small" onclick="orderMeal(${dish.id})">Заказать</button>
                    </div>`;
                });
                return sectionHtml;
            };

            html += renderSection('Завтрак', menu.breakfast);
            html += renderSection('Обед', menu.lunch);
            
            container.innerHTML = html;
            document.getElementById('menuLoading').style.display = 'none';
        } catch(e) { 
            console.error(e);
            container.innerHTML = 'Ошибка загрузки меню'; 
        }
    }

    // ... (остальные функции: orderMeal, loadOrders, pay, reviews, allergens - без изменений) ...
</script>