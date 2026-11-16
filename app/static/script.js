let editingEmployeeId = null;
let employeesData = {}; // Храним актуальный словарь сотрудников в памяти

// 1. Загружаем и отрисовываем таблицу сразу при открытии страницы
document.addEventListener('DOMContentLoaded', async () => {
    await loadEmployees();
});

// 2. Единый обработчик отправки формы (и для создания, и для редактирования)
document.getElementById('employees-form').addEventListener('submit', async (event) => {
    event.preventDefault(); // Предотвращаем перезагрузку страницы

    const firstNameInput = document.getElementById('first-name-input');
    const lastNameInput = document.getElementById('last-name-input');
    const statusSelect = document.getElementById('status-select');

    const payload = {
        first_name: firstNameInput.value.trim(),
        last_name: lastNameInput.value.trim(),
        status: statusSelect.value
    };

    const url = editingEmployeeId ? `/employees/${editingEmployeeId}` : '/employees';
    const method = editingEmployeeId ? 'PATCH' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            // Сбрасываем режим редактирования обратно в режим добавления
            editingEmployeeId = null;

            // Безопасно меняем текст заголовка и кнопки, только если у них заданы id в HTML
            const formTitle = document.getElementById('form-title');
            if (formTitle) formTitle.textContent = 'Принять нового сотрудника';

            const submitBtn = document.getElementById('form-submit-btn');
            if (submitBtn) submitBtn.textContent = 'Оформить';

            event.target.reset();  // Очищаем поля формы
            await loadEmployees(); // Перерисовываем таблицу без перезагрузки страницы
        } else {
            const err = await response.json();
            console.error('Ошибка сервера:', err);
            alert('Ошибка при сохранении: ' + JSON.stringify(err.detail));
        }
    } catch (error) {
        console.error('Ошибка сети:', error);
    }
});

// 3. Срабатывает при клике на зелёную кнопку «Редактировать» в таблице
function startEdit(id) {
    const emp = employeesData[id];
    if (!emp) {
        console.warn('Сотрудник не найден в кэше:', id);
        return;
    }

    editingEmployeeId = id;

    // Подставляем данные сотрудника в поля формы
    document.getElementById('first-name-input').value = emp.first_name;
    document.getElementById('last-name-input').value = emp.last_name;
    document.getElementById('status-select').value = emp.status;

    // Безопасно меняем заголовок и текст кнопки (если элементы с такими id есть)
    const formTitle = document.getElementById('form-title');
    if (formTitle) formTitle.textContent = 'Редактировать сотрудника';

    const submitBtn = document.getElementById('form-submit-btn');
    if (submitBtn) submitBtn.textContent = 'Добавить';
}


// Вспомогательная функция: превращает "2026-11-14" в "14.11.26"
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const [year, month, day] = dateStr.split('-');
    return `${day}.${month}.${year.slice(-2)}`;
}


// 4. Запрос актуального списка и перерисовка таблицы
async function loadEmployees() {
    const response = await fetch('/api/employees');
    if (!response.ok) return;

    employeesData = await response.json();
    const tbody = document.getElementById('employees-tbody');
    if (!tbody) {
        console.error('В HTML не найден элемент <tbody id="employees-tbody">');
        return;
    }

    tbody.innerHTML = ''; // Очищаем старый список

    const entries = Object.values(employeesData);
    if (entries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-table-msg">Сотрудников пока нет.</td></tr>';
        return;
    }

    entries.forEach(emp => {
        const isFired = emp.status === 'уволен';
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="${isFired ? 'fired-name' : ''}">${emp.first_name} ${emp.last_name}</td>
            <td>${emp.status}</td>
            <td>${emp.base_salary.toLocaleString('ru-RU')}</td>
            <td>${emp.hours_plan}</td>
            <td>${formatDate(emp.hire_date)}</td>
            <td>${formatDate(emp.fire_date) ?? '-'}</td>
            <td class="actions-wrapper">
                <button type="button" class="btn-action btn-edit" data-tooltip="редактировать" aria-label="редактировать" onclick="startEdit('${emp.employee_id}')"></button>
                <button type="button" class="btn-action btn-fire" data-tooltip="уволить" aria-label="уволить" onclick="fireEmployee('${emp.employee_id}')"></button>
                <button type="button" class="btn-action btn-delete" data-tooltip="удалить" aria-label="удалить" onclick="deleteEmployee('${emp.employee_id}')"></button>
            </td>
        `;
        tbody.appendChild(row);
    });
}


// Увольнение сотрудника по клику на оранжевую кнопку
async function fireEmployee(id) {
    const emp = employeesData[id];
    if (!emp || emp.status === 'уволен') return; // Если уже уволен — ничего не делаем

    try {
        const response = await fetch(`/employees/${id}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: 'уволен' })
        });

        if (response.ok) {
            await loadEmployees(); // Перерисовываем таблицу с новыми данными
        } else {
            console.error('Ошибка при увольнении:', response.status);
        }
    } catch (error) {
        console.error('Ошибка сети:', error);
    }
}


// Удаление сотрудника по клику на красную кнопку
async function deleteEmployee(id) {
    const emp = employeesData[id];
    const fullName = emp ? `${emp.first_name} ${emp.last_name}` : 'сотрудника';

    // Спрашиваем подтверждение перед удалением
    if (!confirm(`Удалить ${fullName} из списка?`)) {
        return; // Если нажали «Отмена» — выходим
    }

    try {
        const response = await fetch(`/employees/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            // Если удалили сотрудника, который сейчас открыт в форме редактирования — сбрасываем форму
            if (editingEmployeeId === id) {
                editingEmployeeId = null;
                document.getElementById('form-title').textContent = 'Принять нового сотрудника';
                document.getElementById('employees-form').reset();
            }

            await loadEmployees(); // Перерисовываем таблицу без удалённой строки
        } else {
            console.error('Ошибка при удалении:', response.status);
        }
    } catch (error) {
        console.error('Ошибка сети:', error);
    }
}