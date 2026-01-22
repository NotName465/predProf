document.addEventListener('DOMContentLoaded', () => {

    // --- ТАБЫ ---
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');

    tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            tabs.forEach(b => b.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');

            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');

            if (tabId === 'stats') loadStats();
            if (tabId === 'inventory') loadInventoryData();
            if (tabId === 'procurement') loadProcurementData();
        });
    });

    // --- 1. ВЫДАЧА ПИТАНИЯ (НОВАЯ ЛОГИКА) ---
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
                    if (data.orders.length === 0) {
                        resultDiv.innerHTML = `<p style="text-align:center;">У ученика <strong>${data.student_name}</strong> нет активных заказов на сегодня.</p>`;
                    } else {
                        let html = `<h3 style="color:#0d47a1; margin-bottom:15px;">Заказы ученика: ${data.student_name}</h3>`;
                        data.orders.forEach(order => {
                            const mealType = order.meal_type === 'breakfast' ? 'Завтрак' : 'Обед';
                            const bgImage = order.image_url ? `url('${order.image_url}')` : '';
                            const bgStyle = bgImage ? `background-image: ${bgImage}` : 'background-color: #eee';

                            html += `
                            <div class="dish-card">
                                <div class="dish-header">
                                    <div class="dish-img" style="${bgStyle}"></div>
                                    <div>
                                        <h3 style="margin:0 0 5px; color:#1565C0;">${order.dish_name}</h3>
                                        <p style="margin:3px 0;">${mealType} | ${order.calories} ккал</p>
                                    </div>
                                </div>
                                <button onclick="issueSpecificOrder(${order.id})"
                                        style="background:#28a745; margin:0; padding:10px 20px;">
                                    Выдать
                                </button>
                            </div>`;
                        });
                        resultDiv.innerHTML = html;
                    }
                } else {
                    resultDiv.innerHTML = `<p style="color:red; text-align:center;">${data.message}</p>`;
                }
            } catch (e) {
                resultDiv.innerHTML = '<p style="color:red; text-align:center;">Ошибка соединения</p>';
            }
        });
    }

    // Глобальная функция для кнопки "Выдать" внутри HTML
    window.issueSpecificOrder = async function(orderId) {
        if (!confirm('Подтвердить выдачу?')) return;

        try {
            const res = await fetch('/api/cook/finish_order', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ order_id: orderId })
            });
            const data = await res.json();

            if (res.ok) {
                alert(data.message);
                // Повторяем поиск, чтобы обновить список
                btnSearch.click();
            } else {
                alert(data.message);
            }
        } catch (e) { alert('Ошибка сети'); }
    };


    // --- 2. СКЛАД (С ПОДДЕРЖКОЙ +, -) ---
    window.loadInventoryData = async function() {
        try {
            // Блюда
            const resDishes = await fetch('/api/dishes');
            const dishes = await resDishes.json();
            const dishesBody = document.getElementById('dishesTableBody');

            if (dishesBody) {
                dishesBody.innerHTML = dishes.map(d => `
                    <tr id="dish-row-${d.id}" style="${(d.stock_quantity || 0) < 10 ? 'background-color:#ffebee' : ''}">
                        <td>${d.name}</td>
                        <td class="stock-cell" data-val="${d.stock_quantity}">${d.stock_quantity || 0}</td>
                        <td style="color:#1976D2; font-weight:bold;">${d.reserved || 0}</td>
                        <td>
                            <button class="edit-btn" style="padding:4px 8px; font-size:12px; background:#2196F3;"
                                    onclick="toggleEdit(${d.id}, 'dish', this)">Изм.</button>
                        </td>
                    </tr>
                `).join('');
            }

            // Ингредиенты
            const resIng = await fetch('/api/ingredients');
            const ings = await resIng.json();
            const ingBody = document.getElementById('ingredientsTableBody');

            if (ingBody) {
                ingBody.innerHTML = ings.map(i => `
                    <tr id="ing-row-${i.id}" style="${i.current_quantity <= i.min_quantity ? 'background-color:#fff3e0' : ''}">
                        <td>${i.name}</td>
                        <td class="stock-cell" data-val="${i.current_quantity}">
                            ${i.current_quantity} ${i.unit}
                        </td>
                        <td class="min-cell" data-val="${i.min_quantity}">${i.min_quantity}</td>
                        <td>
                            <button class="edit-btn" style="padding:4px 8px; font-size:12px; background:#FF9800;"
                                    onclick="toggleEdit(${i.id}, 'ingredient', this)">Изм.</button>
                        </td>
                    </tr>
                `).join('');
            }
        } catch (e) { console.error(e); }
    };

    // ФУНКЦИЯ РЕДАКТИРОВАНИЯ
    function safeEvaluate(str) {
        const sanitized = str.replace(/[^0-9+\-.\s]/g, '');
        if (!sanitized) return NaN;
        try { return new Function('return ' + sanitized)(); } catch (e) { return NaN; }
    }

    window.toggleEdit = async function(id, type, btn) {
        const row = document.getElementById(type === 'dish' ? `dish-row-${id}` : `ing-row-${id}`);
        const stockCell = row.querySelector('.stock-cell');
        const minCell = row.querySelector('.min-cell');

        if (btn.textContent === 'Сохр.') {
            const stockInput = stockCell.querySelector('input');
            const finalStock = safeEvaluate(stockInput.value);

            let finalMin = null;
            if (minCell) {
                finalMin = safeEvaluate(minCell.querySelector('input').value);
            }

            if (isNaN(finalStock) || (minCell && isNaN(finalMin))) {
                alert('Ошибка в числах'); return;
            }
            if (finalStock < 0) { alert('Не может быть меньше 0'); return; }

            try {
                const payload = { id, type, quantity: finalStock };
                if (finalMin !== null) payload.min_quantity = finalMin;

                const res = await fetch('/api/inventory/update', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    loadInventoryData();
                } else alert('Ошибка');
            } catch (e) { alert('Ошибка сети'); }

        } else {
            const currentStock = parseFloat(stockCell.dataset.val);
            stockCell.innerHTML = `<input type="text" value="${currentStock}" style="width:80px; padding:4px;">`;

            if (minCell) {
                const currentMin = parseFloat(minCell.dataset.val);
                minCell.innerHTML = `<input type="text" value="${currentMin}" style="width:60px; padding:4px;">`;
            }

            btn.textContent = 'Сохр.';
            btn.style.backgroundColor = '#4CAF50';
        }
    };

    // --- 3. ЗАКУПКИ ---
    async function loadProcurementData() {
        try {
            const resIng = await fetch('/api/ingredients');
            const ings = await resIng.json();
            const select = document.getElementById('procurementSelect');
            select.innerHTML = '<option value="">-- Выберите продукт --</option>' +
                ings.map(i => `<option value="${i.id}">${i.name} (сейчас: ${i.current_quantity} ${i.unit})</option>`).join('');

            const resReq = await fetch('/api/purchase_requests');
            const requests = await resReq.json();
            const tbody = document.getElementById('requestsTableBody');

            if (requests.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">История пуста</td></tr>';
            } else {
                tbody.innerHTML = requests.map(r => `
                    <tr>
                        <td>${new Date(r.request_date).toLocaleDateString()}</td>
                        <td>${r.ingredient_name}</td>
                        <td>${r.quantity} ${r.unit}</td>
                        <td class="${r.status === 'approved' ? 'status-approved' : r.status === 'rejected' ? 'status-rejected' : 'status-pending'}">
                            ${r.status === 'approved' ? 'Одобрено' : r.status === 'rejected' ? 'Отклонено' : 'Ожидает'}
                        </td>
                    </tr>`).join('');
            }
        } catch (e) { console.error(e); }
    }

    const btnRequest = document.getElementById('btnRequest');
    if (btnRequest) {
        btnRequest.addEventListener('click', async () => {
            const ingId = document.getElementById('procurementSelect').value;
            const qty = document.getElementById('procurementQty').value;
            if (!ingId || !qty) { alert('Заполните все поля'); return; }

            btnRequest.disabled = true;
            try {
                const res = await fetch('/api/purchase_requests', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ ingredient_id: ingId, quantity: qty })
                });
                if (res.ok) {
                    alert('Заявка отправлена');
                    document.getElementById('procurementQty').value = '';
                    loadProcurementData();
                } else alert('Ошибка');
            } catch (e) { alert('Ошибка сети'); }
            btnRequest.disabled = false;
        });
    }

    // --- 4. СТАТИСТИКА ---
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
                tableBody.innerHTML = data.breakdown.length ? data.breakdown.map(i => `
                    <tr style="border-bottom:1px solid #eee;">
                        <td style="padding:12px;">${i.name}</td>
                        <td style="padding:12px;text-align:right;">${i.count}</td>
                    </tr>`).join('') : '<tr><td colspan="2" style="text-align:center;">Нет данных</td></tr>';
            }
        } catch (e) { console.error(e); } finally { brIssued.style.opacity = 1; }
    };

    // Загрузка
    // loadDishes() больше не нужен при старте, так как мы не заполняем селект
});
