document.addEventListener('DOMContentLoaded', () => {

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

    let allDishes = [];
    const mealSelect = document.getElementById('mealSelect');

    const mealInfoCard = document.getElementById('mealInfoCard');
    const mealInfoName = document.getElementById('mealInfoName');
    const mealInfoStock = document.getElementById('mealInfoStock');
    const mealInfoImage = document.getElementById('mealInfoImage');

    async function loadDishes() {
        try {
            const res = await fetch('/api/dishes');
            allDishes = await res.json();
            const html = '<option value="">-- Выберите блюдо --</option>' +
                allDishes.map(d => `<option value="${d.id}">${d.name} (${d.stock_quantity || 0} шт)</option>`).join('');
            mealSelect.innerHTML = html;
        } catch (e) { console.error(e); }
    }

    mealSelect.addEventListener('change', (e) => {
        const dish = allDishes.find(d => d.id == e.target.value);
        if (!dish) { mealInfoCard.style.display = 'none'; return; }

        mealInfoCard.style.display = 'block';
        mealInfoName.textContent = dish.name;
        mealInfoStock.textContent = dish.stock_quantity || 0;

        if(dish.image_url) mealInfoImage.style.backgroundImage = `url('${dish.image_url}')`;
        else mealInfoImage.style.background = '#eee';
    });

    const btnIssue = document.getElementById('btnIssue');
    if(btnIssue) {
        btnIssue.addEventListener('click', async () => {
            const dishId = mealSelect.value;
            const student = document.getElementById('studentId').value.trim();
            const msg = document.getElementById('issueMessage');

            if (!dishId || !student) {
                msg.textContent = "Выберите блюдо и укажите ID ученика"; msg.style.color = "red"; return;
            }

            try {
                const res = await fetch('/api/issue_meal', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ dish_id: dishId, student_identifier: student })
                });
                const data = await res.json();

                if (res.ok) {
                    msg.textContent = `Успешно: ${data.message}`;
                    msg.style.color = "green";
                    document.getElementById('studentId').value = '';
                    const dish = allDishes.find(d => d.id == dishId);
                    if(dish) {
                        dish.stock_quantity = data.new_stock;
                        mealInfoStock.textContent = data.new_stock;
                        const html = '<option value="">-- Выберите блюдо --</option>' +
                            allDishes.map(d => `<option value="${d.id}" ${d.id==dishId?'selected':''}>${d.name} (${d.stock_quantity} шт)</option>`).join('');
                        mealSelect.innerHTML = html;
                    }
                } else {
                    msg.textContent = `Ошибка: ${data.message}`;
                    msg.style.color = "red";
                }
            } catch (e) { msg.textContent = "Ошибка сервера"; msg.style.color = "red"; }
        });
    }

    window.loadInventoryData = async function() {
        try {
            const resDishes = await fetch('/api/dishes');
            const dishes = await resDishes.json();
            document.getElementById('dishesTableBody').innerHTML = dishes.map(d => `
                <tr style="${(d.stock_quantity || 0) < 10 ? 'background-color:#ffebee' : ''}">
                    <td>${d.name}</td>
                    <td style="${(d.stock_quantity || 0) < 10 ? 'color:red;font-weight:bold' : ''}">${d.stock_quantity || 0}</td>
                </tr>
            `).join('');

            const resIng = await fetch('/api/ingredients');
            const ings = await resIng.json();
            document.getElementById('ingredientsTableBody').innerHTML = ings.map(i => `
                <tr style="${i.current_quantity <= i.min_quantity ? 'background-color:#fff3e0' : ''}">
                    <td>${i.name}</td>
                    <td style="${i.current_quantity <= i.min_quantity ? 'color:red;font-weight:bold' : ''}">${i.current_quantity} ${i.unit}</td>
                    <td style="color:#777">${i.min_quantity}</td>
                </tr>
            `).join('');
        } catch (e) { console.error(e); }
    };

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
                tbody.innerHTML = requests.map(r => {
                    let statusClass = 'status-pending';
                    let statusText = 'Ожидает';
                    if (r.status === 'approved') { statusClass = 'status-approved'; statusText = 'Одобрено'; }
                    if (r.status === 'rejected') { statusClass = 'status-rejected'; statusText = 'Отклонено'; }
                    if (r.status === 'completed') { statusClass = 'status-approved'; statusText = 'Закуплено'; }

                    return `
                    <tr>
                        <td>${new Date(r.request_date).toLocaleDateString()}</td>
                        <td>${r.ingredient_name}</td>
                        <td>${r.quantity} ${r.unit}</td>
                        <td class="${statusClass}">${statusText}</td>
                    </tr>`;
                }).join('');
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
            btnRequest.textContent = 'Отправка...';

            try {
                const res = await fetch('/api/purchase_requests', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ ingredient_id: ingId, quantity: qty })
                });
                const data = await res.json();

                if (res.ok) {
                    alert(data.message);
                    document.getElementById('procurementQty').value = '';
                    loadProcurementData();
                } else {
                    alert(data.message);
                }
            } catch (e) { alert('Ошибка отправки'); }

            btnRequest.disabled = false;
            btnRequest.textContent = 'Отправить заявку';
        });
    }

    window.loadStats = async function() {
        const brIssued = document.getElementById('statIssuedBreakfast');
        const brSold = document.getElementById('statSoldBreakfast');
        const lnIssued = document.getElementById('statIssuedLunch');
        const lnSold = document.getElementById('statSoldLunch');
        const tableBody = document.getElementById('statTableBody');

        brIssued.textContent = '0';
        brSold.textContent = '0';
        lnIssued.textContent = '0';
        lnSold.textContent = '0';
        brIssued.style.opacity = 0.5;

        try {
            const res = await fetch('/api/stats/cook');
            const data = await res.json();

            if (res.ok) {
                brIssued.textContent = data.breakfast.issued;
                brSold.textContent = data.breakfast.sold;
                lnIssued.textContent = data.lunch.issued;
                lnSold.textContent = data.lunch.sold;

                if (data.breakdown && data.breakdown.length > 0) {
                    tableBody.innerHTML = data.breakdown.map(item => `
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 12px; font-weight: 500;">${item.name}</td>
                            <td style="padding: 12px; text-align: right; font-weight: bold;">${item.count}</td>
                        </tr>
                    `).join('');
                } else {
                    tableBody.innerHTML = '<tr><td colspan="2" style="padding: 15px; text-align: center; color: #777;">Пока заказов нет</td></tr>';
                }
            }
        } catch (e) {
            console.error("Ошибка статистики:", e);
        } finally {
            brIssued.style.opacity = 1;
        }
    };

    loadDishes();
});
