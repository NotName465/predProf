document.addEventListener('DOMContentLoaded', () => {

    // Переключение вкладок
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');

    tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            tabs.forEach(b => b.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');

            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');

            // Подтягиваем данные
            if (tabId === 'stats') loadStats();
            if (tabId === 'inventory') loadInventoryData();
            if (tabId === 'procurement') loadProcurementData();
            if (tabId === 'menu') {
                loadDishesForMenu();
                loadMenuEditor();
            }
        });
    });

    let allDishes = [];
    const mealSelect = document.getElementById('mealSelect');
    const mealInfoCard = document.getElementById('mealInfoCard');
    const mealInfoName = document.getElementById('mealInfoName');
    const mealInfoStock = document.getElementById('mealInfoStock');
    const mealInfoImage = document.getElementById('mealInfoImage');

    const btnSearch = document.getElementById('btnSearchOrders');
    const inputSearch = document.getElementById('studentSearchInput');
    const resultDiv = document.getElementById('studentOrdersResult');

    if (btnSearch) {
        btnSearch.addEventListener('click', async () => {
            const ident = inputSearch.value.trim();
            if (!ident) {
                resultDiv.innerHTML = '<p style="color:red; text-align:center;">Введите ID или имя!</p>';
                return;
            }
            resultDiv.innerHTML = '<p style="text-align:center;">Поиск...</p>';

            try {
                const res = await fetch('/api/cook/check_orders', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ student_identifier: ident })
                });
                const data = await res.json();

                if (res.ok) {
                    if (!data.orders || !data.orders.length) {
                        resultDiv.innerHTML = `<p style="text-align:center;">У <strong>${data.student_name}</strong> нет заказов.</p>`;
                    } else {
                        let html = `<h3 style="color:#0d47a1; margin-bottom:15px;">Заказы: ${data.student_name}</h3>`;
                        data.orders.forEach(order => {
                            const bg = order.image_url ? `url('${order.image_url}')` : '';
                            html += `
                            <div class="dish-card" style="display:flex; align-items:center; margin-bottom:10px;">
                                <div class="dish-img" style="background-image:${bg}; background-color:#eee;"></div>
                                <div style="flex:1; margin-left:15px;">
                                    <h3 style="margin:0 0 5px; color:#1565C0;">${order.dish_name}</h3>
                                    <p style="margin:0;">${order.meal_type==='breakfast'?'Завтрак':'Обед'} | ${order.calories} ккал</p>
                                </div>
                                <button onclick="issueSpecificOrder(${order.id})" style="background:#28a745; margin:0; padding:10px 20px;">Выдать</button>
                            </div>`;
                        });
                        resultDiv.innerHTML = html;
                    }
                } else {
                    resultDiv.innerHTML = `<p style="color:red; text-align:center;">${data.message}</p>`;
                }
            } catch (e) {
                resultDiv.innerHTML = '<p style="color:red;">Ошибка</p>';
            }
        });
    }

    // Выдача конкретного заказа
    window.issueSpecificOrder = async function(orderId) {
        if (!confirm('Выдать?')) return;
        try {
            const res = await fetch('/api/cook/finish_order', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ order_id: orderId })
            });
            if (res.ok) {
                alert('Выдано!');
                btnSearch.click(); // Перезагружаем список
            } else {
                alert('Ошибка');
            }
        } catch (e) {
            alert('Ошибка сети');
        }
    };

    // --- БЛОК РАБОТЫ С МЕНЮ ---
    const dateInput = document.getElementById('menuDate');
    if (dateInput) dateInput.valueAsDate = new Date();

    // Загрузка списка блюд для выпадающего списка
    async function loadDishesForMenu() {
        const select = document.getElementById('menuDishSelect');
        if (!select || select.children.length > 1) return;
        try {
            const res = await fetch('/api/dishes');
            const dishes = await res.json();
            select.innerHTML = '<option value="">-- Выберите блюдо --</option>' +
                dishes.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
        } catch (e) {
            console.error('Ошибка загрузки блюд:', e);
        }
    }

    // Загрузка меню на выбранную дату
    window.loadMenuEditor = async function() {
        const date = document.getElementById('menuDate').value;
        const container = document.getElementById('menuListContainer');
        container.innerHTML = '<p>Загрузка...</p>';
        try {
            const res = await fetch(`/api/menu/full?date=${date}`);
            const menu = await res.json();
            if (!menu.length) {
                container.innerHTML = '<p style="color:#777; text-align:center;">Меню пустое</p>';
                return;
            }

            const bf = menu.filter(i => i.meal_type === 'breakfast');
            const ln = menu.filter(i => i.meal_type === 'lunch');
            let html = '';
            if (bf.length) html += '<h4 style="color:#1976D2; margin:15px 0 5px;">Завтрак</h4>' + renderMenuTable(bf);
            if (ln.length) html += '<h4 style="color:#388E3C; margin:15px 0 5px;">Обед</h4>' + renderMenuTable(ln);
            container.innerHTML = html;
        } catch (e) {
            container.innerHTML = 'Ошибка загрузки меню';
        }
    };

    // Формирование таблицы для отображения пунктов меню
    function renderMenuTable(items) {
        return `<table class="accounting-table" style="margin-bottom:10px;">
            <thead>
                <tr><th>Блюдо</th><th>Действие</th></tr>
            </thead>
            <tbody>
                ${items.map(i => `
                    <tr>
                        <td>${i.dish_name}</td>
                        <td>
                            <button style="background:#c62828; padding:4px 8px; font-size:12px; margin:0;"
                                    onclick="deleteMenuItem(${i.id})">Удалить</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>`;
    }

    // Добавление блюда в меню
    window.addMenuItem = async function() {
        const date = document.getElementById('menuDate').value;
        const type = document.getElementById('menuMealType').value;
        const id = document.getElementById('menuDishSelect').value;
        if (!id) return alert('Выберите блюдо');
        await fetch('/api/menu/add', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({date, meal_type:type, dish_id:id})
        });
        loadMenuEditor();
    };

    // Удаление блюда из меню
    window.deleteMenuItem = async function(id) {
        if(confirm('Удалить?')) {
            await fetch(`/api/menu/delete/${id}`, { method:'DELETE'});
            loadMenuEditor();
        }
    };

    // Учёт
    window.loadInventoryData = async function() {
        try {
            // Загрузка блюд
            const resDishes = await fetch('/api/dishes');
            const dishes = await resDishes.json();
            const dBody = document.getElementById('dishesTableBody');
            if (dBody) dBody.innerHTML = dishes.map(d => `
                <tr id="dish-row-${d.id}" style="${(d.stock_quantity||0) < 10 ? 'background-color:#ffebee' : ''}">
                    <td>${d.name}</td>
                    <td class="stock-cell" data-val="${d.stock_quantity}">${d.stock_quantity||0}</td>
                    <td style="color:#1976D2; font-weight:bold;">${d.reserved||0}</td>
                    <td><button class="edit-btn" style="padding:4px 8px; font-size:12px; background:#2196F3;"
                            onclick="toggleEdit(${d.id}, 'dish', this)">Изм.</button></td>
                </tr>`).join('');

            // Загрузка ингредиентов
            const resIng = await fetch('/api/ingredients');
            const ings = await resIng.json();
            const iBody = document.getElementById('ingredientsTableBody');
            if (iBody) iBody.innerHTML = ings.map(i => `
                <tr id="ing-row-${i.id}" style="${i.current_quantity <= i.min_quantity ? 'background-color:#fff3e0' : ''}">
                    <td>${i.name}</td>
                    <td class="stock-cell" data-val="${i.current_quantity}">${i.current_quantity} ${i.unit}</td>
                    <td class="min-cell" data-val="${i.min_quantity}">${i.min_quantity}</td>
                    <td><button class="edit-btn" style="padding:4px 8px; font-size:12px; background:#FF9800;"
                            onclick="toggleEdit(${i.id}, 'ingredient', this)">Изм.</button></td>
                </tr>`).join('');
        } catch (e) {
            console.error('Ошибка загрузки данных склада:', e);
        }
    };

    // Мат выражения
    function safeEvaluate(str) {
        const sanitized = str.replace(/[^0-9+\-.\s]/g, '');
        if (!sanitized) return NaN;
        try {
            return new Function('return ' + sanitized)();
        } catch (e) {
            return NaN;
        }
    }

    window.toggleEdit = async function(id, type, btn) {
        const row = document.getElementById(type === 'dish' ? `dish-row-${id}` : `ing-row-${id}`);
        const stockCell = row.querySelector('.stock-cell');
        const minCell = row.querySelector('.min-cell');

        if (btn.textContent === 'Сохр.') {
            const stockInput = stockCell.querySelector('input');
            const finalStock = safeEvaluate(stockInput.value);
            let finalMin = null;
            if (minCell) finalMin = safeEvaluate(minCell.querySelector('input').value);

            if (isNaN(finalStock)) return alert('Ошибка в числах');
            if (finalStock < 0) return alert('Меньше 0 нельзя');

            try {
                const payload = { id, type, quantity: finalStock };
                if (finalMin !== null) payload.min_quantity = finalMin;
                const res = await fetch('/api/inventory/update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    loadInventoryData();
                    if (type === 'dish') loadDishesForMenu();
                } else {
                    alert('Ошибка сохранения');
                }
            } catch (e) {
                alert('Ошибка сети');
            }
        } else {
            const currentStock = parseFloat(stockCell.dataset.val);
            stockCell.innerHTML = `<input type="text" value="${currentStock}" style="width:70px; padding:4px;">`;
            if (minCell) {
                const currentMin = parseFloat(minCell.dataset.val);
                minCell.innerHTML = `<input type="text" value="${currentMin}" style="width:60px; padding:4px;">`;
            }
            btn.textContent = 'Сохр.';
            btn.style.backgroundColor = '#4CAF50';
        }
    };

    window.openCreateModal = async function() {
        document.getElementById('createModal').style.display = 'flex';
        window.toggleCreateFields();

        const res = await fetch('/api/ingredients');
        const ings = await res.json();
        document.getElementById('ingredientCheckboxes').innerHTML = ings.map(i => `
            <label style="display:flex; align-items:center; margin:5px 0;">
                <input type="checkbox" value="${i.id}" style="margin-right:8px;"> ${i.name}
            </label>`).join('');
    };

    window.toggleCreateFields = function() {
        const type = document.querySelector('input[name="createType"]:checked').value;
        document.getElementById('fieldsDish').style.display = type === 'dish' ? 'block' : 'none';
        document.getElementById('fieldsIngredient').style.display = type === 'dish' ? 'none' : 'block';
    };

    window.submitCreate = async function() {
        const type = document.querySelector('input[name="createType"]:checked').value;
        const name = document.getElementById('createName').value;
        const stock = document.getElementById('createStock').value;
        if (!name) return alert('Название обязательно');

        const formData = new FormData();
        formData.append('type', type);
        formData.append('name', name);
        formData.append('stock', stock);

        if (type === 'dish') {
            formData.append('calories', document.getElementById('createCals').value || 0);
            formData.append('price', document.getElementById('createPrice').value || 0);
            const file = document.getElementById('createImage').files[0];
            if (file) formData.append('image', file);
            const boxes = document.querySelectorAll('#ingredientCheckboxes input:checked');
            const ingIds = Array.from(boxes).map(c => parseInt(c.value));
            formData.append('ingredients', JSON.stringify(ingIds));
        } else {
            formData.append('unit', document.getElementById('createUnit').value);
            formData.append('min_quantity', document.getElementById('createMinQty').value || 0);
        }

        try {
            const res = await fetch('/api/inventory/create_item', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (res.ok) {
                alert('Создано!');
                document.getElementById('createModal').style.display = 'none';
                document.getElementById('createName').value = '';
                loadInventoryData();
                if(type === 'dish') loadDishesForMenu();
            } else {
                alert(data.message);
            }
        } catch (e) {
            alert('Ошибка при создании');
        }
    };

    //Заявки на закупку
    async function loadProcurementData() {
        try {
            // Загрузка ингредиентов для выбора
            const resIng = await fetch('/api/ingredients');
            const ings = await resIng.json();
            document.getElementById('procurementSelect').innerHTML =
                '<option value="">-- Продукт --</option>' +
                ings.map(i => `<option value="${i.id}">${i.name} (сейчас: ${i.current_quantity} ${i.unit})</option>`).join('');

            // Загрузка истории заявок
            const resReq = await fetch('/api/purchase_requests');
            const requests = await resReq.json();
            document.getElementById('requestsTableBody').innerHTML = requests.length ?
                requests.map(r => `
                    <tr>
                        <td>${new Date(r.request_date).toLocaleDateString()}</td>
                        <td>${r.ingredient_name}</td>
                        <td>${r.quantity} ${r.unit}</td>
                        <td class="status-${r.status}">${r.status === 'pending' ? 'Ожидает' : r.status}</td>
                    </tr>
                `).join('') : '<tr><td colspan="4">Пусто</td></tr>';
        } catch (e) {
            console.error('Ошибка загрузки заявок:', e);
        }
    }

    if(document.getElementById('btnRequest')) {
        document.getElementById('btnRequest').addEventListener('click', async () => {
            const id = document.getElementById('procurementSelect').value;
            const qty = document.getElementById('procurementQty').value;
            if(!id || !qty) return alert('Заполните поля');

            await fetch('/api/purchase_requests', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({ingredient_id:id, quantity:qty})
            });
            alert('Отправлено');
            loadProcurementData();
        });
    }

    // Статистика
    window.loadStats = async function() {
        const brIssued = document.getElementById('statIssuedBreakfast');
        const brSold = document.getElementById('statSoldBreakfast');
        const lnIssued = document.getElementById('statIssuedLunch');
        const lnSold = document.getElementById('statSoldLunch');
        const tableBody = document.getElementById('statTableBody');

        brIssued.style.opacity = 0.5;
        try {
            const res = await fetch('/api/stats/cook');
            const data = await res.json();
            if (res.ok) {
                brIssued.textContent = data.breakfast.issued;
                brSold.textContent = data.breakfast.sold;
                lnIssued.textContent = data.lunch.issued;
                lnSold.textContent = data.lunch.sold;
                tableBody.innerHTML = data.breakdown.length ?
                    data.breakdown.map(i => `
                        <tr style="border-bottom:1px solid #eee;">
                            <td style="padding:12px;">${i.name}</td>
                            <td style="padding:12px;text-align:right;">${i.count}</td>
                        </tr>
                    `).join('') : '<tr><td colspan="2" style="text-align:center;">Нет данных</td></tr>';
            }
        } catch (e) {
            console.error('Ошибка загрузки статистики:', e);
        } finally {
            brIssued.style.opacity = 1;
        }
    };

    loadInventoryData();
});