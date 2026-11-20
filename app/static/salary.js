document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generate-salary-btn');
    if (!generateBtn) return;

    const formatNumber = (num) => Number(num).toLocaleString('ru-RU');

    generateBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/api/salary/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) {
                const err = await response.json();
                alert(err.detail || 'Ошибка при расчёте зарплаты');
                return;
            }

            const data = await response.json();

            const t1 = document.getElementById('personal-sales-tbody');
            const t2 = document.getElementById('hours-bonus-tbody');
            const t3 = document.getElementById('company-sales-tbody');
            const t4 = document.getElementById('total-salary-tbody');

            t1.innerHTML = '';
            t2.innerHTML = '';
            t3.innerHTML = '';
            t4.innerHTML = '';

            data.kpi_rows.forEach(row => {
                // 1. Личный план продаж
                t1.insertAdjacentHTML('beforeend', `
                    <tr>
                        <td>${row.full_name}</td>
                        <td>${row.status}</td>
                        <td>${formatNumber(row.sales_plan)}</td>
                        <td>${formatNumber(row.sales_fact)}</td>
                        <td>${row.percent_sales}%</td>
                        <td>${formatNumber(row.employee_sales_bonus)}</td>
                    </tr>
                `);

                // 2. Норма часов
                const differText = row.differ_hours > 0 ? `+${row.differ_hours}` : row.differ_hours;
                t2.insertAdjacentHTML('beforeend', `
                    <tr>
                        <td>${row.full_name}</td>
                        <td>${row.status}</td>
                        <td>${row.hours_plan}</td>
                        <td>${row.hours_fact}</td>
                        <td>${differText}</td>
                        <td>${formatNumber(row.employee_hours_bonus)}</td>
                    </tr>
                `);

                // 3. Общий план продаж
                t3.insertAdjacentHTML('beforeend', `
                    <tr>
                        <td>${row.full_name}</td>
                        <td>${row.status}</td>
                        <td>${formatNumber(data.total_company_plan)}</td>
                        <td>${formatNumber(data.total_company_fact)}</td>
                        <td>${data.total_company_percent}%</td>
                        <td>${formatNumber(data.company_sales_bonus)}</td>
                    </tr>
                `);

                // 4. Итоговая зарплата
                t4.insertAdjacentHTML('beforeend', `
                    <tr>
                        <td>${row.full_name}</td>
                        <td>${row.status}</td>
                        <td>${formatNumber(row.base_salary)}</td>
                        <td>${formatNumber(row.bonus_salary)}</td>
                        <td><strong>${formatNumber(row.total_salary)}</strong></td>
                    </tr>
                `);
            });

            document.getElementById('salary-tables-wrapper').style.display = 'block';
        } catch (error) {
            console.error('Ошибка сети:', error);
            alert('Не удалось связаться с сервером.');
        }
    });
});
