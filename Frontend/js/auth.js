document.addEventListener('DOMContentLoaded', () => {

    // LOGIN
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const msg = document.getElementById('message');
            // Backend ждет поле username, даже если это email
            const user = document.getElementById('username') || document.getElementById('email');
            const pass = document.getElementById('password');
            const next = new URLSearchParams(window.location.search).get('next');

            msg.textContent = "Вход...";
            msg.style.color = "gray";

            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        username: user.value,
                        password: pass.value,
                        next_url: next
                    })
                });
                const data = await res.json();

                if (res.ok) {
                    msg.textContent = "Успешно!";
                    msg.style.color = "green";
                    window.location.href = data.redirect;
                } else {
                    msg.textContent = data.message;
                    msg.style.color = "red";
                }
            } catch (e) { console.error(e); }
        });
    }

    // REGISTER
    const regForm = document.getElementById('registerForm');
    if (regForm) {
        regForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const msg = document.getElementById('message');
            const email = document.getElementById('email').value;
            const user = document.getElementById('username').value;
            const pass = document.getElementById('password').value;
            const conf = document.getElementById('confirm_password').value;

            if (pass !== conf) {
                msg.textContent = "Пароли не совпадают";
                msg.style.color = "red";
                return;
            }

            msg.textContent = "Регистрация...";

            try {
                const res = await fetch('/api/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ email, username: user, password: pass, confirm_password: conf })
                });
                const data = await res.json();

                if (res.ok) {
                    msg.textContent = "Готово!";
                    msg.style.color = "green";
                    setTimeout(() => window.location.href = data.redirect, 1000);
                } else {
                    msg.textContent = data.message;
                    msg.style.color = "red";
                }
            } catch (e) { console.error(e); }
        });
    }
});
