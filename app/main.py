from uuid import uuid4 # позволяет генерировать уникальные id
from datetime import date

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

MAX_ACTIVE_EMPLOYEES = 5

# 1. Ограничиваем возможные значения статуса
class EmployeeStatus(str, Enum):
    INTERN = "стажёр"
    MANAGER = "менеджер"
    LEAD_MANAGER = "ведущий менеджер"
    FIRED = "уволен"

# 2. Задаем настройки для каждого статуса в одном месте
STATUS_CONFIG = {
    EmployeeStatus.INTERN: {"base_salary": 30000, "hours_plan": 5},
    EmployeeStatus.MANAGER: {"base_salary": 50000, "hours_plan": 6},
    EmployeeStatus.LEAD_MANAGER: {"base_salary": 60000, "hours_plan": 6},
    EmployeeStatus.FIRED: {"base_salary": 0, "hours_plan": 0},
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

# Отображение страницы с графиком работы
@app.get("/schedule", response_class=HTMLResponse)
async def schedule_page(request: Request):
    return templates.TemplateResponse(request=request, name="schedule.html")

# Отображение страницы с планом и фактом продаж
@app.get("/sales", response_class=HTMLResponse)
async def sales_page(request: Request):
    return templates.TemplateResponse(request=request, name="sales.html")

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
    # Считаем всех текущих сотрудников, у которых статус НЕ "уволен"
    active_count = sum(1 for emp in EMPLOYEES_DB.values() if emp.status != EmployeeStatus.FIRED)
    if active_count >= MAX_ACTIVE_EMPLOYEES:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя оформить больше {MAX_ACTIVE_EMPLOYEES} работающих сотрудников"
        )

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
        hours_plan=conditions["hours_plan"]
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
        active_count = sum(
            1 for emp in EMPLOYEES_DB.values() if emp.status != EmployeeStatus.FIRED
        )
        if active_count >= MAX_ACTIVE_EMPLOYEES:
            raise HTTPException(
                status_code=400,
                detail=f"В штате уже максимум работающих сотрудников"
            )

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
