document.addEventListener('DOMContentLoaded', () => {

    // --- ЛОГИКА ВХОДА (LOGIN) ---
    const loginForm = document.getElementById('loginForm');

    if (loginForm) {
        loginForm.addEventListener('submit', async function(event) {
            event.preventDefault(); // Остановить перезагрузку

            const messageBox = document.getElementById('message');
            const usernameInput = document.getElementById('username');
            const passwordInput = document.getElementById('password');

            // Проверка URL на наличие параметра ?next=/somewhere
            const urlParams = new URLSearchParams(window.location.search);
            const nextParam = urlParams.get('next');

            messageBox.textContent = 'Вход в систему...';
            messageBox.style.color = 'gray';

            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: usernameInput.value,
                        password: passwordInput.value,
                        next_url: nextParam
                    })
                });

                const result = await response.json();

                if (response.ok) {
                    messageBox.textContent = 'Успешно! Перенаправление...';
                    messageBox.style.color = 'green';

                    setTimeout(() => {
                        window.location.href = result.redirect;
                    }, 500);
                } else {
                    messageBox.textContent = result.message;
                    messageBox.style.color = 'red';
                }

            } catch (error) {
                console.error('Login Error:', error);
                messageBox.textContent = 'Ошибка соединения с сервером';
                messageBox.style.color = 'red';
            }
        });
    }

    // --- ЛОГИКА РЕГИСТРАЦИИ (REGISTER) ---
    const registerForm = document.getElementById('registerForm');

    if (registerForm) {
        registerForm.addEventListener('submit', async function(event) {
            event.preventDefault();

            const messageBox = document.getElementById('message');

            // Сбор данных из формы
            const emailVal = document.getElementById('email').value;
            const usernameVal = document.getElementById('username').value;
            const fullNameVal = document.getElementById('full_name').value;
            const passwordVal = document.getElementById('password').value;
            const confirmVal = document.getElementById('confirm_password').value;

            // Простая проверка на клиенте
            if (passwordVal !== confirmVal) {
                messageBox.textContent = 'Пароли не совпадают!';
                messageBox.style.color = 'red';
                return;
            }

            messageBox.textContent = 'Регистрация...';
            messageBox.style.color = 'gray';

            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        email: emailVal,
                        username: usernameVal,
                        full_name: fullNameVal,
                        password: passwordVal,
                        confirm_password: confirmVal
                    })
                });

                const result = await response.json();

                if (response.ok) {
                    messageBox.textContent = 'Успешно! Вход в кабинет...';
                    messageBox.style.color = 'green';

                    setTimeout(() => {
                        window.location.href = result.redirect;
                    }, 1000);
                } else {
                    messageBox.textContent = result.message;
                    messageBox.style.color = 'red';
                }

            } catch (error) {
                console.error('Register Error:', error);
                messageBox.textContent = 'Ошибка соединения с сервером';
                messageBox.style.color = 'red';
            }
        });
    }

});