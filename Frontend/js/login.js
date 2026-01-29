window.pokazat = function(formType) {
    const loginForm = document.getElementById('forma_vhoda');
    const registerForm = document.getElementById('forma_registracii');

    if (formType === 'vhod') {
        loginForm.classList.remove('forma_skryta');
        registerForm.classList.add('forma_skryta');
        clearMessages();
    } else if (formType === 'registraciya') {
        loginForm.classList.add('forma_skryta');
        registerForm.classList.remove('forma_skryta');
        clearMessages();
        loadAllergens(); // Загрузка список из DB
    }
};

function clearMessages() {
    document.querySelectorAll('.message, .error').forEach(el => {
        el.style.display = 'none';
        el.textContent = '';
    });
}

function showMessage(elementId, text, type) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = text;
        element.className = `message ${type}`;
        element.style.display = 'block';
    }
}

function showError(elementId, text) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = text;
        element.style.display = 'block';
    }
}

async function loadAllergens() {
    const container = document.getElementById('spisok_allergenov');
    const loading = document.getElementById('allergensLoading');

    if (container.children.length > 0) {
        if(loading) loading.style.display = 'none';
        container.style.display = 'grid';
        return;
    }

    try {
        const response = await fetch('/api/ingredients');
        const ingredients = await response.json();

        if (loading) loading.style.display = 'none';

        if (!ingredients || ingredients.length === 0) {
            container.innerHTML = '<p style="grid-column:1/-1; text-align:center;">Список пуст</p>';
        } else {
            container.innerHTML = ingredients.map(ing => `
                <label class="flazok">
                    <input type="checkbox" name="allergen" value="${ing.id}">
                    ${ing.name}
                </label>
            `).join('');
        }
        container.style.display = 'grid';
    } catch (error) {
        console.error('Ошибка:', error);
        if(loading) loading.innerHTML = '<p style="color:red">Ошибка загрузки</p>';
    }
}

document.addEventListener('DOMContentLoaded', () => {

    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('mode') === 'register') {
        window.pokazat('registraciya');
    }

    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = loginForm.querySelector('button');
            const originalText = btn.textContent;

            btn.textContent = "Вход...";
            btn.disabled = true;

            const username = document.getElementById('login').value.trim();
            const password = document.getElementById('parol').value;
            const nextUrl = new URLSearchParams(window.location.search).get('next');

            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        username: username,
                        password: password,
                        next_url: nextUrl
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    window.location.href = data.redirect;
                } else {
                    showMessage('loginMessage', data.message, 'error-message');
                    btn.textContent = originalText;
                    btn.disabled = false;
                }
            } catch (err) {
                showMessage('loginMessage', 'Ошибка сервера', 'error-message');
                btn.textContent = originalText;
                btn.disabled = false;
            }
        });
    }

    const regForm = document.getElementById('regForm');
    if (regForm) {
        regForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('regButton');
            const originalText = btn.textContent;

            btn.textContent = "Регистрация...";
            btn.disabled = true;

            const name = document.getElementById('imya').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('novyy_parol').value;
            const confirm = document.getElementById('povtor_parolya').value;

            if (password !== confirm) {
                showError('confirmPasswordError', 'Пароли не совпадают');
                btn.textContent = originalText;
                btn.disabled = false;
                return;
            }

            const allergens = Array.from(document.querySelectorAll('input[name="allergen"]:checked')).map(cb => parseInt(cb.value));

            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        username: name,
                        email: email,
                        password: password,
                        confirm_password: confirm,
                        allergens: allergens
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    showMessage('registerMessage', 'Успешно! Входим...', 'success');
                    setTimeout(() => window.location.href = data.redirect, 1000);
                } else {
                    showMessage('registerMessage', data.message, 'error-message');
                    btn.textContent = originalText;
                    btn.disabled = false;
                }
            } catch (err) {
                showMessage('registerMessage', 'Ошибка сети', 'error-message');
                btn.textContent = originalText;
                btn.disabled = false;
            }
        });
    }
});
