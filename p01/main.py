from fastapi import FastAPI
from fastapi import HTTPException, Request
from typing import Any
from fastapi.responses import JSONResponse
app = FastAPI()

#test problem 1:

@app.get("/ping" , status_code = 200) #we use to depict fixed status code
def check_ping():
    return{"message" : "pong"}

@app.get("/hello/{name}" , status_code = 200)
def greet_name(name : str): #same variable name as in the path we call name as path parameter
    return {"greeting" : f"Hello, {name}"}

#query parameter is the value that we pass in the url after ?
@app.get("/add" , status_code = 200)
def add(a : int | float, b : int | float):
    if type(a) not in (int , float) or type(b) not in (int , float):
        raise HTTPException(
            status_code = 422,
            detail = "invalid input,correct format is int/float , int/float"
        )
    return{"sum" : a + b}

@app.get("/square/{n}")
def square(n : int):
    if type(n) not in (int,):
        raise HTTPException(
            status_code = 422,
            detail = "input must be an integer"
        )
    return{"result" : n * n}

@app.post("/echo", status_code = 200)
def echo(request : dict):
    data = request
    return data

@app.get("/health" , status_code = 200)
def check_health():
    return{"status" : "ok"}

# @app.exception_handler(404) #fastapi does this automatically but if u have to do it manually then this is the way
# def not_found(request , exc):
#     return JSONResponse(
#         status_code = 404,
#         content = {"error" : "route not found"}
#     )