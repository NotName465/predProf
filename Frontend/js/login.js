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
        loadAllergens();
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

            container.innerHTML = ingredients.slice(0, 20).map(ing => `
                <label class="flazok">
                    <input type="checkbox" name="allergen" value="${ing.id}">
                    ${ing.name}
                </label>
            `).join('');
        }
        container.style.display = 'grid';
    } catch (error) {
        console.error('Ошибка загрузки аллергенов:', error);
        if(loading) loading.innerHTML = '<p style="color:red">Ошибка загрузки</p>';
    }
}

document.addEventListener('DOMContentLoaded', () => {


    const loginForm = document.getElementById('loginForm');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('login').value.trim();
            const password = document.getElementById('parol').value;
            const btn = loginForm.querySelector('button');
            const originalText = btn.textContent;


            clearMessages();

            if (!username || !password) {
                if (!username) showError('loginError', 'Введите логин');
                if (!password) showError('passwordError', 'Введите пароль');
                return;
            }

            btn.textContent = 'Вход...';
            btn.disabled = true;

            try {
                const nextUrl = new URLSearchParams(window.location.search).get('next');

                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: username,
                        password: password,
                        next_url: nextUrl
                    })
                });

                const data = await res.json();

                if (res.ok) {
                    showMessage('loginMessage', 'Успешно! Перенаправление...', 'success');
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 1000);
                } else {
                    showMessage('loginMessage', data.message, 'error-message');
                    btn.textContent = originalText;
                    btn.disabled = false;
                }
            } catch (err) {
                console.error(err);
                showMessage('loginMessage', 'Ошибка соединения с сервером', 'error-message');
                btn.textContent = originalText;
                btn.disabled = false;
            }
        });
    }

    const regForm = document.getElementById('regForm');

    if (regForm) {
        regForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const name = document.getElementById('imya').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('novyy_parol').value;
            const confirm = document.getElementById('povtor_parolya').value;
            const btn = document.getElementById('regButton');
            const originalText = btn.textContent;

            clearMessages();

            let hasError = false;
            if (!name) { showError('nameError', 'Введите имя'); hasError = true; }
            if (!email) { showError('emailError', 'Введите email'); hasError = true; }
            if (!password || password.length < 4) { showError('passwordErrorReg', 'Пароль мин. 4 символа'); hasError = true; }
            if (password !== confirm) { showError('confirmPasswordError', 'Пароли не совпадают'); hasError = true; }

            if (hasError) return;

            const checkedBoxes = document.querySelectorAll('input[name="allergen"]:checked');
            const allergens = Array.from(checkedBoxes).map(cb => parseInt(cb.value));

            btn.textContent = 'Регистрация...';
            btn.disabled = true;

            try {
                const res = await fetch('/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: name,
                        email: email,
                        password: password,
                        confirm_password: confirm,
                        allergens: allergens
                    })
                });

                const data = await res.json();

                if (res.ok) {
                    showMessage('registerMessage', 'Аккаунт создан! Входим...', 'success');
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 1500);
                } else {
                    showMessage('registerMessage', data.message, 'error-message');
                    btn.textContent = originalText;
                    btn.disabled = false;
                }
            } catch (err) {
                console.error(err);
                showMessage('registerMessage', 'Ошибка сети', 'error-message');
                btn.textContent = originalText;
                btn.disabled = false;
            }
        });
    }

    document.querySelectorAll('input').forEach(input => {
        input.addEventListener('input', function() {
            const errDiv = this.nextElementSibling;
            if (errDiv && errDiv.classList.contains('error')) {
                errDiv.style.display = 'none';
            }
        });
    });
});
