document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generate-sales-btn');
    if (!generateBtn) return;

    const formatNumber = (num) => num.toLocaleString('ru-RU');

    generateBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/api/sales/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) {
                const err = await response.json();
                alert(err.detail || 'Ошибка при формировании продаж');
                return;
            }

            const data = await response.json();

            // 1. Заполняем таблицу "План продаж"
            const planTbody = document.getElementById('sales-plan-tbody');
            planTbody.innerHTML = '';

            data.plan_rows.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${row.full_name}</td>
                    <td>${row.status}</td>
                    <td>${formatNumber(row.sales_plan)}</td>
                `;
                planTbody.appendChild(tr);
            });

            const planSummaryTr = document.createElement('tr');
            planSummaryTr.className = 'summary-row';
            planSummaryTr.innerHTML = `
                <td colspan="2">План по компании</td>
                <td>${formatNumber(data.total_company_plan)}</td>
            `;
            planTbody.appendChild(planSummaryTr);

            // 2. Заполняем таблицу "Факт продаж"
            const factTbody = document.getElementById('sales-fact-tbody');
            factTbody.innerHTML = '';

            data.fact_rows.forEach(row => {
                const tr = document.createElement('tr');
                const periodsCells = row.periods
                    .map(val => `<td class="sales-num">${val !== null ? formatNumber(val) : ''}</td>`)
                    .join('');

                tr.innerHTML = `
                    <td>${row.full_name}</td>
                    ${periodsCells}
                    <td><strong>${formatNumber(row.total)}</strong></td>
                `;
                factTbody.appendChild(tr);
            });

            const summaryPeriodsCells = data.period_totals
                .map(pTotal => `<td class="sales-num">${pTotal > 0 ? formatNumber(pTotal) : ''}</td>`)
                .join('');

            const factSummaryTr = document.createElement('tr');
            factSummaryTr.className = 'summary-row';
            factSummaryTr.innerHTML = `
                <td>Продажи по компании</td>
                ${summaryPeriodsCells}
                <td class="sales-num">${formatNumber(data.total_company_sales)}</td>
            `;
            factTbody.appendChild(factSummaryTr);

            // Показываем блок с таблицами
            document.getElementById('sales-tables-wrapper').style.display = 'block';

        } catch (error) {
            console.error('Ошибка сети:', error);
            alert('Не удалось связаться с сервером.');
        }
    });
});
