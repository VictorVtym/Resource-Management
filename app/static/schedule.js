document.addEventListener('DOMContentLoaded', () => {
    const scheduleForm = document.getElementById('schedule-form');
    if (!scheduleForm) return;

    const saveBtn = document.getElementById('save-schedule-btn');
    const editBtn = document.getElementById('edit-schedule-btn');

    // Отправка и превращение чекбоксов в галочки/прочерки
    scheduleForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const rows = document.querySelectorAll('#schedule-tbody tr');
        const payload = [];

        for (const row of rows) {
            const employeeId = row.dataset.employeeId;
            const cells = row.querySelectorAll('.period-cell');
            const periods = [];

            cells.forEach(cell => {
                const checkbox = cell.querySelector('.period-checkbox');
                const isChecked = checkbox ? checkbox.checked : (cell.dataset.checked === 'true');
                periods.push(isChecked);
            });

            // Проверяем, отмечен ли хотя бы один период (true)
            const hasAtLeastOneShift = periods.some(isWorking => isWorking === true);
            if (!hasAtLeastOneShift) {
                alert('График заполнен некорректно: у каждого сотрудника должна быть хоть одна смена.');
                return; // Останавливаем функцию, запрос на сервер не отправляется
            }

            payload.push({
                employee_id: employeeId,
                periods: periods
            });
        }

        try {
            const response = await fetch('/api/schedule', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                // Заменяем чекбоксы на цветные иконки
                rows.forEach(row => {
                    const cells = row.querySelectorAll('.period-cell');
                    cells.forEach(cell => {
                        const checkbox = cell.querySelector('.period-checkbox');
                        if (!checkbox) return;

                        const isChecked = checkbox.checked;
                        cell.dataset.checked = isChecked;
                        cell.innerHTML = isChecked
                            ? '<span class="status-check">✓</span>'
                            : '<span class="status-dash">—</span>';
                    });
                });

                // Прячем «Отправить», показываем «Редактировать»
                if (saveBtn) saveBtn.style.display = 'none';
                if (editBtn) editBtn.style.display = 'inline-block';
            } else {
                const err = await response.json();
                alert('Ошибка при сохранении: ' + JSON.stringify(err.detail));
            }
        } catch (error) {
            console.error('Ошибка сети:', error);
            alert('Не удалось связаться с сервером.');
        }
    });

    // Возврат обратно в режим редактирования с чекбоксами
    if (editBtn) {
        editBtn.addEventListener('click', () => {
            const cells = document.querySelectorAll('.period-cell');
            cells.forEach(cell => {
                const isChecked = cell.dataset.checked === 'true';
                cell.innerHTML = `<input type="checkbox" class="period-checkbox" ${isChecked ? 'checked' : ''}>`;
            });

            editBtn.style.display = 'none';
            if (saveBtn) saveBtn.style.display = 'inline-block';
        });
    }
});
