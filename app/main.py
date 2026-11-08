from uuid import uuid4 # позволяет генерировать уникальные id

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 1. Описываем схему ожидаемого Payload
class EmployeeSchema(BaseModel):
    name: str  # FastAPI проверит, чтобы в JSON обязательно было поле "title" (строка)

@app.get("/")
async def welcome():
    return FileResponse("app/static/index.html")

# 2. Принимаем Payload (передаем схему в аргументы функции)
@app.post("/employees")
async def create_task(employee: EmployeeSchema):
    employee_id = str(uuid4())

    # Доступ к данным payload осуществляется через точку: task.title
    print(f"Получен JSON Payload. Заголовок: {employee.name}")

    return {
        "status": "success",
        "id": employee_id,
        "name": employee.name
    }