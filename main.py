from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, inspect, text

import os
import traceback
from dotenv import load_dotenv
from tabulate import tabulate  

load_dotenv()

# ----- Database Set- Up ----

DATABASE_URL = "postgresql://keinfinalact_user:IahgbbbF5EJAwkb4G0lEV5YWYoCxvMe2@dpg-d0a2tc15pdvs73bkm630-a.singapore-postgres.render.com/keinfinalact"
print("Culanggo, Kein Jake")
try:
    engine = create_engine(DATABASE_URL, client_encoding='utf8')
    print("Database engine created successfully")
    connection = engine.connect()
    print("Database connection established successfully")
    inspector = inspect(engine)
    print("Database inspector created successfully")
except Exception as e:
    print("Error connecting to database:", str(e))
    print("Full error:", traceback.format_exc())
    raise

# Create tables
try:
    connection.execute(
        text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            );

            -- Alter the table to change deadline type or create with VARCHAR
            DROP TABLE IF EXISTS tasks;
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                task VARCHAR(255) NOT NULL,
                deadline VARCHAR(255) NOT NULL,
                username VARCHAR(255) NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS kein ();
        """)
    )
    connection.commit()
    print("Tables created successfully")
except Exception as e:
    print("Error creating tables:", traceback.format_exc())
    connection.rollback()

# Pretty print startup data using tabulate
print("Tables:")
for table in inspector.get_table_names():
    print(f"  - {table}")

print("\nUsers:")
try:
    users_result = connection.execute(text("SELECT * FROM users"))
    users = [dict(row) for row in users_result.mappings()]
    print(tabulate(users, headers="keys", tablefmt="grid"))
except Exception as e:
    print("User query error:", traceback.format_exc())
    connection.rollback()

print("\nTasks:")
try:
    tasks_result = connection.execute(text("SELECT * FROM tasks"))
    tasks = [dict(row) for row in tasks_result.mappings()]
    print(tabulate(tasks, headers="keys", tablefmt="grid"))
except Exception as e:
    print("Task query error:", traceback.format_exc())
    connection.rollback()

# API setup

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class User(BaseModel):
    username: str
    password: str

class Task(BaseModel):
    task: str
    deadline: str  # can now be any string like "everyday"
    user: str

@app.post("/login/")
async def user_login(user: User):
    try:
        result = connection.execute(
            text("""
                SELECT * FROM users
                WHERE username = :username AND password = :password;
            """).bindparams(username=user.username, password=user.password)
        )
        if not result.mappings().all():
            return {"status": "User Not Found!"}
        return {"status": "Logged in"}
    except Exception as e:
        print("Login error:", traceback.format_exc())
        connection.rollback()
        raise HTTPException(status_code=500, detail="Error during login.")

@app.post("/create_user/")
async def create_user(user: User):
    try:
        result = connection.execute(
            text("SELECT * FROM users WHERE username = :username;")
            .bindparams(username=user.username)
        )
        if result.mappings().all():
            raise HTTPException(status_code=400, detail="User already exists!")

        connection.execute(
            text("INSERT INTO users (username, password) VALUES (:username, :password);")
            .bindparams(username=user.username, password=user.password)
        )
        connection.commit()

        # Return updated user list
        users_result = connection.execute(text("SELECT * FROM users"))
        users = [dict(row) for row in users_result.mappings()]
        return {"status": "User Created!", "users": users}
    except Exception as e:
        print("Create user error:", traceback.format_exc())
        connection.rollback()
        raise HTTPException(status_code=500, detail="Error creating user.")

@app.post("/create_task/")
async def create_task(task: Task):
    try:
        user_check = connection.execute(
            text("SELECT * FROM users WHERE username = :username;")
            .bindparams(username=task.user)
        )
        if not user_check.mappings().all():
            return {"status": "User Not Found!"}

        # Check if task already exists for user
        duplicate_check = connection.execute(
            text("""
                SELECT * FROM tasks
                WHERE task = :task AND deadline = :deadline AND username = :user;
            """).bindparams(task=task.task, deadline=task.deadline, user=task.user)
        )
        if duplicate_check.mappings().all():
            return {"status": "Duplicate Task — Not Added."}

        # Insert new task
        connection.execute(
            text("""
                INSERT INTO tasks (task, deadline, username)
                VALUES (:task, :deadline, :user);
            """).bindparams(task=task.task, deadline=task.deadline, user=task.user)
        )
        connection.commit()

        # Return updated task list
        tasks_result = connection.execute(
            text("SELECT id, task, deadline, username FROM tasks WHERE username = :user")
            .bindparams(user=task.user)
        )
        tasks = [dict(row) for row in tasks_result.mappings()]
        return {"status": "Task Created!", "tasks": tasks}
    except Exception as e:
        print("Create task error:", traceback.format_exc())
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating task: {str(e)}")

@app.get("/get_tasks/")
async def get_tasks(name: str):
    try:
        user_check = connection.execute(
            text("SELECT * FROM users WHERE username = :username;")
            .bindparams(username=name)
        )
        if not user_check.mappings().all():
            return {"status": "User Not Found!"}
    except Exception as e:
        print("User check error:", traceback.format_exc())
        connection.rollback()
        return {"status": "Error checking user!"}

    try:
        result = connection.execute(
            text("SELECT task, deadline FROM tasks WHERE username = :username;")
            .bindparams(username=name)
        )
        tasks = [dict(row) for row in result.mappings()]
        return {"tasks": tasks}
    except Exception as e:
        print("Fetch tasks error:", traceback.format_exc())
        connection.rollback()
        return {"status": "Error fetching tasks!"}
