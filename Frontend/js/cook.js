
let issuedMeals = JSON.parse(localStorage.getItem('issuedMeals')) || [];
let inventory = JSON.parse(localStorage.getItem('inventory')) || {
    "Молоко (л)": 100,
    "Хлеб (буханки)": 50,
    "Яйца (шт)": 200,
    "Курица (кг)": 30,
    "Рис (кг)": 40
};
let purchaseRequests = JSON.parse(localStorage.getItem('purchaseRequests')) || [];


const mealsList = [
    { id: '1', name: "Каша овсяная с молоком", type: "breakfast", consumes: { "Молоко (л)": 0.2, "Овсянка (кг)": 0.05 } },
    { id: '2', name: "Суп куриный с лапшой", type: "lunch", consumes: { "Курица (кг)": 0.1, "Лапша (кг)": 0.05 } },
    { id: '3', name: "Плов с курицей", type: "lunch", consumes: { "Курица (кг)": 0.15, "Рис (кг)": 0.1 } }
];

mealsList.forEach(meal => {
    for (const product in meal.consumes) {
        if (!(product in inventory)) {
            inventory[product] = 0;
        }
    }
});
saveData();


function saveData() {
    localStorage.setItem('issuedMeals', JSON.stringify(issuedMeals));
    localStorage.setItem('inventory', JSON.stringify(inventory));
    localStorage.setItem('purchaseRequests', JSON.stringify(purchaseRequests));
}

function showMessage(text, isSuccess = false) {
    const msg = document.createElement('div');
    msg.className = isSuccess ? 'flash success' : 'flash error';
    msg.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${isSuccess ? '#d4edda' : '#f8d7da'};
        color: ${isSuccess ? '#155724' : '#721c24'};
        border: 1px solid ${isSuccess ? '#c3e6cb' : '#f5c6cb'};
        border-radius: 6px;
        z-index: 1000;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    `;
    msg.textContent = text;
    document.body.appendChild(msg);
    setTimeout(() => msg.remove(), 5000);
}

function getCurrentDate() {
    return new Date().toISOString().split('T')[0];
}

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        btn.classList.add('active');
        const tabId = btn.getAttribute('data-tab');
        document.getElementById(tabId).classList.add('active');


        if (tabId === 'inventory') renderInventory();
        if (tabId === 'stats') renderStats();
    });
});

function issueMeal() {
    const studentIdInput = document.getElementById('studentId');
    const studentId = studentIdInput.value.trim();
    const mealSelect = document.getElementById('mealSelect') || { value: '1' };
    const mealId = mealSelect.value;

    if (!studentId || isNaN(studentId)) {
        showMessage('Введите корректный ID ученика');
        return;
    }

    const today = getCurrentDate();
    const alreadyIssued = issuedMeals.some(record =>
        record.studentId == studentId && record.date === today
    );

    if (alreadyIssued) {
        showMessage('Этому ученику сегодня уже выдано питание!', false);
        return;
    }

    const meal = mealsList.find(m => m.id === mealId);
    let canIssue = true;
    if (meal && meal.consumes) {
        for (const [product, needed] of Object.entries(meal.consumes)) {
            if ((inventory[product] || 0) < needed) {
                canIssue = false;
                showMessage(`Недостаточно "${product}" для приготовления "${meal.name}"`, false);
                break;
            }
        }
    }

    if (!canIssue) return;

    if (meal && meal.consumes) {
        for (const [product, needed] of Object.entries(meal.consumes)) {
            inventory[product] = (inventory[product] || 0) - needed;
        }
    }

    issuedMeals.push({
        studentId: parseInt(studentId),
        mealId: mealId,
        date: today,
        timestamp: new Date().toISOString()
    });

    saveData();
    showMessage(`Питание "${meal?.name || 'неизвестное'}" выдано ученику №${studentId}!`, true);
    studentIdInput.value = '';
    renderInventory();
}

function renderInventory() {
    const container = document.getElementById('inventory');
    if (!container) return;

    container.innerHTML = `
        <h2>Остатки продуктов</h2>
        <ul id="inventoryList" style="list-style-type: disc; padding-left: 20px;"></ul>
        <hr style="margin: 20px 0;">
        <h3>Подать заявку на закупку</h3>
        <label>Продукт: <input type="text" id="reqProduct" placeholder="Например: Молоко (л)"></label><br>
        <label>Количество: <input type="number" id="reqQuantity" min="1" placeholder="10"></label><br>
        <button onclick="submitPurchaseRequest()">Отправить заявку</button>
    `;

    const list = document.getElementById('inventoryList');
    for (const [product, qty] of Object.entries(inventory)) {
        const li = document.createElement('li');
        li.textContent = `${product}: ${qty.toFixed(2)} ед.`;
        list.appendChild(li);
    }
}
function submitPurchaseRequest() {
    const product = document.getElementById('reqProduct').value.trim();
    const qty = parseFloat(document.getElementById('reqQuantity').value);

    if (!product || isNaN(qty) || qty <= 0) {
        showMessage('Заполните все поля корректно', false);
        return;
    }

    purchaseRequests.push({
        id: Date.now(),
        product: product,
        quantity: qty,
        status: 'pending',
        createdAt: new Date().toISOString()
    });

    saveData();
    showMessage(`Заявка на "${product}" (${qty} ед.) отправлена администратору!`, true);
    document.getElementById('reqProduct').value = '';
    document.getElementById('reqQuantity').value = '';
}

// === Вкладка: Статистика ===
function renderStats() {
    const container = document.getElementById('stats');
    if (!container) return;

    const today = getCurrentDate();
    const totalIssued = issuedMeals.length;
    const todayIssued = issuedMeals.filter(r => r.date === today).length;

    const breakfasts = issuedMeals.filter(r => mealsList.find(m => m.id === r.mealId)?.type === 'breakfast').length;
    const lunches = issuedMeals.filter(r => mealsList.find(m => m.id === r.mealId)?.type === 'lunch').length;

    container.innerHTML = `
        <h2>Статистика</h2>
        <p><strong>Всего выдано порций:</strong> ${totalIssued}</p>
        <p><strong>Сегодня выдано:</strong> ${todayIssued}</p>
        <p><strong>Завтраков:</strong> ${breakfasts}</p>
        <p><strong>Обедов:</strong> ${lunches}</p>
    `;
}


document.addEventListener('DOMContentLoaded', () => {

    const mealsTab = document.getElementById('meals');
    if (mealsTab && !document.getElementById('mealSelect')) {
        let selectHtml = '<label>Блюдо: <select id="mealSelect">';
        mealsList.forEach(meal => {
            selectHtml += `<option value="${meal.id}">${meal.name} (${meal.type === 'breakfast' ? 'завтрак' : 'обед'})</option>`;
        });
        selectHtml += '</select></label><br>';
        const p = mealsTab.querySelector('p');
        if (p) p.insertAdjacentHTML('afterend', selectHtml);
    }


    const issueBtn = document.querySelector('#meals button[onclick="alert(\'Питание выдано!\')"]');
    if (issueBtn) {
        issueBtn.onclick = issueMeal;
        issueBtn.textContent = 'Выдать';
    }


    renderInventory();
    renderStats();
});