document.addEventListener('DOMContentLoaded', () => {

    // --- ЛОГИКА ТАБОВ ---
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');

    tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            tabs.forEach(b => b.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });

    // --- ПЕРЕМЕННЫЕ ---
    let allDishes = [];
    const mealSelect = document.getElementById('mealSelect');
    const inventorySelect = document.getElementById('inventorySelect');

    // Элементы карточки ВЫДАЧИ
    const mealInfoCard = document.getElementById('mealInfoCard');
    const mealInfoName = document.getElementById('mealInfoName');
    const mealInfoStock = document.getElementById('mealInfoStock');
    const mealInfoCalories = document.getElementById('mealInfoCalories');
    const mealInfoImage = document.getElementById('mealInfoImage');
    const mealInfoIng = document.getElementById('mealInfoIng');

    // Элементы карточки СКЛАДА
    const dishCard = document.getElementById('dishCard');
    const cardName = document.getElementById('cardName');
    const cardStock = document.getElementById('cardStock');
    const cardCalories = document.getElementById('cardCalories');
    const cardImage = document.getElementById('cardImage');
    const cardIngredients = document.getElementById('cardIngredients');

    // --- ЗАГРУЗКА ДАННЫХ ---
    async function loadDishes() {
        try {
            const res = await fetch('/api/dishes');
            if (res.ok) {
                allDishes = await res.json();
                updateDropdowns();
            }
        } catch (e) { console.error("Ошибка загрузки:", e); }
    }

    function updateDropdowns() {
        const savedMeal = mealSelect.value;
        const savedInv = inventorySelect.value;

        const html = '<option value="">-- Выберите блюдо --</option>' +
            allDishes.map(d => `<option value="${d.id}">${d.name} (${d.stock_quantity} шт)</option>`).join('');

        mealSelect.innerHTML = html;
        inventorySelect.innerHTML = html;

        mealSelect.value = savedMeal;
        inventorySelect.value = savedInv;
    }

    loadDishes();

    // --- ПОКАЗ КАРТОЧКИ ---
    function showCard(dishId, isIssue) {
        const dish = allDishes.find(d => d.id == dishId);
        const card = isIssue ? mealInfoCard : dishCard;

        if (!dish) { card.style.display = 'none'; return; }
        card.style.display = 'block';

        if (isIssue) {
            mealInfoName.textContent = dish.name;
            mealInfoStock.textContent = dish.stock_quantity;
            mealInfoCalories.textContent = dish.calories;
            mealInfoIng.textContent = dish.ingredients.join(', ');
            if(dish.image_url) mealInfoImage.style.backgroundImage = `url('${dish.image_url}')`;
            else mealInfoImage.style.background = '#eee';
        } else {
            cardName.textContent = dish.name;
            cardStock.textContent = dish.stock_quantity;
            cardCalories.textContent = dish.calories;
            cardIngredients.innerHTML = dish.ingredients.map(i => `<li>${i}</li>`).join('');
            if(dish.image_url) cardImage.style.backgroundImage = `url('${dish.image_url}')`;
            else cardImage.style.background = '#eee';
        }
    }

    mealSelect.addEventListener('change', (e) => showCard(e.target.value, true));
    inventorySelect.addEventListener('change', (e) => showCard(e.target.value, false));

    // --- ВЫДАЧА ПИТАНИЯ ---
    const btnIssue = document.getElementById('btnIssue');
    const msg = document.getElementById('issueMessage');
    const studentInp = document.getElementById('studentId');

    btnIssue.addEventListener('click', async () => {
        const dishId = mealSelect.value;
        const student = studentInp.value.trim();

        if (!dishId || !student) {
            msg.textContent = "⚠️ Выберите блюдо и введите ученика!";
            msg.style.color = "#d32f2f";
            return;
        }

        msg.textContent = "⏳ Обработка...";
        msg.style.color = "gray";

        try {
            const res = await fetch('/api/issue_meal', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ dish_id: dishId, student_identifier: student })
            });
            const data = await res.json();

            if (res.ok) {
                msg.textContent = `✅ ${data.message}`;
                msg.style.color = "#388e3c";
                studentInp.value = '';

                const dish = allDishes.find(d => d.id == dishId);
                if (dish) {
                    dish.stock_quantity = data.new_stock;
                    updateDropdowns();
                    showCard(dishId, true);
                    mealSelect.value = dishId;
                }
            } else {
                msg.textContent = `❌ ${data.message}`;
                msg.style.color = "#d32f2f";
            }
        } catch (e) {
            msg.textContent = "❌ Ошибка соединения";
            msg.style.color = "#d32f2f";
        }
    });
});
