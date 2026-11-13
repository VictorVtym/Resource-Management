document.getElementById('employees-form').addEventListener('submit', async (event) => {
    event.preventDefault(); // Предотвращаем перезагрузку страницы

    // 1. Получаем элементы всех трёх полей
    const firstNameInput = document.getElementById('first-name-input');
    const lastNameInput = document.getElementById('last-name-input');
    const statusSelect = document.getElementById('status-select');

    // Формируем объект (Payload)
    const payload = {
        first_name: firstNameInput.value.trim(),
        // .trim() убирает случайные пробелы по краям
        last_name: lastNameInput.value.trim(),
        status: statusSelect.value
    };

    try {
        // Отправляем POST-запрос с JSON-payload
        const response = await fetch('/employees', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json' // Говорим серверу, что это JSON
            },
            body: JSON.stringify(payload) // Превращаем объект в строку JSON
        });

        if (response.ok) {
            const result = await response.json();
            // alert(`Сервер принял payload! Имя сотрудника: ${result.first_name} ${result.last_name}`);

            // 3. Очищаем сразу все поля формы
            event.target.reset();

            // 4. Запрашиваем актуальный словарь с сервера и обновляем блок
            await loadEmployees();
        } else {
            console.error('Ошибка сервера:', response.status);
        }
    } catch (error) {
        console.error('Ошибка сети:', error);
    }
});

async function loadEmployees() {
    const response = await fetch('/api/employees');
    if (!response.ok) return;

    const employeesDict = await response.json();
    const tbody = document.getElementById('employees-tbody');
    tbody.innerHTML = ''; // Очищаем старый список

    // Перебираем полученный словарь и рисуем карточки
    const entries = Object.values(employeesDict);
    if (entries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-table-msg">Сотрудников пока нет.</td></tr>';
        return;
    }

    entries.forEach(emp => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${emp.first_name} ${emp.last_name}</td>
            <td>${emp.status}</td>
            <td>${emp.base_salary}</td>
            <td>${emp.hours_plan}</td>
            <td> ${emp.hire_date}</td>
        `;
        tbody.appendChild(row);
    });
}