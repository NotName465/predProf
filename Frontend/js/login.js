function pokazat(forma) {
    const vhod = document.getElementById('forma_vhoda');
    const registraciya = document.getElementById('forma_registracii');
    if (forma === 'vhod') {
        vhod.classList.remove('forma_skryta');
        registraciya.classList.add('forma_skryta');
    } else if (forma === 'registraciya') {
        registraciya.classList.remove('forma_skryta');
        vhod.classList.add('forma_skryta');
    }
}

document.addEventListener('DOMContentLoaded', () => {

    // --- ЛОГИКА ВХОДА (Остается прежней) ---
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = loginForm.querySelector('button');
            const oldText = btn.textContent;
            btn.textContent = "Вход...";
            btn.disabled = true;

            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        username: document.getElementById('login').value,
                        password: document.getElementById('parol').value,
                        next_url: new URLSearchParams(window.location.search).get('next')
                    })
                });
                const data = await res.json();
                if (res.ok) window.location.href = data.redirect;
                else { alert(data.message); btn.textContent = oldText; btn.disabled = false; }
            } catch (err) { alert("Ошибка сети"); btn.textContent = oldText; btn.disabled = false; }
        });
    }

    // --- ЛОГИКА РЕГИСТРАЦИИ (ОБНОВЛЕННАЯ) ---
    const regForm = document.getElementById('regForm');
    if (regForm) {
        regForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = regForm.querySelector('button');
            const oldText = btn.textContent;
            btn.textContent = "Регистрация...";
            btn.disabled = true;

            const name = document.getElementById('imya').value;
            const email = document.getElementById('email').value;
            const pass = document.getElementById('novyy_parol').value;

            // СБОР АЛЛЕРГЕНОВ
            // Находим все отмеченные чекбоксы с именем "allergen"
            const checkboxes = document.querySelectorAll('input[name="allergen"]:checked');
            let selectedAllergens = [];
            checkboxes.forEach((cb) => {
                selectedAllergens.push(cb.value);
            });

            try {
                const res = await fetch('/api/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        username: name,
                        email: email,
                        password: pass,
                        confirm_password: pass,
                        allergens: selectedAllergens // <-- ОТПРАВЛЯЕМ МАССИВ
                    })
                });
                const data = await res.json();

                if (res.ok) {
                    alert("Регистрация успешна!");
                    window.location.href = data.redirect;
                } else {
                    alert(data.message);
                    btn.textContent = oldText;
                    btn.disabled = false;
                }
            } catch (err) {
                console.error(err);
                alert("Ошибка сети");
                btn.textContent = oldText;
                btn.disabled = false;
            }
        });
    }
});
