from uuid import uuid4 # позволяет генерировать уникальные id
from datetime import date
import random

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import re


app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

# Временное хранилище сотрудников (словарь: {id: данные_сотрудника})
EMPLOYEES_DB: dict[str, dict] = {}

# Временное хранилище графика: {employee_id: [True, False, ... (10 элементов)]}
SCHEDULE_DB: dict[str, list[bool]] = {}

# Временное хранилище итоговых продаж и детализации по периодам
# Формат: {emp_id: {"periods": [int | None, ...], "total": int}}
SALES_DB: dict[str, dict] = {}

MAX_ACTIVE_EMPLOYEES = 5

# 1. Ограничиваем возможные значения статуса
class EmployeeStatus(str, Enum):
    INTERN = "стажёр"
    MANAGER = "менеджер"
    LEAD_MANAGER = "ведущий менеджер"
    FIRED = "уволен"

# 2. Задаем настройки для каждого статуса в одном месте
STATUS_CONFIG = {
    EmployeeStatus.INTERN: {"base_salary": 30000, "hours_plan": 5, "sales_plan": 50000},
    EmployeeStatus.MANAGER: {"base_salary": 50000, "hours_plan": 6, "sales_plan": 100000},
    EmployeeStatus.LEAD_MANAGER: {"base_salary": 60000, "hours_plan": 6, "sales_plan": 120000},
    EmployeeStatus.FIRED: {"base_salary": 0, "hours_plan": 0, "sales_plan": 0},
}

# Диапазоны случайных значений для расчёта продаж по статусам
SALES_RANGES = {
    EmployeeStatus.INTERN: (5000, 14000),
    EmployeeStatus.MANAGER: (12000, 21000),
    EmployeeStatus.LEAD_MANAGER: (15000, 24000),
}


# задаём сущность "сотрудник", где указываем все поля (переменные), которые должны должны быть у сотрудника
class EmployeeSchema(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    status: EmployeeStatus
    hire_date: date
    fire_date: date | None = None
    base_salary: int
    hours_plan: int
    sales_plan: int


# Pydantic-схема для валидации графика одного сотрудника
class EmployeeScheduleSchema(BaseModel):
    employee_id: str
    periods: list[bool] = Field(
        ...,
        min_length=10,
        max_length=10,
        description="Список из 10 булевых значений (работает/не работает)"
    )

    @field_validator("periods")
    @classmethod
    def check_at_least_one_shift(cls, value: list[bool]) -> list[bool]:
        if not any(value):
            raise ValueError("График заполнен некорректно: у каждого сотрудника должна быть хоть одна смена")
        return value


# Pydantic-схема. Здесь мы описываем те переменные, которые мы
# должны получить от сайта при заведении нового сотрудника
class EmployeeCreateSchema(BaseModel):
    # FastAPI проверит, чтобы в JSON обязательно были указанные поля
    first_name: str = Field(..., min_length=2, description="Имя сотрудника")
    last_name: str = Field(..., min_length=2, description="Фамилия сотрудника")
    status: EmployeeStatus
    fire_date: date | None = None

    # Проверяем корректность введённых данных в поля
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_only_letters(cls, value: str) -> str:
        cleaned_value = value.strip()
        if len(cleaned_value) < 2:
            raise ValueError("Длина должна быть не менее 2 символов")
        if not re.fullmatch(r"[А-Яа-яЁёA-Za-z\-]+", cleaned_value):
            raise ValueError("Поле должно содержать только буквы")
        return cleaned_value

    # Проверка, чтобы нельзя было принять сотрудника со статусом "уволен" -- ВОЗМОЖНО ИЗЛИШНЯЯ ПРОВЕРКА
    @field_validator("status")
    @classmethod
    def forbid_fired_on_hire(cls, value: EmployeeStatus) -> EmployeeStatus:
        if value == EmployeeStatus.FIRED:
            raise ValueError("Нельзя принять нового сотрудника со статусом 'уволен'")
        return value


# Pydantic-схема. Здесь мы описываем те переменные, которые мы должны
# получить от сайта при редактировании данных сотрудника
class EmployeeUpdateSchema(BaseModel):
    # здесь, в отличии от EmployeeCreateSchema, обязательно указаываем, что
    # поле может быть передано или может быть не передано
    first_name: str | None = Field(None, min_length=2, description="Имя сотрудника")
    last_name: str | None = Field(None, min_length=2, description="Фамилия сотрудника")
    status: EmployeeStatus | None = None

    # Проверяем корректность введённых данных в поля
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_only_letters(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned_value = value.strip()
        if len(cleaned_value) < 2:
            raise ValueError("Длина должна быть не менее 2 символов")
        if not re.fullmatch(r"[А-Яа-яЁёA-Za-z\-]+", cleaned_value):
            raise ValueError("Поле должно содержать только буквы")
        return cleaned_value


def get_active_employees(
        db: dict[str, EmployeeSchema] = EMPLOYEES_DB,
        ) -> dict[str, EmployeeSchema]:
    return {
        emp_id: emp
        for emp_id, emp in db.items()
        if emp.status != EmployeeStatus.FIRED
    }


def check_active_employees_limit(
    detail: str = f"Нельзя оформить больше {MAX_ACTIVE_EMPLOYEES} работающих сотрудников",
) -> None:
    if len(get_active_employees()) >= MAX_ACTIVE_EMPLOYEES:
        raise HTTPException(status_code=400, detail=detail)


# Выводим данные о сотрудниках на страницу сайта. Эта фнукция нужна для передачи информации браузеру (html)
@app.get("/", response_class=HTMLResponse)
async def employees(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="employees.html",
        context={"employees": EMPLOYEES_DB}
        )

# Дополнительный API-эндпоинт для получения списка сотрудников в формате JSON.
# Эта фнукция нужна для передачи информации JS
# В проекте его вызывает JavaScript-функция loadEmployees() сразу после того, как вы нажали кнопку «Добавить»
@app.get("/api/employees")
async def get_employees():
    return EMPLOYEES_DB

# Отображение страницы с зарплатой
@app.get("/salary", response_class=HTMLResponse)
async def salary_page(request: Request):
    return templates.TemplateResponse(request=request, name="salary.html")

# Отображение страницы с достижениями
@app.get("/achievements", response_class=HTMLResponse)
async def achievements_page(request: Request):
    return templates.TemplateResponse(request=request, name="achievements.html")

# 2. Принимаем Payload (передаем схему в аргументы функции)
@app.post("/employees")
async def create_employee(employee: EmployeeCreateSchema) -> EmployeeSchema:
    check_active_employees_limit()

    # Достаем параметры по ключу статуса
    conditions = STATUS_CONFIG[employee.status]
    emp_id = str(uuid4())

    new_employee = EmployeeSchema(
        employee_id=emp_id,
        first_name=employee.first_name,
        last_name=employee.last_name,
        status=employee.status.value,
        hire_date=str(date.today()),
        fire_date=None,
        base_salary=conditions["base_salary"],
        hours_plan=conditions["hours_plan"],
        sales_plan=conditions["sales_plan"]
    )

    # Сохраняем в словарь по ключу id
    EMPLOYEES_DB[emp_id] = new_employee

    return new_employee


@app.patch("/employees/{employee_id}", response_model=EmployeeSchema)
async def update_employee(employee_id: str, employee: EmployeeUpdateSchema):
    if employee_id not in EMPLOYEES_DB:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    stored_employee = EMPLOYEES_DB[employee_id]

    # Если сотрудник был уволен, а его пытаются вернуть в штат — проверяем лимит
    if (
        employee.status is not None
        and stored_employee.status == EmployeeStatus.FIRED
        and employee.status != EmployeeStatus.FIRED
    ):
        check_active_employees_limit()

    # 2. Обновляем имя и фамилию, если они переданы
    if employee.first_name is not None:
        stored_employee.first_name = employee.first_name
    if employee.last_name is not None:
        stored_employee.last_name = employee.last_name

    # 3. Обновляем статус и пересчитываем зарплату и норму часов
    if employee.status is not None:
        stored_employee.status = employee.status
        conditions = STATUS_CONFIG[employee.status]
        stored_employee.base_salary = conditions["base_salary"]
        stored_employee.hours_plan = conditions["hours_plan"]

        # Если статус стал "уволен" — ставим сегодняшнюю дату, иначе сбрасываем
        if employee.status == EmployeeStatus.FIRED:
            stored_employee.fire_date = date.today()
        else:
            stored_employee.fire_date = None

    return stored_employee


@app.delete("/employees/{employee_id}", response_model=EmployeeSchema)
async def delete_employee(employee_id: str):
    if employee_id not in EMPLOYEES_DB:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    deleted_employee = EMPLOYEES_DB.pop(employee_id)

    return deleted_employee



# 2. Обновляем рендер страницы: передаём только НЕ уволенных сотрудников и текущий график
@app.get("/schedule", response_class=HTMLResponse)
async def schedule_page(request: Request):
    active_employees = get_active_employees()
    return templates.TemplateResponse(
        request=request,
        name="schedule.html",
        context={
            "employees": active_employees,
            "schedule": SCHEDULE_DB
        }
    )


# 3. API-эндпоинт для сохранения графика
@app.post("/api/schedule")
async def save_schedule(items: list[EmployeeScheduleSchema]):
    for item in items:
        if item.employee_id not in EMPLOYEES_DB:
            raise HTTPException(
                status_code=404,
                detail=f"Сотрудник с ID {item.employee_id} не найден"
            )
        SCHEDULE_DB[item.employee_id] = item.periods

    return {"status": "ok", "saved_count": len(items)}


# Обновляем рендер страницы продаж (передаём сохранённые данные, если уже нажимали «Сформировать»)
@app.get("/sales", response_class=HTMLResponse)
async def sales_page(request: Request):
    active_employees = get_active_employees()
    total_plan = sum(emp.sales_plan for emp in active_employees.values())
    company_sales = sum(
        SALES_DB[emp_id]["total"]
        for emp_id in active_employees
        if emp_id in SALES_DB
    )

    # Считаем сумму продаж по каждому из 10 периодов
    period_totals = [0] * 10
    for emp_id in active_employees:
        if emp_id in SALES_DB:
            for i, val in enumerate(SALES_DB[emp_id]["periods"]):
                if val is not None:
                    period_totals[i] += val

    return templates.TemplateResponse(
        request=request,
        name="sales.html",
        context={
            "employees": active_employees,
            "sales": SALES_DB,
            "total_plan": total_plan,
            "company_sales": company_sales,
            "period_totals": period_totals,
        }
    )


# Эндпоинт генерации и сохранения факта продаж по нажатию кнопки «Сформировать»
@app.post("/api/sales/generate")
async def generate_sales():
    active_employees = get_active_employees()

    if not active_employees:
        raise HTTPException(status_code=400, detail="Нет активных сотрудников")

    # Проверяем, что для всех работающих сотрудников заполнен график
    missing_schedule = [
        f"{emp.first_name} {emp.last_name}"
        for emp_id, emp in active_employees.items()
        if emp_id not in SCHEDULE_DB
    ]
    if missing_schedule:
        raise HTTPException(
            status_code=400,
            detail=f"Сначала сформируйте график работы для: {', '.join(missing_schedule)}"
        )

    plan_rows = []
    fact_rows = []
    total_company_plan = 0
    total_company_sales = 0
    period_totals = [0] * 10  # <-- Суммы по каждому из 10 периодов

    for emp_id, emp in active_employees.items():
        full_name = f"{emp.first_name} {emp.last_name}"
        total_company_plan += emp.sales_plan

        plan_rows.append({
            "employee_id": emp_id,
            "full_name": full_name,
            "status": emp.status.value,
            "sales_plan": emp.sales_plan,
        })

        # Расчёт факта продаж по 10 периодам
        schedule_periods = SCHEDULE_DB[emp_id]
        min_val, max_val = SALES_RANGES[emp.status]
        emp_periods = []
        emp_total = 0

        for idx, is_working in enumerate(schedule_periods):
            if is_working:
                val1 = random.randint(min_val, max_val)
                val2 = random.randint(min_val, max_val)
                sale_amount = round((val1 + val2) / 2)
                emp_periods.append(sale_amount)
                emp_total += sale_amount
                period_totals[idx] += sale_amount  # <-- Прибавляем к итогу периода
            else:
                emp_periods.append(None)

        # Сохраняем данные на сервере
        SALES_DB[emp_id] = {
            "periods": emp_periods,
            "total": emp_total,
        }

        total_company_sales += emp_total
        fact_rows.append({
            "employee_id": emp_id,
            "full_name": full_name,
            "periods": emp_periods,
            "total": emp_total,
        })

    return {
        "plan_rows": plan_rows,
        "total_company_plan": total_company_plan,
        "fact_rows": fact_rows,
        "period_totals": period_totals,  # <-- Возвращаем на фронтенд
        "total_company_sales": total_company_sales,
    }


# Эндпоинт генерации и сохранения зарплаты по нажатию кнопки «Сформировать»
@app.post("/api/salary/generate")
async def generate_sales():
    active_employees = get_active_employees()
    
    if not active_employees:
        raise HTTPException(status_code=400, detail="Нет активных сотрудников")

    # Проверяем, что для всех работающих сотрудников заполнен график
    missing_schedule = [
        f"{emp.first_name} {emp.last_name}"
        for emp_id, emp in active_employees.items()
        if emp_id not in SCHEDULE_DB
    ]
    if missing_schedule:
        raise HTTPException(
            status_code=400,
            detail=f"Сначала сформируйте график работы для: {', '.join(missing_schedule)}"
        )

    # Проверяем, что для всех работающих сотрудников сформированы продажи
    if len(SALES_DB) == 0:
        raise HTTPException(
            status_code=400,
            detail = f"Сначала сформируйте продажи"
        )

    kpi_rows = []
    total_company_plan = 0
    total_company_fact = 0

    # Формируем список с id, ФИО, должностью и планом продаж по кажому сотруднику
    for emp_id, emp in active_employees.items():
            full_name = f"{emp.first_name} {emp.last_name}"
            total_company_plan += emp.sales_plan
            sales_fact = SALES_DB[id]["total"]
            total_company_fact += sales_fact
            percent_sales = int(round(sales_fact / emp.sales_plan * 100))
            hours_fact = sum(SCHEDULE_DB[id])
            differ_hours = hours_fact - emp.hours_plan
    
            kpi_rows.append({
                "employee_id": emp_id,
                "full_name": full_name,
                "status": emp.status.value,
                "sales_plan": emp.sales_plan,
                "hours_plan": emp.hours_plan,
                "base_salary": emp.base_salary,
                "sales_fact": sales_fact,
                "percent_sales": percent_sales,
                "hours_fact": hours_fact,
                "differ_hours": differ_hours,
            })

    total_percent = int(round(total_company_fact / total_company_plan * 100))

    return {
        "kpi_rows": kpi_rows,
        "total_company_plan": total_company_plan,
        "total_company_fact": total_company_fact,
        "total_percent": total_percent,
    }