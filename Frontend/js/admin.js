document.addEventListener('DOMContentLoaded', () => {

    const menuToggle = document.getElementById('menuToggle');
    const leftPanel = document.getElementById('leftPanel');

    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            leftPanel.classList.toggle('open');
        });
    }

    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768) {
            if (!leftPanel.contains(e.target) && e.target !== menuToggle) {
                leftPanel.classList.remove('open');
            }
        }
    });

    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');

    tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            tabs.forEach(b => b.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');

            if (window.innerWidth <= 768) leftPanel.classList.remove('open');

            if (tabId === 'stats') loadStats();
            if (tabId === 'requests') loadRequests();
            if (tabId === 'reports') loadReports();
        });
    });

    async function loadStats() {
        const statsList = document.getElementById('statsList');
        try {
            const res = await fetch('/api/admin/stats');
            const data = await res.json();
            
            statsList.innerHTML = `
                <li>Заказов сегодня: <strong>${data.attendance_today}</strong></li>
                <li>Выручка сегодня: <strong>${data.revenue_today} ₽</strong></li>
                <li>Всего выдано (за всё время): <strong>${data.total_issued}</strong></li>
            `;
        } catch (e) {
            statsList.innerHTML = '<li style="color:red">Ошибка загрузки данных</li>';
        }
    }


    async function loadRequests() {
        const list = document.getElementById('requestsList');
        const noReq = document.getElementById('noRequests');
        
        try {
            const res = await fetch('/api/purchase_requests');
            const requests = await res.json();
            

            const pending = requests.filter(r => r.status === 'pending');

            if (pending.length === 0) {
                list.innerHTML = '';
                noReq.style.display = 'block';
                return;
            }

            noReq.style.display = 'none';
            list.innerHTML = pending.map(req => `
                <li style="margin-bottom: 12px; padding: 15px; border: 1px solid #eee; border-radius: 8px;">
                    <div style="font-weight:bold; color:#0d47a1;">${req.ingredient_name}</div>
                    <div>Количество: ${req.quantity} ${req.unit}</div>
                    <div style="font-size:12px; color:#666; margin-bottom:8px;">Запросил: ${req.requester} (${new Date(req.request_date).toLocaleDateString()})</div>
                    
                    <button style="background:#2e7d32; padding:6px 12px; font-size:14px; margin-right:5px;" 
                            onclick="updateRequest(${req.id}, 'approved')">Одобрить</button>
                    <button style="background:#c62828; padding:6px 12px; font-size:14px;" 
                            onclick="updateRequest(${req.id}, 'rejected')">Отклонить</button>
                </li>
            `).join('');
        } catch (e) { console.error(e); }
    }

    window.updateRequest = async function(id, status) {
        if (!confirm(status === 'approved' ? 'Одобрить закупку и пополнить склад?' : 'Отклонить заявку?')) return;
        
        try {
            const res = await fetch(`/api/purchase_requests/${id}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ status: status })
            });
            if (res.ok) {
                alert('Статус обновлен');
                loadRequests();
            } else alert('Ошибка');
        } catch (e) { alert('Ошибка сети'); }
    };


    async function loadReports() {
        const table = document.getElementById('reportsTable');
        try {
            const res = await fetch('/api/admin/reports');
            const reports = await res.json();
            
            if (reports.length === 0) {
                table.innerHTML = '<tr><td colspan="3" style="padding:10px;">Нет данных о продажах</td></tr>';
                return;
            }

            table.innerHTML = reports.map(r => `
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding:10px;">${r.date}</td>
                    <td style="padding:10px; font-weight:bold;">${r.revenue} ₽</td>
                    <td style="padding:10px;">${r.transactions}</td>
                </tr>
            `).join('');
        } catch (e) { console.error(e); }
    }


    loadStats();
    loadRequests();
    loadReports();
});
