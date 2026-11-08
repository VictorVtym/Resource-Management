source .venv/Scripts/activate

# основной файл main.py в корне проекта
uvicorn main:app --port 8000 --reload
# основной файл main.py в папке app
uvicorn app.main:app --port 8000 --reload

git push -u origin main

docker run --name pg_container -e POSTGRES_PASSWORD=admin -d -p 5432:5432 postgres
docker exec -it pg_container psql -U postgres
\q или Ctrl + D
docker stop pg-container
docker compose down -v
docker compose up --build

http://localhost:8080/docs

ssh-keygen -t ed25519 -f ~/.ssh/res_manag_key -C "resourse_managment"
cat ~/.ssh/res_manag_key.pub