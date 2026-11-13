from uuid import uuid4 # позволяет генерировать уникальные id
from datetime import date

from fastapi import FastAPI, Request
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

# 1. Ограничиваем возможные значения статуса
class EmployeeStatus(str, Enum):
    INTERN = "стажёр"
    MANAGER = "менеджер"
    LEAD_MANAGER = "ведущий менеджер"

# 2. Задаем настройки для каждого статуса в одном месте
STATUS_CONFIG = {
    EmployeeStatus.INTERN: {"base_salary": 30000, "hours_plan": 5},
    EmployeeStatus.MANAGER: {"base_salary": 50000, "hours_plan": 6},
    EmployeeStatus.LEAD_MANAGER: {"base_salary": 60000, "hours_plan": 6},
}

# 1. Описываем схему ожидаемого Payload
class EmployeeSchema(BaseModel):
    # FastAPI проверит, чтобы в JSON обязательно были указанные поля
    first_name: str = Field(..., min_length=2, description="Имя сотрудника")
    last_name: str = Field(..., min_length=2, description="Фамилия сотрудника")
    status: EmployeeStatus
    fire_date: date | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_only_letters(cls, value: str) -> str:
        cleaned_value = value.strip()
        if len(cleaned_value) < 2:
            raise ValueError("Длина должна быть не менее 2 символов")
        if not re.fullmatch(r"[А-Яа-яЁёA-Za-z\-]+", cleaned_value):
            raise ValueError("Поле должно содержать только буквы")
        return cleaned_value

@app.get("/", response_class=HTMLResponse)
async def employees(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="employees.html",
        context={"employees": EMPLOYEES_DB}
        )

# Дополнительный API-эндпоинт для получения списка сотрудников в формате JSON
@app.get("/api/employees")
async def get_employees():
    return EMPLOYEES_DB

# Роут для Графика работы
@app.get("/schedule", response_class=HTMLResponse)
async def schedule_page(request: Request):
    return templates.TemplateResponse(request=request, name="schedule.html")

# Роут для Продаж
@app.get("/sales", response_class=HTMLResponse)
async def sales_page(request: Request):
    return templates.TemplateResponse(request=request, name="sales.html")

# Роут для Зарплаты
@app.get("/salary", response_class=HTMLResponse)
async def salary_page(request: Request):
    return templates.TemplateResponse(request=request, name="salary.html")

# Роут для Достижений
@app.get("/achievements", response_class=HTMLResponse)
async def achievements_page(request: Request):
    return templates.TemplateResponse(request=request, name="achievements.html")

# 2. Принимаем Payload (передаем схему в аргументы функции)
@app.post("/employees")
async def create_task(employee: EmployeeSchema):
    # Достаем параметры по ключу статуса
    conditions = STATUS_CONFIG[employee.status]
    emp_id = str(uuid4())

    # Доступ к данным payload осуществляется через точку: task.title
    # print(f"Получен JSON Payload. Заголовок: {employee.first_name} {employee.last_name}")

    new_employee = {
        "id": emp_id,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "status": employee.status.value,
        "hire_date": str(date.today()),
        "fire_date": employee.fire_date,
        "base_salary": conditions["base_salary"],
        "hours_plan": conditions["hours_plan"],
    }

    # Сохраняем в словарь по ключу id
    EMPLOYEES_DB[emp_id] = new_employee

    return new_employee